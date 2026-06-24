from datetime import datetime, timezone
from typing import Optional, List
import re

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import raise_biz, ErrorCodes
from app.utils.json_helpers import safe_json_load
from app.models.test_scene import TestScene
from app.models.scene_step import SceneStep
from app.models.scene_edge import SceneEdge
from app.models.api_definition import ApiDefinition
from app.schemas.scene import SceneCreate, SceneUpdate


class SceneService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def to_dict(self, scene: TestScene) -> dict:
        return {
            "id": scene.id,
            "project_id": scene.project_id,
            "name": scene.name,
            "category_id": scene.category_id,
            "description": scene.description,
            "env_id": scene.env_id,
            "loop_count": scene.loop_count,
            "thread_count": scene.thread_count,
            "delay": scene.delay,
            "on_failure": scene.on_failure,
            "on_error": scene.on_error,
            "save_detail": scene.save_detail,
            "retry_count": scene.retry_count,
            "global_cookie": scene.global_cookie,
            "save_cookie_to_global": scene.save_cookie_to_global,
            "var_persist_target": scene.var_persist_target,
            "schedule_cron": scene.schedule_cron,
            "schedule_enabled": scene.schedule_enabled,
            "created_at": str(scene.created_at),
            "updated_at": str(scene.updated_at),
        }

    async def get(self, scene_id: int, project_id: int | None = None) -> TestScene:
        from sqlalchemy import and_

        conditions = [TestScene.id == scene_id, TestScene.deleted_at.is_(None)]
        if project_id is not None:
            conditions.append(TestScene.project_id == project_id)
        result = await self.db.execute(select(TestScene).where(and_(*conditions)))
        scene = result.scalar_one_or_none()
        if not scene:
            raise_biz(ErrorCodes.SCENE_NOT_FOUND)
        return scene

    async def get_include_deleted(self, scene_id: int) -> TestScene:
        result = await self.db.execute(
            select(TestScene).where(TestScene.id == scene_id)
        )
        scene = result.scalar_one_or_none()
        if not scene:
            raise_biz(ErrorCodes.SCENE_NOT_FOUND)
        return scene

    async def list(
        self,
        project_id: int,
        keyword: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple:
        query = select(TestScene).where(
            TestScene.project_id == project_id, TestScene.deleted_at.is_(None)
        )
        count_query = select(func.count(TestScene.id)).where(
            TestScene.project_id == project_id, TestScene.deleted_at.is_(None)
        )
        if keyword:
            kw = f"%{re.escape(keyword)}%"
            query = query.where(TestScene.name.ilike(kw))
            count_query = count_query.where(TestScene.name.ilike(kw))
        total = await self.db.scalar(count_query) or 0
        result = await self.db.execute(
            query.order_by(TestScene.updated_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return [self.to_dict(s) for s in result.scalars().all()], total

    async def get_detail(self, scene_id: int) -> dict:
        scene = await self.get(scene_id)
        steps_result = await self.db.execute(
            select(SceneStep)
            .where(SceneStep.scene_id == scene_id)
            .order_by(SceneStep.sort_order)
        )
        edges_result = await self.db.execute(
            select(SceneEdge).where(SceneEdge.scene_id == scene_id)
        )
        steps_raw = steps_result.scalars().all()
        api_ids = [s.api_id for s in steps_raw if s.api_id]
        api_defs: dict[int, tuple[str, str]] = {}
        if api_ids:
            api_result = await self.db.execute(
                select(ApiDefinition).where(ApiDefinition.id.in_(api_ids))
            )
            for a in api_result.scalars().all():
                api_defs[a.id] = (a.method, a.path)

        steps = []
        for s in steps_raw:
            method, path = api_defs.get(s.api_id, (None, None))
            steps.append(
                {
                    "id": s.id,
                    "scene_id": s.scene_id,
                    "node_id": s.node_id,
                    "node_type": s.node_type,
                    "label": s.label,
                    "position_x": s.position_x,
                    "position_y": s.position_y,
                    "api_id": s.api_id,
                    "test_case_id": s.test_case_id,
                    "sort_order": s.sort_order,
                    "enabled": bool(s.enabled),
                    "timeout": s.timeout,
                    "retry_count": s.retry_count,
                    "request_body": s.request_body,
                    "headers": s.headers,
                    "query_params": s.query_params,
                    "assertions": s.assertions,
                    "extract_vars": s.extract_vars,
                    "condition_expression": s.condition_expression,
                    "loop_count": s.loop_count,
                    "loop_variable": s.loop_variable,
                    "wait_duration": s.wait_duration,
                    "wait_mode": getattr(s, "wait_mode", "fixed"),
                    "wait_min": getattr(s, "wait_min", None),
                    "wait_max": getattr(s, "wait_max", None),
                    "parallel_group": getattr(s, "parallel_group", 0),
                    "method": method,
                    "path": path,
                }
            )
        edges = []
        for e in edges_result.scalars().all():
            edges.append(
                {
                    "id": e.id,
                    "scene_id": e.scene_id,
                    "edge_id": e.edge_id,
                    "source_node_id": e.source_node_id,
                    "target_node_id": e.target_node_id,
                    "source_handle": e.source_handle,
                    "label": e.label,
                }
            )
        return {**self.to_dict(scene), "steps": steps, "edges": edges}

    async def create(self, project_id: int, req: SceneCreate) -> TestScene:
        # 检查同项目下是否存在同名场景（排除已软删除的）
        name_dup = await self.db.execute(
            select(TestScene).where(
                TestScene.project_id == project_id,
                TestScene.name == req.name,
                TestScene.deleted_at.is_(None),
            )
        )
        if name_dup.scalar_one_or_none():
            raise_biz(ErrorCodes.SCENE_NAME_DUPLICATE, "场景名称已存在")

        scene = TestScene(
            project_id=project_id,
            name=req.name,
            description=req.description,
            category_id=req.category_id,
            env_id=req.env_id,
            loop_count=req.loop_count,
            thread_count=req.thread_count,
            delay=req.delay,
            on_failure=req.on_failure,
            on_error=req.on_error,
            save_detail=req.save_detail,
            retry_count=req.retry_count,
            global_cookie=req.global_cookie,
            save_cookie_to_global=req.save_cookie_to_global,
            var_persist_target=req.var_persist_target,
        )
        self.db.add(scene)
        await self.db.flush()
        await self.db.refresh(scene)
        await self._save_steps_edges(scene.id, req.steps, req.edges)
        return scene

    async def update(
        self, scene_id: int, req: SceneUpdate, project_id: int | None = None
    ) -> TestScene:
        scene = await self.get(scene_id, project_id)
        if req.name:
            # 检查同项目下是否存在同名场景（排除当前场景自身和已软删除的）
            name_dup = await self.db.execute(
                select(TestScene).where(
                    TestScene.project_id == (project_id or scene.project_id),
                    TestScene.name == req.name,
                    TestScene.id != scene_id,
                    TestScene.deleted_at.is_(None),
                )
            )
            if name_dup.scalar_one_or_none():
                raise_biz(ErrorCodes.SCENE_NAME_DUPLICATE, "场景名称已存在")
            scene.name = req.name
        if req.description is not None:
            scene.description = req.description
        if req.category_id is not None:
            scene.category_id = req.category_id
        scene.env_id = req.env_id
        scene.loop_count = req.loop_count
        scene.thread_count = req.thread_count
        scene.delay = req.delay
        scene.on_failure = req.on_failure
        scene.on_error = req.on_error
        scene.save_detail = req.save_detail
        scene.retry_count = req.retry_count
        scene.global_cookie = req.global_cookie
        scene.save_cookie_to_global = req.save_cookie_to_global
        if req.var_persist_target is not None:
            scene.var_persist_target = req.var_persist_target
        await self.db.flush()
        await self._save_steps_edges(scene_id, req.steps, req.edges)
        await self.db.refresh(scene)
        return scene

    async def _save_steps_edges(self, scene_id: int, steps: list, edges: list):
        await self.db.execute(
            SceneStep.__table__.delete().where(SceneStep.scene_id == scene_id)
        )
        await self.db.execute(
            SceneEdge.__table__.delete().where(SceneEdge.scene_id == scene_id)
        )
        steps = [s.model_dump() if hasattr(s, "model_dump") else s for s in steps]
        edges = [e.model_dump() if hasattr(e, "model_dump") else e for e in edges]
        # 校验步骤引用的 api_id 是否存在，避免 FOREIGN KEY constraint failed 的不友好报错
        api_ids = {s.get("api_id") for s in steps if s.get("api_id")}
        if api_ids:
            existing_result = await self.db.execute(
                select(ApiDefinition.id).where(ApiDefinition.id.in_(api_ids))
            )
            existing_ids = set(existing_result.scalars().all())
            missing_ids = api_ids - existing_ids
            if missing_ids:
                missing_str = ", ".join(str(aid) for aid in sorted(missing_ids))
                raise_biz(ErrorCodes.API_NOT_FOUND, f"API ID {missing_str} 不存在")
        for i, s in enumerate(steps):
            self.db.add(
                SceneStep(
                    scene_id=scene_id,
                    node_id=s.get("node_id", ""),
                    node_type=s.get("node_type", "request"),
                    label=s.get("label", ""),
                    position_x=s.get("position_x", 0),
                    position_y=s.get("position_y", 0),
                    api_id=s.get("api_id"),
                    test_case_id=s.get("test_case_id"),
                    sort_order=i,
                    enabled=int(s.get("enabled", 1)),
                    timeout=s.get("timeout", 30000),
                    retry_count=s.get("retry_count", 0),
                    request_body=s.get("request_body"),
                    headers=s.get("headers"),
                    query_params=s.get("query_params"),
                    assertions=s.get("assertions"),
                    extract_vars=s.get("extract_vars"),
                    condition_expression=s.get("condition_expression"),
                    loop_count=s.get("loop_count"),
                    loop_variable=s.get("loop_variable"),
                    wait_duration=s.get("wait_duration"),
                    wait_mode=s.get("wait_mode", "fixed"),
                    wait_min=s.get("wait_min"),
                    wait_max=s.get("wait_max"),
                )
            )
        for e in edges:
            self.db.add(
                SceneEdge(
                    scene_id=scene_id,
                    edge_id=getattr(e, "edge_id", None) or e.get("edge_id", ""),
                    source_node_id=getattr(e, "source_node_id", None)
                    or e.get("source_node_id", ""),
                    target_node_id=getattr(e, "target_node_id", None)
                    or e.get("target_node_id", ""),
                    source_handle=getattr(e, "source_handle", None)
                    or e.get("source_handle"),
                    label=getattr(e, "label", None) or e.get("label", ""),
                )
            )
        await self.db.flush()

    async def delete(self, scene_id: int, project_id: int | None = None):
        """软删除场景及其步骤"""
        from sqlalchemy import update

        scene = await self.get(scene_id, project_id)
        now = datetime.now(timezone.utc)
        scene.deleted_at = now
        await self.db.execute(
            update(SceneStep)
            .where(SceneStep.scene_id == scene_id, SceneStep.deleted_at.is_(None))
            .values(deleted_at=now)
        )
        await self.db.flush()

    async def list_deleted(self, project_id: int) -> list:
        """列出回收站中已软删除的场景"""
        result = await self.db.execute(
            select(TestScene)
            .where(TestScene.project_id == project_id, TestScene.deleted_at.isnot(None))
            .order_by(TestScene.deleted_at.desc())
        )
        return [
            {
                "id": s.id,
                "name": s.name,
                "project_id": s.project_id,
                "deleted_at": str(s.deleted_at),
            }
            for s in result.scalars().all()
        ]

    async def restore(self, scene_id: int, project_id: int):
        from sqlalchemy import update

        scene = await self.get_include_deleted(scene_id)
        if scene.project_id != project_id:
            raise_biz(ErrorCodes.PROJECT_FORBIDDEN, "资源不属于该项目")
        if scene.deleted_at is None:
            return

        # 检查分类是否仍存在
        parent_exists = True
        if scene.category_id:
            from app.models.scene_category import SceneCategory
            cat_result = await self.db.execute(
                select(SceneCategory).where(SceneCategory.id == scene.category_id)
            )
            cat = cat_result.scalar_one_or_none()
            if not cat:
                parent_exists = False
                scene.category_id = None

        scene.deleted_at = None
        # 同时恢复关联的已软删除步骤
        result = await self.db.execute(
            update(SceneStep)
            .where(SceneStep.scene_id == scene_id, SceneStep.deleted_at.isnot(None))
            .values(deleted_at=None)
        )
        await self.db.flush()
        return {"parent_exists": parent_exists, "restored_steps": result.rowcount}

    async def permanent_delete(self, scene_id: int, project_id: int):
        scene = await self.get_include_deleted(scene_id)
        if scene.project_id != project_id:
            raise_biz(ErrorCodes.PROJECT_FORBIDDEN, "资源不属于该项目")
        await self.db.delete(scene)
        await self.db.flush()

    async def update_schedule(
        self, scene_id: int, cron: str, enabled: bool, env_id: Optional[int] = None
    ):
        scene = await self.get(scene_id)
        scene.schedule_cron = cron
        scene.schedule_enabled = int(enabled)
        if env_id is not None:
            scene.schedule_env_id = env_id
        await self.db.flush()
        # 同步运行时调度器
        from app.utils.scheduler import sync_scene_schedule

        await sync_scene_schedule(scene_id, cron, enabled, env_id)

    async def get_schedule(self, scene_id: int) -> dict:
        scene = await self.get(scene_id)
        return {
            "cron": scene.schedule_cron or "",
            "enabled": bool(scene.schedule_enabled),
            "env_id": scene.schedule_env_id,
        }

    async def delete_schedule(self, scene_id: int):
        scene = await self.get(scene_id)
        scene.schedule_cron = ""
        scene.schedule_enabled = 0
        scene.schedule_env_id = None
        await self.db.flush()
        # 同步移除运行时调度器中的任务
        from app.utils.scheduler import remove_scene_job

        await remove_scene_job(scene_id)

    async def validate_extract_vars_unique(self, scene_id: int) -> None:
        """校验同一场景内所有步骤的 extract_vars 变量名不重复"""
        from collections import Counter

        result = await self.db.execute(
            select(SceneStep).where(
                SceneStep.scene_id == scene_id, SceneStep.enabled == 1
            )
        )
        steps = result.scalars().all()

        all_vars = []  # [(variable_name, step_label), ...]
        for step in steps:
            rules = safe_json_load(step.extract_vars, [])
            for rule in rules:
                if isinstance(rule, dict):
                    var_key = rule.get("variable") or rule.get("var_name")
                    if var_key:
                        all_vars.append(
                            (var_key, step.label or f"步骤 {step.sort_order + 1}")
                        )

        # 检测重名
        counter = Counter(v for v, _ in all_vars)
        for var_name, count in counter.items():
            if count > 1:
                conflicting_steps = [
                    step_label for v, step_label in all_vars if v == var_name
                ]
                raise_biz(
                    ErrorCodes.SCENE_VARIABLE_DUPLICATE,
                    detail=f"变量名 '{var_name}' 在以下步骤中重复: {', '.join(conflicting_steps)}",
                )

    async def batch_copy_steps(
        self, target_scene_id: int, steps: List[dict], user_id: int, project_id: int
    ) -> dict:
        """批量复制步骤到目标场景"""
        from app.models.scene_step import SceneStep

        # 验证目标场景存在
        result = await self.db.execute(
            select(TestScene).where(TestScene.id == target_scene_id)
        )
        scene = result.scalar_one_or_none()
        if not scene:
            raise_biz("SCENE_NOT_FOUND", detail=f"场景 {target_scene_id} 不存在")
        # project_id 权限由 router 层 check_write_access 校验

        # 创建步骤
        created_ids = []
        for step_data in steps:
            step = SceneStep(
                scene_id=target_scene_id,
                node_id=step_data.get("node_id", ""),
                node_type=step_data.get("node_type", "request"),
                label=step_data.get("label", ""),
                position_x=step_data.get("position_x", 0),
                position_y=step_data.get("position_y", 0),
                api_id=step_data.get("api_id"),
                test_case_id=step_data.get("test_case_id"),
                sort_order=step_data.get("sort_order", 0),
                enabled=step_data.get("enabled", 1),
                timeout=step_data.get("timeout", 30000),
                retry_count=step_data.get("retry_count", 0),
                request_body=step_data.get("request_body"),
                headers=step_data.get("headers"),
                query_params=step_data.get("query_params"),
                assertions=step_data.get("assertions"),
                extract_vars=step_data.get("extract_vars"),
                condition_expression=step_data.get("condition_expression"),
                loop_count=step_data.get("loop_count"),
                loop_variable=step_data.get("loop_variable"),
                wait_duration=step_data.get("wait_duration"),
                wait_mode=step_data.get("wait_mode", "fixed"),
                wait_min=step_data.get("wait_min"),
                wait_max=step_data.get("wait_max"),
            )
            self.db.add(step)
            await self.db.flush()
            created_ids.append(step.id)

        await self.db.flush()
        return {"count": len(created_ids), "step_ids": created_ids}

    async def batch_delete_steps(
        self, scene_id: int, step_ids: List[int], user_id: int, project_id: int
    ) -> dict:
        """批量删除场景步骤（软删除）"""
        from app.models.scene_step import SceneStep
        from datetime import datetime, timezone

        if not step_ids:
            raise ValueError("step_ids 不能为空")

        # 验证步骤属于指定场景
        result = await self.db.execute(
            select(SceneStep).where(
                SceneStep.id.in_(step_ids),
                SceneStep.scene_id == scene_id,
            )
        )
        steps = result.scalars().all()

        if not steps:
            raise ValueError("未找到匹配的步骤")

        # 验证场景权限（通过 project_id）
        scene_result = await self.db.execute(
            select(TestScene).where(TestScene.id == scene_id)
        )
        scene = scene_result.scalar_one_or_none()
        if not scene or scene.project_id != project_id:
            raise_biz(ErrorCodes.SCENE_NOT_FOUND, detail=f"场景 {scene_id} 不存在")

        # 软删除
        deleted_ids = []
        for step in steps:
            step.deleted_at = datetime.now(timezone.utc)
            deleted_ids.append(step.id)

        await self.db.flush()
        return {"count": len(deleted_ids), "step_ids": deleted_ids}

    async def batch_toggle_steps(
        self,
        scene_id: int,
        step_ids: List[int],
        enabled: bool,
        user_id: int,
        project_id: int,
    ) -> dict:
        """批量启用/禁用场景步骤"""
        from app.models.scene_step import SceneStep

        if not step_ids:
            raise ValueError("step_ids 不能为空")

        # 验证步骤属于指定场景
        result = await self.db.execute(
            select(SceneStep).where(
                SceneStep.id.in_(step_ids),
                SceneStep.scene_id == scene_id,
            )
        )
        steps = result.scalars().all()

        if not steps:
            raise ValueError("未找到匹配的步骤")

        # 验证场景权限
        scene_result = await self.db.execute(
            select(TestScene).where(TestScene.id == scene_id)
        )
        scene = scene_result.scalar_one_or_none()
        if not scene or scene.project_id != project_id:
            raise_biz(ErrorCodes.SCENE_NOT_FOUND, detail=f"场景 {scene_id} 不存在")

        # 批量更新
        updated_ids = []
        for step in steps:
            step.enabled = 1 if enabled else 0
            updated_ids.append(step.id)

        await self.db.flush()
        return {"count": len(updated_ids), "step_ids": updated_ids, "enabled": enabled}
