from sqlalchemy import (
    String,
    Text,
    Integer,
    Boolean,
    ForeignKey,
    Index,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin, SoftDeleteMixin


class ApiDefinition(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "api_definitions"
    __table_args__ = (
        Index("ix_api_defs_project_not_deleted", "project_id", "deleted_at"),
    )
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("api_categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    method: Mapped[str] = mapped_column(String(10), nullable=False, default="GET")
    path: Mapped[str] = mapped_column(String(500), nullable=False, default="/")
    description: Mapped[str] = mapped_column(Text, default="")
    description_md: Mapped[str] = mapped_column(Text, default="")
    headers: Mapped[str] = mapped_column(Text, default="[]")
    params: Mapped[str] = mapped_column(Text, default="[]")
    body: Mapped[str] = mapped_column(Text, default='{"type":"none","content":""}')
    auth_type: Mapped[str] = mapped_column(String(20), default="none")
    apifox_id: Mapped[str] = mapped_column(
        String(100), nullable=True, index=True, default=None
    )
    response_schema: Mapped[str] = mapped_column(Text, nullable=True, default=None)
    response_examples: Mapped[str] = mapped_column(Text, nullable=True, default=None)
    # Apifox 对齐字段：前置操作、后置操作、Cookies、Auth 配置、请求设置
    pre_script: Mapped[str] = mapped_column(Text, nullable=True, default="")
    post_script: Mapped[str] = mapped_column(Text, nullable=True, default="")
    cookies: Mapped[str] = mapped_column(Text, nullable=True, default="[]")
    auth: Mapped[str] = mapped_column(Text, nullable=True, default='{"type":"none"}')
    settings: Mapped[str] = mapped_column(
        Text,
        nullable=True,
        default='{"follow_redirects":true,"verify_ssl":true,"timeout":30}',
    )
    extract_vars: Mapped[str] = mapped_column(Text, nullable=True, default="[]")
    # 种子标记：管理员可将接口标记为种子数据，重置时保留
    is_seed: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False, server_default=text("0")
    )
    # 收藏/置顶
    is_starred: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, server_default=text("0")
    )
    sort_order: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False, server_default=text("0")
    )
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False)
    version: Mapped[str] = mapped_column(String(20), default="v1.0", nullable=False)
    created_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
