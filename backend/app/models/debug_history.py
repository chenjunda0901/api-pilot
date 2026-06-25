from datetime import datetime, UTC
from sqlalchemy import String, Text, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class DebugHistory(Base):
    __tablename__ = "debug_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    api_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("api_definitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="关联接口ID",
    )
    project_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="项目ID",
    )
    url: Mapped[str] = mapped_column(Text, nullable=False, comment="请求URL")
    method: Mapped[str] = mapped_column(String(10), nullable=False, comment="请求方法")
    request_headers: Mapped[str] = mapped_column(
        Text, default="[]", comment="请求头JSON数组"
    )
    request_body: Mapped[str] = mapped_column(Text, default="", comment="请求体")
    response_status: Mapped[int] = mapped_column(
        Integer, nullable=True, comment="响应状态码"
    )
    response_headers: Mapped[str] = mapped_column(
        Text, default="[]", comment="响应头JSON数组"
    )
    response_body: Mapped[str] = mapped_column(Text, default="", comment="响应体")
    duration_ms: Mapped[int] = mapped_column(Integer, default=0, comment="耗时毫秒")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), comment="创建时间"
    )
