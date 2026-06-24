import json

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.models.project import Project
from app.schemas.test_dataset import DatasetCreate, DatasetUpdate, BatchRowsRequest
from app.services.dataset_service import DatasetService
from app.services.permission_service import check_read_access, check_write_access
from app.utils.response import success

router = APIRouter(prefix="/projects/{project_id}/datasets", tags=["Datasets"])


@router.get("")
async def list_datasets(project_id: int,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_read_access),
    db: AsyncSession = Depends(get_db)):
    return success(await DatasetService(db).list(project_id))


@router.get("/{dataset_id}")
async def get_dataset(project_id: int, dataset_id: int,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_read_access),
    db: AsyncSession = Depends(get_db)):
    s = DatasetService(db)
    ds = await s.get(dataset_id)
    rows = await s.get_rows(dataset_id)
    return success({
        "id": ds.id, "name": ds.name, "description": ds.description,
        "project_id": ds.project_id, "is_builtin": ds.is_builtin,
        "created_at": str(ds.created_at), "updated_at": str(ds.updated_at),
        "rows": [{"id": r.id, "row_index": r.row_index, "data": r.data, "is_enabled": r.is_enabled} for r in rows]
    })


@router.post("")
async def create_dataset(project_id: int, req: DatasetCreate,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
    db: AsyncSession = Depends(get_db)):
    ds = await DatasetService(db).create(project_id, req.name, req.description)
    return success({"id": ds.id, "name": ds.name})


@router.put("/{dataset_id}")
async def update_dataset(project_id: int, dataset_id: int, req: DatasetUpdate,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
    db: AsyncSession = Depends(get_db)):
    ds = await DatasetService(db).update(dataset_id, req.name, req.description)
    return success({"id": ds.id, "name": ds.name})


@router.delete("/{dataset_id}")
async def delete_dataset(project_id: int, dataset_id: int,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
    db: AsyncSession = Depends(get_db)):
    await DatasetService(db).delete(dataset_id)
    return success(message="Dataset deleted")


@router.post("/{dataset_id}/rows")
async def add_rows(project_id: int, dataset_id: int, req: BatchRowsRequest,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
    db: AsyncSession = Depends(get_db)):
    count = await DatasetService(db).batch_add_rows(dataset_id, req.rows)
    return success(message=f"Added {count} rows")


@router.put("/{dataset_id}/rows/batch")
async def batch_update_rows(project_id: int, dataset_id: int, req: BatchRowsRequest,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
    db: AsyncSession = Depends(get_db)):
    s = DatasetService(db)
    updated = 0
    for rd in req.rows:
        row_id = rd.get("id")
        if row_id:
            await s.update_row(row_id, data=rd.get("data"), is_enabled=rd.get("is_enabled"))
            updated += 1
    return success(message=f"Updated {updated} rows")


@router.delete("/{dataset_id}/rows/{row_id}")
async def delete_row(project_id: int, dataset_id: int, row_id: int,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
    db: AsyncSession = Depends(get_db)):
    await DatasetService(db).delete_row(row_id)
    return success(message="Row deleted")


@router.get("/{dataset_id}/export", summary="导出数据集", description="导出数据集为JSON或CSV格式")
async def export_dataset(
    project_id: int,
    dataset_id: int,
    format: str = Query("json", description="导出格式：json 或 csv", regex="^(json|csv)$"),
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_read_access),
    db: AsyncSession = Depends(get_db),
):
    """导出数据集为指定格式

    - json: 完整JSON格式，包含所有字段
    - csv: 表格格式，适合Excel打开
    """
    from fastapi.responses import Response
    import csv
    import io

    s = DatasetService(db)
    dataset = await s.get(dataset_id)
    rows = await s.get_rows(dataset_id)

    if format == "json":
        # JSON格式：包含完整信息
        data = {
            "id": dataset.id,
            "name": dataset.name,
            "description": dataset.description,
            "project_id": dataset.project_id,
            "is_builtin": dataset.is_builtin,
            "created_at": str(dataset.created_at),
            "updated_at": str(dataset.updated_at),
            "total_rows": len(rows),
            "rows": [
                {
                    "id": r.id,
                    "row_index": r.row_index,
                    "data": r.data,
                    "is_enabled": r.is_enabled,
                }
                for r in rows
            ],
        }
        json_str = json.dumps(data, ensure_ascii=False, indent=2)
        return Response(
            content=json_str,
            media_type="application/json",
            headers={
                "Content-Disposition": f"attachment; filename={dataset.name}.json",
            },
        )
    else:
        # CSV格式：扁平化表格
        # 先解析所有data字段，提取键作为表头
        all_data = []
        for row in rows:
            try:
                data_obj = json.loads(row.data) if isinstance(row.data, str) else row.data
                if isinstance(data_obj, dict):
                    all_data.append(data_obj)
            except (json.JSONDecodeError, TypeError):
                all_data.append({"_raw": row.data})

        if not all_data:
            # 空数据集，返回空CSV
            csv_content = "No data"
        else:
            # 收集所有可能的键
            all_keys = set()
            for d in all_data:
                all_keys.update(d.keys())

            # 排序键，确保列顺序一致
            sorted_keys = sorted(all_keys)

            # 生成CSV
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=sorted_keys, extrasaction='ignore')
            writer.writeheader()
            for d in all_data:
                writer.writerow(d)
            csv_content = output.getvalue()

        return Response(
            content=csv_content.encode('utf-8-sig'),  # BOM for Excel compatibility
            media_type="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": f"attachment; filename={dataset.name}.csv",
            },
        )
