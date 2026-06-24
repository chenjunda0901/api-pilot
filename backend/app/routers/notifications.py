"""通知系统：查询、标记已读、批量已读、SSE 实时推送"""
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.models.notification import Notification
from app.utils.response import success

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", summary="通知列表", description="获取当前用户的通知列表")
async def list_notifications(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    unread_only: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)):

    query = select(Notification).where(Notification.user_id == current_user.id)
    count_query = select(func.count(Notification.id)).where(Notification.user_id == current_user.id)

    if unread_only:
        query = query.where(Notification.is_read == 0)
        count_query = count_query.where(Notification.is_read == 0)

    total = await db.scalar(count_query) or 0
    result = await db.execute(
        query.order_by(Notification.created_at.desc())
        .offset((page - 1) * page_size).limit(page_size))
    items = []
    for n in result.scalars().all():
        items.append({
            "id": n.id, "type": n.type, "title": n.title,
            "content": n.content, "is_read": bool(n.is_read),
            "link": n.link, "created_at": str(n.created_at),
        })

    # 未读计数
    unread = await db.scalar(
        select(func.count(Notification.id)).where(
            Notification.user_id == current_user.id, Notification.is_read == 0)) or 0

    return success({"items": items, "total": total, "unread": unread, "page": page, "page_size": page_size})


from app.services.sse_manager import sse_manager


@router.get("/stream", summary="SSE 通知流", description="通过 Server-Sent Events 实时推送通知（需使用 EventSource 连接）")
async def notification_stream(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """SSE 实时通知推送端点。

    前端用法：
        const es = new EventSource('/api/notifications/stream?token=' + accessToken)
        es.addEventListener('notification', (e) => {
            const data = JSON.parse(e.data)
            // data = { id, type, title, content, link, created_at }
        })
        es.addEventListener('heartbeat', () => {})
    """
    return StreamingResponse(
        sse_manager.event_generator(current_user.id, request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用 Nginx 缓冲
        },
    )


@router.get("/unread-count", summary="未读数量", description="获取当前用户未读通知数量")
async def unread_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)):
    count = await db.scalar(
        select(func.count(Notification.id)).where(
            Notification.user_id == current_user.id, Notification.is_read == 0)) or 0
    return success({"unread": count})


@router.put("/{notification_id}/read", summary="标记已读", description="标记指定通知为已读")
async def mark_read(notification_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)):
    await db.execute(
        update(Notification)
        .where(Notification.id == notification_id, Notification.user_id == current_user.id)
        .values(is_read=1))
    await db.flush()
    return success(message="Marked as read")


@router.put("/read-all", summary="全部已读", description="标记所有通知为已读")
async def mark_all_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)):
    await db.execute(
        update(Notification)
        .where(Notification.user_id == current_user.id, Notification.is_read == 0)
        .values(is_read=1))
    await db.flush()
    return success(message="All marked as read")


@router.delete("/{notification_id}", summary="删除通知", description="删除指定通知")
async def delete_notification(notification_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)):
    from app.core.exceptions import raise_biz, ErrorCodes
    result = await db.execute(
        select(Notification).where(Notification.id == notification_id, Notification.user_id == current_user.id))
    notif = result.scalar_one_or_none()
    if not notif:
        raise_biz(ErrorCodes.NOT_FOUND)
    await db.delete(notif)
    await db.flush()
    return success(message="Notification deleted")
