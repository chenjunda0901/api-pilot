from typing import Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from fastapi import Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user, get_optional_user
from app.models.user import User
from app.models.project import Project
from app.models.test_report import TestReport
from app.models.report_step import ReportStep
from app.models.scene_step import SceneStep
from app.schemas.scene import (
    SceneCreate,
    SceneUpdate,
    BatchCopyStepsRequest,
    BatchStepIdsRequest,
    BatchToggleStepsRequest,
)
from app.services.scene_service import SceneService
from app.services.permission_service import check_read_access, check_write_access, check_seed_mark_access
from app.services.executor.assertion_engine import jsonpath_get
from app.utils.response import success
from app.utils.json_helpers import safe_json_load

router = APIRouter(prefix="/projects/{project_id}/scenes", tags=["Test Scenes"])


@router.get("", summary="场景列表", description="获取项目下的测试场景列表")
async def list_scenes(
    project_id: int,
    keyword: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User | None = Depends(get_optional_user),
    _project: Project = Depends(check_read_access),
    db: AsyncSession = Depends(get_db),
):
    s = SceneService(db)
    items, total = await s.list(project_id, keyword, page, page_size)
    return success(
        {"items": items, "total": total, "page": page, "page_size": page_size}
    )


@router.get(
    "/{scene_id}", summary="场景详情", description="获取指定场景的完整配置和步骤列表"
)
async def get_scene(
    project_id: int,
    scene_id: int,
    current_user: User | None = Depends(get_optional_user),
    _project: Project = Depends(check_read_access),
    db: AsyncSession = Depends(get_db),
):
    s = SceneService(db)
    return success(await s.get_detail(scene_id))


@router.post("", summary="创建场景", description="新建测试场景（支持多步骤编排）")
async def create_scene(
    project_id: int,
    req: SceneCreate,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
    db: AsyncSession = Depends(get_db),
):
    s = SceneService(db)
    result = s.to_dict(await s.create(project_id, req))
    return success(result)


@router.put(
    "/{scene_id}", summary="更新场景", description="修改场景的步骤、配置和依赖关系"
)
async def update_scene(
    project_id: int,
    scene_id: int,
    req: SceneUpdate,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
    db: AsyncSession = Depends(get_db),
):
    s = SceneService(db)
    result = s.to_dict(await s.update(scene_id, req, project_id))
    return success(result)


@router.delete("/{scene_id}", summary="删除场景", description="删除指定的测试场景")
async def delete_scene(
    project_id: int,
    scene_id: int,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
    db: AsyncSession = Depends(get_db),
):
    # 检查是否有测试计划引用了该场景
    from app.models.api_test_plan import ApiTestPlanStep
    from sqlalchemy import func

    ref_count = (
        await db.scalar(
            select(func.count(ApiTestPlanStep.id)).where(
                ApiTestPlanStep.step_type == "scene",
                ApiTestPlanStep.step_id == scene_id,
            )
        )
        or 0
    )
    if ref_count > 0:
        from app.core.exceptions import raise_biz, ErrorCodes

        raise_biz(ErrorCodes.CONFLICT, f"该场景被 {ref_count} 个测试计划引用，无法删除")

    s = SceneService(db)
    await s.delete(scene_id, project_id)
    return success(message="场景已移至回收站")


@router.get("/recycle/list", summary="场景回收站", description="列出已软删除的场景")
async def list_deleted_scenes(
    project_id: int,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_read_access),
    db: AsyncSession = Depends(get_db),
):
    s = SceneService(db)
    return success({"items": await s.list_deleted(project_id)})


@router.post("/{scene_id}/restore", summary="恢复场景", description="从回收站恢复场景")
async def restore_scene(
    project_id: int,
    scene_id: int,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
    db: AsyncSession = Depends(get_db),
):
    s = SceneService(db)
    result = await s.restore(scene_id, project_id)
    return success(result)


@router.delete(
    "/{scene_id}/permanent", summary="永久删除场景", description="从数据库永久移除场景"
)
async def permanent_delete_scene(
    project_id: int,
    scene_id: int,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
    db: AsyncSession = Depends(get_db),
):
    s = SceneService(db)
    await s.permanent_delete(scene_id, project_id)
    return success(message="场景已永久删除")


@router.put(
    "/{scene_id}/seed-mark",
    summary="标记/取消标记为种子",
    description="管理员将场景标记为种子数据，下次重置种子时保留；再次调用可取消标记",
)
async def mark_scene_as_seed(
    project_id: int,
    scene_id: int,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_seed_mark_access),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role != "admin":
        from app.core.exceptions import raise_biz, ErrorCodes

        raise_biz(ErrorCodes.PROJECT_FORBIDDEN, "仅管理员可标记种子数据")
    from sqlalchemy import select
    from app.models.test_scene import TestScene
    from app.models.project import Project

    result = await db.execute(
        select(TestScene).where(TestScene.id == scene_id, TestScene.project_id == project_id).limit(1)
    )
    scene = result.scalar_one_or_none()
    if not scene:
        from app.core.exceptions import raise_biz, ErrorCodes

        raise_biz(ErrorCodes.NOT_FOUND, "场景不存在")
    # 种子标记仅对全局种子项目（global_demo=1）有效
    project = await db.get(Project, scene.project_id)
    if not project or project.global_demo != 1:
        from app.core.exceptions import raise_biz, ErrorCodes
        raise_biz(ErrorCodes.PARAM_ERROR, "种子标记仅对全局种子项目生效")
    scene.is_seed = 1 if scene.is_seed == 0 else 0
    await db.flush()
    return success(
        {
            "is_seed": scene.is_seed,
            "message": "已标记为种子" if scene.is_seed else "已取消种子标记",
        }
    )


@router.get(
    "/{scene_id}/schedule", summary="获取定时配置", description="获取场景的定时执行配置"
)
async def get_schedule(
    project_id: int,
    scene_id: int,
    current_user: User | None = Depends(get_optional_user),
    _project: Project = Depends(check_read_access),
    db: AsyncSession = Depends(get_db),
):
    s = SceneService(db)
    return success(await s.get_schedule(scene_id))


@router.put(
    "/{scene_id}/schedule",
    summary="更新定时配置",
    description="修改场景的定时执行计划（Cron 表达式）",
)
async def update_schedule(
    project_id: int,
    scene_id: int,
    cron: str = Query(...),
    enabled: bool = Query(...),
    env_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
    db: AsyncSession = Depends(get_db),
):
    s = SceneService(db)
    await s.update_schedule(scene_id, cron, enabled, env_id)
    return success(message="定时配置已更新")


@router.delete(
    "/{scene_id}/schedule", summary="删除定时配置", description="清除场景的定时执行配置"
)
async def delete_schedule(
    project_id: int,
    scene_id: int,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
    db: AsyncSession = Depends(get_db),
):
    s = SceneService(db)
    await s.delete_schedule(scene_id)
    return success(message="定时配置已删除")


@router.get(
    "/{scene_id}/steps/{step_id}/last-extracted",
    summary="获取步骤变量",
    description="获取场景步骤最近一次执行提取的变量值",
)
async def get_step_last_extracted(
    project_id: int,
    scene_id: int,
    step_id: int,
    current_user: User | None = Depends(get_optional_user),
    _project: Project = Depends(check_read_access),
    db: AsyncSession = Depends(get_db),
):
    """获取指定步骤最近一次执行时提取的变量值（用于变量选择器预览）"""
    from app.core.exceptions import raise_biz, ErrorCodes

    # 校验步骤存在
    step = await db.get(SceneStep, step_id)
    if not step or step.scene_id != scene_id:
        raise_biz(ErrorCodes.SCENE_STEP_NOT_FOUND)

    # 查询最新的报告
    result = await db.execute(
        select(TestReport)
        .where(TestReport.scene_id == scene_id)
        .order_by(TestReport.created_at.desc())
        .limit(1)
    )
    report = result.scalar_one_or_none()
    if not report:
        return success({})

    # 查询该步骤在最新报告中的执行结果
    step_result = await db.execute(
        select(ReportStep)
        .where(ReportStep.report_id == report.id, ReportStep.scene_step_id == step_id)
        .limit(1)
    )
    report_step = step_result.scalar_one_or_none()
    if not report_step:
        return success({})

    # 从 response_body 中提取与当前步骤 extract_vars 匹配的变量值
    response_body = safe_json_load(report_step.response_body, {})

    response_headers = safe_json_load(report_step.response_headers, {})

    extracted = {}
    rules = safe_json_load(step.extract_vars, [])
    for rule in rules:
        if isinstance(rule, dict) and rule.get("variable"):
            var_name = rule["variable"]
            source = rule.get("source", "body")
            val = None
            if source == "header":
                val = response_headers.get(rule.get("header_name", ""))
            else:
                val = jsonpath_get(response_body, rule.get("path", ""))
            if val is not None:
                extracted[var_name] = {
                    "value": val,
                    "source_step": step.label,
                    "source_type": "extract",
                }

    return success(extracted)


@router.post(
    "/{scene_id}/steps/batch",
    summary="批量复制步骤",
    description="批量复制步骤到指定场景",
)
async def batch_copy_steps(
    project_id: int,
    scene_id: int,
    req: BatchCopyStepsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
):
    """批量复制步骤到指定场景"""
    from app.services.scene_service import SceneService
    from app.models.test_scene import TestScene

    # Validate target scene exists and belongs to project
    scene_result = await db.execute(
        select(TestScene).where(
            TestScene.id == scene_id,
            TestScene.project_id == project_id,
            TestScene.deleted_at.is_(None),
        )
    )
    target_scene = scene_result.scalar_one_or_none()
    if not target_scene:
        from app.core.exceptions import raise_biz, ErrorCodes

        raise_biz(ErrorCodes.SCENE_NOT_FOUND, f"目标场景 {scene_id} 不存在或无权访问")

    async with db.begin():
        service = SceneService(db)
        result = await service.batch_copy_steps(
            scene_id, req.steps, current_user.id, project_id
        )
    return success(result)


@router.delete(
    "/{scene_id}/steps/batch",
    summary="批量删除步骤",
    description="批量删除场景步骤（软删除）",
)
async def batch_delete_steps(
    project_id: int,
    scene_id: int,
    req: BatchStepIdsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
):
    """批量删除场景步骤"""
    from app.services.scene_service import SceneService

    async with db.begin():
        service = SceneService(db)
        result = await service.batch_delete_steps(
            scene_id, req.step_ids, current_user.id, project_id
        )
    return success(result)


@router.put(
    "/{scene_id}/steps/batch/enable",
    summary="批量启用/禁用步骤",
    description="批量启用或禁用场景步骤",
)
async def batch_toggle_steps(
    project_id: int,
    scene_id: int,
    req: BatchToggleStepsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
):
    """批量启用/禁用场景步骤"""
    from app.services.scene_service import SceneService

    service = SceneService(db)
    result = await service.batch_toggle_steps(
        scene_id, req.step_ids, req.enabled, current_user.id, project_id
    )
    return success(result)


class SceneImportStepData(BaseModel):
    """场景导入中单条步骤的数据（字段与 SceneStep 模型对齐）"""
    node_id: str = Field(default="", max_length=50, description="节点 ID")
    node_type: str = Field(default="request", max_length=50, description="步骤类型")
    step_type: Optional[str] = Field(default=None, description="步骤类型（兼容字段，优先使用 node_type）")
    label: str = Field(default="", max_length=200, description="步骤名称/标签")
    name: Optional[str] = Field(default=None, description="步骤名称（兼容字段，回退到 label）")
    api_id: Optional[int] = Field(default=None, description="关联接口 ID")
    test_case_id: Optional[int] = Field(default=None, description="关联用例 ID")
    sort_order: int = Field(default=0, description="排序")
    enabled: bool = Field(default=True, description="是否启用")
    timeout: int = Field(default=30000, description="超时(ms)")
    retry_count: int = Field(default=0, description="重试次数")
    request_body: Optional[str] = Field(default=None, description="请求体")
    headers: Optional[str] = Field(default=None, description="请求头(JSON)")
    query_params: Optional[str] = Field(default=None, description="查询参数(JSON)")
    assertions: Optional[str] = Field(default=None, description="断言列表(JSON)")
    extract_vars: Optional[str] = Field(default=None, description="变量提取规则(JSON)")
    condition_expression: Optional[str] = Field(default=None, description="条件表达式")
    loop_count: Optional[int] = Field(default=None, description="循环次数")
    loop_variable: Optional[str] = Field(default=None, description="循环变量")
    wait_duration: Optional[int] = Field(default=None, description="等待时长(ms)")
    wait_mode: Optional[str] = Field(default="fixed", description="等待模式")
    wait_min: Optional[int] = Field(default=None, description="最小等待(ms)")
    wait_max: Optional[int] = Field(default=None, description="最大等待(ms)")
    parallel_group: int = Field(default=0, description="并行组")
    config: Optional[dict] = Field(default=None, description="步骤配置（兼容字段，优先使用具体字段）")


class SceneImportData(BaseModel):
    """场景导入数据"""
    name: str = Field(default="Imported Scene", min_length=1, max_length=200, description="场景名称")
    description: str = Field(default="", max_length=2000, description="场景描述")
    steps: list[SceneImportStepData] = Field(default_factory=list, description="步骤列表")


class SceneImportRequest(BaseModel):
    data: SceneImportData
    overwrite: bool = False
    target_scene_id: Optional[int] = Field(default=None, description="覆盖导入时的目标场景 ID")


@router.post("/{scene_id}/export", summary="Export scene")
async def export_scene(
    project_id: int,
    scene_id: int,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_read_access),
    db: AsyncSession = Depends(get_db),
):
    from app.services.scene_service import SceneService

    s = SceneService(db)
    scene = await s.get(scene_id)
    from sqlalchemy import select
    from app.models.scene_step import SceneStep

    steps_result = await db.execute(
        select(SceneStep)
        .where(SceneStep.scene_id == scene_id)
        .order_by(SceneStep.sort_order)
    )
    steps = steps_result.scalars().all()
    return success(
        {
            "name": scene.name,
            "description": scene.description or "",
            "steps": [
                {
                    "sort_order": st.sort_order,
                    "node_id": st.node_id,
                    "node_type": st.node_type,
                    "step_type": st.node_type,
                    "label": st.label,
                    "name": st.label,
                    "api_id": st.api_id,
                    "test_case_id": st.test_case_id,
                    "enabled": bool(st.enabled),
                    "timeout": st.timeout,
                    "retry_count": st.retry_count,
                    "request_body": st.request_body,
                    "headers": st.headers,
                    "query_params": st.query_params,
                    "assertions": st.assertions,
                    "extract_vars": st.extract_vars,
                    "condition_expression": st.condition_expression,
                    "loop_count": st.loop_count,
                    "loop_variable": st.loop_variable,
                    "wait_duration": st.wait_duration,
                    "wait_mode": getattr(st, "wait_mode", "fixed"),
                    "wait_min": getattr(st, "wait_min", None),
                    "wait_max": getattr(st, "wait_max", None),
                    "parallel_group": getattr(st, "parallel_group", 0),
                    "config": {
                        "timeout": st.timeout,
                        "retry_count": st.retry_count,
                        "request_body": st.request_body,
                        "headers": st.headers,
                        "query_params": st.query_params,
                        "extract_vars": st.extract_vars,
                        "condition_expression": st.condition_expression,
                        "loop_count": st.loop_count,
                        "loop_variable": st.loop_variable,
                        "wait_duration": st.wait_duration,
                        "wait_mode": getattr(st, "wait_mode", "fixed"),
                        "wait_min": getattr(st, "wait_min", None),
                        "wait_max": getattr(st, "wait_max", None),
                        "parallel_group": getattr(st, "parallel_group", 0),
                    },
                }
                for st in steps
            ],
        }
    )


@router.post("/import", summary="Import scene")
async def import_scene(
    project_id: int,
    req: SceneImportRequest,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
    db: AsyncSession = Depends(get_db),
):
    import json
    import logging
    from app.services.scene_service import SceneService
    from app.models.test_scene import TestScene
    from app.models.scene_step import SceneStep
    from app.models.api_definition import ApiDefinition
    from app.models.test_case import TestCase
    from app.schemas.scene import SceneCreate
    from app.core.exceptions import raise_biz, ErrorCodes

    _logger = logging.getLogger("api_pilot.routers.scenes")

    s = SceneService(db)
    data = req.data

    # 预收集步骤中引用的 api_id 和 test_case_id，批量校验其是否存在于当前项目
    referenced_api_ids = {sd.api_id for sd in data.steps if sd.api_id is not None}
    referenced_case_ids = {sd.test_case_id for sd in data.steps if sd.test_case_id is not None}
    valid_api_ids: set[int] = set()
    valid_case_ids: set[int] = set()
    if referenced_api_ids:
        api_rows = await db.execute(
            select(ApiDefinition.id).where(
                ApiDefinition.id.in_(referenced_api_ids),
                ApiDefinition.project_id == project_id,
            )
        )
        valid_api_ids = {r[0] for r in api_rows.all()}
    if referenced_case_ids:
        case_rows = await db.execute(
            select(TestCase.id).where(
                TestCase.id.in_(referenced_case_ids),
                TestCase.project_id == project_id,
            )
        )
        valid_case_ids = {r[0] for r in case_rows.all()}

    # Bug 16 修复：真正的覆盖逻辑——overwrite=True 且指定 target_scene_id 时更新已有场景，否则创建新场景
    if req.overwrite and req.target_scene_id:
        scene_result = await db.execute(
            select(TestScene).where(
                TestScene.id == req.target_scene_id,
                TestScene.project_id == project_id,
                TestScene.deleted_at.is_(None),
            )
        )
        scene = scene_result.scalar_one_or_none()
        if not scene:
            raise_biz(ErrorCodes.SCENE_NOT_FOUND, f"目标场景 {req.target_scene_id} 不存在")
        # 更新场景基本信息
        if data.name:
            scene.name = data.name
        if data.description:
            scene.description = data.description
        # 使用嵌套事务保护：删除旧步骤 + 插入新步骤，若插入失败则回滚保留旧步骤
        async with db.begin_nested():
            # 删除旧步骤，稍后用导入数据重建
            from sqlalchemy import delete
            await db.execute(
                delete(SceneStep).where(SceneStep.scene_id == scene.id)
            )
            for i, step_data in enumerate(data.steps):
                # 校验 api_id / test_case_id 是否存在于当前项目，不存在则跳过该步骤
                if step_data.api_id is not None and step_data.api_id not in valid_api_ids:
                    _logger.warning("导入跳过步骤 %d: api_id=%d 在项目 %d 中不存在", i + 1, step_data.api_id, project_id)
                    continue
                if step_data.test_case_id is not None and step_data.test_case_id not in valid_case_ids:
                    _logger.warning("导入跳过步骤 %d: test_case_id=%d 在项目 %d 中不存在", i + 1, step_data.test_case_id, project_id)
                    continue
                # 兼容字段：step_type 回退到 node_type，name 回退到 label
                node_type = step_data.node_type or step_data.step_type or "request"
                label = step_data.label or step_data.name or f"Step {i + 1}"
                # assertions 可能是 list（旧格式）或 str（JSON 字符串），统一转为字符串
                assertions = step_data.assertions
                if assertions is not None and not isinstance(assertions, str):
                    assertions = json.dumps(assertions, ensure_ascii=False)
                step = SceneStep(
                    scene_id=scene.id,
                    sort_order=i + 1,
                    node_id=step_data.node_id,
                    node_type=node_type,
                    label=label,
                    api_id=step_data.api_id,
                    test_case_id=step_data.test_case_id,
                    enabled=1 if step_data.enabled else 0,
                    timeout=step_data.timeout,
                    retry_count=step_data.retry_count,
                    request_body=step_data.request_body,
                    headers=step_data.headers,
                    query_params=step_data.query_params,
                    assertions=assertions,
                    extract_vars=step_data.extract_vars,
                    condition_expression=step_data.condition_expression,
                    loop_count=step_data.loop_count,
                    loop_variable=step_data.loop_variable,
                    wait_duration=step_data.wait_duration,
                    wait_mode=step_data.wait_mode or "fixed",
                    wait_min=step_data.wait_min,
                    wait_max=step_data.wait_max,
                    parallel_group=step_data.parallel_group,
                )
                db.add(step)
    else:
        # 创建新场景
        scene_req = SceneCreate(name=data.name, description=data.description)
        scene = await s.create(project_id, scene_req)
        for i, step_data in enumerate(data.steps):
            # 校验 api_id / test_case_id 是否存在于当前项目，不存在则跳过该步骤
            if step_data.api_id is not None and step_data.api_id not in valid_api_ids:
                _logger.warning("导入跳过步骤 %d: api_id=%d 在项目 %d 中不存在", i + 1, step_data.api_id, project_id)
                continue
            if step_data.test_case_id is not None and step_data.test_case_id not in valid_case_ids:
                _logger.warning("导入跳过步骤 %d: test_case_id=%d 在项目 %d 中不存在", i + 1, step_data.test_case_id, project_id)
                continue
            # 兼容字段：step_type 回退到 node_type，name 回退到 label
            node_type = step_data.node_type or step_data.step_type or "request"
            label = step_data.label or step_data.name or f"Step {i + 1}"
            # assertions 可能是 list（旧格式）或 str（JSON 字符串），统一转为字符串
            assertions = step_data.assertions
            if assertions is not None and not isinstance(assertions, str):
                assertions = json.dumps(assertions, ensure_ascii=False)
            step = SceneStep(
                scene_id=scene.id,
                sort_order=i + 1,
                node_id=step_data.node_id,
                node_type=node_type,
                label=label,
                api_id=step_data.api_id,
                test_case_id=step_data.test_case_id,
                enabled=1 if step_data.enabled else 0,
                timeout=step_data.timeout,
                retry_count=step_data.retry_count,
                request_body=step_data.request_body,
                headers=step_data.headers,
                query_params=step_data.query_params,
                assertions=assertions,
                extract_vars=step_data.extract_vars,
                condition_expression=step_data.condition_expression,
                loop_count=step_data.loop_count,
                loop_variable=step_data.loop_variable,
                wait_duration=step_data.wait_duration,
                wait_mode=step_data.wait_mode or "fixed",
                wait_min=step_data.wait_min,
                wait_max=step_data.wait_max,
                parallel_group=step_data.parallel_group,
            )
            db.add(step)
    await db.flush()
    return success(
        {"id": scene.id, "name": scene.name, "steps_count": len(data.steps)}
    )


# ── 数据集管理接口 ──


class DatasetCreate(BaseModel):
    name: str
    data: list[dict]
    type: str = "json"


class DatasetUpdate(BaseModel):
    name: str | None = None
    data: list[dict] | None = None
    type: str | None = None


@router.get("/{scene_id}/datasets", summary="获取场景数据集列表")
async def list_datasets(
    project_id: int,
    scene_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=0, ge=0, le=100),
    current_user: User | None = Depends(get_optional_user),
    _project: Project = Depends(check_read_access),
    db: AsyncSession = Depends(get_db),
):
    from app.models.scene_dataset import SceneDataset
    from sqlalchemy import func

    base_query = select(SceneDataset).where(SceneDataset.scene_id == scene_id)
    total = await db.scalar(
        select(func.count(SceneDataset.id)).where(SceneDataset.scene_id == scene_id)
    ) or 0

    if page_size > 0:
        base_query = base_query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(base_query.order_by(SceneDataset.id))
    datasets = result.scalars().all()
    import json

    items = [
        {
            "id": d.id,
            "scene_id": d.scene_id,
            "name": d.name,
            "data": json.loads(d.data) if d.data else [],
            "type": d.type,
            "created_at": d.created_at.isoformat() if d.created_at else None,
        }
        for d in datasets
    ]
    if page_size > 0:
        return success({"items": items, "total": total, "page": page, "page_size": page_size})
    return success(items)


@router.post("/{scene_id}/datasets", summary="创建数据集")
async def create_dataset(
    project_id: int,
    scene_id: int,
    req: DatasetCreate,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
    db: AsyncSession = Depends(get_db),
):
    import json
    from app.models.scene_dataset import SceneDataset

    ds = SceneDataset(
        scene_id=scene_id,
        name=req.name,
        data=json.dumps(req.data, ensure_ascii=False),
        type=req.type,
    )
    db.add(ds)
    await db.flush()
    return success({"id": ds.id, "name": ds.name, "type": ds.type})


@router.put("/{scene_id}/datasets/{dataset_id}", summary="更新数据集")
async def update_dataset(
    project_id: int,
    scene_id: int,
    dataset_id: int,
    req: DatasetUpdate,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
    db: AsyncSession = Depends(get_db),
):
    import json
    from app.models.scene_dataset import SceneDataset

    ds = await db.get(SceneDataset, dataset_id)
    if not ds or ds.scene_id != scene_id:
        from app.core.exceptions import raise_biz, ErrorCodes

        raise_biz(ErrorCodes.NOT_FOUND, "数据集不存在")
    if req.name is not None:
        ds.name = req.name
    if req.data is not None:
        ds.data = json.dumps(req.data, ensure_ascii=False)
    if req.type is not None:
        ds.type = req.type
    await db.flush()
    return success({"id": ds.id, "name": ds.name})


@router.delete("/{scene_id}/datasets/{dataset_id}", summary="删除数据集")
async def delete_dataset(
    project_id: int,
    scene_id: int,
    dataset_id: int,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
    db: AsyncSession = Depends(get_db),
):
    from app.models.scene_dataset import SceneDataset

    ds = await db.get(SceneDataset, dataset_id)
    if not ds or ds.scene_id != scene_id:
        from app.core.exceptions import raise_biz, ErrorCodes

        raise_biz(ErrorCodes.NOT_FOUND, "数据集不存在")
    await db.delete(ds)
    await db.flush()
    return success(message="数据集已删除")
