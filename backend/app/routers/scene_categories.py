from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user, get_optional_user
from app.models.user import User
from app.models.project import Project
from app.models.scene_category import SceneCategory
from app.models.test_scene import TestScene
from app.schemas.scene_category import CategoryCreate, CategoryUpdate
from app.services.permission_service import check_read_access, check_write_access
from app.utils.response import success
from app.core.exceptions import raise_biz, ErrorCodes

router = APIRouter(prefix="/projects/{project_id}/scene-categories", tags=["Scene Categories"])


def to_dict(cat: SceneCategory) -> dict:
    return {"id": cat.id, "project_id": cat.project_id, "name": cat.name,
            "parent_id": cat.parent_id, "sort_order": cat.sort_order}


async def get_category_or_404(db: AsyncSession, cat_id: int) -> SceneCategory:
    result = await db.execute(select(SceneCategory).where(SceneCategory.id == cat_id))
    cat = result.scalar_one_or_none()
    if not cat:
        raise_biz(ErrorCodes.SCENE_CATEGORY_NOT_FOUND)
    return cat


@router.get("", summary="场景接口目录列表", description="获取项目下的场景接口目录树")
async def list_categories(project_id: int,
    current_user: User | None = Depends(get_optional_user),
    _project: Project = Depends(check_read_access),
    db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(SceneCategory).where(SceneCategory.project_id == project_id)
        .order_by(SceneCategory.sort_order))
    categories = result.scalars().all()

    scenes_result = await db.execute(
        select(TestScene).where(TestScene.project_id == project_id, TestScene.deleted_at.is_(None))
        .order_by(TestScene.updated_at.desc()))
    scenes = scenes_result.scalars().all()

    scenes_by_cat: dict[int | None, list[dict]] = {}
    for s in scenes:
        scenes_by_cat.setdefault(s.category_id, []).append({
            "id": s.id, "name": s.name, "category_id": s.category_id,
            "step_count": 0, "created_at": str(s.created_at),
            "updated_at": str(s.updated_at)})

    result_list = []
    for c in categories:
        d = to_dict(c)
        d["scenes"] = scenes_by_cat.pop(c.id, [])
        result_list.append(d)

    uncategorized = scenes_by_cat.get(None, [])
    if uncategorized:
        result_list.insert(0, {
            "id": 0, "name": "未接口目录", "parent_id": None,
            "sort_order": -1, "scenes": uncategorized})

    return success(result_list)


@router.post("", summary="创建场景接口目录", description="新建场景目录接口目录")
async def create_category(project_id: int, req: CategoryCreate,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
    db: AsyncSession = Depends(get_db)):
    max_order = await db.scalar(
        select(func.coalesce(func.max(SceneCategory.sort_order), -1))
        .where(SceneCategory.project_id == project_id))
    cat = SceneCategory(
        project_id=project_id, name=req.name,
        parent_id=req.parent_id, sort_order=(max_order or 0) + 1)
    db.add(cat)
    await db.flush()
    await db.refresh(cat)
    return success(to_dict(cat))


@router.put("/{category_id}", summary="更新场景接口目录", description="修改场景接口目录名称")
async def update_category(project_id: int, category_id: int, req: CategoryUpdate,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
    db: AsyncSession = Depends(get_db)):
    cat = await get_category_or_404(db, category_id)
    if req.name is not None:
        cat.name = req.name
    await db.flush()
    return success(to_dict(cat))


@router.delete("/{category_id}", summary="删除场景接口目录", description="删除场景接口目录及其中的场景")
async def delete_category(project_id: int, category_id: int,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
    db: AsyncSession = Depends(get_db)):
    cat = await get_category_or_404(db, category_id)
    from sqlalchemy import update as sa_update
    await db.execute(
        sa_update(TestScene.__table__).where(TestScene.category_id == category_id)
        .values(category_id=None))
    await db.execute(
        sa_update(SceneCategory.__table__).where(SceneCategory.parent_id == category_id)
        .values(parent_id=None))
    await db.delete(cat)
    await db.flush()
    return success(message="目录已删除")
