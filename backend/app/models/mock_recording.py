from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class MockRecording(Base):
    """Mock 录制模型

    保存真实请求/响应对，用于后续回放或转换为 Mock 规则。
    """
    __tablename__ = "mock_recordings"
    __table_args__ = (
        Index("ix_mock_recordings_captured_at", "captured_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    api_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("api_definitions.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    request_json: Mapped[str] = mapped_column(Text, nullable=False)
    response_json: Mapped[str] = mapped_column(Text, nullable=False)
    captured_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
