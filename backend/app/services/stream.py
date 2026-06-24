"""流式响应处理。

支持按行 / 按块读取，避免 OOM。常用于 SSE、大文件下载。

典型用法::

    processor = StreamProcessor()
    async for line in processor.stream_lines(response.aiter_lines()):
        print(line)
"""

from __future__ import annotations

import logging
from typing import Any, AsyncIterator

logger = logging.getLogger("service.stream")


class StreamProcessor:
    """流式响应处理器。"""

    DEFAULT_MAX_BYTES: int = 10 * 1024 * 1024
    DEFAULT_CHUNK_SIZE: int = 8192

    def __init__(self, max_bytes: int | None = None, chunk_size: int | None = None) -> None:
        self.max_bytes = max_bytes or self.DEFAULT_MAX_BYTES
        self.chunk_size = chunk_size or self.DEFAULT_CHUNK_SIZE

    async def stream_lines(
        self,
        source: AsyncIterator[str] | Any,
    ) -> AsyncIterator[str]:
        """按行迭代；累计字节数超过 ``max_bytes`` 时抛 ``StreamSizeLimitExceeded``。"""
        total = 0
        try:
            iterator = source.aiter_lines() if hasattr(source, "aiter_lines") else source
            async for line in iterator:  # type: ignore[union-attr]
                total += len(line.encode("utf-8", errors="ignore"))
                if total > self.max_bytes:
                    raise StreamSizeLimitExceeded(f"流式响应超过 {self.max_bytes} 字节上限")
                yield line
        except StreamSizeLimitExceeded:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.warning("stream_lines error: %s", exc)
            raise

    async def stream_chunks(
        self,
        source: Any,
        chunk_size: int | None = None,
    ) -> AsyncIterator[bytes]:
        """按块迭代（默认 ``self.chunk_size``）。"""
        size = chunk_size or self.chunk_size
        total = 0
        try:
            aiter_bytes = source.aiter_bytes if hasattr(source, "aiter_bytes") else None
            if aiter_bytes is not None:
                async for chunk in aiter_bytes(chunk_size=size):
                    total += len(chunk)
                    if total > self.max_bytes:
                        raise StreamSizeLimitExceeded(
                            f"流式响应超过 {self.max_bytes} 字节上限"
                        )
                    yield chunk
            else:
                # 退化：read() 模式
                while True:
                    chunk = source.read(size)
                    if not chunk:
                        break
                    if isinstance(chunk, str):
                        chunk = chunk.encode("utf-8", errors="ignore")
                    total += len(chunk)
                    if total > self.max_bytes:
                        raise StreamSizeLimitExceeded(
                            f"流式响应超过 {self.max_bytes} 字节上限"
                        )
                    yield chunk
        except StreamSizeLimitExceeded:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.warning("stream_chunks error: %s", exc)
            raise

    async def collect(
        self,
        source: Any,
        max_bytes: int | None = None,
    ) -> bytes:
        """把流读完到内存（带上限）。"""
        cap = max_bytes or self.max_bytes
        buf = bytearray()
        async for chunk in self.stream_chunks(source, chunk_size=self.chunk_size):
            buf.extend(chunk)
            if len(buf) > cap:
                raise StreamSizeLimitExceeded(f"流式响应超过 {cap} 字节上限")
        return bytes(buf)


class StreamError(Exception):
    """流式处理错误。"""


class StreamSizeLimitExceeded(StreamError):
    """流式响应超过 max_bytes 上限。"""
