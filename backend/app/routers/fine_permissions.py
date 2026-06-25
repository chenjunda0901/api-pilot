"""细粒度权限管理路由

提供项目成员权限的查询和修改API。
"""
import json
from typing import Any

from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ErrorCodes, raise_biz
from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.user import User
from app.services.fine_permission_service import FineGrainedPermissionService
from app.services.permission_service import PermissionService, check_read_access, check_write_access
from app.utils.response import success

router = APIRouter(prefix="/projects/{project_id}/permissions", tags=["Fine-Grained Permissions"])


@router.get("", summary="获取权限模板", description="获取指定角色的权限模板")
async def get_permission_template(
    project_id: int,
    role: str = Query("member", description="角色名称", pattern="^(viewer|member|editor|owner|admin)$"),
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_read_access),
    db: AsyncSession = Depends(get_db),
):
    """获取角色的权限模板

    返回该角色的默认权限配置。
    """
    service = FineGrainedPermissionService(db)
    permissions = service.get_permission_template(role)

    return success({
        "role": role,
        "permissions": permissions,
    })


@router.get("/my", summary="我的权限", description="获取当前用户在项目中的权限")
async def get_my_permissions(
    project_id: int,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_read_access),
    db: AsyncSession = Depends(get_db),
):
    """获取当前用户的权限

    返回用户在项目中的所有权限配置（包括角色默认权限和自定义权限）。
    """
    service = FineGrainedPermissionService(db)
    permissions = await service.get_member_permissions(project_id, current_user.id)

    # 获取用户角色
    perm_service = PermissionService(db)
    role = await perm_service.get_project_role(project_id, current_user)

    return success({
        "role": role,
        "permissions": permissions,
    })


@router.get("/{user_id}", summary="用户权限", description="获取指定用户在项目中的权限（需管理权限）")
async def get_user_permissions(
    project_id: int,
    user_id: int,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_read_access),
    db: AsyncSession = Depends(get_db),
):
    """获取指定用户的权限

    需要管理权限（owner/admin）。
    """
    # 权限检查：只有owner/admin可查看其他成员权限
    perm_service = PermissionService(db)
    await perm_service.require_permission(project_id, current_user.id, "can_manage_members")

    # 查询目标用户
    user_result = await db.execute(select(User).where(User.id == user_id))
    target_user = user_result.scalar_one_or_none()
    if not target_user:
        raise_biz(ErrorCodes.NOT_FOUND, "用户不存在")

    service = FineGrainedPermissionService(db)
    permissions = await service.get_member_permissions(project_id, user_id)
    role = await perm_service.get_project_role(project_id, target_user)

    return success({
        "user_id": user_id,
        "username": target_user.username,
        "role": role,
        "permissions": permissions,
    })


@router.put("/{user_id}", summary="更新用户权限", description="更新指定用户的细粒度权限（需管理权限）")
async def update_user_permissions(
    project_id: int,
    user_id: int,
    permissions: dict[str, Any] = Body(..., description="权限配置"),
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
    db: AsyncSession = Depends(get_db),
):
    """更新用户的自定义权限

    需要管理权限（owner/admin）。
    permissions格式：
    {
        "can_delete": true,
        "can_export": true,
        "can_share": false,
        "can_manage_members": false,
        "can_modify_settings": false
    }
    """
    # 权限检查
    perm_service = PermissionService(db)
    await perm_service.require_permission(project_id, current_user.id, "can_manage_members")

    # 验证目标用户
    user_result = await db.execute(select(User).where(User.id == user_id))
    target_user = user_result.scalar_one_or_none()
    if not target_user:
        raise_biz(ErrorCodes.NOT_FOUND, "用户不存在")

    # 查询项目成员
    result = await db.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id,
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        raise_biz(ErrorCodes.NOT_FOUND, "用户不是项目成员")

    # 限定只允许已定义权限键，且值必须为布尔值
    allowed_keys = set(FineGrainedPermissionService.ROLE_PERMISSIONS.get("owner", {}).keys())
    sanitized_permissions: dict[str, bool] = {}
    for key, value in permissions.items():
        if key not in allowed_keys:
            raise_biz(ErrorCodes.INVALID_PARAM, f"不支持的权限项: {key}")
        if not isinstance(value, bool):
            raise_biz(ErrorCodes.INVALID_PARAM, f"权限项 {key} 的值必须为布尔值")
        sanitized_permissions[key] = value

    member.permissions = json.dumps(sanitized_permissions, ensure_ascii=False)
    await db.flush()

    return success({
        "user_id": user_id,
        "permissions": sanitized_permissions,
        "message": "权限已更新",
    })


@router.delete("/{user_id}", summary="重置用户权限", description="清除用户的自定义权限，恢复为角色默认权限")
async def reset_user_permissions(
    project_id: int,
    user_id: int,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
    db: AsyncSession = Depends(get_db),
):
    """重置用户权限

    清除自定义权限，恢复为角色默认权限。
    需要管理权限（owner/admin）。
    """
    # 权限检查
    perm_service = PermissionService(db)
    await perm_service.require_permission(project_id, current_user.id, "can_manage_members")

    # 查询项目成员
    result = await db.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id,
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        raise_biz(ErrorCodes.NOT_FOUND, "用户不是项目成员")

    # 清除自定义权限
    member.permissions = None
    await db.flush()

    return success(message="权限已重置")
