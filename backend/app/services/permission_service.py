import logging

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ErrorCodes, raise_biz
from app.database import get_db
from app.middleware.auth import get_current_user, get_optional_user
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.user import User

logger = logging.getLogger("api_pilot.permission")


class PermissionService:
    """统一的项目权限检查服务。

    角色等级（从低到高）:
      viewer(1, 只读) → member(2) → editor(3) → owner(4) → admin(5)

    权限矩阵:
      - 公开项目: 所有认证用户可读；写操作需要 member 及以上
      - 私有项目: viewer 可读(只读)；写操作需要 editor 及以上
      - 管理操作(删除项目/管理成员): 需要 owner/admin
    """

    ROLE_LEVELS = {
        "viewer": 1,
        "member": 2,
        "editor": 3,
        "owner": 4,
        "admin": 5,
    }

    def __init__(self, db: AsyncSession):
        self.db = db

    async def check_project_access(
        self, project_id: int, user: User | None, require_write: bool = False
    ) -> Project:
        """检查用户对项目的访问权限。

        种子项目（global_demo=1）特殊处理：
          - 任何用户可读（未登录 / 登录用户均可）
          - 写操作一律禁止（含 admin）。需修改时，用户应在自己的私有副本上操作。
        """
        if user and user.role == "admin":
            project = await self.db.get(Project, project_id)
            if not project:
                raise_biz(ErrorCodes.PROJECT_NOT_FOUND)
            if require_write and getattr(project, "global_demo", 0) == 1:
                logger.warning(
                    "403: 种子项目只读被拒 admin user_id=%d project_id=%d",
                    user.id, project_id,
                )
                raise_biz(
                    ErrorCodes.PROJECT_FORBIDDEN,
                    "种子演示项目为只读，Fork 到您的私有副本后即可自由编辑",
                )
            return project

        project = await self.db.get(Project, project_id)
        if not project:
            raise_biz(ErrorCodes.PROJECT_NOT_FOUND)

        if require_write and getattr(project, "global_demo", 0) == 1:
            logger.warning(
                "403: 种子项目只读被拒 user_id=%s project_id=%d",
                getattr(user, "id", "anonymous"), project_id,
            )
            raise_biz(
                ErrorCodes.PROJECT_FORBIDDEN,
                "种子演示项目为只读，Fork 到您的私有副本后即可自由编辑",
            )

        if not user:
            if project.is_public and not require_write:
                return project
            logger.warning(
                "401: 未认证用户访问 project_id=%d (is_public=%s, require_write=%s)",
                project_id, project.is_public, require_write,
            )
            raise_biz(ErrorCodes.AUTH_TOKEN_MISSING, "请先登录后访问")

        if project.created_by == user.id:
            return project

        member_result = await self.db.execute(
            select(ProjectMember).where(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == user.id,
            )
        )
        member = member_result.scalar_one_or_none()

        if project.is_public:
            if not require_write:
                return project
            if member and self.ROLE_LEVELS.get(member.role, 0) >= self.ROLE_LEVELS["member"]:
                return project
            logger.warning(
                "403: user_id=%d 无项目写权限 project_id=%d (role=%s, is_public=True)",
                user.id, project_id, getattr(member, 'role', None),
            )
            raise_biz(ErrorCodes.PROJECT_FORBIDDEN, "您没有该项目的写权限，需要 member 及以上角色")

        if not member:
            logger.warning(
                "403: user_id=%d 非成员访问私有项目 project_id=%d (created_by=%d)",
                user.id, project_id, project.created_by,
            )
            raise_biz(ErrorCodes.PROJECT_FORBIDDEN, "私有项目仅成员可访问")

        if require_write and self.ROLE_LEVELS.get(member.role, 0) < self.ROLE_LEVELS["editor"]:
            raise_biz(ErrorCodes.PROJECT_FORBIDDEN, "您没有该项目的写权限，需要 editor 及以上角色")
        return project

    async def check_project_member(
        self, project_id: int, user: User, require_role: str = "viewer"
    ) -> ProjectMember | None:
        """检查用户是否是项目成员并且满足角色要求。"""
        if user.role == "admin":
            return ProjectMember(project_id=project_id, user_id=user.id, role="admin")

        result = await self.db.execute(
            select(ProjectMember).where(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == user.id,
            )
        )
        member = result.scalar_one_or_none()
        if not member:
            return None

        required_level = self.ROLE_LEVELS.get(require_role, 1)
        user_level = self.ROLE_LEVELS.get(member.role, 0)
        return member if user_level >= required_level else None

    async def get_project_role(self, project_id: int, user: User) -> str | None:
        """获取用户在项目中的角色。"""
        if user.role == "admin":
            return "admin"

        project = await self.db.get(Project, project_id)
        if project and project.created_by == user.id:
            return "owner"

        member = await self.check_project_member(project_id, user)
        return member.role if member else None


async def require_project_access(
    db: AsyncSession, project_id: int, user: User, require_write: bool = False
) -> Project:
    service = PermissionService(db)
    return await service.check_project_access(project_id, user, require_write)


async def check_read_access(
    project_id: int,
    current_user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
) -> Project:
    """FastAPI dependency for project read access."""
    return await PermissionService(db).check_project_access(project_id, current_user, require_write=False)


async def check_write_access(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Project:
    """FastAPI dependency for project write access."""
    return await PermissionService(db).check_project_access(project_id, current_user, require_write=True)


async def check_seed_mark_access(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Project:
    """FastAPI dependency for seed-mark endpoints.

    种子标记端点的权限逻辑：
      - 种子项目（global_demo=1）且用户为 admin：允许操作
      - 其他情况：要求正常写权限
    """
    project = await db.get(Project, project_id)
    if project and getattr(project, "global_demo", 0) == 1 and current_user.role == "admin":
        return project
    return await PermissionService(db).check_project_access(project_id, current_user, require_write=True)


async def check_seed_template_readonly(project: Project | None, method: str) -> None:
    """种子项目（global_demo=1）写操作守卫（独立函数版）。

    通常由 check_project_access 内置调用；如下游路由不经过
    ``check_project_access``（如直接 ``db.get(Project, id)``），可显式调用本函数。
    """
    if project is None:
        return
    if getattr(project, "global_demo", 0) == 1 and method.upper() in {
        "POST", "PUT", "PATCH", "DELETE"
    }:
        raise_biz(
            ErrorCodes.PROJECT_FORBIDDEN,
            "种子演示项目为只读，Fork 到您的私有副本后即可自由编辑",
        )
