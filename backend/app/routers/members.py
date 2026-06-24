"""项目成员管理路由"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.models.project_member import ProjectMember
from app.schemas.member import MemberAddRequest, MemberUpdateRoleRequest
from app.services.permission_service import PermissionService
from app.utils.response import success
from app.core.exceptions import raise_biz, ErrorCodes

router = APIRouter(prefix="/projects/{project_id}/members", tags=["项目成员管理"])


async def _get_member_or_404(db: AsyncSession, project_id: int, user_id: int) -> ProjectMember:
    """获取成员记录，不存在则 404"""
    result = await db.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id,
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        raise_biz(ErrorCodes.PROJECT_MEMBER_NOT_FOUND)
    return member


@router.get("", summary="成员列表", description="获取项目的所有成员列表")
async def list_members(
    project_id: int,
    page: int = Query(default=1, ge=1, le=1000),
    page_size: int = Query(default=0, ge=0, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """列出项目所有成员及其角色"""
    # 验证项目存在且用户可读
    perm = PermissionService(db)
    await perm.check_project_access(project_id, current_user, require_write=False)

    base_query = (
        select(
            ProjectMember.id,
            ProjectMember.user_id,
            User.username,
            User.nickname,
            User.email,
            ProjectMember.role,
            ProjectMember.created_at,
        )
        .join(User, ProjectMember.user_id == User.id)
        .where(ProjectMember.project_id == project_id)
        .order_by(ProjectMember.created_at.asc())
    )

    # 统计总数
    from sqlalchemy import func
    count_query = select(func.count(ProjectMember.id)).where(
        ProjectMember.project_id == project_id
    )
    total = await db.scalar(count_query) or 0

    # 分页（page_size=0 时不分页，返回全部）
    if page_size > 0:
        base_query = base_query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(base_query)
    members = [
        {
            "id": row.id,
            "user_id": row.user_id,
            "username": row.username,
            "nickname": row.nickname,
            "email": row.email,
            "role": row.role,
            "created_at": str(row.created_at),
        }
        for row in result.all()
    ]
    if page_size > 0:
        return success({"items": members, "total": total, "page": page, "page_size": page_size})
    return success(members)


@router.post("", summary="添加成员", description="邀请用户加入项目（仅 owner/admin 可操作）")
async def add_member(
    project_id: int,
    req: MemberAddRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """邀请指定用户加入项目"""
    perm = PermissionService(db)
    await perm.check_project_access(project_id, current_user, require_write=True)

    # 验证操作者是否是 owner 或 admin
    member_role = await perm.get_project_role(project_id, current_user)
    if member_role not in ("owner", "admin"):
        raise_biz(ErrorCodes.PROJECT_FORBIDDEN, "只有项目管理员或创建者可以添加成员")

    # 验证被邀请的用户存在
    invitee = await db.get(User, req.user_id)
    if not invitee:
        raise_biz(ErrorCodes.USER_NOT_FOUND)

    # 不能添加自己（自己已经是 owner）
    if req.user_id == current_user.id:
        raise_biz(ErrorCodes.PROJECT_MEMBER_EXISTS, "不能添加自己为成员")

    # 检查是否已是成员
    existing = await db.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == req.user_id,
        )
    )
    if existing.scalar_one_or_none():
        raise_biz(ErrorCodes.PROJECT_MEMBER_EXISTS, "该用户已经是项目成员")

    # 验证角色有效性
    valid_roles = {"viewer", "member", "editor", "owner"}
    if req.role not in valid_roles:
        raise_biz(ErrorCodes.PARAM_ERROR, f"无效角色: {req.role}，可选: {', '.join(sorted(valid_roles))}")

    member = ProjectMember(
        project_id=project_id,
        user_id=req.user_id,
        role=req.role,
    )
    db.add(member)
    await db.flush()
    await db.refresh(member)

    return success({
        "id": member.id,
        "user_id": member.user_id,
        "username": invitee.username,
        "nickname": invitee.nickname,
        "email": invitee.email,
        "role": member.role,
        "created_at": str(member.created_at),
    }, message=f"已添加成员 {invitee.nickname or invitee.username}")


@router.put("/{user_id}/role", summary="修改成员角色", description="修改项目成员的角色权限")
async def update_member_role(
    project_id: int,
    user_id: int,
    req: MemberUpdateRoleRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """修改指定成员的角色"""
    perm = PermissionService(db)
    await perm.check_project_access(project_id, current_user, require_write=True)

    member_role = await perm.get_project_role(project_id, current_user)
    if member_role not in ("owner", "admin"):
        raise_biz(ErrorCodes.PROJECT_FORBIDDEN, "只有项目管理员或创建者可以修改成员角色")

    # 不能修改自己的角色（避免意外失去管理权限）
    if user_id == current_user.id:
        raise_biz(ErrorCodes.PROJECT_FORBIDDEN, "不能修改自己的角色")

    member = await _get_member_or_404(db, project_id, user_id)

    valid_roles = {"viewer", "member", "editor", "owner"}
    if req.role not in valid_roles:
        raise_biz(ErrorCodes.PARAM_ERROR, f"无效角色: {req.role}")

    old_role = member.role
    member.role = req.role
    await db.flush()

    return success({"user_id": user_id, "role": req.role}, message=f"角色已变更为 {req.role}")


@router.delete("/{user_id}", summary="移除成员", description="从项目中移除指定成员")
async def remove_member(
    project_id: int,
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """移除项目成员"""
    perm = PermissionService(db)
    await perm.check_project_access(project_id, current_user, require_write=True)

    member_role = await perm.get_project_role(project_id, current_user)
    if member_role not in ("owner", "admin"):
        raise_biz(ErrorCodes.PROJECT_FORBIDDEN, "只有项目管理员或创建者可以移除成员")

    member = await _get_member_or_404(db, project_id, user_id)
    await db.delete(member)
    await db.flush()

    return success(message="成员已移除")


@router.post("/leave", summary="退出项目", description="当前用户主动退出项目")
async def leave_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """主动退出项目"""
    member = await _get_member_or_404(db, project_id, current_user.id)

    # 如果是 owner，不能退出（需要先转让所有权或删除项目）
    if member.role == "owner":
        raise_biz(ErrorCodes.PROJECT_FORBIDDEN, "项目创建者不能退出项目，请转让所有权后退出")

    await db.delete(member)
    await db.flush()

    return success(message="已退出项目")
