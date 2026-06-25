"""SSE (Server-Sent Events) 连接管理器 — 推送通知和事件"""

import asyncio
import json
import logging
from collections.abc import AsyncGenerator
from fastapi import Request

logger = logging.getLogger("sse_manager")


class SSEManager:
    """管理 SSE 连接，支持按用户 ID 推送事件"""

    def __init__(self):
        # user_id -> list[asyncio.Queue]
        self._queues: dict[int, list[asyncio.Queue]] = {}
        self._lock = asyncio.Lock()

    async def subscribe(self, user_id: int) -> asyncio.Queue:
        """为用户创建一个事件队列"""
        queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        async with self._lock:
            if user_id not in self._queues:
                self._queues[user_id] = []
            self._queues[user_id].append(queue)
        return queue

    async def unsubscribe(self, user_id: int, queue: asyncio.Queue):
        """移除用户的事件队列"""
        async with self._lock:
            if user_id in self._queues:
                self._queues[user_id] = [q for q in self._queues[user_id] if q is not queue]
                if not self._queues[user_id]:
                    del self._queues[user_id]

    async def publish(self, user_id: int, event: str, data: dict):
        """向用户的 SSE 流推送事件"""
        async with self._lock:
            queues = list(self._queues.get(user_id, []))

        payload = json.dumps(data, ensure_ascii=False)
        dead: list[asyncio.Queue] = []
        for q in queues:
            try:
                q.put_nowait({"event": event, "data": payload})
            except asyncio.QueueFull:
                dead.append(q)

        if dead:
            async with self._lock:
                if user_id in self._queues:
                    self._queues[user_id] = [q for q in self._queues[user_id] if q not in dead]

    async def publish_notification(
        self, user_id: int, notif_id: int, title: str, content: str, notif_type: str = "info", link: str = ""
    ):
        """快捷推送通知事件"""
        await self.publish(user_id, "notification", {
            "id": notif_id,
            "type": notif_type,
            "title": title,
            "content": content,
            "link": link,
            "created_at": __import__("datetime").datetime.now().isoformat(),
        })

    async def event_generator(
        self, user_id: int, request: Request
    ) -> AsyncGenerator[str, None]:
        """生成 SSE 事件流，用于 FastAPI StreamingResponse"""
        queue = await self.subscribe(user_id)
        try:
            # 先发送一个连接建立事件
            yield f"event: connected\ndata: {json.dumps({'status': 'connected'})}\n\n"

            while True:
                # 检查客户端是否断开
                if await request.is_disconnected():
                    break

                try:
                    # 等待新事件（超时 30s 发送心跳）
                    msg = await asyncio.wait_for(queue.get(), timeout=30)
                    yield f"event: {msg['event']}\ndata: {msg['data']}\n\n"
                except asyncio.TimeoutError:
                    # 发送心跳保活
                    yield f"event: heartbeat\ndata: {json.dumps({'time': __import__('datetime').datetime.now().isoformat()})}\n\n"
        finally:
            await self.unsubscribe(user_id, queue)


# 全局单例
sse_manager = SSEManager()
