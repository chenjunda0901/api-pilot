from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ApiAssertion(Base):
    """断言库模型（6 类断言）

    通过 owner_type + owner_id 多态挂载到具体接口或用例，按 order_index 顺序执行。
    """

    __tablename__ = "api_assertions"
    __table_args__ = (
        Index("ix_api_assertions_owner", "owner_type", "owner_id"),
        Index("ix_api_assertions_owner_order", "owner_type", "owner_id", "order_index"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    owner_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="枚举: api / case",
    )
    owner_id: Mapped[int] = mapped_column(Integer, nullable=False)
    assertion_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        comment="枚举: jsonpath / jsonschema / regex / duration / header / cookie",
    )
    expression: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="断言表达式, 例如: $.data[0].name",
    )
    operator: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="枚举: eq / ne / gt / lt / in / contains / regex / exists",
    )
    expected_value: Mapped[str] = mapped_column(Text, default="", nullable=False)
    enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
