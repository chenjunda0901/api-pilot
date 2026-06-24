"""健康检查路由（无 /api/v1 前缀）。"""

import logging

from fastapi import APIRouter
from sqlalchemy import text

from app.config import settings
from app.database import engine
from app.services.health import HealthChecker
from app.utils.response import success
from app.utils.scheduler import scheduler as ap_scheduler

logger = logging.getLogger("api_pilot.routers.health")
router = APIRouter(tags=["Health"])


@router.get("/health", summary="综合健康检查")
async def health():
    """返回服务整体健康状态（含各依赖）。"""
    checker = HealthChecker(scheduler=ap_scheduler)
    body = await checker.readiness()
    body["version"] = "1.0.0"
    body["environment"] = settings.ENVIRONMENT
    return success(body)


@router.get("/health/live", summary="Liveness 探针")
async def health_live():
    """Liveness：仅判断应用是否存活，不做依赖检查。"""
    return {"status": "ok"}


@router.get("/health/ready", summary="Readiness 探针（含依赖）")
async def health_ready():
    """Readiness：检查 DB / scheduler 等依赖是否就绪。"""
    checker = HealthChecker(scheduler=ap_scheduler)
    # DB 检查：临时从 engine 取连接
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        from app.services.health import ComponentStatus
        db_status = ComponentStatus(name="db", status="ok")
    except Exception as exc:
        from app.services.health import ComponentStatus
        db_status = ComponentStatus(name="db", status="down", detail=str(exc))
    scheduler_status = await checker.check_scheduler()
    overall = "ok"
    if db_status.status == "down" or scheduler_status.status == "down":
        overall = "down"
    return {
        "status": overall,
        "components": {
            "db": db_status.to_dict(),
            "scheduler": scheduler_status.to_dict(),
        },
    }
