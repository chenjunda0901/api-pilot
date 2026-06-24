from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Webhook(Base):
    """出站 Webhook 配置模型

    平台通过该配置向 IM / 邮件等渠道推送事件，secret 用于 HMAC 签名校验。
    """
    __tablename__ = "webhooks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    secret: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    channel: Mapped[str] = mapped_column(
        String(30), nullable=False, index=True,
        comment="枚举: feishu / dingtalk / wechat / slack / email / custom",
    )
    events_json: Mapped[str] = mapped_column(
        Text, default="[]", nullable=False,
        comment='事件列表, 例如: ["test_plan.failed", "api.updated"]',
    )
    template: Mapped[str] = mapped_column(Text, default="", nullable=False, comment="Jinja2 模板")
    enabled: Mapped[int] = mapped_column(
        Integer, default=1, nullable=False, index=True,
        comment="0/1 软启用标记",
    )
    created_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
