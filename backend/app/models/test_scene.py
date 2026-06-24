from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, Integer, DateTime, ForeignKey, func, text
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class TestScene(Base):
    __test__ = False  # 防止 pytest 误扫描为测试类
    __tablename__ = "test_scenes"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    category_id: Mapped[int] = mapped_column(Integer, ForeignKey("scene_categories.id", ondelete="SET NULL"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    env_id: Mapped[int] = mapped_column(Integer, ForeignKey("environments.id"), nullable=True)
    loop_count: Mapped[int] = mapped_column(Integer, default=1)
    thread_count: Mapped[int] = mapped_column(Integer, default=1)
    delay: Mapped[int] = mapped_column(Integer, default=0)
    on_failure: Mapped[str] = mapped_column(String(20), default="stop")
    on_error: Mapped[str] = mapped_column(String(30), default="stop")
    save_detail: Mapped[str] = mapped_column(String(20), default="all")
    save_vars: Mapped[int] = mapped_column(Integer, default=1)
    global_cookie: Mapped[int] = mapped_column(Integer, default=0)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    save_cookie_to_global: Mapped[int] = mapped_column(Integer, default=0)
    # 变量持久化目标：environment（写入环境变量）/ global（写入全局变量）/ none（不持久化）
    var_persist_target: Mapped[str] = mapped_column(String(20), default="environment", nullable=False, server_default=text("'environment'"))
    schedule_cron: Mapped[str] = mapped_column(String(100), default="")
    schedule_env_id: Mapped[int] = mapped_column(Integer, ForeignKey("environments.id"), nullable=True)
    schedule_enabled: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, default=None)
    # 种子标记：管理员可将场景标记为种子数据，重置时保留
    is_seed: Mapped[int] = mapped_column(Integer, default=0, nullable=False, server_default=text('0'))
