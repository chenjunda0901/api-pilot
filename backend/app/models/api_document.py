"""API 文档发布模型 — 支持分享链接、密码保护、过期时间"""

from datetime import datetime
from sqlalchemy import String, Text, Integer, DateTime, Boolean, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class ApiDocument(Base):
    """API 文档发布记录

    将项目的 API 定义发布为在线文档，支持：
    - 分享链接（token 鉴权）
    - 密码保护
    - 过期时间
    """
    __tablename__ = "api_documents"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    description: Mapped[str] = mapped_column(Text, default="")
    # 分享令牌
    share_token: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )
    # 密码保护（可选）
    password_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    # 过期时间（可选）
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # 包含的接口目录(JSON)，为空表示全部接口
    include_categories: Mapped[str] = mapped_column(Text, default="[]")
    # 包含的环境 ID（可选，用于文档中的变量替换）
    env_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # 是否启用
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    # 浏览次数
    view_count: Mapped[int] = mapped_column(Integer, default=0)
    created_by: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
