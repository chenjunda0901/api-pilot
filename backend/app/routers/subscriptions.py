"""订阅路由。"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ErrorCodes, raise_biz
from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.api_definition import ApiDefinition
from app.models.api_test_plan import ApiTestPlan
from app.models.subscription import Subscription
from app.models.test_case import TestCase
from app.models.test_report import TestReport
from app.models.test_scene import TestScene
from app.models.user import User
from app.schemas.subscription import SubscriptionCreate
from app.services.permission_service import require_project_access
from app.utils.response import success

router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])
logger = logging.getLogger("api_pilot.routers.subscriptions")

# 资源类型 → ORM 模型映射
_RESOURCE_MODELS = {
    "api": ApiDefinition,
    "case": TestCase,
    "scene": TestScene,
    "report": TestReport,
    "plan": ApiTestPlan,
}


def _to_dict(s: Subscription) -> dict:
    return {
        "id": s.id,
        "user_id": s.user_id,
        "resource_type": s.resource_type,
        "resource_id": s.resource_id,
        "created_at": s.created_at.isoformat() if s.created_at else None,
    }


# ── 列表 ──────────────────────────────────────────────────────────────────


@router.get("", summary="当前用户的订阅列表")
async def list_subscriptions(
    resource_type: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Subscription).where(Subscription.user_id == current_user.id)
    count_q = select(func.count(Subscription.id)).where(Subscription.user_id == current_user.id)
    if resource_type:
        query = query.where(Subscription.resource_type == resource_type)
        count_q = count_q.where(Subscription.resource_type == resource_type)
    total = await db.scalar(count_q) or 0
    result = await db.execute(
        query.order_by(Subscription.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = [_to_dict(s) for s in result.scalars().all()]
    return success({"items": items, "total": total, "page": page, "page_size": page_size})


# ── 订阅 ──────────────────────────────────────────────────────────────────


@router.post("", summary="创建订阅")
async def create_subscription(
    req: SubscriptionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """订阅某个资源（已订阅则返回 200 不重复创建）。"""
    # 验证用户对资源所属项目有读权限
    model = _RESOURCE_MODELS.get(req.resource_type)
    if model:
        resource = await db.get(model, req.resource_id)
        if resource:
            project_id = getattr(resource, "project_id", None)
            if project_id is not None:
                await require_project_access(db, project_id, current_user, require_write=False)

    # 检查是否已存在
    existing = await db.execute(
        select(Subscription).where(
            Subscription.user_id == current_user.id,
            Subscription.resource_type == req.resource_type,
            Subscription.resource_id == req.resource_id,
        )
    )
    if existing.scalar_one_or_none():
        raise_biz(ErrorCodes.PROJECT_MEMBER_EXISTS, "已订阅该资源")

    s = Subscription(
        user_id=current_user.id,
        resource_type=req.resource_type,
        resource_id=req.resource_id,
    )
    db.add(s)
    try:
        await db.flush()
    except IntegrityError:
        # 并发场景下唯一约束触发
        await db.rollback()
        raise_biz(ErrorCodes.PROJECT_MEMBER_EXISTS, "已订阅该资源")
    return success(_to_dict(s))


# ── 取消订阅 ──────────────────────────────────────────────────────────────


@router.delete("/{subscription_id}", summary="取消订阅")
async def delete_subscription(
    subscription_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Subscription).where(
            Subscription.id == subscription_id,
            Subscription.user_id == current_user.id,
        )
    )
    s = result.scalar_one_or_none()
    if not s:
        raise_biz(ErrorCodes.API_NOT_FOUND, "订阅不存在")
    await db.delete(s)
    await db.flush()
    return success(message="已取消订阅")
