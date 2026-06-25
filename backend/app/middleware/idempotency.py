"""Idempotency-Key 中间件 —— 阶段 4：避免 POST 写操作重复执行。

检测 ``Idempotency-Key`` 请求头：
  - 命中缓存：直接返回上次结果（标记 ``X-Idempotent-Replay: true``），不执行业务
  - 未命中：执行业务 + 缓存结果 24h
  - 同一 key 关联不同请求体：返回 409

仅作用于写操作（POST/PUT/PATCH/DELETE），GET/HEAD/OPTIONS 直通。

实现：复用 ``app.services.idempotency.IdempotencyStore``（进程内 LRU + TTL）。
"""

from __future__ import annotations

import hashlib
import logging
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.services.idempotency import IdempotencyError, IdempotencyStore, default_store

logger = logging.getLogger("api_pilot.idempotency")

# 24 小时 TTL
DEFAULT_TTL_SECONDS: int = 24 * 60 * 60
HEADER_NAME: str = "Idempotency-Key"
REPLAY_HEADER: str = "X-Idempotent-Replay"
HASH_HEADER: str = "X-Idempotent-Hash"

_WRITE_METHODS: frozenset[str] = frozenset({"POST", "PUT", "PATCH", "DELETE"})


def _fingerprint_request(method: str, path: str, body: bytes) -> str:
    """请求指纹 = sha256(method|path|body)。"""
    h = hashlib.sha256()
    h.update(method.encode("utf-8"))
    h.update(b"|")
    h.update(path.encode("utf-8"))
    h.update(b"|")
    h.update(body or b"")
    return h.hexdigest()[:32]


def _is_idempotency_enabled() -> bool:
    """环境变量控制：默认开。设置 ``DISABLE_IDEMPOTENCY=1`` 可关闭。"""
    import os

    return os.getenv("DISABLE_IDEMPOTENCY", "0").lower() not in ("1", "true", "yes")


class IdempotencyMiddleware(BaseHTTPMiddleware):
    """Idempotency-Key 中间件。"""

    def __init__(
        self,
        app,
        *,
        store: IdempotencyStore | None = None,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
    ) -> None:
        super().__init__(app)
        self.store = store or default_store
        self.ttl_seconds = ttl_seconds

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if not _is_idempotency_enabled():
            return await call_next(request)

        # 只对写操作生效
        if request.method not in _WRITE_METHODS:
            return await call_next(request)

        key = request.headers.get(HEADER_NAME)
        if not key:
            return await call_next(request)

        # 读取 body 一次以生成指纹
        body = await request.body()
        fingerprint = _fingerprint_request(request.method, request.url.path, body)

        # 原子检查并设置（防止 TOCTOU 竞态）
        try:
            is_new, cached = await self.store.aget_or_set(key, fingerprint)
        except IdempotencyError:
            # 同一 key 关联不同 body：拒绝
            return JSONResponse(
                status_code=409,
                content={
                    "code": "2004",
                    "message": "Idempotency-Key 已被其他请求使用",
                    "suggestion": "请使用新的 Idempotency-Key，或保持请求体一致",
                    "category": "resource",
                    "detail": "key fingerprint mismatch",
                },
            )

        if not is_new and cached is not None:
            # 命中且一致：直接重放
            cached_status = cached.get("status_code", 200)
            cached_body_bytes = cached.get("body", b"")
            cached_content_type = cached.get("content_type", "application/json")
            cached_hash = cached.get("fingerprint", "")
            logger.info("Idempotency replay key=%s status=%d", key[:16], cached_status)
            headers = {
                REPLAY_HEADER: "true",
                HASH_HEADER: cached_hash,
            }
            return Response(
                content=cached_body_bytes,
                status_code=cached_status,
                headers=headers,
                media_type=cached_content_type,
            )

        # 未命中（is_new=True）：执行请求
        # 把 body 放回 receive stream，使下游能再次读取
        async def receive() -> dict:
            return {"type": "http.request", "body": body, "more_body": False}

        # 同时替换 _receive 与 scope["receive"] 以兼容 Starlette 内部
        request._receive = receive  # type: ignore[attr-defined]
        try:
            request.scope["receive"] = receive
        except (AttributeError, KeyError):
            pass
        response = await call_next(request)

        # 只缓存 2xx 成功的写操作结果；4xx/5xx 仍允许重试
        if 200 <= response.status_code < 300:
            # 读取响应体以缓存
            resp_body = b""
            async for chunk in response.body_iterator:
                resp_body += chunk
            content_type = response.headers.get("content-type", "application/json")
            await self.store.aset(
                key,
                {
                    "status_code": response.status_code,
                    "body": resp_body,
                    "fingerprint": fingerprint,
                    "content_type": content_type,
                },
                ttl_seconds=self.ttl_seconds,
            )
            # 重新构造 response（body_iterator 已被消费）
            return Response(
                content=resp_body,
                status_code=response.status_code,
                headers={
                    **dict(response.headers),
                    REPLAY_HEADER: "false",
                    HASH_HEADER: fingerprint,
                },
                media_type=content_type,
            )

        return response
