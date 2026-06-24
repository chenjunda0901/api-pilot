"""API 文档版本快照模型 — 保存文档编辑历史，支持版本回滚"""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class DocVersion(Base):
    """文档版本快照

    每次发布（publish）文档时创建一条版本记录，
    保存当时的完整文档数据快照，支持查看历史和回滚。
    """
    __tablename__ = "doc_versions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    api_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("api_definitions.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    version_data: Mapped[str] = mapped_column(
        Text, nullable=False, comment="JSON 字符串，包含完整文档数据",
    )
    change_summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    changed_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False,
    )
