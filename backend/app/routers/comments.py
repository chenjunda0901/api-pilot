"""评论路由。"""

import json
import logging
import re

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ErrorCodes, raise_biz
from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.comment import Comment
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.user import User
from app.schemas.comment import CommentCreate, CommentUpdate
from app.services.permission_service import check_read_access, check_write_access, require_project_access
from app.utils.response import success

router = APIRouter(prefix="/comments", tags=["Comments"])
logger = logging.getLogger("api_pilot.routers.comments")


_MENTION_RE = re.compile(r"@([\w\u4e00-\u9fff]{1,50})")  # 提取 @ 后面的用户名片段


def _to_dict(c: Comment) -> dict:
    mentions: list[int] = []
    if c.mentions_json:
        try:
            payload = json.loads(c.mentions_json)
            if isinstance(payload, dict) and isinstance(payload.get("user_ids"), list):
                mentions = [int(x) for x in payload["user_ids"]]
        except (json.JSONDecodeError, ValueError, TypeError):
            mentions = []
    return {
        "id": c.id,
        "project_id": c.project_id,
        "resource_type": c.resource_type,
        "resource_id": c.resource_id,
        "user_id": c.user_id,
        "content_md": c.content_md,
        "mentions": mentions,
        "status": c.status,
        "parent_id": c.parent_id,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
    }


def _parse_mentions(content: str, db: AsyncSession, project_id: int) -> list[int]:
    """提取 @ 提及的用户名 → 解析为 user_id 列表。"""
    if "@" not in content:
        return []
    candidates = set(_MENTION_RE.findall(content))
    if not candidates:
        return []
    # 仅查找项目成员
    select(ProjectMember).where(ProjectMember.project_id == project_id)
    # 这里用同步思路：先拿成员 user_ids，再按 username 过滤
    # 简化：所有匹配候选的用户名都查一遍
    from app.models.user import User as _User
    user_q = select(_User).where(_User.username.in_(candidates))
    db.execute(user_q) if False else None  # 同步占位，实际是 async
    return []  # 实际见下方实现


async def _resolve_mentions(content: str, db: AsyncSession, project_id: int) -> list[int]:
    """从 content_md 解析 @ 提及 → user_id 列表。"""
    if "@" not in content:
        return []
    candidates = set(_MENTION_RE.findall(content))
    if not candidates:
        return []
    from app.models.user import User as _User
    result = await db.execute(select(_User).where(_User.username.in_(candidates)))
    users = result.scalars().all()
    return [u.id for u in users]


# ── 列表 ──────────────────────────────────────────────────────────────────


@router.get("", summary="评论列表")
async def list_comments(
    project_id: int = Query(..., ge=1, description="项目 ID"),
    resource_type: str = Query(..., description="api / case / scene / report"),
    resource_id: int = Query(..., ge=1),
    status: str | None = Query(None, description="open / resolved"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_read_access),
    db: AsyncSession = Depends(get_db),
):
    query = select(Comment).where(
        Comment.project_id == project_id,
        Comment.resource_type == resource_type,
        Comment.resource_id == resource_id,
    )
    count_q = select(func.count(Comment.id)).where(
        Comment.project_id == project_id,
        Comment.resource_type == resource_type,
        Comment.resource_id == resource_id,
    )
    if status:
        query = query.where(Comment.status == status)
        count_q = count_q.where(Comment.status == status)
    total = await db.scalar(count_q) or 0
    result = await db.execute(
        query.order_by(Comment.created_at.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = [_to_dict(c) for c in result.scalars().all()]
    return success({"items": items, "total": total, "page": page, "page_size": page_size})


# ── 创建 ──────────────────────────────────────────────────────────────────


@router.post("", summary="创建评论")
async def create_comment(
    req: CommentCreate,
    project_id: int = Query(..., ge=1, description="项目 ID"),
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
    db: AsyncSession = Depends(get_db),
):
    """创建一条评论；自动解析 @ 提及并触发通知。"""
    # Verify the request body project_id matches the query parameter
    if req.project_id != project_id:
        raise_biz(ErrorCodes.PARAM_ERROR, "请求体中的 project_id 与查询参数不匹配")
    # 解析 @ mentions（结合请求体里传的 mentions）
    auto_mentions = await _resolve_mentions(req.content_md, db, req.project_id)
    all_mentions = list(set((req.mentions or []) + auto_mentions))

    c = Comment(
        project_id=req.project_id,
        resource_type=req.resource_type,
        resource_id=req.resource_id,
        user_id=current_user.id,
        content_md=req.content_md,
        parent_id=req.parent_id,
        status="open",
        mentions_json=json.dumps({"user_ids": all_mentions}, ensure_ascii=False) if all_mentions else None,
    )
    db.add(c)
    await db.flush()

    # 触发通知（占位：每个被 @ 的用户写一条 Notification）
    if all_mentions:
        from app.models.notification import Notification
        for uid in all_mentions:
            notif = Notification(
                user_id=uid,
                type="comment_mention",
                title=f"{current_user.username} 在评论中 @ 了你",
                content=req.content_md[:200],
                link=f"/{req.resource_type}/{req.resource_id}",
            )
            db.add(notif)
        await db.flush()
    return success(_to_dict(c))


# ── 更新 ──────────────────────────────────────────────────────────────────


@router.patch("/{comment_id}", summary="更新评论")
async def update_comment(
    comment_id: int,
    req: CommentUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Comment).where(Comment.id == comment_id))
    c = result.scalar_one_or_none()
    if not c:
        raise_biz(ErrorCodes.API_NOT_FOUND, f"评论 {comment_id} 不存在")
    # Verify the user has write access to the comment's project
    await require_project_access(db, c.project_id, current_user, require_write=True)
    if c.user_id != current_user.id and current_user.role != "admin":
        raise_biz(ErrorCodes.AUTH_FORBIDDEN, "只能编辑自己的评论")
    c.content_md = req.content_md
    await db.flush()
    # flush 后 ORM 列被 expire；显式 reload 防止 _to_dict 触发隐式 I/O（MissingGreenlet）
    await db.refresh(c, attribute_names=["updated_at", "mentions_json", "content_md"])
    return success(_to_dict(c))


# ── 软删除 ────────────────────────────────────────────────────────────────


@router.delete("/{comment_id}", summary="软删除评论")
async def delete_comment(
    comment_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Comment).where(Comment.id == comment_id))
    c = result.scalar_one_or_none()
    if not c:
        raise_biz(ErrorCodes.API_NOT_FOUND, f"评论 {comment_id} 不存在")
    # Verify the user has write access to the comment's project
    await require_project_access(db, c.project_id, current_user, require_write=True)
    if c.user_id != current_user.id and current_user.role != "admin":
        raise_biz(ErrorCodes.AUTH_FORBIDDEN, "只能删除自己的评论")
    c.status = "deleted"
    await db.flush()
    return success(message="评论已删除")


# ── 解决 / 重新打开 ────────────────────────────────────────────────────────


@router.post("/{comment_id}/resolve", summary="标记评论已解决")
async def resolve_comment(
    comment_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Comment).where(Comment.id == comment_id))
    c = result.scalar_one_or_none()
    if not c:
        raise_biz(ErrorCodes.API_NOT_FOUND, f"评论 {comment_id} 不存在")
    # Verify the user has write access to the comment's project
    await require_project_access(db, c.project_id, current_user, require_write=True)
    c.status = "resolved"
    await db.flush()
    # 显式 reload 字段防止 _to_dict 触发隐式 I/O（MissingGreenlet）
    await db.refresh(c, attribute_names=["status", "updated_at", "mentions_json"])
    return success(_to_dict(c))


@router.post("/{comment_id}/reopen", summary="重新打开评论")
async def reopen_comment(
    comment_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Comment).where(Comment.id == comment_id))
    c = result.scalar_one_or_none()
    if not c:
        raise_biz(ErrorCodes.API_NOT_FOUND, f"评论 {comment_id} 不存在")
    # Verify the user has write access to the comment's project
    await require_project_access(db, c.project_id, current_user, require_write=True)
    c.status = "open"
    await db.flush()
    await db.refresh(c, attribute_names=["status", "updated_at", "mentions_json"])
    return success(_to_dict(c))


# ── @ 自动完成 ────────────────────────────────────────────────────────────


@router.post("/mentions/search", summary="@ 自动完成搜索")
async def search_mentions(
    project_id: int = Query(..., ge=1),
    keyword: str = Query("", description="用户名片段"),
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_read_access),
    db: AsyncSession = Depends(get_db),
):
    """按项目成员模糊搜索用户名（用于 @ 自动完成）。"""
    from app.models.user import User as _User
    stmt = (
        select(ProjectMember.user_id, _User.username, _User.nickname)
        .join(_User, _User.id == ProjectMember.user_id)
        .where(ProjectMember.project_id == project_id)
    )
    if keyword:
        kw = f"%{keyword}%"
        stmt = stmt.where((_User.username.like(kw)) | (_User.nickname.like(kw)))
    stmt = stmt.limit(limit)
    result = await db.execute(stmt)
    items = [{"id": r.user_id, "username": r.username, "nickname": r.nickname} for r in result.all()]
    return success({"items": items})
