from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user, get_optional_user
from app.models.user import User
from app.models.project import Project
from app.models.test_case import TestCase
from app.schemas.case import CaseCreate, CaseUpdate, AssertionCreate, AssertionUpdate, AssertionTestRequest
from app.schemas.api import BatchIdsRequest
from app.services.case_service import CaseService
from app.services.permission_service import check_read_access, check_write_access, check_seed_mark_access
from app.utils.response import success
router = APIRouter(prefix="/projects/{project_id}/cases", tags=["Test Cases"])

# 统一的断言类型集合，供 create_case 与 create_case_assertion 共用
ALLOWED_ASSERTION_TYPES = {
    "status", "jsonpath", "jsonschema", "regex", "header",
    "response_time", "body_contains", "duration", "cookie",
}


@router.get("", summary="用例列表", description="获取项目下的测试用例列表，支持分页筛选")
async def list_cases(project_id: int, api_id: int | None = Query(None),
    status: str | None = Query(None), case_type: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User | None = Depends(get_optional_user),
    _project: Project = Depends(check_read_access),
    db: AsyncSession = Depends(get_db)):
    s = CaseService(db)
    items, total = await s.list(project_id, api_id, status, case_type, page, page_size)
    return success({"items": items, "total": total, "page": page, "page_size": page_size})


@router.get("/{case_id}", summary="用例详情", description="获取指定测试用例的完整信息")
async def get_case(project_id: int, case_id: int,
    current_user: User | None = Depends(get_optional_user),
    _project: Project = Depends(check_read_access),
    db: AsyncSession = Depends(get_db)):
    s = CaseService(db)
    return success(s.to_dict(await s.get(case_id, project_id)))


@router.post("", summary="创建用例", description="为接口创建参数化的测试用例")
async def create_case(project_id: int, req: CaseCreate,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
    db: AsyncSession = Depends(get_db)):

    # Validate API exists
    from app.models.api_definition import ApiDefinition
    api_result = await db.execute(
        select(ApiDefinition).where(
            ApiDefinition.id == req.api_id,
            ApiDefinition.project_id == project_id,
            ApiDefinition.deleted_at.is_(None)
        )
    )
    api = api_result.scalar_one_or_none()
    if not api:
        from app.core.exceptions import raise_biz, ErrorCodes
        raise_biz(ErrorCodes.API_NOT_FOUND, f"接口 {req.api_id} 不存在")

    # Validate request_body format if provided
    if req.request_body:
        import json
        try:
            json.loads(req.request_body)
        except json.JSONDecodeError as e:
            from app.core.exceptions import raise_biz, ErrorCodes
            raise_biz(ErrorCodes.PARAM_ERROR, f"请求体格式错误: {str(e)}")

    # Validate assertions format
    if req.assertions and not isinstance(req.assertions, list):
        from app.core.exceptions import raise_biz, ErrorCodes
        raise_biz(ErrorCodes.PARAM_ERROR, "断言规则必须是数组格式")

    # Validate assertions element format
    # Frontend AssertionTab uses `type` field; ApiAssertion sub-resource uses `assertion_type`.
    # Accept both for compatibility.
    if req.assertions:
        from app.core.exceptions import raise_biz, ErrorCodes
        for i, assertion in enumerate(req.assertions):
            if not isinstance(assertion, dict):
                raise_biz(ErrorCodes.PARAM_ERROR, f"断言规则第 {i+1} 项必须是对象格式")
            atype = assertion.get("assertion_type") or assertion.get("type")
            if not atype:
                raise_biz(ErrorCodes.PARAM_ERROR, f"断言规则第 {i+1} 项缺少 assertion_type/type 字段")
            if atype not in ALLOWED_ASSERTION_TYPES:
                raise_biz(ErrorCodes.PARAM_ERROR, f"断言规则第 {i+1} 项 assertion_type 无效，允许值: {', '.join(sorted(ALLOWED_ASSERTION_TYPES))}")

    # Validate extract_vars format
    if req.extract_vars and not isinstance(req.extract_vars, list):
        from app.core.exceptions import raise_biz, ErrorCodes
        raise_biz(ErrorCodes.PARAM_ERROR, "变量提取规则必须是数组格式")

    # Validate extract_vars element format
    if req.extract_vars:
        from app.core.exceptions import raise_biz, ErrorCodes
        for i, rule in enumerate(req.extract_vars):
            if not isinstance(rule, dict):
                raise_biz(ErrorCodes.PARAM_ERROR, f"变量提取规则第 {i+1} 项必须是对象格式")
            if not rule.get("variable"):
                raise_biz(ErrorCodes.PARAM_ERROR, f"变量提取规则第 {i+1} 项缺少 variable 字段")

    s = CaseService(db)
    return success(s.to_dict(await s.create(project_id, req)))


@router.put("/{case_id}", summary="更新用例", description="修改测试用例的参数和配置")
async def update_case(project_id: int, case_id: int, req: CaseUpdate,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
    db: AsyncSession = Depends(get_db)):
    s = CaseService(db)
    return success(s.to_dict(await s.update(case_id, req, project_id)))


@router.delete("/{case_id}", summary="删除用例", description="删除指定的测试用例")
async def delete_case(project_id: int, case_id: int,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
    db: AsyncSession = Depends(get_db)):
    s = CaseService(db)
    await s.delete(case_id, project_id)
    return success(message="用例已移至回收站")


@router.get("/recycle/list", summary="用例回收站", description="列出已软删除的测试用例")
async def list_deleted_cases(project_id: int,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_read_access),
    db: AsyncSession = Depends(get_db)):
    s = CaseService(db)
    return success({"items": await s.list_deleted(project_id)})


@router.post("/{case_id}/restore", summary="恢复用例", description="从回收站恢复用例")
async def restore_case(project_id: int, case_id: int,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
    db: AsyncSession = Depends(get_db)):
    s = CaseService(db)
    result = await s.restore(case_id, project_id)
    return success(result)


@router.delete("/{case_id}/permanent", summary="永久删除用例", description="从数据库永久移除用例")
async def permanent_delete_case(project_id: int, case_id: int,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
    db: AsyncSession = Depends(get_db)):
    s = CaseService(db)
    await s.permanent_delete(case_id, project_id)
    return success(message="用例已永久删除")


@router.put("/batch/update", summary="批量更新用例", description="批量更新用例的优先级和标签")
async def batch_update_cases(project_id: int, req: BatchIdsRequest,
    priority: str = Query("", description="新优先级：P0/P1/P2/P3，空=不变"),
    tags: str = Query("", description="新标签，空=不变"),
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
    db: AsyncSession = Depends(get_db)):

    id_list = [n for n in req.ids if 1 <= n <= 999999999]
    if not id_list:
        return success(message="未提供有效的 ID")
    verify = await db.execute(
        select(TestCase.id).where(
            TestCase.id.in_(id_list),
            TestCase.project_id == project_id
        )
    )
    valid_ids = [r[0] for r in verify.all()]
    skipped_ids = [n for n in req.ids if n not in set(valid_ids)]
    if valid_ids and (priority or tags):
        s = CaseService(db)
        await s.batch_update(valid_ids, priority=priority or None, tags=tags or None)
    return success({"success_count": len(valid_ids), "skipped_ids": skipped_ids}, message=f"已更新 {len(valid_ids)} 条用例")


@router.delete("/batch", summary="批量删除用例", description="同时删除多个测试用例")
async def batch_delete_cases(project_id: int, req: BatchIdsRequest,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
    db: AsyncSession = Depends(get_db)):
    id_list = [n for n in req.ids if 1 <= n <= 999999999]
    if not id_list:
        return success(message="未提供有效的 ID")
    verify = await db.execute(
        select(TestCase.id).where(
            TestCase.id.in_(id_list),
            TestCase.project_id == project_id
        )
    )
    valid_ids = [r[0] for r in verify.all()]
    skipped_ids = [n for n in req.ids if n not in set(valid_ids)]
    if valid_ids:
        s = CaseService(db)
        await s.batch_delete(valid_ids)
    return success({"success_count": len(valid_ids), "skipped_ids": skipped_ids}, message=f"已删除 {len(valid_ids)} 条用例")


@router.put("/{case_id}/seed-mark", summary="标记/取消标记为种子", description="管理员将用例标记为种子数据，下次重置种子时保留；再次调用可取消标记")
async def mark_case_as_seed(project_id: int, case_id: int,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_seed_mark_access),
    db: AsyncSession = Depends(get_db)):
    if current_user.role != "admin":
        from app.core.exceptions import raise_biz, ErrorCodes
        raise_biz(ErrorCodes.PROJECT_FORBIDDEN, "仅管理员可标记种子数据")
    from sqlalchemy import select
    from app.models.project import Project
    result = await db.execute(select(TestCase).where(TestCase.id == case_id, TestCase.project_id == project_id).limit(1))
    case = result.scalar_one_or_none()
    if not case:
        from app.core.exceptions import raise_biz, ErrorCodes
        raise_biz(ErrorCodes.NOT_FOUND, "用例不存在")
    # 种子标记仅对全局种子项目（global_demo=1）有效
    project = await db.get(Project, case.project_id)
    if not project or project.global_demo != 1:
        from app.core.exceptions import raise_biz, ErrorCodes
        raise_biz(ErrorCodes.PARAM_ERROR, "种子标记仅对全局种子项目生效")
    case.is_seed = 1 if case.is_seed == 0 else 0
    await db.flush()
    return success({"is_seed": case.is_seed, "message": "已标记为种子" if case.is_seed else "已取消种子标记"})


class CasesToSceneRequest(BaseModel):
    """用例转场景请求"""
    case_ids: list[int] = Field(..., description="用例ID列表", min_length=1)
    scene_name: str = Field(..., description="新场景名称", min_length=1, max_length=200)
    scene_description: str | None = Field(None, description="场景描述")
    target_scene_id: int | None = Field(None, description="目标场景ID（为空则创建新场景）")


@router.post("/batch/to-scene", summary="用例转场景", description="将选中的测试用例批量转换为场景步骤")
async def cases_to_scene(
    project_id: int,
    req: CasesToSceneRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
):
    """批量将用例转换为场景步骤"""
    from app.core.exceptions import raise_biz, ErrorCodes
    from app.models.test_scene import TestScene
    from app.models.scene_step import SceneStep

    CaseService(db)

    # 验证用例存在且属于项目
    result = await db.execute(
        select(TestCase).where(
            TestCase.id.in_(req.case_ids),
            TestCase.project_id == project_id,
        )
    )
    cases = result.scalars().all()

    if not cases:
        raise_biz(ErrorCodes.CASE_NOT_FOUND, "未找到匹配的用例")

    # 目标场景
    target_scene_id = req.target_scene_id
    if not target_scene_id:
        # 创建新场景
        new_scene = TestScene(
            project_id=project_id,
            name=req.scene_name,
            description=req.scene_description or "",
            created_by=current_user.id,
        )
        db.add(new_scene)
        await db.flush()
        target_scene_id = new_scene.id
    else:
        # 验证目标场景存在且属于项目
        scene_result = await db.execute(
            select(TestScene).where(
                TestScene.id == target_scene_id,
                TestScene.project_id == project_id,
            )
        )
        target_scene = scene_result.scalar_one_or_none()
        if not target_scene:
            raise_biz(ErrorCodes.SCENE_NOT_FOUND, f"目标场景 {target_scene_id} 不存在")

    # 查询目标场景当前最大 sort_order
    max_order_result = await db.execute(
        select(SceneStep.sort_order)
        .where(SceneStep.scene_id == target_scene_id)
        .order_by(SceneStep.sort_order.desc())
        .limit(1)
    )
    max_order = max_order_result.scalar_one_or_none() or 0

    # 批量创建步骤
    created_steps = []
    for idx, case in enumerate(cases):
        step = SceneStep(
            scene_id=target_scene_id,
            test_case_id=case.id,
            sort_order=max_order + idx + 1,
            enabled=1,
            label=case.name,
        )
        db.add(step)
        created_steps.append(step)

    await db.flush()

    return success({
        "scene_id": target_scene_id,
        "scene_name": req.scene_name,
        "created_steps": len(created_steps),
        "step_ids": [s.id for s in created_steps],
    })


# =============================================================================
#  阶段 3 增强：用例下挂载断言（CRUD 子路由）
# =============================================================================
#  - GET    /{id}/assertions            列出该用例的所有断言
#  - POST   /{id}/assertions            批量创建断言
#  - PATCH  /{id}/assertions/{aid}      更新某条断言
#  - DELETE /{id}/assertions/{aid}      删除某条断言
#  - POST   /{id}/assertions/test       临时测试断言（沿用 AssertionRunner）
# =============================================================================


@router.get("/{case_id}/assertions", summary="用例的断言列表")
async def list_case_assertions(
    project_id: int,
    case_id: int,
    current_user: User | None = Depends(get_optional_user),
    _project: Project = Depends(check_read_access),
    db: AsyncSession = Depends(get_db),
):
    """列出指定用例下挂载的所有断言。"""
    from app.models.api_assertion import ApiAssertion
    s = CaseService(db)
    await s.get(case_id, project_id)
    result = await db.execute(
        select(ApiAssertion)
        .where(ApiAssertion.owner_type == "case", ApiAssertion.owner_id == case_id)
        .order_by(ApiAssertion.order_index, ApiAssertion.id)
    )
    items = [
        {
            "id": a.id,
            "owner_type": a.owner_type,
            "owner_id": a.owner_id,
            "assertion_type": a.assertion_type,
            "expression": a.expression,
            "operator": a.operator,
            "expected_value": a.expected_value,
            "enabled": bool(a.enabled),
            "order_index": a.order_index,
        }
        for a in result.scalars().all()
    ]
    return success({"items": items, "total": len(items)})


@router.post("/{case_id}/assertions", summary="为用例创建一条断言")
async def create_case_assertion(
    project_id: int,
    case_id: int,
    payload: AssertionCreate,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
    db: AsyncSession = Depends(get_db),
):
    """用例下创建一条断言。"""
    from app.core.exceptions import raise_biz, ErrorCodes
    from app.models.api_assertion import ApiAssertion
    s = CaseService(db)
    await s.get(case_id, project_id)
    if payload.assertion_type not in ALLOWED_ASSERTION_TYPES:
        raise_biz(ErrorCodes.PARAM_ERROR, f"不支持的 assertion_type，允许值: {', '.join(sorted(ALLOWED_ASSERTION_TYPES))}")
    a = ApiAssertion(
        owner_type="case",
        owner_id=case_id,
        assertion_type=payload.assertion_type,
        expression=payload.expression,
        operator=payload.operator,
        expected_value=payload.expected_value,
        enabled=1 if payload.enabled else 0,
        order_index=payload.order_index,
    )
    db.add(a)
    await db.flush()
    return success({"id": a.id, "owner_type": a.owner_type, "owner_id": a.owner_id})


@router.patch("/{case_id}/assertions/{assertion_id}", summary="更新用例下的某条断言")
async def update_case_assertion(
    project_id: int,
    case_id: int,
    assertion_id: int,
    payload: AssertionUpdate,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
    db: AsyncSession = Depends(get_db),
):
    from app.core.exceptions import raise_biz, ErrorCodes
    from app.models.api_assertion import ApiAssertion
    s = CaseService(db)
    await s.get(case_id, project_id)
    result = await db.execute(
        select(ApiAssertion).where(
            ApiAssertion.id == assertion_id,
            ApiAssertion.owner_type == "case",
            ApiAssertion.owner_id == case_id,
        )
    )
    a = result.scalar_one_or_none()
    if not a:
        raise_biz(ErrorCodes.API_NOT_FOUND, f"断言 {assertion_id} 不存在")
    for field in ("assertion_type", "expression", "operator", "expected_value", "order_index"):
        value = getattr(payload, field, None)
        if value is not None:
            setattr(a, field, value)
    if payload.enabled is not None:
        a.enabled = 1 if payload.enabled else 0
    await db.flush()
    return success({"id": a.id})


@router.delete("/{case_id}/assertions/{assertion_id}", summary="删除用例下的某条断言")
async def delete_case_assertion(
    project_id: int,
    case_id: int,
    assertion_id: int,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
    db: AsyncSession = Depends(get_db),
):
    from app.core.exceptions import raise_biz, ErrorCodes
    from app.models.api_assertion import ApiAssertion
    s = CaseService(db)
    await s.get(case_id, project_id)
    result = await db.execute(
        select(ApiAssertion).where(
            ApiAssertion.id == assertion_id,
            ApiAssertion.owner_type == "case",
            ApiAssertion.owner_id == case_id,
        )
    )
    a = result.scalar_one_or_none()
    if not a:
        raise_biz(ErrorCodes.API_NOT_FOUND, f"断言 {assertion_id} 不存在")
    await db.delete(a)
    await db.flush()
    return success(message="断言已删除")


@router.post("/{case_id}/assertions/test", summary="用例断言临时测试")
async def test_case_assertions(
    project_id: int,
    case_id: int,
    payload: AssertionTestRequest,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_read_access),
    db: AsyncSession = Depends(get_db),
):
    """用一段响应数据临时执行用例下全部断言。

    请求体::

        {
          "response_json": {...},
          "response_headers": {...},
          "duration_ms": 123
        }
    """
    from app.services.assertion_runner import AssertionRunner
    from app.models.api_assertion import ApiAssertion

    s = CaseService(db)
    await s.get(case_id, project_id)
    result = await db.execute(
        select(ApiAssertion).where(
            ApiAssertion.owner_type == "case",
            ApiAssertion.owner_id == case_id,
        )
    )
    assertions = result.scalars().all()

    class _FakeResp:
        def __init__(self, body, headers):
            self._body = body
            self.headers = _FakeH(headers or {})
            self.cookies = _FakeC({})

        def json(self):
            return self._body

    class _FakeH:
        def __init__(self, raw):
            self._raw = {k.lower(): v for k, v in raw.items()}

        def get(self, k, default=None):
            return self._raw.get(k.lower(), default)

    class _FakeC:
        def __init__(self, raw):
            self._raw = raw

        def get(self, k, default=None):
            return self._raw.get(k, default)

    fake = _FakeResp(payload.response_json, payload.response_headers)
    runner = AssertionRunner()
    results = await runner.run(fake, assertions, duration_ms=payload.duration_ms)
    out = [r.to_dict() for r in results]
    return success({
        "total": len(out),
        "passed": sum(1 for r in out if r["passed"]),
        "results": out,
    })
