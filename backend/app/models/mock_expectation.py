from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class MockExpectation(Base):
    """Mock 期望规则模型

    在请求匹配后返回指定响应，支持按 headers / query 维度精确匹配。
    """
    __tablename__ = "mock_expectations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    api_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("api_definitions.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    matchers_json: Mapped[str] = mapped_column(
        Text, default="{}", nullable=False,
        comment='例如: {"headers":{...}, "query":{...}}',
    )
    expected_status: Mapped[int] = mapped_column(Integer, default=200, nullable=False)
    expected_body: Mapped[str] = mapped_column(Text, default="", nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
