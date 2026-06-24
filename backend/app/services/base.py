"""Service 层基类 — 统一所有业务服务的构造与通用能力。

使用方式::

    from app.services.base import BaseService

    class ProjectService(BaseService):
        async def get_project(self, project_id: int) -> Project:
            return await self.db.get(Project, project_id)

所有 Service 自动获得：
  - self.db: AsyncSession 数据库会话
  - self.raise_biz: 快捷抛出业务异常
  - self.logger: 带类名前缀的结构化日志
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, TypeVar

from pydantic import BaseModel as PydanticBaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import raise_biz, ErrorCodes

if TYPE_CHECKING:
    pass

T = TypeVar("T")
S = TypeVar("S", bound=PydanticBaseModel)


class BaseService:
    """业务服务基类。

    约定：
      - 构造函数只接受 db: AsyncSession
      - 公开方法返回领域模型或 schema，不返回原始 SQLAlchemy 对象（除非必要）
      - 所有业务异常通过 self.raise_biz 抛出，不直接 raise BizError
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    @property
    def logger(self) -> logging.Logger:
        """返回带服务类名前缀的 logger，便于日志过滤。"""
        return logging.getLogger(f"service.{type(self).__name__}")

    # ── 快捷方法 ──────────────────────────────────────

    def _raise(self, code: ErrorCodes, message: str = "", detail: str | None = None) -> None:
        """抛出业务异常的快捷方法。"""
        raise_biz(code, message, detail)

    # ── ORM → Schema 转换 ─────────────────────────────

    @staticmethod
    def to_schema(orm_instance: object, schema_class: type[S]) -> S:
        """将 ORM 实例转换为 Pydantic schema。

        子类可覆盖此方法以支持自定义转换逻辑。
        使用 Pydantic v2 的 ``model_validate`` 从 ORM 对象属性读取。
        """
        return schema_class.model_validate(orm_instance)

    def to_schema_list(self, orm_instances: list[object], schema_class: type[S]) -> list[S]:
        """将 ORM 实例列表批量转换为 Pydantic schema 列表。"""
        return [self.to_schema(inst, schema_class) for inst in orm_instances]
