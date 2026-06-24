import json
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import raise_biz, ErrorCodes
from app.models.environment import Environment
from app.schemas.environment import EnvironmentCreate, EnvironmentUpdate


def _parse_json(val) -> list:
    """将 JSON 列字段转换为 Python list。兼容已序列化字符串或原始列表。"""
    if val is None:
        return []
    if isinstance(val, str):
        try:
            return json.loads(val)
        except (json.JSONDecodeError, ValueError):
            return []
    if isinstance(val, list):
        return val
    return []


class EnvService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def to_dict(self, env):
        """将 Environment 模型转换为字典。JSON 字段统一转为 Python list。"""
        return {
            "id": env.id,
            "project_id": env.project_id,
            "name": env.name,
            "base_url": env.base_url or "",
            "auth_config": env.auth_config or None,
            "services": _parse_json(env.services),
            "variables": _parse_json(env.variables),
            "headers": _parse_json(env.headers),
            "created_at": str(env.created_at),
            "updated_at": str(env.updated_at),
        }

    async def list(self, project_id: int, page: int = 1, page_size: int = 0) -> tuple[list, int]:
        from sqlalchemy import func, select
        from app.models.environment import Environment as EnvModel

        base_query = select(EnvModel).where(EnvModel.project_id == project_id)
        total = await self.db.scalar(
            select(func.count(EnvModel.id)).where(EnvModel.project_id == project_id)
        ) or 0

        if page_size > 0:
            base_query = base_query.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(base_query.order_by(EnvModel.id))
        items = [self.to_dict(env) for env in result.scalars().all()]
        return items, total

    async def get(self, env_id: int, project_id: int | None = None) -> Environment:
        result = await self.db.execute(
            select(Environment).where(Environment.id == env_id)
        )
        env = result.scalar_one_or_none()
        if not env:
            raise_biz(ErrorCodes.ENV_NOT_FOUND)
        if project_id is not None and env.project_id != project_id:
            raise_biz(ErrorCodes.ENV_FORBIDDEN)
        return env

    async def create(self, project_id: int, req: EnvironmentCreate):
        # SQLAlchemy JSON 类型自动处理序列化，直接传入 list 即可
        env = Environment(
            project_id=project_id,
            name=req.name,
            base_url=req.base_url,
            auth_config=req.auth_config,
            services=req.services,
            variables=req.variables,
            headers=req.headers,
        )
        self.db.add(env)
        await self.db.flush()
        await self.db.refresh(env)
        return env

    async def update(self, env_id: int, req: EnvironmentUpdate, project_id: int | None = None):
        env = await self.get(env_id, project_id=project_id)
        if req.name is not None:
            env.name = req.name
        if hasattr(req, "base_url") and req.base_url is not None:
            env.base_url = req.base_url
        if hasattr(req, "auth_config") and req.auth_config is not None:
            env.auth_config = req.auth_config
        # SQLAlchemy JSON 类型自动处理序列化，直接赋值 list
        if req.services is not None:
            env.services = req.services
        if req.variables is not None:
            env.variables = req.variables
        if req.headers is not None:
            env.headers = req.headers
        await self.db.flush()
        await self.db.refresh(env)
        return env

    async def delete(self, env_id: int, project_id: int | None = None):
        env = await self.get(env_id, project_id=project_id)
        # 检查是否有场景引用该环境
        from app.models.test_scene import TestScene

        result = await self.db.execute(
            select(TestScene)
            .where(TestScene.env_id == env_id, TestScene.deleted_at.is_(None))
            .limit(1)
        )
        referenced_scene = result.scalar_one_or_none()
        if referenced_scene:
            raise_biz(
                ErrorCodes.ENV_IN_USE,
                detail=f"该环境正被场景「{referenced_scene.name}」使用，请先修改场景配置",
            )
        await self.db.delete(env)
        await self.db.flush()
