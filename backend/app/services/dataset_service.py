import logging
from typing import Optional
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.test_dataset import TestDataset, TestDatasetRow
from app.core.exceptions import raise_biz, ErrorCodes

logger = logging.getLogger("api_pilot.services.dataset_service")


class DatasetService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self, dataset_id: int) -> TestDataset:
        result = await self.db.execute(select(TestDataset).where(TestDataset.id == dataset_id))
        ds = result.scalar_one_or_none()
        if not ds:
            raise_biz(ErrorCodes.NOT_FOUND, f"Dataset {dataset_id} not found")
        return ds

    async def list(self, project_id: int) -> list:
        result = await self.db.execute(
            select(TestDataset).where(TestDataset.project_id == project_id)
            .order_by(TestDataset.updated_at.desc())
        )
        datasets = result.scalars().all()
        items = []
        for ds in datasets:
            row_count = await self.db.scalar(
                select(func.count(TestDatasetRow.id)).where(TestDatasetRow.dataset_id == ds.id)
            ) or 0
            items.append({
                "id": ds.id, "name": ds.name, "description": ds.description,
                "project_id": ds.project_id, "is_builtin": ds.is_builtin,
                "row_count": row_count,
                "created_at": str(ds.created_at), "updated_at": str(ds.updated_at),
            })
        return items

    async def create(self, project_id: int, name: str, description: Optional[str] = None) -> TestDataset:
        ds = TestDataset(project_id=project_id, name=name, description=description)
        self.db.add(ds)
        await self.db.flush()
        await self.db.refresh(ds)
        return ds

    async def update(self, dataset_id: int, name: Optional[str] = None, description: Optional[str] = None):
        ds = await self.get(dataset_id)
        if name is not None:
            ds.name = name
        if description is not None:
            ds.description = description
        await self.db.flush()
        await self.db.refresh(ds)
        return ds

    async def delete(self, dataset_id: int):
        ds = await self.get(dataset_id)
        await self.db.delete(ds)
        await self.db.flush()

    async def get_rows(self, dataset_id: int, enabled_only: bool = False) -> list:
        query = select(TestDatasetRow).where(TestDatasetRow.dataset_id == dataset_id)
        if enabled_only:
            query = query.where(TestDatasetRow.is_enabled)
        query = query.order_by(TestDatasetRow.row_index)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def batch_add_rows(self, dataset_id: int, rows_data: list) -> int:
        max_idx = await self.db.scalar(
            select(func.max(TestDatasetRow.row_index)).where(TestDatasetRow.dataset_id == dataset_id)
        ) or -1
        for i, rd in enumerate(rows_data):
            row = TestDatasetRow(
                dataset_id=dataset_id, row_index=max_idx + 1 + i,
                data=rd.get("data", "{}"), is_enabled=rd.get("is_enabled", True)
            )
            self.db.add(row)
        await self.db.flush()
        return len(rows_data)

    async def update_row(self, row_id: int, data: Optional[str] = None, is_enabled: Optional[bool] = None):
        result = await self.db.execute(select(TestDatasetRow).where(TestDatasetRow.id == row_id))
        row = result.scalar_one_or_none()
        if not row:
            raise_biz(ErrorCodes.NOT_FOUND, f"Row {row_id} not found")
        if data is not None:
            row.data = data
        if is_enabled is not None:
            row.is_enabled = is_enabled
        await self.db.flush()

    async def delete_row(self, row_id: int):
        await self.db.execute(delete(TestDatasetRow).where(TestDatasetRow.id == row_id))
        await self.db.flush()
