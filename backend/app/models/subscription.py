from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Subscription(Base):
    """关注/订阅模型

    用户订阅资源（接口/用例/场景/报告等）后，会收到对应事件的通知。
    """
    __tablename__ = "subscriptions"
    __table_args__ = (
        UniqueConstraint("user_id", "resource_type", "resource_id", name="uq_subscriptions_user_resource"),
        Index("ix_subscriptions_resource", "resource_type", "resource_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    resource_type: Mapped[str] = mapped_column(
        String(30), nullable=False,
        comment="枚举: api / case / scene / report / plan",
    )
    resource_id: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
