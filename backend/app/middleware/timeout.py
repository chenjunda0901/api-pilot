"""请求超时中间件 —— 阶段 4：三层超时控制的第一层（请求级）。

行为：
  - 检测 ``X-Request-Timeout`` 头（秒）。缺失则用默认 30s。
  - 用 ``asyncio.wait_for`` 包裹 ``call_next``。
  - 超时返回 504 + 统一错误体（code=3013）。
  - 通过环境变量 ``DISABLE_REQUEST_TIMEOUT=1`` 可关闭（默认开）。

注意：
  - 已发出的 StreamingResponse 不会因超时而被取消（已被消费）。
  - 静态资源路径默认跳过（由 ``skip_path_prefixes`` 控制）。
"""

from __future__ import annotations

import asyncio
import logging
import os
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

logger = logging.getLogger("api_pilot.timeout")

DEFAULT_TIMEOUT_SECONDS: float = 30.0
MAX_TIMEOUT_SECONDS: float = 120.0  # 硬上限 2 分钟
HEADER_NAME: str = "X-Request-Timeout"

# 默认跳过：探针 + 静态资源
_SKIP_PATH_PREFIXES: tuple[str, ...] = (
    "/health",
    "/favicon",
    "/static",
    "/docs",
    "/openapi.json",
    "/redoc",
)


def _is_enabled() -> bool:
    return os.getenv("DISABLE_REQUEST_TIMEOUT", "0").lower() not in ("1", "true", "yes")


def _parse_timeout(value: str | None) -> float:
    """解析 header 值；无效则返回默认。"""
    if not value:
        return DEFAULT_TIMEOUT_SECONDS
    try:
        v = float(value)
    except (TypeError, ValueError):
        return DEFAULT_TIMEOUT_SECONDS
    if v <= 0:
        return DEFAULT_TIMEOUT_SECONDS
    return min(v, MAX_TIMEOUT_SECONDS)


class RequestTimeoutMiddleware(BaseHTTPMiddleware):
    """请求级超时中间件。"""

    def __init__(
        self,
        app,
        *,
        default_timeout: float = DEFAULT_TIMEOUT_SECONDS,
        skip_path_prefixes: tuple[str, ...] = _SKIP_PATH_PREFIXES,
    ) -> None:
        super().__init__(app)
        self.default_timeout = default_timeout
        self.skip_path_prefixes = skip_path_prefixes

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if not _is_enabled():
            return await call_next(request)

        path = request.url.path
        if any(path.startswith(p) for p in self.skip_path_prefixes):
            return await call_next(request)

        timeout = _parse_timeout(request.headers.get(HEADER_NAME))
        try:
            return await asyncio.wait_for(call_next(request), timeout=timeout)
        except asyncio.TimeoutError:
            logger.warning(
                "Request timeout after %.1fs: %s %s",
                timeout,
                request.method,
                path,
            )
            return JSONResponse(
                status_code=504,
                content={
                    "code": "3013",
                    "message": "请求处理超时",
                    "suggestion": "请稍后重试或增加 X-Request-Timeout 头（秒）",
                    "category": "business",
                    "detail": f"timeout={timeout}s",
                    "data": None,
                },
            )
