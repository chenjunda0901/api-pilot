"""断言库路由。"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ErrorCodes, raise_biz
from app.database import get_db
from app.middleware.auth import get_current_user, get_optional_user
from app.models.api_assertion import ApiAssertion
from app.models.user import User
from app.schemas.assertion import (
    AssertionCreate,
    AssertionUpdate,
    AssertionTestRequest,
    AssertionTestResponse,
    AssertionTestResult,
    AssertionReorderRequest,
)
from app.services.assertion_runner import AssertionRunner
from app.utils.response import success

router = APIRouter(prefix="/assertions", tags=["Assertions"])
logger = logging.getLogger("api_pilot.routers.assertions")


def _to_dict(a: ApiAssertion) -> dict:
    return {
        "id": a.id,
        "owner_type": a.owner_type,
        "owner_id": a.owner_id,
        "assertion_type": a.assertion_type,
        "expression": a.expression,
        "operator": a.operator,
        "expected_value": a.expected_value,
        "enabled": bool(a.enabled),
        "order_index": a.order_index,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }


# ── 列表 ──────────────────────────────────────────────────────────────────


@router.get("", summary="断言列表")
async def list_assertions(
    owner_type: Optional[str] = Query(None, description="api / case"),
    owner_id: Optional[int] = Query(None, ge=1),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """按 owner_type + owner_id 过滤的断言列表。"""
    query = select(ApiAssertion)
    count_q = select(func.count(ApiAssertion.id))
    if owner_type:
        query = query.where(ApiAssertion.owner_type == owner_type)
        count_q = count_q.where(ApiAssertion.owner_type == owner_type)
    if owner_id is not None:
        query = query.where(ApiAssertion.owner_id == owner_id)
        count_q = count_q.where(ApiAssertion.owner_id == owner_id)
    total = await db.scalar(count_q) or 0
    result = await db.execute(
        query.order_by(ApiAssertion.owner_type, ApiAssertion.owner_id, ApiAssertion.order_index, ApiAssertion.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = [_to_dict(a) for a in result.scalars().all()]
    return success({"items": items, "total": total, "page": page, "page_size": page_size})


# ── 创建 ──────────────────────────────────────────────────────────────────


@router.post("", summary="创建断言")
async def create_assertion(
    req: AssertionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建一条断言。"""
    a = ApiAssertion(
        owner_type=req.owner_type,
        owner_id=req.owner_id,
        assertion_type=req.assertion_type,
        expression=req.expression,
        operator=req.operator,
        expected_value=req.expected_value,
        enabled=1 if req.enabled else 0,
        order_index=req.order_index,
    )
    db.add(a)
    await db.flush()
    return success(_to_dict(a))


# ── 更新 ──────────────────────────────────────────────────────────────────


@router.patch("/{assertion_id}", summary="更新断言")
async def update_assertion(
    assertion_id: int,
    req: AssertionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """更新一条断言。"""
    result = await db.execute(select(ApiAssertion).where(ApiAssertion.id == assertion_id))
    a = result.scalar_one_or_none()
    if not a:
        raise_biz(ErrorCodes.API_NOT_FOUND, f"断言 {assertion_id} 不存在")
    data = req.model_dump(exclude_unset=True)
    if "enabled" in data:
        data["enabled"] = 1 if data["enabled"] else 0
    for field, value in data.items():
        setattr(a, field, value)
    await db.flush()
    return success(_to_dict(a))


# ── 删除 ──────────────────────────────────────────────────────────────────


@router.delete("/{assertion_id}", summary="删除断言")
async def delete_assertion(
    assertion_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ApiAssertion).where(ApiAssertion.id == assertion_id))
    a = result.scalar_one_or_none()
    if not a:
        raise_biz(ErrorCodes.API_NOT_FOUND, f"断言 {assertion_id} 不存在")
    await db.delete(a)
    await db.flush()
    return success(message="断言已删除")


# ── 临时测试断言 ──────────────────────────────────────────────────────────


@router.post("/test", summary="临时测试断言", description="用指定响应数据立即执行断言并返回 pass/fail 与 diff")
async def test_assertions(
    req: AssertionTestRequest,
    current_user: User = Depends(get_current_user),
):
    """用一段响应数据临时执行断言列表，返回每条断言的通过情况。"""
    # 构造一个伪 response（duck-type）
    class _FakeResponse:
        def __init__(self, body: dict, headers: dict | None, cookies: dict | None) -> None:
            self._body = body
            self.headers = _FakeHeaders(headers or {})
            self.cookies = _FakeCookies(cookies or {})

        def json(self):
            return self._body

    class _FakeHeaders:
        def __init__(self, raw: dict) -> None:
            self._raw = {k.lower(): v for k, v in raw.items()}

        def get(self, key: str, default=None):
            return self._raw.get(key.lower(), default)

    class _FakeCookies:
        def __init__(self, raw: dict) -> None:
            self._raw = raw

        def get(self, key: str, default=None):
            return self._raw.get(key, default)

    fake = _FakeResponse(req.response_json, req.response_headers, req.response_cookies)
    runner = AssertionRunner()
    results = await runner.run(fake, req.assertions, duration_ms=req.duration_ms)

    out: list[AssertionTestResult] = []
    passed = 0
    for r in results:
        if r.passed:
            passed += 1
        out.append(AssertionTestResult(
            expression=r.expression,
            operator=r.operator,
            expected=r.expected_value,
            actual=r.actual_value,
            passed=r.passed,
            error=r.error,
            diff=r.diff,
        ))
    return success(AssertionTestResponse(
        total=len(out),
        passed=passed,
        failed=len(out) - passed,
        results=out,
    ).model_dump())

# ── 批量重排 ──────────────────────────────────────────────────────────────


@router.post("/reorder", summary="批量重排断言顺序")
async def reorder_assertions(
    req: AssertionReorderRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """批量更新断言的 order_index。"""
    updated = 0
    for item in req.items:
        aid = item.get("id")
        order_index = item.get("order_index")
        if not aid or order_index is None:
            continue
        result = await db.execute(select(ApiAssertion).where(ApiAssertion.id == aid))
        a = result.scalar_one_or_none()
        if not a:
            continue
        a.order_index = order_index
        updated += 1
    await db.flush()
    return success({"updated": updated})
