"""幂等性键存储。

默认实现：进程内 LRU + TTL。可选 Redis 适配（暂留接口，不强制依赖）。

典型用法::

    store = IdempotencyStore(default_ttl=3600)
    if (cached := store.get(key)) is not None:
        return cached
    result = await do_work()
    store.set(key, result)
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import OrderedDict
from typing import Any

logger = logging.getLogger("service.idempotency")


# ── 异常 ────────────────────────────────────────────────────────────────


class IdempotencyError(Exception):
    """幂等性错误。"""


# ── 存储条目 ────────────────────────────────────────────────────────────


class _Entry:
    __slots__ = ("value", "expires_at")

    def __init__(self, value: Any, expires_at: float) -> None:
        self.value = value
        self.expires_at = expires_at

    def is_expired(self, now: float) -> bool:
        return self.expires_at > 0 and now >= self.expires_at


# ── 实现 ────────────────────────────────────────────────────────────────


class IdempotencyStore:
    """进程内幂等性键存储。"""

    DEFAULT_CAPACITY: int = 4096

    def __init__(self, default_ttl: int = 86400, capacity: int | None = None) -> None:
        self.default_ttl = default_ttl
        self.capacity = capacity or self.DEFAULT_CAPACITY
        self._store: OrderedDict[str, _Entry] = OrderedDict()
        self._lock = asyncio.Lock()

    # ── 公共 ────────────────────────────────────────────────────

    def get(self, key: str) -> Any | None:
        """读取 key；不存在或已过期返回 None。"""
        if not key:
            raise IdempotencyError("key 不能为空")
        entry = self._store.get(key)
        if entry is None:
            return None
        if entry.is_expired(time.time()):
            try:
                del self._store[key]
            except KeyError:
                pass
            return None
        # LRU
        self._store.move_to_end(key)
        return entry.value

    def set(self, key: str, result: Any, ttl_seconds: int | None = None) -> None:
        """写入 key。"""
        if not key:
            raise IdempotencyError("key 不能为空")
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl
        expires_at = time.time() + ttl if ttl > 0 else 0.0
        self._store[key] = _Entry(result, expires_at)
        self._store.move_to_end(key)
        # 容量限制
        while len(self._store) > self.capacity:
            self._store.popitem(last=False)

    def delete(self, key: str) -> None:
        """删除 key；不存在时静默。"""
        if not key:
            return
        self._store.pop(key, None)

    def clear(self) -> None:
        self._store.clear()

    def size(self) -> int:
        return len(self._store)

    # ── 异步便捷（与 Redis 切换时签名保持一致） ─────────────────

    async def aget(self, key: str) -> Any | None:
        async with self._lock:
            return self.get(key)

    async def aset(self, key: str, result: Any, ttl_seconds: int | None = None) -> None:
        async with self._lock:
            self.set(key, result, ttl_seconds)

    async def adelete(self, key: str) -> None:
        async with self._lock:
            self.delete(key)


# ── 全局默认实例（线程/协程内共享） ───────────────────────────────


default_store = IdempotencyStore()
