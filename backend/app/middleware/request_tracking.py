"""请求追踪中间件 —— 为每个请求分配唯一 ID，记录耗时和关键上下文

功能：
1. 为每个请求生成 UUID request_id，注入到 request.state 和响应头
2. 记录请求耗时，超过阈值的慢请求自动告警
3. 在日志中统一格式化 request_id，便于链路追踪
4. 响应头返回 X-Request-ID，便于前端排查问题
"""

import time
import uuid
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("api_pilot.request")

# 慢请求阈值（毫秒）
SLOW_REQUEST_THRESHOLD_MS = 1000


class RequestTrackingMiddleware(BaseHTTPMiddleware):
    """请求追踪中间件"""

    async def dispatch(self, request: Request, call_next):
        # 生成或复用 request_id
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:16]
        request.state.request_id = request_id

        # 记录请求开始
        start_time = time.monotonic()
        method = request.method
        path = request.url.path

        try:
            response: Response = await call_next(request)
        except Exception:
            # 记录异常但不处理（由全局异常处理器负责）
            elapsed_ms = (time.monotonic() - start_time) * 1000
            logger.error(
                "[%s] %s %s → ERROR (%.0fms)",
                request_id, method, path, elapsed_ms,
            )
            raise

        # 计算耗时
        elapsed_ms = (time.monotonic() - start_time) * 1000

        # 注入 response header
        response.headers["X-Request-ID"] = request_id

        # 跳过静态资源和健康检查的日志
        if not path.startswith("/api/health") and not path.endswith((".js", ".css", ".png", ".ico")):
            status = response.status_code
            log_fn = logger.warning if elapsed_ms > SLOW_REQUEST_THRESHOLD_MS else logger.info

            if status >= 500:
                log_fn = logger.error
            elif status >= 400:
                log_fn = logger.warning

            log_fn(
                "[%s] %s %s → %d (%.0fms)",
                request_id, method, path, status, elapsed_ms,
            )

        return response
