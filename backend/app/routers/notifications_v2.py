"""通知 v2 路由：分页、未读计数、标记已读、批量操作、偏好设置。"""

import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select, func, update, delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ErrorCodes, raise_biz
from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.notification import Notification
from app.models.notification_preference import NotificationPreference
from app.models.user import User
from app.utils.response import success

router = APIRouter(prefix="/notifications-v2", tags=["Notifications v2"])
logger = logging.getLogger("api_pilot.routers.notifications_v2")


def _to_dict(n: Notification) -> dict:
    return {
        "id": n.id,
        "type": n.type,
        "title": n.title,
        "content": n.content,
        "is_read": bool(n.is_read),
        "link": n.link,
        "created_at": n.created_at.isoformat() if n.created_at else None,
    }


# ── 列表 ──────────────────────────────────────────────────────────────────


@router.get("", summary="当前用户通知列表（分页）")
async def list_notifications_v2(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    read: Optional[bool] = Query(None, description="true=已读 false=未读"),
    type: Optional[str] = Query(None, description="按类型过滤"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """分页 + 按 read 过滤的通知列表。"""
    query = select(Notification).where(Notification.user_id == current_user.id)
    count_q = select(func.count(Notification.id)).where(Notification.user_id == current_user.id)
    if read is not None:
        query = query.where(Notification.is_read == (1 if read else 0))
        count_q = count_q.where(Notification.is_read == (1 if read else 0))
    if type:
        query = query.where(Notification.type == type)
        count_q = count_q.where(Notification.type == type)
    total = await db.scalar(count_q) or 0
    result = await db.execute(
        query.order_by(Notification.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = [_to_dict(n) for n in result.scalars().all()]

    unread = await db.scalar(
        select(func.count(Notification.id)).where(
            Notification.user_id == current_user.id, Notification.is_read == 0)) or 0
    return success({
        "items": items, "total": total, "unread": unread,
        "page": page, "page_size": page_size,
    })


# ── 未读数量 ──────────────────────────────────────────────────────────────


@router.get("/unread-count", summary="未读数量")
async def unread_count_v2(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    count = await db.scalar(
        select(func.count(Notification.id)).where(
            Notification.user_id == current_user.id, Notification.is_read == 0)) or 0
    return success({"unread": count})


# ── 标记已读 ──────────────────────────────────────────────────────────────


@router.post("/{notification_id}/read", summary="标记已读")
async def mark_read_v2(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == current_user.id,
        )
    )
    n = result.scalar_one_or_none()
    if not n:
        raise_biz(ErrorCodes.API_NOT_FOUND, f"通知 {notification_id} 不存在")
    n.is_read = 1
    await db.flush()
    return success(_to_dict(n))


# ── 全部已读 ──────────────────────────────────────────────────────────────


@router.post("/read-all", summary="全部已读")
async def mark_all_read_v2(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        update(Notification)
        .where(Notification.user_id == current_user.id, Notification.is_read == 0)
        .values(is_read=1)
    )
    await db.flush()
    return success({"updated": result.rowcount})


# ── 批量操作 ─────────────────────────────────────────────────────────────


class BatchIdsBody(BaseModel):
    ids: list[int]


@router.post("/batch-read", summary="批量标记已读")
async def batch_read(
    body: BatchIdsBody,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not body.ids:
        return success({"updated": 0})
    result = await db.execute(
        update(Notification)
        .where(Notification.id.in_(body.ids), Notification.user_id == current_user.id, Notification.is_read == 0)
        .values(is_read=1)
    )
    await db.flush()
    return success({"updated": result.rowcount})


@router.post("/batch-delete", summary="批量删除通知")
async def batch_delete(
    body: BatchIdsBody,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not body.ids:
        return success({"deleted": 0})
    result = await db.execute(
        sa_delete(Notification)
        .where(Notification.id.in_(body.ids), Notification.user_id == current_user.id)
    )
    await db.flush()
    return success({"deleted": result.rowcount})


@router.post("/mark-all-read", summary="全部标记已读")
async def mark_all_read_post(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        update(Notification)
        .where(Notification.user_id == current_user.id, Notification.is_read == 0)
        .values(is_read=1)
    )
    await db.flush()
    return success({"updated": result.rowcount})


# ── 通知偏好 ─────────────────────────────────────────────────────────────

EVENT_TYPES = [
    "test_completed", "plan_failed", "schedule_triggered",
    "comment_mentioned", "comment_replied", "resource_shared",
    "import_completed", "export_completed", "recycle_expiring",
]

DEFAULT_PREFS = {et: {"in_app": True, "email": False, "webhook": False} for et in EVENT_TYPES}


@router.get("/projects/{project_id}/notification-preferences", summary="获取通知偏好")
async def get_notification_preferences(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(NotificationPreference).where(
            NotificationPreference.user_id == current_user.id,
            NotificationPreference.project_id == project_id,
        )
    )
    pref = result.scalar_one_or_none()
    if not pref:
        return success({"event_types": DEFAULT_PREFS})
    try:
        stored = json.loads(pref.preferences)
    except (json.JSONDecodeError, TypeError):
        stored = {}
    # 合并默认值，确保新增事件类型有默认配置
    merged = {**DEFAULT_PREFS, **stored}
    return success({"event_types": merged})


class ChannelToggles(BaseModel):
    in_app: bool = True
    email: bool = False
    webhook: bool = False


class PreferencesBody(BaseModel):
    event_types: dict[str, ChannelToggles]


@router.put("/projects/{project_id}/notification-preferences", summary="更新通知偏好")
async def update_notification_preferences(
    project_id: int,
    body: PreferencesBody,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # 序列化为 JSON
    prefs_dict = {k: v.model_dump() for k, v in body.event_types.items()}
    prefs_json = json.dumps(prefs_dict, ensure_ascii=False)

    result = await db.execute(
        select(NotificationPreference).where(
            NotificationPreference.user_id == current_user.id,
            NotificationPreference.project_id == project_id,
        )
    )
    pref = result.scalar_one_or_none()
    if pref:
        pref.preferences = prefs_json
    else:
        pref = NotificationPreference(
            user_id=current_user.id,
            project_id=project_id,
            preferences=prefs_json,
        )
        db.add(pref)
    await db.flush()
    return success({"event_types": prefs_dict})
