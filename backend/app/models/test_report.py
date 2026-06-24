from datetime import datetime
from sqlalchemy import String, Text, Integer, Float, DateTime, ForeignKey, func
from typing import Optional
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class TestReport(Base):
    __test__ = False  # 防止 pytest 误扫描为测试类
    __tablename__ = "test_reports"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("api_test_plans.id", ondelete="SET NULL"), nullable=True, index=True)
    scene_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("test_scenes.id", ondelete="SET NULL"), nullable=True)
    environment_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("environments.id", ondelete="SET NULL"), nullable=True)
    name: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="running")
    trigger_type: Mapped[str] = mapped_column(String(30), default="manual", server_default="manual", nullable=False, comment="manual/ci/schedule/webhook")
    ref: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, comment="git ref (e.g. refs/heads/main)")
    triggered_by: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    pass_count: Mapped[int] = mapped_column(Integer, default=0)
    fail_count: Mapped[int] = mapped_column(Integer, default=0)
    skip_count: Mapped[int] = mapped_column(Integer, default=0)
    total_count: Mapped[int] = mapped_column(Integer, default=0)
    duration: Mapped[float] = mapped_column(Float, default=0.0)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    executor_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    share_token: Mapped[Optional[str]] = mapped_column(String(64), default="", nullable=True)
    share_token_expire_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    share_enabled: Mapped[int] = mapped_column(Integer, default=1)  # 1=启用, 0=禁用
    share_password: Mapped[Optional[str]] = mapped_column(String(128), default=None, nullable=True)

    compare_with: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    tags: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
