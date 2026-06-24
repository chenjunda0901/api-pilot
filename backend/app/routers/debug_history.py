from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.models.project import Project
from app.schemas.debug_history import DebugHistoryOut
from app.services.debug_history_service import DebugHistoryService
from app.services.permission_service import check_read_access, check_write_access
from app.utils.response import success

router = APIRouter(prefix="/projects/{project_id}/debug-history", tags=["Debug History"])


@router.get("", summary="请求历史列表", description="获取指定接口的调试请求历史")
async def list_history(
    project_id: int,
    api_id: int = Query(..., description="接口ID"),
    limit: int = Query(30, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_read_access),
    db: AsyncSession = Depends(get_db),
):
    s = DebugHistoryService(db)
    items = await s.list_by_api(project_id, api_id, limit)
    return success({"items": [DebugHistoryOut.model_validate(i).model_dump(mode='json') for i in items]})


@router.delete("", summary="清空请求历史", description="清空指定接口的所有调试历史")
async def clear_history(
    project_id: int,
    api_id: int = Query(..., description="接口ID"),
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
    db: AsyncSession = Depends(get_db),
):
    s = DebugHistoryService(db)
    await s.clear_by_api(project_id, api_id)
    return success(message="请求历史已清空")


@router.get("/{history_id}", summary="请求历史详情", description="获取单条调试历史详情")
async def get_history(
    project_id: int,
    history_id: int,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_read_access),
    db: AsyncSession = Depends(get_db),
):
    from app.core.exceptions import raise_biz, ErrorCodes
    s = DebugHistoryService(db)
    item = await s.get(history_id)
    if not item:
        raise_biz(ErrorCodes.NOT_FOUND)
    return success(DebugHistoryOut.model_validate(item).model_dump(mode='json'))
