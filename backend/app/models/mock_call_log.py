from datetime import datetime
from sqlalchemy import String, Text, Integer, DateTime, ForeignKey, func, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class MockCallLog(Base):
    """Mock 调用日志。

    每次 Mock 引擎服务响应时记录一条日志，用于审计和统计。

    Migration note: 新增表，需执行 alembic revision 或开发模式下自动建表。
    """
    __tablename__ = "mock_call_logs"
    __table_args__ = (
        Index("ix_mock_call_logs_project_created", "project_id", "created_at"),
        Index("ix_mock_call_logs_rule_id", "mock_rule_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    mock_rule_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("mock_rules.id", ondelete="SET NULL"), nullable=True)
    request_method: Mapped[str] = mapped_column(String(10), nullable=False)
    request_path: Mapped[str] = mapped_column(String(500), nullable=False)
    request_headers: Mapped[str | None] = mapped_column(Text, nullable=True, comment="请求头 JSON")
    request_query: Mapped[str | None] = mapped_column(Text, nullable=True, comment="查询参数 JSON")
    matched_rule_name: Mapped[str | None] = mapped_column(String(200), nullable=True, comment="匹配的规则名称")
    response_status: Mapped[int] = mapped_column(Integer, default=200)
    response_body_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="响应体 SHA256 哈希")
    duration_ms: Mapped[int] = mapped_column(Integer, default=0, comment="响应耗时(ms)")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
