from datetime import datetime
from sqlalchemy import String, Text, Integer, DateTime, ForeignKey, func, Boolean, text
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class MockRule(Base):
    __tablename__ = "mock_rules"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    match_method: Mapped[str] = mapped_column(String(10), default="*")
    match_path: Mapped[str] = mapped_column(String(500), default="")
    response_status: Mapped[int] = mapped_column(Integer, default=200)
    response_headers: Mapped[str] = mapped_column(Text, default="{}")
    response_body: Mapped[str] = mapped_column(Text, default="")
    response_delay: Mapped[int] = mapped_column(Integer, default=0)
    conditions: Mapped[str] = mapped_column(Text, nullable=True, comment="条件JSON数组")
    script: Mapped[str] = mapped_column(Text, nullable=True, comment="自定义JS脚本")
    hit_count: Mapped[int] = mapped_column(Integer, default=0, comment="命中次数统计")
    is_seed: Mapped[int] = mapped_column(Integer, default=0, nullable=False, server_default=text('0'))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
