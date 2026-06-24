"""trace_id 生成与上下文。

基于 ``contextvars`` 存储当前请求的 trace_id，提供 UUID4 hex 生成、设置、获取。
``with_trace`` 装饰器把函数返回值同时记录到日志。

典型用法::

    ctx = TraceContext()
    ctx.set("abc-123")
    print(ctx.get())  # abc-123
"""

from __future__ import annotations

import functools
import logging
import uuid
from contextvars import ContextVar, Token
from typing import Any, Callable, TypeVar

logger = logging.getLogger("service.trace")

_T = TypeVar("_T")

_current_trace_id: ContextVar[str | None] = ContextVar("trace_id", default=None)


class TraceContext:
    """trace_id 上下文管理器。"""

    HEADER_NAME: str = "X-Trace-Id"

    @staticmethod
    def generate_id() -> str:
        """生成新 trace_id（UUID4 hex，去除连字符）。"""
        return uuid.uuid4().hex

    @staticmethod
    def set(trace_id: str) -> None:
        """显式设置当前 trace_id。"""
        if not trace_id:
            raise ValueError("trace_id 不能为空")
        _current_trace_id.set(trace_id)

    @staticmethod
    def get() -> str | None:
        """获取当前 trace_id；未设置时返回 None。"""
        return _current_trace_id.get()

    @staticmethod
    def clear() -> None:
        """清除当前 trace_id。"""
        _current_trace_id.set(None)

    @staticmethod
    def token() -> Token[str | None]:
        """返回 ``ContextVar.set`` 的 token，用于回滚。"""
        return _current_trace_id.set(uuid.uuid4().hex)

    @staticmethod
    def reset(token: Token[str | None]) -> None:
        """重置 ``token`` 到先前状态。"""
        _current_trace_id.reset(token)

    @staticmethod
    def from_headers(headers: dict[str, str] | None) -> str:
        """从请求头里读 trace_id；缺失则生成新的并写入 context。"""
        if headers:
            for k, v in headers.items():
                if k.lower() == TraceContext.HEADER_NAME.lower() and v:
                    TraceContext.set(v)
                    return v
        new_id = TraceContext.generate_id()
        TraceContext.set(new_id)
        return new_id

    @staticmethod
    def with_trace(fn: Callable[..., _T]) -> Callable[..., _T]:
        """装饰器：进入函数时确保有 trace_id，并把 trace_id 写入日志记录。"""

        @functools.wraps(fn)
        def sync_wrapper(*args: Any, **kwargs: Any) -> _T:
            tid = _current_trace_id.get() or TraceContext.generate_id()
            TraceContext.set(tid)
            logger.debug("trace[%s] enter %s", tid, fn.__qualname__)
            try:
                return fn(*args, **kwargs)
            finally:
                logger.debug("trace[%s] exit %s", tid, fn.__qualname__)

        return sync_wrapper


# 模块级单例
default_context = TraceContext()
