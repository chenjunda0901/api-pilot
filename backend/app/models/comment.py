from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Comment(Base):
    """评论模型

    支持对 api / case / scene / report 等资源的多人讨论，通过 parent_id 实现回复树。
    """
    __tablename__ = "comments"
    __table_args__ = (
        # SQLite 不允许在 CREATE TABLE 内直接写自引用 FK，use_alter 让 DDL 拆为两步
        Index("ix_comments_resource", "resource_type", "resource_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    resource_type: Mapped[str] = mapped_column(
        String(30), nullable=False,
        comment="枚举: api / case / scene / report",
    )
    resource_id: Mapped[int] = mapped_column(Integer, nullable=False)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False, index=True,
    )
    content_md: Mapped[str] = mapped_column(Text, nullable=False)
    mentions_json: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment='例如: {"user_ids":[1,2]}',
    )
    status: Mapped[str] = mapped_column(
        String(20), default="open", nullable=False,
        comment="枚举: open / resolved",
    )
    parent_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("comments.id", ondelete="CASCADE", use_alter=True),
        nullable=True, index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
