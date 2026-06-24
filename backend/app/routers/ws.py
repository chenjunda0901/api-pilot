"""WebSocket 端点 — 实时执行进度推送"""

import json
import logging

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.database import async_session_factory
from app.models.test_report import TestReport
from app.models.project import Project
from app.models.project_member import ProjectMember

from app.middleware.auth import decode_token
from app.services.ws_manager import ws_manager

logger = logging.getLogger("ws_router")

router = APIRouter()


@router.websocket("/ws/report/{report_id}")
async def websocket_report_progress(
    websocket: WebSocket,
    report_id: int,
    token: str = Query(""),
):
    """WebSocket 端点：订阅测试报告的实时执行进度。

    连接后将收到以下消息格式：
        {"type": "step_progress", "report_id": 1, "step_index": 0,
         "total_steps": 5, "step_id": 10, "step_name": "GET /users",
         "status": "running", "duration": 0.0, "error_message": "",
         "timestamp": "2024-01-01T00:00:00"}

        {"type": "report_done", "report_id": 1, "status": "success",
         "pass_count": 4, "fail_count": 1, "total_count": 5,
         "timestamp": "2024-01-01T00:00:10"}

    客户端应当处理这些消息类型并更新 UI。
    """
    if not token:
        await websocket.close(code=4001, reason="Missing token")
        return
    payload = decode_token(token)
    if not payload:
        await websocket.close(code=4001, reason="Invalid token")
        return

    user_id = int(payload.get("sub", 0) or 0)
    if payload.get("type") != "access" or user_id <= 0:
        await websocket.close(code=4001, reason="Invalid token")
        return

    async with async_session_factory() as db:
        report_result = await db.execute(select(TestReport).where(TestReport.id == report_id))
        report = report_result.scalar_one_or_none()
        if not report:
            await websocket.close(code=4404, reason="Report not found")
            return

        project_result = await db.execute(select(Project).where(Project.id == report.project_id))
        project = project_result.scalar_one_or_none()
        if not project:
            await websocket.close(code=4404, reason="Project not found")
            return

        if project.created_by != user_id:
            member_result = await db.execute(
                select(ProjectMember).where(
                    ProjectMember.project_id == project.id,
                    ProjectMember.user_id == user_id,
                )
            )
            member = member_result.scalar_one_or_none()
            if not member:
                await websocket.close(code=4003, reason="Forbidden")
                return

    room = f"report:{report_id}"
    await ws_manager.connect(websocket, room)
    try:
        while True:
            # 保持连接，接收心跳或取消指令
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
                elif msg.get("type") == "cancel":
                    # 客户端取消执行（预留功能）
                    logger.info("Cancel requested for report %s", report_id)
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.warning("WebSocket error for report %s: %s", report_id, e)
    finally:
        await ws_manager.disconnect(websocket, room)


@router.websocket("/ws/project/{project_id}")
async def websocket_project_events(
    websocket: WebSocket,
    project_id: int,
    token: str = Query(""),
):
    """WebSocket 端点：订阅项目级事件（成员变更、通知等）"""
    if not token:
        await websocket.close(code=4001, reason="Missing token")
        return
    payload = decode_token(token)
    if not payload:
        await websocket.close(code=4001, reason="Invalid token")
        return

    user_id = int(payload.get("sub", 0) or 0)
    if payload.get("type") != "access" or user_id <= 0:
        await websocket.close(code=4001, reason="Invalid token")
        return

    async with async_session_factory() as db:
        project_result = await db.execute(select(Project).where(Project.id == project_id))
        project = project_result.scalar_one_or_none()
        if not project:
            await websocket.close(code=4404, reason="Project not found")
            return

        if project.created_by != user_id:
            member_result = await db.execute(
                select(ProjectMember).where(
                    ProjectMember.project_id == project_id,
                    ProjectMember.user_id == user_id,
                )
            )
            member = member_result.scalar_one_or_none()
            if not member:
                await websocket.close(code=4003, reason="Forbidden")
                return

    room = f"project:{project_id}"
    await ws_manager.connect(websocket, room)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.warning("WebSocket error for project %s: %s", project_id, e)
    finally:
        await ws_manager.disconnect(websocket, room)
