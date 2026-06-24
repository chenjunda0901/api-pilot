from fastapi import APIRouter, Depends
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

from app.database import get_db
from app.middleware.auth import get_current_user, get_optional_user
from app.models.user import User
from app.models.project import Project
from app.models.api_category import ApiCategory
from app.models.api_definition import ApiDefinition
from app.schemas.category import CategoryCreate, CategoryUpdate
from app.utils.response import success
from app.core.exceptions import raise_biz, ErrorCodes
from app.services.permission_service import check_read_access, check_write_access

router = APIRouter(prefix="/projects/{project_id}/categories", tags=["API Categories"])


def _find_first_api(result_set: list[dict]) -> dict | None:
    for cat in result_set:
        if cat.get("first_api"):
            return cat["first_api"]
        if cat.get("children"):
            found = _find_first_api(cat["children"])
            if found:
                return found
    return None


async def _build_tree(db: AsyncSession, project_id: int) -> list:
    cat_result = await db.execute(
        select(ApiCategory)
        .where(ApiCategory.project_id == project_id, ApiCategory.deleted_at.is_(None))
        .order_by(ApiCategory.sort_order)
    )
    all_cats = cat_result.scalars().all()

    api_result = await db.execute(
        select(ApiDefinition)
        .where(ApiDefinition.project_id == project_id, ApiDefinition.deleted_at.is_(None))
        .order_by(ApiDefinition.category_id, ApiDefinition.id)
    )
    all_apis = api_result.scalars().all()

    # 批量查询 case_count
    from app.models.test_case import TestCase
    from sqlalchemy import func
    api_ids = [a.id for a in all_apis]
    case_count_map: dict[int, int] = {}
    if api_ids:
        case_counts = await db.execute(
            select(TestCase.api_id, func.count(TestCase.id))
            .where(TestCase.api_id.in_(api_ids))
            .group_by(TestCase.api_id)
        )
        case_count_map = dict(case_counts.all())

    apis_by_cat: dict[int, list] = {}
    for api in all_apis:
        if api.category_id is not None:
            apis_by_cat.setdefault(api.category_id, []).append(api)

    def build_node(cat: ApiCategory) -> dict:
        cat_apis = apis_by_cat.get(cat.id, [])
        first_api_obj = cat_apis[0] if cat_apis else None
        children = [
            build_node(child)
            for child in all_cats
            if child.parent_id == cat.id
        ]
        return {
            "id": cat.id, "name": cat.name, "parent_id": cat.parent_id,
            "sort_order": cat.sort_order, "api_count": len(cat_apis),
            "children": children,
            "first_api": {
                "id": first_api_obj.id, "name": first_api_obj.name,
                "method": first_api_obj.method, "category_id": cat.id,
                "case_count": case_count_map.get(first_api_obj.id, 0),
            } if first_api_obj else None,
        }

    return [build_node(c) for c in all_cats if not c.parent_id]


async def _collect_descendant_ids(db: AsyncSession, parent_id: int) -> list[int]:
    """递归收集指定父目录下的所有子孙目录 ID（仅未删除的）"""
    child_result = await db.execute(
        select(ApiCategory.id).where(
            ApiCategory.parent_id == parent_id,
            ApiCategory.deleted_at.is_(None),
        )
    )
    ids = list(child_result.scalars().all())
    descendant_ids = list(ids)
    for cid in ids:
        descendant_ids.extend(await _collect_descendant_ids(db, cid))
    return descendant_ids


@router.get("", summary="接口目录树", description="获取项目接口目录的树形结构")
async def get_category_tree(project_id: int,
    current_user: User | None = Depends(get_optional_user),
    _project: Project = Depends(check_read_access),
    db: AsyncSession = Depends(get_db)):
    tree = await _build_tree(db, project_id)
    first_api = _find_first_api(tree)
    return success({"tree": tree, "first_api": first_api})


@router.post("", summary="创建接口目录", description="在指定父接口目录下创建新的接口目录")
async def create_category(project_id: int, req: CategoryCreate,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
    db: AsyncSession = Depends(get_db)):
    # 检查同父目录下是否存在同名目录
    dup = await db.execute(
        select(ApiCategory).where(
            ApiCategory.project_id == project_id,
            ApiCategory.name == req.name,
            ApiCategory.parent_id == (req.parent_id if req.parent_id else None),
            ApiCategory.deleted_at.is_(None),
        )
    )
    if dup.scalar_one_or_none():
        raise_biz(ErrorCodes.PROJECT_NAME_EXISTS, "同目录下已存在同名分类")

    # 验证父目录属于当前项目
    if req.parent_id:
        parent_check = await db.execute(
            select(ApiCategory).where(
                ApiCategory.id == req.parent_id,
                ApiCategory.project_id == project_id,
                ApiCategory.deleted_at.is_(None),
            )
        )
        if not parent_check.scalar_one_or_none():
            raise_biz(ErrorCodes.CATEGORY_NOT_FOUND, "父目录不存在或不属于当前项目")

    cat = ApiCategory(project_id=project_id, name=req.name,
                      parent_id=req.parent_id if req.parent_id else None, sort_order=req.sort_order)
    db.add(cat)
    await db.flush()
    await db.refresh(cat)
    return success({"id": cat.id, "name": cat.name})


@router.put("/{cat_id}/seed-mark", summary="标记/取消标记为种子", description="管理员将接口目录标记为种子数据，下次重置种子时保留；再次调用可取消标记")
async def mark_category_as_seed(project_id: int, cat_id: int,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_read_access),  # 使用 read 守卫（write 会拦截 admin 写种子项目）
    db: AsyncSession = Depends(get_db)):
    if current_user.role != "admin":
        raise_biz(ErrorCodes.PROJECT_FORBIDDEN, "仅管理员可标记种子数据")
    from app.models.project import Project
    result = await db.execute(select(ApiCategory).where(ApiCategory.id == cat_id, ApiCategory.project_id == project_id, ApiCategory.deleted_at.is_(None)))
    cat = result.scalar_one_or_none()
    if not cat:
        raise_biz(ErrorCodes.CATEGORY_NOT_FOUND)
    # 种子标记仅对全局种子项目（global_demo=1）有效
    project = await db.get(Project, cat.project_id)
    if not project or project.global_demo != 1:
        raise_biz(ErrorCodes.PARAM_ERROR, "种子标记仅对全局种子项目生效")
    cat.is_seed = 1 if cat.is_seed == 0 else 0
    await db.flush()
    return success({"is_seed": cat.is_seed, "message": "已标记为种子" if cat.is_seed else "已取消种子标记"})


@router.put("/{cat_id}", summary="更新接口目录", description="修改接口目录名称或排序")
async def update_category(project_id: int, cat_id: int, req: CategoryUpdate,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
    db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ApiCategory).where(ApiCategory.id == cat_id, ApiCategory.project_id == project_id, ApiCategory.deleted_at.is_(None)))
    cat = result.scalar_one_or_none()
    if not cat:
        raise_biz(ErrorCodes.CATEGORY_NOT_FOUND)
    if req.name and req.name != cat.name:
        dup = await db.execute(
            select(ApiCategory).where(
                ApiCategory.project_id == project_id,
                ApiCategory.name == req.name,
                ApiCategory.parent_id == cat.parent_id,
                ApiCategory.id != cat_id,
                ApiCategory.deleted_at.is_(None),
            )
        )
        if dup.scalar_one_or_none():
            raise_biz(ErrorCodes.PROJECT_NAME_EXISTS, "同目录下已存在同名分类")
        cat.name = req.name
    if req.parent_id is not None:
        if req.parent_id == cat_id:
            raise_biz(ErrorCodes.PARAM_ERROR, "不能将目录设为自身的子目录")
        # 递归收集当前目录的所有子孙 ID，防止循环引用
        child_ids = await _collect_descendant_ids(db, cat_id)
        if req.parent_id in child_ids:
            raise_biz(ErrorCodes.PARAM_ERROR, "不能将目录移动到其子目录下")
        cat.parent_id = req.parent_id if req.parent_id else None
    cat.sort_order = req.sort_order
    await db.flush()
    return success({"id": cat.id, "name": cat.name})


@router.delete("/{cat_id}", summary="删除接口目录", description="删除接口目录及其下的所有接口")
async def delete_category(project_id: int, cat_id: int,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
    db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ApiCategory).where(ApiCategory.id == cat_id, ApiCategory.project_id == project_id, ApiCategory.deleted_at.is_(None)))
    cat = result.scalar_one_or_none()
    if not cat:
        raise_biz(ErrorCodes.CATEGORY_NOT_FOUND)

    # 递归收集所有子孙目录 ID（含自身）
    all_cat_ids = [cat_id] + await _collect_descendant_ids(db, cat_id)

    # 软删除所有子孙目录下的接口（与接口软删除保持一致，恢复时 category_id 不会悬空）
    await db.execute(
        update(ApiDefinition)
        .where(
            ApiDefinition.category_id.in_(all_cat_ids),
            ApiDefinition.project_id == project_id,
            ApiDefinition.deleted_at.is_(None),
        )
        .values(deleted_at=datetime.now(timezone.utc))
    )

    # 软删除当前目录及其所有子孙目录（递归处理，与接口软删除一致）
    await db.execute(
        update(ApiCategory)
        .where(
            ApiCategory.id.in_(all_cat_ids),
            ApiCategory.project_id == project_id,
        )
        .values(deleted_at=datetime.now(timezone.utc))
    )
    await db.flush()
    return success(message="目录及下属接口已删除")
