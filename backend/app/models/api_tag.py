from datetime import datetime
from sqlalchemy import String, Integer, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class ApiTag(Base):
    __tablename__ = "api_tags"
    __table_args__ = (
        UniqueConstraint("project_id", "name", name="uq_api_tag_project_name"),
    )
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    color: Mapped[str] = mapped_column(String(20), nullable=True, default="#7a8fd0")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ApiTagRelation(Base):
    __tablename__ = "api_tag_relations"
    __table_args__ = (
        UniqueConstraint("api_id", "tag_id", name="uq_api_tag_relation"),
    )
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    api_id: Mapped[int] = mapped_column(Integer, ForeignKey("api_definitions.id", ondelete="CASCADE"), nullable=False, index=True)
    tag_id: Mapped[int] = mapped_column(Integer, ForeignKey("api_tags.id", ondelete="CASCADE"), nullable=False, index=True)
