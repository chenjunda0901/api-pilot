"""请求结构化日志中间件 —— 阶段 4：J5 可观测性。

行为：
  - 每个请求注入 ``trace_id``（从 ``X-Trace-Id`` 头读取或生成）
  - 把 trace_id / request_id / user_id / project_id / path / method 写入响应头
  - 请求开始 → INFO（轻量）
  - 请求结束 → INFO（成功）/ WARNING（4xx）/ ERROR（5xx，含 stacktrace）
  - 与 ``app.services.trace.TraceContext`` 配合：在请求处理过程中通过
    ``logger.bind(trace_id=...)`` 输出带 trace 字段的日志

为什么单独成文件：保持 ``app.utils.logging`` 通用工具属性，专注于
"在中间件里如何把上下文塞进日志"。
"""

from __future__ import annotations

import logging
import time
import traceback
from typing import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.services.trace import TraceContext

logger = logging.getLogger("api_pilot.request_log")

# 拿到一个支持 bind 的 logger
try:
    import structlog
    _bound_logger = structlog.get_logger("api_pilot.request_log")
except ImportError:  # pragma: no cover
    structlog = None  # type: ignore
    _bound_logger = logger


def _safe_log(logger_instance, level: str, msg: str):
    """安全日志调用，兼容 structlog 和标准 logging。"""
    try:
        getattr(logger_instance, level)(msg)
    except Exception:
        pass  # 日志失败不应中断请求


def _get_bound_logger():
    """每次重新取，避免在 configure_logging 之后仍未启用 structlog。"""
    if structlog is not None:
        return structlog.get_logger("api_pilot.request_log")
    return logger

# 跳过路径前缀（健康检查、Swagger、静态资源）
_SKIP_PATH_PREFIXES: tuple[str, ...] = (
    "/health",
    "/favicon",
    "/static",
    "/docs",
    "/openapi.json",
    "/redoc",
)


def _resolve_user_id(request: Request) -> int | None:
    """从 ``request.state`` 或 header 推断 user_id。"""
    state = getattr(request, "state", None)
    if state is not None:
        uid = getattr(state, "user_id", None)
        if uid is not None:
            return int(uid)
    return None


class StructuredRequestLoggingMiddleware(BaseHTTPMiddleware):
    """结构化请求日志中间件。

    响应头注入：
      - X-Trace-Id: 全局链路 ID
      - X-Request-Id: 与 request_tracking 保持一致
    """

    def __init__(self, app, *, skip_path_prefixes: tuple[str, ...] = _SKIP_PATH_PREFIXES) -> None:
        super().__init__(app)
        self.skip_path_prefixes = skip_path_prefixes

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        path = request.url.path
        method = request.method
        skip = any(path.startswith(p) for p in self.skip_path_prefixes)

        # 注入 trace_id
        trace_id = TraceContext.from_headers(dict(request.headers))
        # 取 request_id（由 RequestTrackingMiddleware 设置过或自己生成）
        request_id = request.headers.get("X-Request-ID") or trace_id
        request.state.request_id = request_id
        request.state.trace_id = trace_id

        # 绑定 trace_id 的 logger（fallback 到普通 logger）
        bind = getattr(_get_bound_logger(), "bind", None)
        if callable(bind):
            bound = bind(
                trace_id=trace_id,
                request_id=request_id,
                method=method,
                path=path,
            )
        else:
            bound = logger
        user_id = _resolve_user_id(request)

        if not skip:
            bound.info("request_start")

        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            elapsed_ms = (time.perf_counter() - start) * 1000
            if not skip:
                bound.error(
                    "request_failed: unhandled exception (%.0fms) [user=%s]\n%s",
                    elapsed_ms, user_id or "?", traceback.format_exc(),
                )
            raise

        elapsed_ms = (time.perf_counter() - start) * 1000
        status = response.status_code
        # 注入 trace_id / request_id
        response.headers["X-Trace-Id"] = trace_id
        response.headers["X-Request-ID"] = request_id

        if not skip:
            if status >= 500:
                _safe_log(bound, "error", f"request_end status={status} user_id={user_id} duration={elapsed_ms:.0f}ms")
            elif status >= 400:
                _safe_log(bound, "warning", f"request_end status={status} user_id={user_id} duration={elapsed_ms:.0f}ms")
            else:
                _safe_log(bound, "info", f"request_end status={status} duration={elapsed_ms:.0f}ms")
        return response
