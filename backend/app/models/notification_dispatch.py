from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class NotificationDispatch(Base):
    """出站通知投递历史模型

    记录每次通过 Webhook / 邮件 / IM 投递事件的结果，用于审计与重试。
    注意：表名 notification_dispatches 与站内消息表 notifications 区分。
    """
    __tablename__ = "notification_dispatches"
    __table_args__ = (
        Index("ix_notification_dispatches_status_created", "status", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    project_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True, index=True,
    )
    channel: Mapped[str] = mapped_column(
        String(30), nullable=False,
        comment="枚举: feishu / dingtalk / wechat / slack / email / custom",
    )
    event: Mapped[str] = mapped_column(String(100), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default="pending", nullable=False, index=True,
        comment="枚举: pending / sent / failed",
    )
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
