import json
from datetime import datetime, UTC
from sqlalchemy import select, func, update as sa_update, delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import raise_biz, ErrorCodes
from app.models.project import Project
from app.models.user import User
from app.models.api_definition import ApiDefinition
from app.models.test_case import TestCase
from app.models.test_scene import TestScene
from app.models.environment import Environment
from app.models.api_category import ApiCategory
from app.models.scene_category import SceneCategory
from app.models.schedule import Schedule
from app.models.mock_rule import MockRule
from app.models.api_snapshot import ApiSnapshot
from app.models.api_test_history import ApiTestHistory
from app.models.test_report import TestReport
from app.models.report_step import ReportStep
from app.models.scene_dataset import SceneDataset
from app.models.api_tag import ApiTag, ApiTagRelation
from app.models.api_test_plan import ApiTestPlan, ApiTestPlanStep
from app.schemas.project import ProjectCreate, ProjectUpdate, GlobalConfigUpdate


class ProjectService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_projects(self, current_user: User | None = None) -> list:
        if not current_user:
            return []
        query = (
            select(Project)
            .where(Project.created_by == current_user.id, Project.global_demo == 0)
            .order_by(Project.updated_at.desc())
        )
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_project(
        self, project_id: int, current_user: User | None = None
    ) -> Project:
        """获取项目详情（读权限）。

        使用 PermissionService 统一权限校验：
        - 公开项目：所有用户（含未登录）可读
        - 私有项目：成员(viewer及以上)可读
        """
        from app.services.permission_service import PermissionService
        return await PermissionService(self.db).check_project_access(
            project_id, current_user, require_write=False
        )

    async def batch_scene_counts(self, project_ids: list[int]) -> dict[int, int]:
        if not project_ids:
            return {}
        result = await self.db.execute(
            select(TestScene.project_id, func.count(TestScene.id))
            .where(TestScene.project_id.in_(project_ids))
            .group_by(TestScene.project_id)
        )
        return {row[0]: row[1] for row in result.all()}

    async def get_project_stats(self, project_id: int) -> dict:
        api_count = await self.db.scalar(
            select(func.count(ApiDefinition.id)).where(
                ApiDefinition.project_id == project_id,
                ApiDefinition.deleted_at.is_(None)
            )
        )
        case_count = await self.db.scalar(
            select(func.count(TestCase.id)).where(
                TestCase.project_id == project_id,
                TestCase.deleted_at.is_(None)
            )
        )
        scene_count = await self.db.scalar(
            select(func.count(TestScene.id)).where(
                TestScene.project_id == project_id,
                TestScene.deleted_at.is_(None)
            )
        )
        return {
            "api_count": api_count or 0,
            "case_count": case_count or 0,
            "scene_count": scene_count or 0,
        }

    async def create_project(self, req: ProjectCreate, user: User) -> Project:
        # 同一用户下项目名不可重复
        existing = await self.db.scalar(
            select(Project).where(
                Project.name == req.name, Project.created_by == user.id
            )
        )
        if existing:
            raise_biz(ErrorCodes.PROJECT_NAME_EXISTS)
        project = Project(
            name=req.name,
            description=req.description,
            is_public=req.is_public,
            created_by=user.id,
        )
        self.db.add(project)
        await self.db.flush()
        await self.db.refresh(project)

        # 创建者自动添加为 owner 成员（防并发重复插入）
        from app.models.project_member import ProjectMember
        from sqlalchemy import select as sa_select
        exists = await self.db.scalar(
            sa_select(ProjectMember).where(
                ProjectMember.project_id == project.id,
                ProjectMember.user_id == user.id,
            )
        )
        if not exists:
            member = ProjectMember(
                project_id=project.id,
                user_id=user.id,
                role="owner",
            )
            self.db.add(member)
            await self.db.flush()

        return project

    async def update_project(
        self, project_id: int, req: ProjectUpdate, user: User
    ) -> Project:
        from app.services.permission_service import PermissionService
        # 需要写权限（editor 及以上）
        project = await PermissionService(self.db).check_project_access(
            project_id, user, require_write=True
        )
        if req.name:
            # 检查项目名称是否已被其他项目使用（同用户下不可重复，与创建逻辑一致）
            dup = await self.db.execute(
                select(Project).where(
                    Project.name == req.name,
                    Project.id != project_id,
                    Project.created_by == project.created_by,
                )
            )
            if dup.scalar_one_or_none():
                raise_biz(ErrorCodes.PROJECT_NAME_EXISTS, "项目名称已存在")
            project.name = req.name
        if req.description is not None:
            project.description = req.description
        if req.is_public is not None:
            project.is_public = req.is_public
        await self.db.flush()
        await self.db.refresh(project)
        return project

    async def delete_project(self, project_id: int, user: User):
        from app.services.permission_service import PermissionService
        from app.services.transaction import transaction_scope

        project = await PermissionService(self.db).check_project_access(
            project_id, user, require_write=True
        )
        count = await self.db.scalar(
            select(func.count(Project.id)).where(Project.created_by == user.id)
        )
        if count <= 1:
            raise_biz(ErrorCodes.PROJECT_FORBIDDEN, "不能删除最后一个项目")

        async with transaction_scope(self.db):
            now = datetime.now(UTC)

            # ── 1. 软删除：API、用例、场景、API分类 ──
            models_to_soft_delete = [
                ApiDefinition,
                TestCase,
                TestScene,
                ApiCategory,
            ]
            for model in models_to_soft_delete:
                await self.db.execute(
                    sa_update(model)
                    .where(model.project_id == project_id)
                    .where(model.deleted_at.is_(None))
                    .values(deleted_at=now)
                )

            # ── 2. 物理删除：通过子查询关联的记录（无 project_id） ──

            # 2a. ApiSnapshot（通过 api_id 关联项目的 API）
            api_ids_subq = (
                select(ApiDefinition.id)
                .where(ApiDefinition.project_id == project_id)
            )
            await self.db.execute(
                sa_delete(ApiSnapshot).where(ApiSnapshot.api_id.in_(api_ids_subq))
            )

            # 2b. ApiTagRelation（通过 api_id 关联项目的 API）
            await self.db.execute(
                sa_delete(ApiTagRelation).where(ApiTagRelation.api_id.in_(api_ids_subq))
            )

            # 2c. SceneDataset（通过 scene_id 关联项目的场景）
            scene_ids_subq = (
                select(TestScene.id)
                .where(TestScene.project_id == project_id)
            )
            await self.db.execute(
                sa_delete(SceneDataset).where(SceneDataset.scene_id.in_(scene_ids_subq))
            )

            # 2d. ApiTestPlanStep → Schedule → ReportStep（通过 plan_id 关联）
            plan_ids_subq = (
                select(ApiTestPlan.id)
                .where(ApiTestPlan.project_id == project_id)
            )
            await self.db.execute(
                sa_delete(ApiTestPlanStep).where(ApiTestPlanStep.plan_id.in_(plan_ids_subq))
            )
            await self.db.execute(
                sa_delete(Schedule).where(Schedule.plan_id.in_(plan_ids_subq))
            )

            # 2e. ReportStep（通过 report_id 关联项目的报告）
            report_ids_subq = (
                select(TestReport.id)
                .where(TestReport.project_id == project_id)
            )
            await self.db.execute(
                sa_delete(ReportStep).where(ReportStep.report_id.in_(report_ids_subq))
            )

            # ── 3. 物理删除：直接有 project_id 的记录 ──

            await self.db.execute(
                sa_delete(ApiTestHistory).where(ApiTestHistory.project_id == project_id)
            )
            await self.db.execute(
                sa_delete(TestReport).where(TestReport.project_id == project_id)
            )
            await self.db.execute(
                sa_delete(ApiTestPlan).where(ApiTestPlan.project_id == project_id)
            )
            await self.db.execute(
                sa_delete(MockRule).where(MockRule.project_id == project_id)
            )
            await self.db.execute(
                sa_delete(Environment).where(Environment.project_id == project_id)
            )
            await self.db.execute(
                sa_delete(SceneCategory).where(SceneCategory.project_id == project_id)
            )
            await self.db.execute(
                sa_delete(ApiTag).where(ApiTag.project_id == project_id)
            )

            # ── 4. 物理删除项目成员记录 ──
            from app.models.project_member import ProjectMember
            await self.db.execute(
                sa_delete(ProjectMember).where(ProjectMember.project_id == project_id)
            )

            # ── 5. 删除项目本身 ──
            await self.db.delete(project)
            await self.db.flush()

    async def get_global_config(self, project_id: int, user: User | None) -> dict:
        from app.services.permission_service import PermissionService
        project = await PermissionService(self.db).check_project_access(
            project_id, user, require_write=False
        )
        try:
            gv = (
                json.loads(project.global_variables) if project.global_variables else []
            )
        except (json.JSONDecodeError, TypeError):
            gv = []
        try:
            gp = json.loads(project.global_params) if project.global_params else {}
        except (json.JSONDecodeError, TypeError):
            gp = {}
        return {"global_variables": gv, "global_params": gp}

    async def update_global_config(
        self, project_id: int, req: GlobalConfigUpdate, user: User
    ):
        from app.services.permission_service import PermissionService
        # 写全局配置需要 editor 及以上权限
        await PermissionService(self.db).check_project_access(
            project_id, user, require_write=True
        )
        project = await self.db.get(Project, project_id)
        project.global_variables = json.dumps(req.global_variables, ensure_ascii=False)
        project.global_params = json.dumps(req.global_params, ensure_ascii=False)
        await self.db.flush()

    async def list_projects_with_scene_count(
        self, current_user: User | None = None, page: int = 1, page_size: int = 20,
    ) -> tuple[list[dict], int]:
        """获取项目列表，包含场景数量（单次查询优化），支持分页"""
        from sqlalchemy import func, select
        from app.models.test_scene import TestScene

        # 权限过滤：admin 可查看所有项目（含种子模板），普通用户也能看到种子模板 + 自己有权限的项目
        if current_user:
            if current_user.role == "admin":
                query = select(Project).order_by(Project.updated_at.desc())
                count_query = select(func.count(Project.id))
            else:
                from app.models.project_member import ProjectMember

                member_subquery = (
                    select(ProjectMember.project_id)
                    .where(ProjectMember.user_id == current_user.id)
                    .subquery()
                )
                base_where = (
                    (
                        # 种子模板对所有登录用户可见（只读）
                        (Project.global_demo == 1)
                        |
                        # 普通项目：自己创建的、公开的、或作为成员的
                        (
                            (Project.global_demo == 0)
                            & (
                                (Project.is_public == True)  # noqa: E712
                                | (Project.created_by == current_user.id)
                                | (Project.id.in_(select(member_subquery.c.project_id)))
                            )
                        )
                    ),
                )
                query = select(Project).where(*base_where).order_by(
                    Project.global_demo.desc(), Project.updated_at.desc()
                )
                count_query = select(func.count(Project.id)).where(*base_where)
            total = await self.db.scalar(count_query) or 0
            results = await self.db.execute(
                query.offset((page - 1) * page_size).limit(page_size)
            )
            projects = results.scalars().all()
        else:
            # 未登录用户只能看到公开项目，但包括种子模板（global_demo=1）
            base_where = (Project.is_public == True,)  # noqa: E712
            count_query = select(func.count(Project.id)).where(*base_where)
            total = await self.db.scalar(count_query) or 0
            results = await self.db.execute(
                select(Project)
                .where(*base_where)
                .order_by(Project.global_demo.desc(), Project.updated_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
            projects = results.scalars().all()

        if not projects:
            return [], total

        project_ids = [p.id for p in projects]

        # 批量查询场景数量（单次查询）
        scene_count_query = (
            select(TestScene.project_id, func.count(TestScene.id).label("scene_count"))
            .where(
                TestScene.project_id.in_(project_ids), TestScene.deleted_at.is_(None)
            )
            .group_by(TestScene.project_id)
        )

        scene_result = await self.db.execute(scene_count_query)
        scene_counts = {row.project_id: row.scene_count for row in scene_result}

        # 批量查询当前用户在各项目中的角色（已登录用户）
        role_map: dict[int, str] = {}
        if current_user:
            from app.models.project_member import ProjectMember

            if current_user.role == "admin":
                # 管理员对所有项目都是 admin 角色
                for pid in project_ids:
                    role_map[pid] = "admin"
            else:
                member_query = select(ProjectMember.project_id, ProjectMember.role).where(
                    ProjectMember.user_id == current_user.id,
                    ProjectMember.project_id.in_(project_ids),
                )
                member_result = await self.db.execute(member_query)
                for row in member_result.all():
                    role_map[row.project_id] = row.role
                # 项目创建者自动是 owner 角色
                for p in projects:
                    if p.created_by == current_user.id:
                        role_map[p.id] = "owner"

        # 组装结果
        items = [
            {
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "is_public": p.is_public,
                "global_demo": p.global_demo,
                "created_by": p.created_by,
                "created_at": str(p.created_at),
                "updated_at": str(p.updated_at),
                "scene_count": scene_counts.get(p.id, 0),
                "role": role_map.get(p.id),
            }
            for p in projects
        ]
        return items, total
