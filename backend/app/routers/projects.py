from typing import Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import raise_biz, ErrorCodes
from app.database import get_db
from app.middleware.auth import get_current_user, get_optional_user
from app.models.project import Project
from app.models.user import User
from app.schemas.project import ProjectCreate, ProjectUpdate, GlobalConfigUpdate, GlobalVariableUpsert
from app.services.project_service import ProjectService
from app.services.transaction import transaction_scope
from app.services.permission_service import check_read_access, check_write_access
from app.utils.response import success

router = APIRouter(prefix="/projects", tags=["项目管理"])


# ── 批量操作请求体 ──────────────────────────────────────────────────────────


class BatchMoveRequest(BaseModel):
    """批量移动资源请求。"""

    resource_type: str = Field(..., description="api / case / scene")
    resource_ids: list[int] = Field(..., min_length=1, max_length=200)
    target_id: Optional[int] = Field(default=None, description="目标分类 ID")


class BatchTagRequest(BaseModel):
    """批量打标签请求。"""

    resource_type: str = Field(..., description="api / case / scene")
    resource_ids: list[int] = Field(..., min_length=1, max_length=200)
    add_tags: list[str] = Field(default_factory=list)
    remove_tags: list[str] = Field(default_factory=list)


class BatchStatusRequest(BaseModel):
    """批量更新状态请求。"""

    resource_type: str = Field(..., description="api / case / scene")
    resource_ids: list[int] = Field(..., min_length=1, max_length=200)
    status: str = Field(..., description="draft / published / deprecated / active / archived")



@router.get("", summary="项目列表", description="获取当前用户有权限访问的项目列表（公开项目未登录也可访问）")
async def list_projects(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    service = ProjectService(db)
    items, total = await service.list_projects_with_scene_count(current_user, page, page_size)
    return success({"items": items, "total": total, "page": page, "page_size": page_size})
@router.get("/{project_id}", summary="项目详情", description="获取指定项目的详细信息（公开项目未登录也可访问）")
async def get_project(project_id: int, current_user: User | None = Depends(get_optional_user), _project: Project = Depends(check_read_access), db: AsyncSession = Depends(get_db)):
    service = ProjectService(db)
    project = await service.get_project(project_id, current_user)
    stats = await service.get_project_stats(project_id)

    # 计算当前用户在项目中的角色
    role = None
    if current_user:
        from app.services.permission_service import PermissionService
        role = await PermissionService(db).get_project_role(project_id, current_user)

    return success({"id": project.id, "name": project.name, "description": project.description,
                    "is_public": project.is_public, "created_by": project.created_by,
                    "global_demo": project.global_demo, "role": role, **stats})


@router.post("", summary="创建项目", description="新建 API 测试项目")
async def create_project(req: ProjectCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    service = ProjectService(db)
    project = await service.create_project(req, current_user)
    return success({"id": project.id, "name": project.name, "description": project.description, "is_public": project.is_public})


@router.put("/{project_id}", summary="更新项目", description="修改项目名称、描述等信息")
async def update_project(project_id: int, req: ProjectUpdate, current_user: User = Depends(get_current_user), _project: Project = Depends(check_write_access), db: AsyncSession = Depends(get_db)):
    service = ProjectService(db)
    project = await service.update_project(project_id, req, current_user)
    return success({"id": project.id, "name": project.name, "description": project.description, "is_public": project.is_public})


@router.delete("/{project_id}", summary="删除项目", description="删除项目及其所有关联数据")
async def delete_project(project_id: int, current_user: User = Depends(get_current_user), _project: Project = Depends(check_write_access), db: AsyncSession = Depends(get_db)):
    service = ProjectService(db)
    await service.delete_project(project_id, current_user)
    return success(message="项目已删除")

@router.get("/{project_id}/variables/{key}/references", summary="变量引用追踪", description="查找引用指定变量的场景步骤和测试用例")
async def variable_references(
    project_id: int,
    key: str,
    current_user: User | None = Depends(get_optional_user),
    _project: Project = Depends(check_read_access),
    db: AsyncSession = Depends(get_db),
):
    """搜索项目中所有场景步骤和测试用例里对 {{key}} 的引用。"""
    import re
    from app.models.scene_step import SceneStep
    from app.models.test_case import TestCase
    from app.models.test_scene import TestScene

    pattern = re.compile(r"\{\{" + re.escape(key) + r"\}\}")
    references = []

    # 查询场景步骤
    steps_result = await db.execute(
        select(SceneStep).join(TestScene, SceneStep.scene_id == TestScene.id).where(
            TestScene.project_id == project_id,
            TestScene.deleted_at.is_(None),
        )
    )
    for step in steps_result.scalars().all():
        text_fields = [
            step.request_body, step.headers, step.query_params,
            step.assertions, step.extract_vars, step.condition_expression,
        ]
        if any(pattern.search(f or "") for f in text_fields):
            scene_result = await db.execute(
                select(TestScene).where(TestScene.id == step.scene_id)
            )
            scene = scene_result.scalar_one_or_none()
            references.append({
                "type": "step",
                "id": step.id,
                "name": step.label or f"步骤#{step.id}",
                "scene_name": scene.name if scene else "",
                "scene_id": step.scene_id,
            })

    # 查询测试用例
    cases_result = await db.execute(
        select(TestCase).where(
            TestCase.project_id == project_id,
            TestCase.deleted_at.is_(None),
        )
    )
    for case in cases_result.scalars().all():
        text_fields = [case.request_body, case.assertions, case.extract_vars]
        if any(pattern.search(f or "") for f in text_fields):
            references.append({
                "type": "case",
                "id": case.id,
                "name": case.name,
                "scene_name": "",
                "scene_id": None,
            })

    return success(references)


@router.get("/{project_id}/global-config", summary="获取全局配置", description="获取项目的全局变量和公共配置")
async def get_global_config(project_id: int, current_user: User | None = Depends(get_optional_user), db: AsyncSession = Depends(get_db)):
    service = ProjectService(db)
    return success(await service.get_global_config(project_id, current_user))


@router.put("/{project_id}/global-config", summary="更新全局配置", description="修改项目的全局变量和公共配置")
async def update_global_config(project_id: int, req: GlobalConfigUpdate, current_user: User = Depends(get_current_user), _project: Project = Depends(check_write_access), db: AsyncSession = Depends(get_db)):
    service = ProjectService(db)
    await service.update_global_config(project_id, req, current_user)
    return success(message="全局配置已更新")


@router.post("/{project_id}/global-variables", summary="添加/更新全局变量", description="添加或更新单个全局变量（仅需读权限）")
async def upsert_global_variable(project_id: int, req: GlobalVariableUpsert,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_read_access),
    db: AsyncSession = Depends(get_db)):
    """添加或更新单个全局变量。此端点仅需读权限，用于 API 测试时保存提取的变量。"""
    import json
    project = await db.get(Project, project_id)
    if not project:
        from app.core.exceptions import raise_biz, ErrorCodes
        raise_biz(ErrorCodes.PROJECT_NOT_FOUND)
    raw = project.global_variables
    if isinstance(raw, str):
        try:
            variables = json.loads(raw) if raw else []
        except (json.JSONDecodeError, ValueError):
            variables = []
    elif isinstance(raw, list):
        variables = raw
    else:
        variables = []
    idx = next((i for i, v in enumerate(variables) if v.get("key") == req.key), None)
    if idx is not None:
        variables[idx]["value"] = req.value
    else:
        variables.append({"key": req.key, "value": req.value, "enabled": True})
    project.global_variables = json.dumps(variables, ensure_ascii=False) if isinstance(raw, str) else variables
    await db.flush()
    operation = "updated" if idx is not None else "created"
    return success({
        "key": req.key,
        "value": req.value,
        "updated": idx is not None,
        "operation": operation,
        "total_variables": len(variables),
    }, message=f"全局变量 '{req.key}' 已{'更新' if idx is not None else '创建'}")


# =============================================================================
#  阶段 3 增强：批量操作 + 业务回滚
# =============================================================================
#  - POST /batch/move       批量移动（api/case/scene）
#  - POST /batch/tag        批量打/去标签
#  - POST /batch/status     批量更新状态
#  - POST /resources/{type}/{id}/rollback  业务回滚到指定审计日志
# =============================================================================


@router.post("/batch/move", summary="批量移动资源")
async def batch_move(
    req: BatchMoveRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _project: Project = Depends(check_write_access),
):
    """批量移动资源到指定目录。"""
    project_id = _project.id
    if req.resource_type not in ("api", "case", "scene"):
        raise_biz(ErrorCodes.PARAM_ERROR, "resource_type 必须是 api / case / scene")
    moved = 0
    # 阶段 4：批量操作包在 SAVEPOINT 事务中，失败可回滚
    async with transaction_scope(db, nested=True) as session:
        if req.resource_type == "api":
            from app.models.api_definition import ApiDefinition
            for rid in req.resource_ids:
                row = await session.get(ApiDefinition, rid)
                if not row:
                    continue
                if row.project_id != project_id:
                    continue
                row.category_id = req.target_id
                moved += 1
        elif req.resource_type == "case":
            from app.models.test_case import TestCase
            for rid in req.resource_ids:
                case = await session.get(TestCase, rid)
                if not case:
                    continue
                if case.project_id != project_id:
                    continue
                case.api_id = req.target_id
                moved += 1
        elif req.resource_type == "scene":
            from app.models.scene_category import SceneCategory
            for rid in req.resource_ids:
                row = await session.get(SceneCategory, rid)
                if not row:
                    continue
                if row.project_id != project_id:
                    continue
                row.parent_id = req.target_id
                moved += 1
        await session.flush()
    return success({"moved": moved, "resource_type": req.resource_type})


@router.post("/batch/tag", summary="批量打/去标签")
async def batch_tag(
    req: BatchTagRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _project: Project = Depends(check_write_access),
):
    """批量管理资源标签。"""
    project_id = _project.id
    if req.resource_type not in ("api", "case", "scene"):
        raise_biz(ErrorCodes.PARAM_ERROR, "resource_type 必须是 api / case / scene")
    if req.resource_type != "case":
        raise_biz(ErrorCodes.PARAM_ERROR, "当前仅 case 支持标签")
    from app.models.test_case import TestCase
    updated = 0
    # 阶段 4：批量打标签包在 SAVEPOINT 事务中
    async with transaction_scope(db, nested=True) as session:
        result = await session.execute(select(TestCase).where(TestCase.id.in_(req.resource_ids)))
        cases = result.scalars().all()
        for c in cases:
            if c.project_id != project_id:
                continue
            tags = set(filter(None, (c.tags or "").split(",")))
            for t in req.add_tags:
                tags.add(t)
            for t in req.remove_tags:
                tags.discard(t)
            c.tags = ",".join(sorted(tags))
            updated += 1
        await session.flush()
    return success({"updated": updated})


@router.post("/batch/status", summary="批量更新状态")
async def batch_status(
    req: BatchStatusRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _project: Project = Depends(check_write_access),
):
    """批量更新资源状态。"""
    project_id = _project.id
    if req.resource_type not in ("api", "case", "scene"):
        raise_biz(ErrorCodes.PARAM_ERROR, "resource_type 必须是 api / case / scene")
    updated = 0
    # 阶段 4：批量状态更新包在 SAVEPOINT 事务中
    async with transaction_scope(db, nested=True) as session:
        if req.resource_type == "api":
            from app.models.api_definition import ApiDefinition
            for rid in req.resource_ids:
                row = await session.get(ApiDefinition, rid)
                if not row:
                    continue
                if row.project_id != project_id:
                    continue
                row.status = req.status
                updated += 1
        elif req.resource_type == "case":
            from app.models.test_case import TestCase
            for rid in req.resource_ids:
                row = await session.get(TestCase, rid)
                if not row:
                    continue
                if row.project_id != project_id:
                    continue
                row.status = req.status
                updated += 1
        await session.flush()
    return success({"updated": updated, "status": req.status})


@router.post("/seed/fork", summary="Fork 种子演示项目", description="将种子演示项目复制为当前用户的私有副本（幂等：已有私有项目则直接返回）")
async def fork_seed_project(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Fork 种子演示项目为用户私有副本。

    - 幂等操作：用户已有私有项目则直接返回第一个项目
    - 无种子模板时返回错误提示
    """
    from app.utils.seed_core import copy_project_to_user

    tpl_result = await db.execute(select(Project).where(Project.global_demo == 1).limit(1))
    template = tpl_result.scalar_one_or_none()

    if not template:
        raise_biz(ErrorCodes.PROJECT_NOT_FOUND, "种子演示项目不存在，无法 Fork")

    # 先检查用户是否已有私有项目（幂等）
    existing = await db.execute(
        select(Project).where(
            Project.created_by == current_user.id,
            Project.global_demo == 0,
        ).order_by(Project.id.asc()).limit(1)
    )
    existing_proj = existing.scalar_one_or_none()
    if existing_proj:
        return success({
            "id": existing_proj.id,
            "name": existing_proj.name,
            "is_new": False,
            "message": "您已有私有项目，直接跳转",
        })

    # 执行 Fork
    new_pid = await copy_project_to_user(
        db, template.id, current_user.id,
        nickname=current_user.nickname or current_user.username,
    )
    await db.commit()

    # 读取新项目信息返回
    new_proj = await db.get(Project, new_pid)
    return success({
        "id": new_pid,
        "name": new_proj.name if new_proj else "我的演示项目",
        "is_new": True,
        "message": "Fork 成功，已为您创建私有副本",
    })

