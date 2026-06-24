from datetime import datetime
from sqlalchemy import Integer, DateTime, ForeignKey, Text, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class NotificationPreference(Base):
    """用户在项目维度的通知偏好设置"""
    __tablename__ = "notification_preferences"
    __table_args__ = (
        UniqueConstraint("user_id", "project_id", name="uq_notif_pref_user_project"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    # JSON 格式: {"test_completed": {"in_app": true, "email": false, "webhook": true}, ...}
    preferences: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
