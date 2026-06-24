from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user, get_optional_user
from app.models.user import User
from app.models.project import Project
from app.models.data_schema import DataSchema
from app.schemas.data_schema import (
    DataSchemaCreate,
    DataSchemaUpdate,
    DataSchemaOut,
)
from app.utils.response import success
from app.core.exceptions import raise_biz, ErrorCodes
from app.services.permission_service import check_read_access, check_write_access

router = APIRouter(prefix="/projects/{project_id}/data-schemas", tags=["Data Schemas"])


@router.get("", summary="数据模型列表", description="获取项目下的数据模型列表")
async def list_data_schemas(
    project_id: int,
    current_user: User | None = Depends(get_optional_user),
    _project: Project = Depends(check_read_access),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(DataSchema)
        .where(DataSchema.project_id == project_id)
        .order_by(DataSchema.updated_at.desc())
    )
    items = [
        DataSchemaOut.model_validate(s, from_attributes=True).model_dump()
        for s in result.scalars().all()
    ]
    return success({"items": items, "total": len(items)})


@router.post("", summary="创建数据模型", description="新建数据模型 / JSON Schema")
async def create_data_schema(
    project_id: int,
    req: DataSchemaCreate,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
    db: AsyncSession = Depends(get_db),
):
    schema = DataSchema(
        project_id=project_id,
        name=req.name,
        description=req.description,
        schema_json=req.schema_json,
        created_by=current_user.id,
    )
    db.add(schema)
    await db.flush()
    await db.refresh(schema)
    return success(DataSchemaOut.model_validate(schema, from_attributes=True).model_dump())


@router.put("/{schema_id}", summary="更新数据模型", description="修改数据模型名称、描述或 schema 内容")
async def update_data_schema(
    project_id: int,
    schema_id: int,
    req: DataSchemaUpdate,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(DataSchema).where(
            DataSchema.id == schema_id, DataSchema.project_id == project_id
        )
    )
    schema = result.scalar_one_or_none()
    if not schema:
        raise_biz(ErrorCodes.PARAM_ERROR, "数据模型不存在")
    if req.name is not None:
        schema.name = req.name
    if req.description is not None:
        schema.description = req.description
    if req.schema_json is not None:
        schema.schema_json = req.schema_json
    await db.flush()
    await db.refresh(schema)
    return success(DataSchemaOut.model_validate(schema, from_attributes=True).model_dump())


@router.delete("/{schema_id}", summary="删除数据模型", description="删除指定的数据模型")
async def delete_data_schema(
    project_id: int,
    schema_id: int,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(DataSchema).where(
            DataSchema.id == schema_id, DataSchema.project_id == project_id
        )
    )
    schema = result.scalar_one_or_none()
    if not schema:
        raise_biz(ErrorCodes.PARAM_ERROR, "数据模型不存在")
    await db.delete(schema)
    await db.flush()
    return success(message="数据模型已删除")
