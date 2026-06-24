from datetime import datetime
from typing import Optional, TypeVar
from sqlalchemy import DateTime, func, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

T = TypeVar("T")


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )


class SoftDeleteMixin:
    """软删除混入类。

    为模型添加 ``deleted_at`` 列并提供统一的过滤方法。

    使用方式::

        class MyModel(Base, SoftDeleteMixin):
            ...

        # 查询时始终过滤已删除记录
        stmt = MyModel.active_select().where(MyModel.name == "foo")
        # 或手动附加过滤条件
        stmt = select(MyModel).where(MyModel.active_filter(), MyModel.name == "foo")
    """

    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, default=None
    )

    @classmethod
    def active_filter(cls):
        """返回 SQL 过滤条件，排除已软删除的记录。"""
        return cls.deleted_at.is_(None)

    @classmethod
    def active_select(cls) -> "select":
        """返回一个预置了软删除过滤的 SELECT 语句，可直接链式追加 WHERE 条件。"""
        return select(cls).where(cls.active_filter())
