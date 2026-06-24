from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, Integer, DateTime, ForeignKey, func, Index, text
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class TestCase(Base):
    __tablename__ = "test_cases"
    __table_args__ = (
        Index("ix_test_cases_api_id", "api_id"),
        Index("ix_test_cases_project_api", "project_id", "api_id"),
    )
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    api_id: Mapped[int] = mapped_column(Integer, ForeignKey("api_definitions.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    priority: Mapped[str] = mapped_column(String(10), default="P2")
    status: Mapped[str] = mapped_column(String(20), default="active")
    case_type: Mapped[str] = mapped_column(String(20), default="other")
    tags: Mapped[str] = mapped_column(String(500), default="")
    request_body: Mapped[str] = mapped_column(Text, nullable=True)
    assertions: Mapped[str] = mapped_column(Text, default="[]")
    extract_vars: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, default=None)
    # 种子标记：管理员可将用例标记为种子数据，重置时保留
    is_seed: Mapped[int] = mapped_column(Integer, default=0, nullable=False, server_default=text('0'))
