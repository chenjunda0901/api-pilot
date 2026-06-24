from datetime import datetime
from sqlalchemy import String, Text, Integer, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class MockHitLog(Base):
    __tablename__ = "mock_hit_logs"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    rule_id: Mapped[int] = mapped_column(Integer, ForeignKey("mock_rules.id", ondelete="SET NULL"), nullable=True)
    request_method: Mapped[str] = mapped_column(String(10))
    request_path: Mapped[str] = mapped_column(String(500))
    request_headers: Mapped[str] = mapped_column(Text, nullable=True)
    matched: Mapped[bool] = mapped_column(Boolean, default=True)
    response_delay_ms: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
