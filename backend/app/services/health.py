"""健康检查服务。

提供 ``liveness()`` / ``readiness()`` 与各组件状态（db / redis / scheduler）。

输出格式::

    {
      "status": "ok" | "degraded" | "down",
      "components": {
        "db":        {"status": "ok", "latency_ms": 1.2},
        "redis":     {"status": "ok", "latency_ms": 0.4},
        "scheduler": {"status": "ok", "running": true}
      }
    }

典型用法::

    checker = HealthChecker(db=db, scheduler=scheduler)
    body = await checker.readiness()
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("service.health")


# ── 数据结构 ────────────────────────────────────────────────────────────


@dataclass
class ComponentStatus:
    """单个组件的健康状态。"""

    name: str
    status: str = "unknown"  # ok / down / disabled / unknown
    latency_ms: float = 0.0
    detail: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "latency_ms": self.latency_ms,
            "detail": self.detail,
            **self.extra,
        }


# ── 服务实现 ────────────────────────────────────────────────────────────


class HealthChecker:
    """健康检查聚合器。"""

    def __init__(
        self,
        db: AsyncSession | None = None,
        scheduler: Any = None,
        redis_client: Any = None,
    ) -> None:
        self.db = db
        self.scheduler = scheduler
        self.redis_client = redis_client

    # ── 组件检查 ────────────────────────────────────────────────

    async def check_db(self) -> ComponentStatus:
        if self.db is None:
            return ComponentStatus(name="db", status="disabled", detail="db not provided")
        start = time.perf_counter()
        try:
            result = await self.db.execute(__import__("sqlalchemy").text("SELECT 1"))
            result.scalar()
        except Exception as exc:  # noqa: BLE001
            return ComponentStatus(
                name="db",
                status="down",
                detail=str(exc),
                latency_ms=(time.perf_counter() - start) * 1000,
            )
        return ComponentStatus(
            name="db",
            status="ok",
            latency_ms=(time.perf_counter() - start) * 1000,
        )

    async def check_redis(self) -> ComponentStatus:
        if self.redis_client is None:
            return ComponentStatus(name="redis", status="disabled", detail="redis not configured")
        start = time.perf_counter()
        try:
            client = self.redis_client
            if hasattr(client, "ping"):
                ping = client.ping
                if asyncio.iscoroutinefunction(ping):
                    await ping()
                else:
                    ping()
            else:
                return ComponentStatus(
                    name="redis",
                    status="unknown",
                    detail="client has no ping()",
                )
        except Exception as exc:  # noqa: BLE001
            return ComponentStatus(
                name="redis",
                status="down",
                detail=str(exc),
                latency_ms=(time.perf_counter() - start) * 1000,
            )
        return ComponentStatus(
            name="redis",
            status="ok",
            latency_ms=(time.perf_counter() - start) * 1000,
        )

    async def check_scheduler(self) -> ComponentStatus:
        if self.scheduler is None:
            return ComponentStatus(
                name="scheduler", status="disabled", detail="scheduler not registered"
            )
        running = bool(getattr(self.scheduler, "is_running", False))
        return ComponentStatus(
            name="scheduler",
            status="ok" if running else "down",
            extra={"running": running},
        )

    # ── 聚合 ────────────────────────────────────────────────────

    async def liveness(self) -> dict[str, Any]:
        """应用是否存活（只做最轻量判断）。"""
        return {
            "status": "ok",
            "components": {
                "app": {"status": "ok"},
            },
        }

    async def readiness(self) -> dict[str, Any]:
        """依赖是否就绪。"""
        db_status, redis_status, sched_status = await asyncio.gather(
            self.check_db(),
            self.check_redis(),
            self.check_scheduler(),
            return_exceptions=False,
        )
        components = [db_status, redis_status, sched_status]
        statuses = [c.status for c in components]
        if any(s == "down" for s in statuses):
            overall = "down"
        elif any(s not in ("ok", "disabled") for s in statuses):
            overall = "degraded"
        else:
            overall = "ok"
        return {
            "status": overall,
            "components": {c.name: c.to_dict() for c in components},
        }
