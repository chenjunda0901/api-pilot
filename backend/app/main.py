import time
import traceback
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException, RequestValidationError
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.database import engine, async_session_factory, warmup_pool
from sqlalchemy import text
from app.limiter import limiter
from app.models.base import Base
from app.core.exceptions import BizError
from app.middleware.request_tracking import RequestTrackingMiddleware
from app.middleware.timeout import RequestTimeoutMiddleware
from app.middleware.idempotency import IdempotencyMiddleware
from app.middleware.request_logging import StructuredRequestLoggingMiddleware


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

logger = logging.getLogger("api_pilot")
_app_start_time = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        if settings.ENVIRONMENT != "production":
            await conn.run_sync(Base.metadata.create_all)
    await warmup_pool()
    from app.utils.scheduler import init_scheduler

    await init_scheduler()
    # 自动初始化种子数据（确保模板存在 + 老用户自动补齐私有副本）
    from app.utils.seed_core import seed_demo_data

    try:
        async with async_session_factory() as db:
            await seed_demo_data(db, auto_migrate=True)
    except Exception as e:
        import logging

        logging.getLogger("api_pilot").warning(
            f"种子数据初始化跳过（不影响服务启动）: {e}"
        )
    logger.info("App started")
    yield
    from app.utils.scheduler import shutdown_scheduler

    await shutdown_scheduler()
    from app.utils.http_client import close_http_client

    await close_http_client()
    await engine.dispose()


# ── 模块级安全配置检查（在 lifespan 和 middleware 注册之前执行）────

# CORS 安全检查：ENFORCE_CORS_WHITELIST=true 时拒绝全开（独立于 is_production）
if settings.cors_has_restrictions and settings.CORS_ORIGINS == "*":
    raise RuntimeError(
        "FATAL: ENFORCE_CORS_WHITELIST=true，不允许 CORS_ORIGINS=*，"
        "请通过 CORS_ORIGINS 环境变量设置允许的域名（逗号分隔）"
    )
if settings.is_production and settings.CORS_ORIGINS == "*":
    raise RuntimeError(
        "FATAL: 生产环境 (API_PILOT_SECRET_KEY 已设置) 不允许 CORS_ORIGINS=*，"
        "请通过 CORS_ORIGINS 环境变量设置允许的域名（逗号分隔）"
    )
if settings.CORS_ORIGINS == "*":
    logger.warning(
        "CORS: allow_origins=* (development mode) — 生产环境请通过 CORS_ORIGINS 环境变量限制允许的域名"
    )

app = FastAPI(
    title="API Pilot",
    description="Enterprise API automation testing platform",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS: 从环境变量读取允许的域名，逗号分隔，默认允许所有来源（开发环境）
_cors_origins_str = settings.CORS_ORIGINS
_cors_allow_origins = (
    ["*"]
    if _cors_origins_str == "*"
    else [o.strip() for o in _cors_origins_str.split(",")]
)
# 安全规则：当 origins 为 "*"（通配）时不能设置 allow_credentials=True
_cors_allow_creds = _cors_origins_str != "*"
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_allow_origins,
    allow_credentials=_cors_allow_creds,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "Accept",
        "X-Requested-With",
        "X-Request-ID",
    ],
)
if not _cors_allow_creds:
    logger.info(
        "CORS: allow_origins=* (development mode) — credentials cookies disabled"
    )
else:
    logger.info(
        "CORS: restricted origins=%s with credentials enabled", _cors_allow_origins
    )

# 请求追踪中间件（整合性能监控：耗时记录 + 慢请求告警 + 静态资源过滤）
app.add_middleware(RequestTrackingMiddleware)

# 阶段 4 增强：结构化请求日志（trace_id 注入 + 完整请求生命周期日志）
app.add_middleware(StructuredRequestLoggingMiddleware)

# 阶段 4 增强：幂等性中间件（POST/PUT/PATCH/DELETE 写操作）
# 注意：add_middleware 是 LIFO，逆序包裹；放在最外层意味着最先生效
app.add_middleware(IdempotencyMiddleware)

# 阶段 4 增强：请求级超时（默认 30s，X-Request-Timeout 头可覆盖）
app.add_middleware(RequestTimeoutMiddleware)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.exception_handler(BizError)
async def biz_error_handler(request: Request, exc: BizError):
    """拦截 BizError：利用异常对象自带的 http_status 动态返回状态码。

    阶段 4 增强：返回 ``suggestion`` / ``category`` / ``details``，便于前端展示。
    """
    body = exc.to_payload()
    body["data"] = None
    return JSONResponse(
        status_code=exc.http_status,
        content=body,
        headers={"X-Error-Code": exc.code} if exc.code else None,
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """万能兜底拦截器：捕获所有未处理异常，返回用户友好的错误信息"""
    traceback.format_exc()

    # 只记录 traceback 的文件/行号/函数名，过滤变量值以防止凭据泄漏到日志
    tb = traceback.extract_tb(exc.__traceback__)
    sanitized_tb = "\n".join(
        f'  File "{frame.filename}", line {frame.lineno}, in {frame.name}'
        for frame in tb
    )
    logger.critical(
        "系统未捕获异常 [%s %s] %s: %s\n%s",
        request.method,
        request.url.path,
        type(exc).__name__,
        exc,
        sanitized_tb,
    )

    # 根据异常类型返回友好的错误信息
    friendly_messages = {
        "TimeoutError": "请求超时，请稍后重试",
        "asyncio.TimeoutError": "请求超时，请稍后重试",
        "ConnectionError": "网络连接失败，请检查网络后重试",
        "OperationalError": "数据库操作失败，请稍后重试",
        "IntegrityError": "数据冲突，请刷新后重试",
        "ReferenceError": "数据引用错误，请刷新后重试",
        "AttributeError": "系统内部错误，请联系管理员",
        "TypeError": "数据类型错误，请稍后重试",
        "ValueError": "数据值错误，请检查输入后重试",
        "FileNotFoundError": "请求的资源不存在",
        "PermissionError": "权限不足，请联系管理员",
    }

    exc_type_name = type(exc).__name__
    friendly_message = friendly_messages.get(exc_type_name, "服务器繁忙，请稍后重试")

    # 开发环境显示更多信息
    if settings.is_production:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "code": "INTERNAL_ERROR",
                "message": friendly_message,
                "detail": None,
                "data": None,
            },
        )
    else:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "code": "INTERNAL_ERROR",
                "message": friendly_message,
                "detail": f"{type(exc).__name__}: {exc}" if exc else None,
                "data": None,
            },
        )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """HTTP 异常处理：返回友好的错误信息"""
    status_messages = {
        400: "请求格式错误，请检查输入",
        401: "未登录或登录已过期，请重新登录",
        403: "权限不足，无法执行此操作",
        404: "请求的资源不存在",
        405: "不支持的请求方法",
        408: "请求超时，请重试",
        409: "资源冲突，请刷新后重试",
        413: "请求数据过大，请精简后重试",
        429: "请求过于频繁，请稍后重试",
        500: "服务器内部错误，请稍后重试",
        502: "网关错误，请稍后重试",
        503: "服务暂时不可用，请稍后重试",
        504: "网关超时，请重试",
    }

    message = status_messages.get(exc.status_code, exc.detail or "请求处理失败")

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": f"HTTP_{exc.status_code}",
            "message": message,
            "detail": str(exc.detail)
            if exc.detail and not settings.is_production
            else None,
            "data": None,
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """请求参数校验失败：返回友好的错误信息"""
    errors = []
    for error in exc.errors():
        loc = " -> ".join(str(loc_item) for loc_item in error["loc"])
        errors.append(
            {
                "field": loc,
                "message": error["msg"],
            }
        )

    # 格式化友好消息
    error_fields = [e["field"].split(" -> ")[-1] for e in errors]
    friendly_message = f"参数错误: {', '.join(error_fields)}"

    return JSONResponse(
        status_code=422,
        content={
            "code": "VALIDATION_ERROR",
            "message": friendly_message,
            "detail": "请检查以下参数后重试",
            "data": errors,
        },
    )


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """限流异常：返回友好的限流提示"""
    return JSONResponse(
        status_code=429,
        content={
            "code": "RATE_LIMIT_EXCEEDED",
            "message": "操作太频繁了，请稍后再试",
            "detail": "已触发限流保护，请等待片刻后再试",
            "data": None,
        },
        headers={"Retry-After": "60"},
    )


from app.routers import (
    auth,
    projects,
    members,
    categories,
    apis,
    environments,
    system,
    cases,
    scenes,
    scene_categories,
    reports,
    run,
    mock,
    import_export,
    search,
    debug_history,
    docs,
    data_schemas,
)


# ── 健康检查端点（负载均衡器 / K8s 探针 / 监控系统）────
@app.get("/health", tags=["system"], summary="服务健康检查")
async def health_check():
    """返回服务状态、版本号、运行时间和数据库连通性。用于部署探活。"""
    db_status = "unknown"
    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception:
        db_status = "error"

    return {
        "status": "ok",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "database": db_status,
        "uptime_seconds": round(time.time() - _app_start_time, 1),
    }


@app.get("/health/ready", tags=["system"], summary="就绪检查（含DB）")
async def readiness_check():
    """检查服务是否就绪（含数据库连通性和连接池状态）。"""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        pool_status = {
            "size": engine.pool.size() if hasattr(engine.pool, "size") else None,
            "checked_in": engine.pool.checkedin()
            if hasattr(engine.pool, "checkedin")
            else None,
            "checked_out": engine.pool.checkedout()
            if hasattr(engine.pool, "checkedout")
            else None,
        }
        return {"status": "ready", "database": "ok", "pool": pool_status}
    except Exception as exc:
        logger.error("Readiness check failed: %s", exc)
        raise HTTPException(
            status_code=503, detail={"status": "not_ready", "reason": str(exc)}
        )


app.include_router(auth.router, prefix="/api/v1")
app.include_router(projects.router, prefix="/api/v1")
app.include_router(categories.router, prefix="/api/v1")
app.include_router(apis.router, prefix="/api/v1")
app.include_router(environments.router, prefix="/api/v1")
app.include_router(system.router, prefix="/api/v1")
app.include_router(cases.router, prefix="/api/v1")
app.include_router(scenes.router, prefix="/api/v1")
app.include_router(scene_categories.router, prefix="/api/v1")
app.include_router(reports.router, prefix="/api/v1")
app.include_router(reports.public_router, prefix="/api/v1")
app.include_router(run.router, prefix="/api/v1")
app.include_router(mock.router, prefix="/api/v1")
app.include_router(mock.mock_request_router, prefix="/api/v1")
app.include_router(mock.mock_test_router, prefix="/api/v1")
app.include_router(import_export.router, prefix="/api/v1")
app.include_router(search.router, prefix="/api/v1")
app.include_router(debug_history.router, prefix="/api/v1")
app.include_router(members.router, prefix="/api/v1")
app.include_router(docs.router, prefix="/api/v1")
app.include_router(docs.shared_router, prefix="/api/v1")
app.include_router(data_schemas.router, prefix="/api/v1")

# ── 阶段 3 新增路由 ──────────────────────────────────────────────────
from app.routers import (
    assertions,  # 断言库
    variables,  # 5 层变量
)

app.include_router(assertions.router, prefix="/api/v1")
app.include_router(variables.router, prefix="/api/v1")
from app.routers import tags

app.include_router(tags.router, prefix="/api/v1")
# 健康检查（无 v1 前缀）
from app.routers import health

app.include_router(health.router)
# 电商 Mock 路由（模拟外部 API）：默认开启，测试环境直接可用
if settings.MOCK_ECOMMERCE_ENABLED:
    from app.routers.mock_ecommerce import router as mock_ecommerce_router

    app.include_router(mock_ecommerce_router)
    logger.info("电商 Mock 路由已注册（MOCK_ECOMMERCE_ENABLED=true）")


# 调试路由（仅开发/测试环境，生产环境不注册）
if not settings.is_production:
    from app.routers.debug import router as debug_router

    app.include_router(debug_router, prefix="/api/v1")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=not settings.is_production,
        server_header=False,
    )
