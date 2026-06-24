from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class MetricsSnapshot(Base):
    """运行指标时序模型

    写入项目/接口/计划维度的 duration / qps / error_rate / p50 / p95 / p99 等指标。
    """
    __tablename__ = "metrics_snapshots"
    __table_args__ = (
        Index("ix_metrics_snapshots_scope", "scope", "scope_id"),
        Index("ix_metrics_snapshots_scope_metric_time", "scope", "scope_id", "metric", "recorded_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    scope: Mapped[str] = mapped_column(
        String(20), nullable=False,
        comment="枚举: project / api / plan",
    )
    scope_id: Mapped[int] = mapped_column(Integer, nullable=False)
    metric: Mapped[str] = mapped_column(
        String(30), nullable=False,
        comment="枚举: duration / qps / error_rate / p50 / p95 / p99",
    )
    value: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
