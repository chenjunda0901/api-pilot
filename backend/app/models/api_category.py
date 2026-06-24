from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, DateTime, ForeignKey, func, text
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class ApiCategory(Base):
    __tablename__ = "api_categories"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    parent_id: Mapped[int] = mapped_column(Integer, ForeignKey("api_categories.id"), nullable=True, index=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    # 种子标记：管理员可将接口目录标记为种子数据，重置时保留
    is_seed: Mapped[int] = mapped_column(Integer, default=0, nullable=False, server_default=text('0'))
    # 软删除标记：与接口/用例/场景保持一致，支持回收站恢复
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, default=None)
