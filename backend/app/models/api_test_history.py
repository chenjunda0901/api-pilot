from datetime import datetime
from sqlalchemy import String, Text, Integer, Float, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class ApiTestHistory(Base):
    """接口测试历史记录模型

    用于持久化接口在线调试的测试结果，支持历史追溯和对比分析。
    """
    __tablename__ = "api_test_histories"
    __table_args__ = (
        # 索引优化：按接口和时间范围查询
        # e.g. GET /api/projects/{pid}/apis/{aid}/test-history?start=2026-06-01&end=2026-06-09
        # e.g. GET /api/projects/{pid}/apis/{aid}/test-history?env_id=1
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    api_id: Mapped[int] = mapped_column(Integer, ForeignKey("api_definitions.id", ondelete="CASCADE"), nullable=False, index=True)
    environment_id: Mapped[int] = mapped_column(Integer, ForeignKey("environments.id", ondelete="SET NULL"), nullable=True, index=True)
    executor_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # 请求信息
    request_url: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    request_method: Mapped[str] = mapped_column(String(10), nullable=False, default="GET")
    request_headers: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    request_body: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)

    # 响应信息
    response_status: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    response_headers: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    response_body: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)

    # 执行信息
    duration: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)  # 耗时（秒）
    error: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)  # 错误信息

    # 断言结果（用于快速判断测试是否通过）
    status: Mapped[str] = mapped_column(String(20), default="unknown", nullable=False, index=True)
    # status 取值: success / failed / error / timeout / unknown

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False, index=True)
