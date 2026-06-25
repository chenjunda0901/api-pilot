from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.debug_history import DebugHistory


class DebugHistoryService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, project_id: int, api_id: int, url: str,
                     method: str, duration_ms: int,
                     request_headers: str = "[]",
                     request_body: str = "",
                     response_status: int | None = None,
                     response_headers: str = "[]",
                     response_body: str = "") -> DebugHistory:
        entry = DebugHistory(
            project_id=project_id,
            api_id=api_id,
            url=url,
            method=method,
            duration_ms=duration_ms,
            request_headers=request_headers,
            request_body=request_body,
            response_status=response_status,
            response_headers=response_headers,
            response_body=response_body,
        )
        self.db.add(entry)
        await self.db.flush()
        return entry

    async def list_by_api(self, project_id: int, api_id: int,
                          limit: int = 30) -> list[DebugHistory]:
        stmt = (
            select(DebugHistory)
            .where(
                DebugHistory.project_id == project_id,
                DebugHistory.api_id == api_id,
            )
            .order_by(DebugHistory.created_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def clear_by_api(self, project_id: int, api_id: int) -> None:
        stmt = delete(DebugHistory).where(
            DebugHistory.project_id == project_id,
            DebugHistory.api_id == api_id,
        )
        await self.db.execute(stmt)

    async def get(self, history_id: int) -> DebugHistory | None:
        stmt = select(DebugHistory).where(DebugHistory.id == history_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
