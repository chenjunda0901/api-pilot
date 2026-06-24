from datetime import datetime
from typing import Optional
from sqlalchemy import Integer, DateTime, ForeignKey, String, Text, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class ProjectMember(Base):
    __tablename__ = "project_members"
    __table_args__ = (
        UniqueConstraint("project_id", "user_id", name="uq_project_member"),
    )
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="viewer")
    # 细粒度权限配置（JSON格式）
    # 示例: {"can_delete_api": true, "can_export": true, "can_manage_members": false}
    permissions: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
