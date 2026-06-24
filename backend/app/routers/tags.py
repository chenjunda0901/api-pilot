from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user, get_optional_user
from app.models.api_tag import ApiTag, ApiTagRelation
from app.models.project import Project
from app.models.user import User
from app.services.permission_service import check_read_access, check_write_access
from app.utils.response import success
from app.core.exceptions import raise_biz, ErrorCodes
from pydantic import BaseModel, Field

router = APIRouter(prefix="/projects/{project_id}/tags", tags=["API Tags"])


class TagCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    color: str = Field(default="#7a8fd0", max_length=20)


class TagUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    color: Optional[str] = Field(None, max_length=20)


class TagApisRequest(BaseModel):
    api_ids: list[int] = Field(..., min_length=1)


@router.get("", summary="获取项目标签列表")
async def list_tags(
    project_id: int,
    current_user: User | None = Depends(get_optional_user),
    _project: Project = Depends(check_read_access),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ApiTag).where(ApiTag.project_id == project_id).order_by(ApiTag.id)
    )
    tags = result.scalars().all()
    items = []
    for t in tags:
        # 统计每个标签关联的接口数量
        count_result = await db.execute(
            select(func.count(ApiTagRelation.id)).where(ApiTagRelation.tag_id == t.id)
        )
        api_count = count_result.scalar() or 0
        items.append({
            "id": t.id,
            "project_id": t.project_id,
            "name": t.name,
            "color": t.color,
            "api_count": api_count,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        })
    return success(items)


@router.post("", summary="创建标签")
async def create_tag(
    project_id: int,
    req: TagCreate,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
    db: AsyncSession = Depends(get_db),
):
    # 检查同名标签
    existing = await db.execute(
        select(ApiTag).where(
            ApiTag.project_id == project_id,
            ApiTag.name == req.name,
        )
    )
    if existing.scalar_one_or_none():
        raise_biz(ErrorCodes.PARAM_ERROR, "该标签名称已存在")
    tag = ApiTag(project_id=project_id, name=req.name, color=req.color)
    db.add(tag)
    await db.flush()
    return success({
        "id": tag.id,
        "project_id": tag.project_id,
        "name": tag.name,
        "color": tag.color,
    })


@router.put("/{tag_id}", summary="更新标签")
async def update_tag(
    project_id: int,
    tag_id: int,
    req: TagUpdate,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ApiTag).where(ApiTag.id == tag_id, ApiTag.project_id == project_id)
    )
    tag = result.scalar_one_or_none()
    if not tag:
        raise_biz(ErrorCodes.NOT_FOUND, "标签不存在")
    if req.name is not None:
        # 检查同名
        dup = await db.execute(
            select(ApiTag).where(
                ApiTag.project_id == project_id,
                ApiTag.name == req.name,
                ApiTag.id != tag_id,
            )
        )
        if dup.scalar_one_or_none():
            raise_biz(ErrorCodes.PARAM_ERROR, "该标签名称已存在")
        tag.name = req.name
    if req.color is not None:
        tag.color = req.color
    await db.flush()
    return success({"id": tag.id, "name": tag.name, "color": tag.color})


@router.delete("/{tag_id}", summary="删除标签")
async def delete_tag(
    project_id: int,
    tag_id: int,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ApiTag).where(ApiTag.id == tag_id, ApiTag.project_id == project_id)
    )
    tag = result.scalar_one_or_none()
    if not tag:
        raise_biz(ErrorCodes.NOT_FOUND, "标签不存在")
    # 级联删除关联关系
    await db.execute(delete(ApiTagRelation).where(ApiTagRelation.tag_id == tag_id))
    await db.delete(tag)
    await db.flush()
    return success(message="标签已删除")


@router.post("/{tag_id}/apis", summary="为接口添加标签")
async def add_apis_to_tag(
    project_id: int,
    tag_id: int,
    req: TagApisRequest,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
    db: AsyncSession = Depends(get_db),
):
    # 校验标签存在
    tag_result = await db.execute(
        select(ApiTag).where(ApiTag.id == tag_id, ApiTag.project_id == project_id)
    )
    if not tag_result.scalar_one_or_none():
        raise_biz(ErrorCodes.NOT_FOUND, "标签不存在")
    added = 0
    for api_id in req.api_ids:
        # 检查是否已存在
        existing = await db.execute(
            select(ApiTagRelation).where(
                ApiTagRelation.api_id == api_id,
                ApiTagRelation.tag_id == tag_id,
            )
        )
        if not existing.scalar_one_or_none():
            db.add(ApiTagRelation(api_id=api_id, tag_id=tag_id))
            added += 1
    await db.flush()
    return success({"added": added})


@router.delete("/{tag_id}/apis", summary="移除接口标签")
async def remove_apis_from_tag(
    project_id: int,
    tag_id: int,
    req: TagApisRequest,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        delete(ApiTagRelation).where(
            ApiTagRelation.tag_id == tag_id,
            ApiTagRelation.api_id.in_(req.api_ids),
        )
    )
    await db.flush()
    return success({"removed": result.rowcount})
