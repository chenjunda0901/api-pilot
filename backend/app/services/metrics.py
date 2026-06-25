"""运行指标采集与统计。

基于 ``metrics_snapshots`` 表（scope + scope_id + metric）写入原始观测点，
并提供 ``p50 / p95 / p99``、慢请求 TopN、基线告警等聚合查询。

典型用法::

    collector = MetricsCollector(db)
    await collector.record_duration("api", 1, 123.0)
    stats = await collector.get_p50_p95_p99(api_id=1, days=7)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, UTC
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("service.metrics")


# ── 异常 ────────────────────────────────────────────────────────────────


class MetricsError(Exception):
    """指标错误。"""


# ── 数据结构 ────────────────────────────────────────────────────────────


@dataclass
class Alert:
    """基线告警。"""

    api_id: int
    scope: str
    scope_id: int
    current_ms: float
    threshold_ms: float
    message: str = ""


@dataclass
class PercentileResult:
    """百分位结果。"""

    count: int
    avg_ms: float
    p50_ms: float
    p95_ms: float
    p99_ms: float
    min_ms: float
    max_ms: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "count": self.count,
            "avg": self.avg_ms,
            "p50": self.p50_ms,
            "p95": self.p95_ms,
            "p99": self.p99_ms,
            "min": self.min_ms,
            "max": self.max_ms,
        }


@dataclass
class SlowRequest:
    """慢请求条目。"""

    scope: str
    scope_id: int
    duration_ms: float
    recorded_at: datetime
    extra: dict[str, Any] = field(default_factory=dict)


# ── 服务实现 ────────────────────────────────────────────────────────────


class MetricsCollector:
    """运行指标采集器。"""

    # metric 名称
    METRIC_DURATION = "duration"
    METRIC_QPS = "qps"
    METRIC_ERROR_RATE = "error_rate"
    METRIC_P50 = "p50"
    METRIC_P95 = "p95"
    METRIC_P99 = "p99"

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── 写入 ────────────────────────────────────────────────────

    async def record_duration(
        self,
        scope: str,
        scope_id: int,
        duration_ms: float,
        project_id: int,
    ) -> None:
        await self._record(project_id, scope, scope_id, self.METRIC_DURATION, float(duration_ms))

    async def record_qps(
        self,
        scope: str,
        scope_id: int,
        count: int,
        project_id: int,
    ) -> None:
        await self._record(project_id, scope, scope_id, self.METRIC_QPS, float(count))

    async def record_error(
        self,
        scope: str,
        scope_id: int,
        error_type: str,
        project_id: int,
    ) -> None:
        # 用 0/1 计数 + error_type 写 description 不太方便，简化成 metric=error_rate, value=1
        await self._record(
            project_id,
            scope,
            scope_id,
            self.METRIC_ERROR_RATE,
            1.0,
            extra={"error_type": error_type},
        )

    async def _record(
        self,
        project_id: int,
        scope: str,
        scope_id: int,
        metric: str,
        value: float,
        extra: dict[str, Any] | None = None,
    ) -> None:
        try:
            from app.models.metrics_snapshot import MetricsSnapshot
        except ImportError as exc:  # pragma: no cover
            raise MetricsError("无法加载 MetricsSnapshot 模型") from exc
        snap = MetricsSnapshot(
            project_id=project_id,
            scope=scope,
            scope_id=scope_id,
            metric=metric,
            value=value,
        )
        self.db.add(snap)
        try:
            await self.db.flush()
        except Exception as exc:  # noqa: BLE001
            logger.warning("metrics record failed: %s", exc)
            await self.db.rollback()

    # ── 聚合查询 ────────────────────────────────────────────────

    async def get_p50_p95_p99(
        self,
        api_id: int,
        days: int = 7,
    ) -> PercentileResult:
        """拉取近 N 天 api 维度的 duration 指标并计算百分位。"""
        values = await self._fetch_durations("api", api_id, days)
        if not values:
            return PercentileResult(0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        values_sorted = sorted(values)
        return PercentileResult(
            count=len(values_sorted),
            avg_ms=sum(values_sorted) / len(values_sorted),
            p50_ms=self._percentile(values_sorted, 0.5),
            p95_ms=self._percentile(values_sorted, 0.95),
            p99_ms=self._percentile(values_sorted, 0.99),
            min_ms=values_sorted[0],
            max_ms=values_sorted[-1],
        )

    async def get_slow_requests(
        self,
        top_n: int = 20,
        days: int = 7,
        scope: str = "api",
    ) -> list[SlowRequest]:
        """返回 N 天内 top N 慢请求。"""
        try:
            from app.models.metrics_snapshot import MetricsSnapshot
        except ImportError as exc:  # pragma: no cover
            raise MetricsError("无法加载 MetricsSnapshot 模型") from exc
        threshold = datetime.now(UTC) - timedelta(days=days)
        q = (
            select(MetricsSnapshot)
            .where(
                MetricsSnapshot.scope == scope,
                MetricsSnapshot.metric == self.METRIC_DURATION,
                MetricsSnapshot.recorded_at >= threshold,
            )
            .order_by(MetricsSnapshot.value.desc())
            .limit(top_n)
        )
        result = await self.db.execute(q)
        rows = result.scalars().all()
        return [
            SlowRequest(
                scope=r.scope,
                scope_id=r.scope_id,
                duration_ms=r.value,
                recorded_at=r.recorded_at,
            )
            for r in rows
        ]

    async def check_baseline_alert(
        self,
        api_id: int,
        threshold_ms: float = 1500.0,
        days: int = 1,
    ) -> list[Alert]:
        """检查 api 是否存在 p95 超过阈值的告警。"""
        stats = await self.get_p50_p95_p99(api_id=api_id, days=days)
        if stats.count == 0:
            return []
        alerts: list[Alert] = []
        if stats.p95_ms > threshold_ms:
            alerts.append(
                Alert(
                    api_id=api_id,
                    scope="api",
                    scope_id=api_id,
                    current_ms=stats.p95_ms,
                    threshold_ms=threshold_ms,
                    message=f"p95 {stats.p95_ms:.1f}ms 超过基线 {threshold_ms}ms",
                )
            )
        return alerts

    # ── 内部 ────────────────────────────────────────────────────

    async def _fetch_durations(self, scope: str, scope_id: int, days: int) -> list[float]:
        try:
            from app.models.metrics_snapshot import MetricsSnapshot
        except ImportError as exc:  # pragma: no cover
            raise MetricsError("无法加载 MetricsSnapshot 模型") from exc
        threshold = datetime.now(UTC) - timedelta(days=days)
        q = select(MetricsSnapshot.value).where(
            MetricsSnapshot.scope == scope,
            MetricsSnapshot.scope_id == scope_id,
            MetricsSnapshot.metric == self.METRIC_DURATION,
            MetricsSnapshot.recorded_at >= threshold,
        )
        result = await self.db.execute(q)
        return [float(r[0]) for r in result.all()]

    @staticmethod
    def _percentile(sorted_values: list[float], p: float) -> float:
        if not sorted_values:
            return 0.0
        if len(sorted_values) == 1:
            return float(sorted_values[0])
        k = (len(sorted_values) - 1) * p
        f = int(k)
        c = min(f + 1, len(sorted_values) - 1)
        if f == c:
            return float(sorted_values[f])
        return float(sorted_values[f] + (sorted_values[c] - sorted_values[f]) * (k - f))
