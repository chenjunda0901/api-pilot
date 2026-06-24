from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Schedule(Base):
    """定时任务模型

    关联测试计划，支持 cron 表达式与时区，由调度器根据 next_run_at 触发执行。
    """
    __tablename__ = "schedules"
    __table_args__ = (
        Index("ix_schedules_enabled_next_run", "enabled", "next_run_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    plan_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("api_test_plans.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    cron_expression: Mapped[str] = mapped_column(String(100), nullable=False)
    timezone: Mapped[str] = mapped_column(String(50), default="UTC", nullable=False)
    enabled: Mapped[int] = mapped_column(
        Integer, default=1, nullable=False, index=True,
        comment="0/1 启用标记",
    )
    last_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    next_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
