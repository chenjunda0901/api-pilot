"""WebSocket 连接管理器 — 支持按场景执行房间广播进度"""

import json
import asyncio
import logging
from fastapi import WebSocket

logger = logging.getLogger("ws_manager")


class WSConnectionManager:
    """管理 WebSocket 连接，支持按房间分组广播"""

    def __init__(self):
        # room_id -> list[WebSocket]
        self._rooms: dict[str, list[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, room: str):
        """接受 WebSocket 连接并加入房间"""
        await websocket.accept()
        async with self._lock:
            if room not in self._rooms:
                self._rooms[room] = []
            self._rooms[room].append(websocket)
            logger.debug(f"WS connected: room={room}, total={len(self._rooms[room])}")

    async def disconnect(self, websocket: WebSocket, room: str):
        """从房间断开 WebSocket 连接"""
        async with self._lock:
            if room in self._rooms:
                self._rooms[room] = [ws for ws in self._rooms[room] if ws != websocket]
                if not self._rooms[room]:
                    del self._rooms[room]
            logger.debug(f"WS disconnected: room={room}")

    async def broadcast(self, room: str, message: dict):
        """向房间内所有连接广播消息"""
        async with self._lock:
            sockets = self._rooms.get(room, []).copy()

        if not sockets:
            return

        payload = json.dumps(message, ensure_ascii=False)
        dead: list[WebSocket] = []

        for ws in sockets:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)

        # 清理断开的连接
        if dead:
            async with self._lock:
                if room in self._rooms:
                    self._rooms[room] = [ws for ws in self._rooms[room] if ws not in dead]

    async def broadcast_step_progress(
        self,
        report_id: int,
        step_index: int,
        total_steps: int,
        step_id: int,
        step_name: str,
        status: str,  # "running" | "success" | "failed" | "skipped" | "error"
        duration: float = 0,
        error_message: str = "",
    ):
        """广播步骤执行进度"""
        room = f"report:{report_id}"
        await self.broadcast(room, {
            "type": "step_progress",
            "report_id": report_id,
            "step_index": step_index,
            "total_steps": total_steps,
            "step_id": step_id,
            "step_name": step_name,
            "status": status,
            "duration": duration,
            "error_message": error_message,
            "timestamp": __import__("datetime").datetime.now().isoformat(),
        })

    async def broadcast_report_done(
        self,
        report_id: int,
        status: str,
        pass_count: int,
        fail_count: int,
        total_count: int,
    ):
        """广播报告完成"""
        room = f"report:{report_id}"
        await self.broadcast(room, {
            "type": "report_done",
            "report_id": report_id,
            "status": status,
            "pass_count": pass_count,
            "fail_count": fail_count,
            "total_count": total_count,
            "timestamp": __import__("datetime").datetime.now().isoformat(),
        })


# 全局单例
ws_manager = WSConnectionManager()
