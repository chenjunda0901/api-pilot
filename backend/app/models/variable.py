from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Variable(Base):
    """变量模型（5 层作用域）

    解析顺序：global → project → env → case → runtime，同名变量后者覆盖前者。
    is_secret=true 时不返回明文。
    """

    __tablename__ = "variables"
    __table_args__ = (
        UniqueConstraint("scope", "scope_id", "name", name="uq_variables_scope_name"),
        Index("ix_variables_scope_name", "scope", "name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    scope: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="枚举: global / project / env / case",
    )
    scope_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="对应 project/case 的 id，global/env 可为 NULL",
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    value: Mapped[str] = mapped_column(Text, default="", nullable=False)
    is_secret: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
