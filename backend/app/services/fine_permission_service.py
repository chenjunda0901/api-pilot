"""细粒度权限控制服务

提供资源级操作权限的检查和管理。
"""

import json
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ErrorCodes, raise_biz
from app.models.project_member import ProjectMember

logger = logging.getLogger("api_pilot.services.fine_permission")


class FineGrainedPermissionService:
    """细粒度权限控制服务

    在角色级权限基础上，支持更细粒度的操作权限控制。
    权限分为两类：
    1. 角色级权限（Role-based）：viewer/member/editor/owner/admin
    2. 资源级权限（Resource-based）：删除/导出/分享/管理成员等
    """

    # 默认权限配置（基于角色的权限模板）
    ROLE_PERMISSIONS: dict[str, dict[str, bool]] = {
        "viewer": {
            "can_view": True,
            "can_export": False,
            "can_delete": False,
            "can_share": False,
            "can_manage_members": False,
            "can_modify_settings": False,
        },
        "member": {
            "can_view": True,
            "can_export": True,
            "can_delete": False,
            "can_share": True,
            "can_manage_members": False,
            "can_modify_settings": False,
        },
        "editor": {
            "can_view": True,
            "can_export": True,
            "can_delete": True,
            "can_share": True,
            "can_manage_members": False,
            "can_modify_settings": False,
        },
        "owner": {
            "can_view": True,
            "can_export": True,
            "can_delete": True,
            "can_share": True,
            "can_manage_members": True,
            "can_modify_settings": True,
        },
        "admin": {
            "can_view": True,
            "can_export": True,
            "can_delete": True,
            "can_share": True,
            "can_manage_members": True,
            "can_modify_settings": True,
        },
    }

    # 资源类型到权限的映射
    RESOURCE_PERMISSIONS: dict[str, str] = {
        # 接口管理
        "api": "can_delete",  # 删除接口
        "api_export": "can_export",  # 导出接口
        # 场景测试
        "scene": "can_delete",  # 删除场景
        "scene_run": "can_share",  # 执行场景
        # 测试用例
        "case": "can_delete",
        # 测试报告
        "report": "can_delete",
        "report_share": "can_share",
        # 数据集
        "dataset": "can_delete",
        "dataset_export": "can_export",
        # 项目管理
        "project_settings": "can_modify_settings",
        "project_member": "can_manage_members",
        # 环境管理
        "environment": "can_delete",
    }

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_member_permissions(
        self, project_id: int, user_id: int
    ) -> dict[str, bool]:
        """获取用户在项目中的权限

        Args:
            project_id: 项目ID
            user_id: 用户ID

        Returns:
            权限字典
        """
        # 查询项目成员
        result = await self.db.execute(
            select(ProjectMember).where(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == user_id,
            )
        )
        member = result.scalar_one_or_none()

        if not member:
            return {}

        # 基于角色获取默认权限
        permissions = self.ROLE_PERMISSIONS.get(member.role, {}).copy()

        # 合并自定义权限（如果存在），严格校验只允许更新已知权限 key
        if member.permissions:
            try:
                custom_perms = json.loads(member.permissions)
                if isinstance(custom_perms, dict):
                    allowed_keys = set(
                        self.ROLE_PERMISSIONS.get(member.role, {}).keys()
                    )
                    filtered = {
                        k: v
                        for k, v in custom_perms.items()
                        if k in allowed_keys and isinstance(v, bool)
                    }
                    permissions.update(filtered)
                    if set(custom_perms.keys()) - set(filtered.keys()):
                        logger.warning(
                            "过滤了 %d 个无效自定义权限（不在模板中或非布尔值）",
                            len(set(custom_perms.keys()) - set(filtered.keys())),
                        )
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning("解析自定义权限失败: %s: %s", type(e).__name__, e)

        return permissions

    async def check_permission(
        self,
        project_id: int,
        user_id: int,
        permission: str,
    ) -> bool:
        """检查用户是否有指定权限

        Args:
            project_id: 项目ID
            user_id: 用户ID
            permission: 权限名称 (e.g., "can_delete", "can_export")

        Returns:
            是否有权限
        """
        # 超级管理员拥有所有权限
        from app.models.user import User

        user_result = await self.db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        if user and user.role == "admin":
            return True

        # 项目创建者拥有所有权限
        from app.models.project import Project

        project_result = await self.db.execute(
            select(Project).where(Project.id == project_id)
        )
        project = project_result.scalar_one_or_none()
        if project and project.created_by == user_id:
            return True

        # 检查成员权限
        permissions = await self.get_member_permissions(project_id, user_id)
        return permissions.get(permission, False)

    async def check_resource_permission(
        self,
        project_id: int,
        user_id: int,
        resource_type: str,
    ) -> bool:
        """检查用户对资源类型的操作权限

        Args:
            project_id: 项目ID
            user_id: 用户ID
            resource_type: 资源类型 (e.g., "api", "scene", "dataset_export")

        Returns:
            是否有权限
        """
        # 映射资源类型到权限
        permission = self.RESOURCE_PERMISSIONS.get(resource_type)
        if not permission:
            logger.warning("资源类型 %s 未映射到具体权限，默认拒绝", resource_type)
            return False

        return await self.check_permission(project_id, user_id, permission)

    async def require_permission(
        self,
        project_id: int,
        user_id: int,
        permission: str,
    ) -> None:
        """要求权限（无权限时抛出异常）

        Args:
            project_id: 项目ID
            user_id: 用户ID
            permission: 权限名称

        Raises:
            BizError: 无权限时抛出
        """
        has_perm = await self.check_permission(project_id, user_id, permission)
        if not has_perm:
            raise_biz(ErrorCodes.PROJECT_FORBIDDEN, f"缺少 {permission} 权限")

    async def require_resource_permission(
        self,
        project_id: int,
        user_id: int,
        resource_type: str,
    ) -> None:
        """要求资源操作权限（无权限时抛出异常）

        Args:
            project_id: 项目ID
            user_id: 用户ID
            resource_type: 资源类型

        Raises:
            BizError: 无权限时抛出
        """
        has_perm = await self.check_resource_permission(
            project_id, user_id, resource_type
        )
        if not has_perm:
            raise_biz(ErrorCodes.PROJECT_FORBIDDEN, f"无 {resource_type} 操作权限")

    def get_permission_template(self, role: str) -> dict[str, bool]:
        """获取角色的权限模板

        Args:
            role: 角色名称

        Returns:
            权限字典
        """
        return self.ROLE_PERMISSIONS.get(role, {}).copy()

    def get_all_permissions(self) -> dict[str, dict[str, bool]]:
        """获取所有角色的权限配置

        Returns:
            角色权限字典
        """
        return {role: perms.copy() for role, perms in self.ROLE_PERMISSIONS.items()}
