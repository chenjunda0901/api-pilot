from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ApiSnapshot(Base):
    """接口变更快照模型

    每次接口的 create/update/delete 自动落盘，保留历史可回滚/可对比。
    """
    __tablename__ = "api_snapshots"
    __table_args__ = (
        Index("ix_api_snapshots_api_created", "api_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    api_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("api_definitions.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    snapshot_data: Mapped[str] = mapped_column(Text, nullable=False, comment="JSON 字符串")
    change_type: Mapped[str] = mapped_column(
        String(20), nullable=False,
        comment="枚举: create / update / delete",
    )
    change_summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    changed_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
