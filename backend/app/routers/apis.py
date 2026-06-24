from typing import Optional
import logging
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user, get_optional_user
from app.models.api_category import ApiCategory
from app.models.api_definition import ApiDefinition
from app.models.api_test_history import ApiTestHistory
from app.models.project import Project
from app.models.user import User
from app.schemas.api import ApiCreate, ApiMove, ApiTestRequest, ApiUpdate, BatchCopyRequest, BatchIdsRequest, BatchMoveRequest
from app.services.api_service import ApiService
from app.services.case_service import CaseService
from app.services.export_service import ExportService
from app.services.permission_service import check_read_access, check_write_access, check_seed_mark_access
from app.utils.response import success
from app.utils.json_helpers import safe_json_load
from app.core.exceptions import raise_biz, ErrorCodes
router = APIRouter(prefix="/projects/{project_id}/apis", tags=["API Definitions"])


@router.get("", summary="接口列表", description="获取项目下的所有接口定义，支持接口目录筛选")
async def list_apis(project_id: int, category_id: Optional[int] = Query(None),
    method: Optional[str] = Query(None, description="HTTP 方法筛选"),
    status: Optional[str] = Query(None, description="状态筛选"),
    keyword: Optional[str] = Query(None, description="名称/路径模糊搜索"),
    tag: Optional[str] = Query(None, description="标签名称筛选"),
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    current_user: User | None = Depends(get_optional_user),
    _project: Project = Depends(check_read_access),
    db: AsyncSession = Depends(get_db)):
    s = ApiService(db)
    items, total = await s.list(project_id, category_id, page, page_size,
                                method=method, status=status, keyword=keyword, tag=tag)
    return success({"items": items, "total": total, "page": page, "page_size": page_size})


@router.get("/{api_id}", summary="接口详情", description="获取指定接口的完整定义信息")
async def get_api(project_id: int, api_id: int,
    current_user: User | None = Depends(get_optional_user),
    _project: Project = Depends(check_read_access),
    db: AsyncSession = Depends(get_db)):
    s = ApiService(db)
    api_dict = s.to_dict(await s.get(api_id, project_id))
    # 加载标签
    from app.models.api_tag import ApiTag, ApiTagRelation
    tag_rows = await db.execute(
        select(ApiTag.name)
        .join(ApiTagRelation, ApiTag.id == ApiTagRelation.tag_id)
        .where(ApiTagRelation.api_id == api_id)
    )
    api_dict["tags"] = [r[0] for r in tag_rows.all()]
    return success(api_dict)


@router.post("", summary="创建接口", description="在指定接口目录下创建新的接口定义")
async def create_api(project_id: int, req: ApiCreate,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
    db: AsyncSession = Depends(get_db)):
    # 检查同项目同目录下是否存在同名接口
    name_dup = await db.execute(
        select(ApiDefinition).where(
            ApiDefinition.project_id == project_id,
            ApiDefinition.category_id == req.category_id if req.category_id else ApiDefinition.category_id.is_(None),
            ApiDefinition.name == req.name,
            ApiDefinition.deleted_at.is_(None),
        )
    )
    if name_dup.scalar_one_or_none():
        raise_biz(ErrorCodes.API_NAME_DUPLICATE, "该目录下已存在同名接口")

    # 检查同项目同目录下是否存在相同路径+方法的接口
    path_dup = await db.execute(
        select(ApiDefinition).where(
            ApiDefinition.project_id == project_id,
            ApiDefinition.category_id == req.category_id if req.category_id else ApiDefinition.category_id.is_(None),
            ApiDefinition.path == req.path,
            ApiDefinition.method == req.method,
            ApiDefinition.deleted_at.is_(None),
        )
    )
    if path_dup.scalar_one_or_none():
        raise_biz(ErrorCodes.API_PATH_DUPLICATE, "该目录下已存在相同路径和方法的接口")

    # 校验目标目录存在性
    if req.category_id is not None:
        cat_check = await db.execute(
            select(ApiCategory).where(
                ApiCategory.id == req.category_id,
                ApiCategory.project_id == project_id,
            )
        )
        if not cat_check.scalar_one_or_none():
            raise_biz(ErrorCodes.CATEGORY_NOT_FOUND, "目标目录不存在")

    s = ApiService(db)
    result = s.to_dict(await s.create(project_id, req))
    return success(result)


@router.put("/{api_id}", summary="更新接口", description="修改指定接口的请求方法、路径、参数等")
async def update_api(project_id: int, api_id: int, req: ApiUpdate,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
    db: AsyncSession = Depends(get_db)):
    s = ApiService(db)
    result = s.to_dict(await s.update(api_id, req, project_id))
    return success(result)


@router.delete("/{api_id}", summary="删除接口", description="删除指定接口定义及其关联的测试用例")
async def delete_api(project_id: int, api_id: int,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
    db: AsyncSession = Depends(get_db)):
    s = ApiService(db)
    await s.delete(api_id, project_id)
    return success(message="接口已移至回收站")

@router.get("/recycle/list", summary="回收站列表", description="列出已软删除的接口")
async def list_deleted_apis(project_id: int,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_read_access),
    db: AsyncSession = Depends(get_db)):
    s = ApiService(db)
    return success({"items": await s.list_deleted(project_id)})


@router.post("/{api_id}/restore", summary="恢复接口", description="从回收站恢复已删除的接口")
async def restore_api(project_id: int, api_id: int,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
    db: AsyncSession = Depends(get_db)):
    s = ApiService(db)
    result = await s.restore(api_id, project_id)
    return success(result)


@router.delete("/{api_id}/permanent", summary="永久删除接口", description="从数据库中永久移除接口")
async def permanent_delete_api(project_id: int, api_id: int,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
    db: AsyncSession = Depends(get_db)):
    s = ApiService(db)
    await s.permanent_delete(api_id, project_id)
    return success(message="接口已永久删除")

@router.post("/{api_id}/duplicate", summary="复制接口", description="快速复制已有接口的配置生成新接口")
async def duplicate_api(project_id: int, api_id: int,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
    db: AsyncSession = Depends(get_db)):
    s = ApiService(db)
    result = s.to_dict(await s.duplicate(api_id))
    return success(result)


@router.put("/{api_id}/seed-mark", summary="标记/取消标记为种子", description="管理员将接口标记为种子数据，下次重置种子时保留；再次调用可取消标记")
async def mark_api_as_seed(project_id: int, api_id: int,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_seed_mark_access),
    db: AsyncSession = Depends(get_db)):
    if current_user.role != "admin":
        from app.core.exceptions import raise_biz, ErrorCodes
        raise_biz(ErrorCodes.PROJECT_FORBIDDEN, "仅管理员可标记种子数据")
    from sqlalchemy import select
    from app.models.api_definition import ApiDefinition
    from app.models.project import Project
    result = await db.execute(select(ApiDefinition).where(ApiDefinition.id == api_id, ApiDefinition.project_id == project_id).limit(1))
    api = result.scalar_one_or_none()
    if not api:
        from app.core.exceptions import raise_biz, ErrorCodes
        raise_biz(ErrorCodes.NOT_FOUND, "接口不存在")
    # 种子标记仅对全局种子项目（global_demo=1）有效
    project = await db.get(Project, api.project_id)
    if not project or project.global_demo != 1:
        from app.core.exceptions import raise_biz, ErrorCodes
        raise_biz(ErrorCodes.PARAM_ERROR, "种子标记仅对全局种子项目生效")
    api.is_seed = 1 if api.is_seed == 0 else 0
    await db.flush()
    return success({"is_seed": api.is_seed, "message": "已标记为种子" if api.is_seed else "已取消种子标记"})


@router.post("/{api_id}/star", summary="收藏接口", description="将接口标记为收藏，收藏的接口在列表中置顶显示")
async def star_api(project_id: int, api_id: int,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
    db: AsyncSession = Depends(get_db)):
    s = ApiService(db)
    api = await s.get(api_id, project_id)
    api.is_starred = True
    await db.flush()
    return success({"is_starred": True, "message": "已收藏"})


@router.post("/{api_id}/unstar", summary="取消收藏", description="取消接口的收藏标记")
async def unstar_api(project_id: int, api_id: int,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
    db: AsyncSession = Depends(get_db)):
    s = ApiService(db)
    api = await s.get(api_id, project_id)
    api.is_starred = False
    await db.flush()
    return success({"is_starred": False, "message": "已取消收藏"})


@router.put("/{api_id}/move", summary="移动接口", description="将接口移动到其他接口目录")
async def move_api(project_id: int, api_id: int, req: ApiMove,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
    db: AsyncSession = Depends(get_db)):
    # 校验目标目录存在性
    if req.category_id is not None:
        from app.models.api_category import ApiCategory
        cat_result = await db.execute(
            select(ApiCategory).where(
                ApiCategory.id == req.category_id,
                ApiCategory.project_id == project_id,
            )
        )
        if not cat_result.scalar_one_or_none():
            raise_biz(ErrorCodes.CATEGORY_NOT_FOUND, "目标目录不存在")
    s = ApiService(db)
    await s.move(api_id, req.category_id)
    return success(message="API moved")


@router.post("/{api_id}/test", summary="测试接口", description="发送请求测试接口定义的正确性")
async def test_api(project_id: int, api_id: int, req: ApiTestRequest,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_read_access),
    db: AsyncSession = Depends(get_db)):
    s = ApiService(db)
    result = await s.test_api(api_id, req.env_id, req.overrides, req.extract_vars)
    # 保存测试历史（传递user_id）
    try:
        import json
        # 确定测试状态
        status = "unknown"
        if result.get("error"):
            status = "error"
        elif result.get("response_status", 0) >= 400:
            status = "failed"
        elif result.get("response_status", 0) > 0:
            status = "success"

        # 获取接口信息
        api = await s.get(api_id, project_id)
        url = result.get("request_url", "")
        method = result.get("request_method", "GET")
        duration = result.get("duration", 0)

        # 序列化请求/响应数据
        req_headers_json = json.dumps([{"key": k, "value": v} for k, v in result.get("request_headers", {}).items()], ensure_ascii=False)
        resp_headers_json = json.dumps(
            [{"key": k, "value": v} for k, v in result.get("response_headers", {}).items()],
            ensure_ascii=False)

        history = ApiTestHistory(
            project_id=project_id,
            api_id=api_id,
            environment_id=req.env_id,
            executor_id=current_user.id,
            request_url=url,
            request_method=method,
            request_headers=req_headers_json,
            request_body=result.get("request_body", ""),
            response_status=result.get("response_status", 0),
            response_headers=resp_headers_json,
            response_body=result.get("response_body", ""),
            duration=duration,
            error=result.get("error"),
            status=status,
        )
        db.add(history)
        await db.flush()
    except Exception as e:
        logger = logging.getLogger("api_pilot.routers.apis")
        logger.warning("保存测试历史失败（不影响主流程）: %s: %s", type(e).__name__, e)

    return success(result)


@router.get("/{api_id}/cases", summary="接口用例列表", description="获取指定接口下的所有测试用例")
async def list_api_cases(project_id: int, api_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=9999),
    current_user: User | None = Depends(get_optional_user),
    _project: Project = Depends(check_read_access),
    db: AsyncSession = Depends(get_db)):
    s = CaseService(db)
    items, total = await s.list(project_id, api_id=api_id, page=page, page_size=page_size)
    return success({"items": items, "total": total, "page": page, "page_size": page_size})


@router.delete("/batch", summary="批量删除接口", description="同时软删除多个接口定义（移至回收站）")
async def batch_delete_apis(project_id: int, req: BatchIdsRequest,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
    db: AsyncSession = Depends(get_db)):
    id_list = [n for n in req.ids if n >= 1]  # 移除无效 ID（负数/零）
    if not id_list:
        return success({"success_count": 0, "failed_count": 0, "failed_items": []}, message="未提供有效的 ID")

    s = ApiService(db)
    success_ids = []
    failed_items = []

    async with db.begin_nested():
        for api_id_item in id_list:
            try:
                await s.delete(api_id_item, project_id)
                success_ids.append(api_id_item)
            except Exception as e:
                failed_items.append({
                    "id": api_id_item,
                    "reason": str(e) or "删除失败"
                })

    return success({
        "success_count": len(success_ids),
        "failed_count": len(failed_items),
        "failed_items": failed_items,
        "deleted_ids": success_ids,
    }, message=f"成功删除 {len(success_ids)} 个接口" + (f"，{len(failed_items)} 个失败" if failed_items else ""))

@router.post("/batch/move", summary="Batch move APIs")
async def batch_move_apis(project_id: int, req: BatchMoveRequest,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
    db: AsyncSession = Depends(get_db)):
    s = ApiService(db)
    moved = await s.batch_move(req.api_ids, req.target_category_id, project_id)
    return success(message=f"Moved {moved} APIs")


@router.post("/batch/copy", summary="Batch copy APIs")
async def batch_copy_apis(project_id: int, req: BatchCopyRequest,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
    db: AsyncSession = Depends(get_db)):
    s = ApiService(db)
    copied = await s.batch_copy(req.api_ids, req.target_category_id, project_id)
    return success(message=f"Copied {copied} APIs")


@router.get("/{api_id}/export", summary="导出接口", description="导出单个接口为指定格式（apifox/openapi/postman）")
async def export_api(
    project_id: int,
    api_id: int,
    format: str = Query("apifox", description="导出格式", pattern="^(apifox|openapi|postman)$"),
    current_user: User | None = Depends(get_optional_user),
    _project: Project = Depends(check_read_access),
    db: AsyncSession = Depends(get_db),
):
    """导出单个接口为指定格式"""
    s = ExportService(db)
    data = await s.export_single_api(api_id, project_id, format)
    return success(data)


@router.get("/{api_id}/test-history", summary="接口测试历史", description="获取接口的测试历史记录，支持分页筛选")
async def get_api_test_history(
    project_id: int,
    api_id: int,
    status: Optional[str] = Query(None, description="状态筛选：success/failed/error"),
    env_id: Optional[int] = Query(None, description="环境ID筛选"),
    start_date: Optional[str] = Query(None, description="开始日期 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM-DD)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User | None = Depends(get_optional_user),
    _project: Project = Depends(check_read_access),
    db: AsyncSession = Depends(get_db),
):
    """获取接口的测试历史记录"""
    from app.models.api_test_history import ApiTestHistory

    # 验证接口存在
    api_svc = ApiService(db)
    await api_svc.get(api_id, project_id)

    # 构建查询
    query = select(ApiTestHistory).where(
        ApiTestHistory.api_id == api_id,
        ApiTestHistory.project_id == project_id,
    )
    count_query = select(func.count(ApiTestHistory.id)).where(
        ApiTestHistory.api_id == api_id,
        ApiTestHistory.project_id == project_id,
    )

    # 状态筛选
    if status:
        query = query.where(ApiTestHistory.status == status)
        count_query = count_query.where(ApiTestHistory.status == status)

    # 环境筛选
    if env_id:
        query = query.where(ApiTestHistory.environment_id == env_id)
        count_query = count_query.where(ApiTestHistory.environment_id == env_id)

    # 日期范围筛选
    from datetime import datetime
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            query = query.where(ApiTestHistory.created_at >= start_dt)
            count_query = count_query.where(ApiTestHistory.created_at >= start_dt)
        except ValueError:
            raise_biz(ErrorCodes.INVALID_PARAM, "start_date 格式错误，应为 YYYY-MM-DD")
    if end_date:
        try:
            # 结束日期包含当天，所以加一天
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
            query = query.where(ApiTestHistory.created_at <= end_dt)
            count_query = count_query.where(ApiTestHistory.created_at <= end_dt)
        except ValueError:
            raise_biz(ErrorCodes.INVALID_PARAM, "end_date 格式错误，应为 YYYY-MM-DD")

    # 统计总数
    total = await db.scalar(count_query) or 0

    # 分页查询
    result = await db.execute(
        query.order_by(ApiTestHistory.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = result.scalars().all()

    # 序列化
    def to_dict(h: ApiTestHistory) -> dict:
        return {
            "id": h.id,
            "api_id": h.api_id,
            "environment_id": h.environment_id,
            "executor_id": h.executor_id,
            "request_url": h.request_url,
            "request_method": h.request_method,
            "request_headers": safe_json_load(h.request_headers, []),
            "request_body": h.request_body or "",
            "response_status": h.response_status,
            "response_headers": safe_json_load(h.response_headers, {}),
            "response_body": h.response_body or "",
            "duration": h.duration,
            "error": h.error,
            "status": h.status,
            "created_at": h.created_at.isoformat() if h.created_at else None,
        }

    return success({
        "items": [to_dict(item) for item in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    })


@router.delete("/{api_id}/test-history", summary="清空测试历史", description="删除指定接口的全部测试历史记录")
async def clear_api_test_history(
    project_id: int,
    api_id: int,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
    db: AsyncSession = Depends(get_db),
):
    """清空接口的测试历史记录"""
    # 验证接口存在
    api_svc = ApiService(db)
    await api_svc.get(api_id, project_id)

    stmt = delete(ApiTestHistory).where(
        ApiTestHistory.api_id == api_id,
        ApiTestHistory.project_id == project_id,
    )
    result = await db.execute(stmt)
    await db.flush()

    return success({"deleted_count": result.rowcount})


# =============================================================================
#  阶段 3 增强：接口变更快照 / Diff / 版本对比
# =============================================================================
# - POST/PUT 写入 api_snapshots（由 ApiService hook 自动完成）
# - GET /{id}/history  返回快照列表
# - GET /{id}/diff?v1=&v2=  返回两版本 diff
# =============================================================================


def _api_to_snapshot_dict(api: ApiDefinition) -> dict:
    """把 ApiDefinition ORM 实例转可 JSON 序列化的快照数据。"""
    return {
        "id": api.id,
        "project_id": api.project_id,
        "category_id": api.category_id,
        "name": api.name,
        "method": api.method,
        "path": api.path,
        "description": api.description,
        "description_md": api.description_md or "",
        "headers": safe_json_load(api.headers, []),
        "params": safe_json_load(api.params, []),
        "body": safe_json_load(api.body, {"type": "none"}),
        "auth_type": api.auth_type,
        "pre_script": api.pre_script or "",
        "post_script": api.post_script or "",
        "cookies": safe_json_load(api.cookies, []),
        "auth": safe_json_load(api.auth, {"type": "none"}),
        "settings": safe_json_load(api.settings, {}),
        "response_schema": api.response_schema,
        "response_examples": safe_json_load(api.response_examples, []),
        "status": api.status,
        "version": api.version,
    }


async def _write_api_snapshot(
    db: AsyncSession,
    api: ApiDefinition,
    change_type: str,
    user_id: Optional[int] = None,
    change_summary: str = "",
) -> None:
    """写入一条 ApiSnapshot 记录（内部使用，不抛异常以免影响主流程）。"""
    try:
        from app.models.api_snapshot import ApiSnapshot
        import json as _json
        snap = ApiSnapshot(
            api_id=api.id,
            snapshot_data=_json.dumps(_api_to_snapshot_dict(api), ensure_ascii=False, default=str),
            change_type=change_type,
            change_summary=change_summary,
            changed_by=user_id,
        )
        db.add(snap)
        await db.flush()
    except Exception as exc:
        logger = logging.getLogger("api_pilot.routers.apis.snapshot")
        logger.warning("写入 api 快照失败（不影响主流程）: %s: %s", type(exc).__name__, exc)


@router.post("/{api_id}/snapshot", summary="手动写一条快照")
async def write_snapshot(
    project_id: int,
    api_id: int,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
    db: AsyncSession = Depends(get_db),
):
    """手动触发一次快照写入（用于重大节点打 tag）。"""
    api_svc = ApiService(db)
    api = await api_svc.get(api_id, project_id)
    await _write_api_snapshot(
        db, api, change_type="update", user_id=current_user.id,
        change_summary=f"manual snapshot by {current_user.id}",
    )
    return success(message="快照已写入")


@router.get("/{api_id}/history", summary="接口快照历史")
async def get_api_history(
    project_id: int,
    api_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User | None = Depends(get_optional_user),
    _project: Project = Depends(check_read_access),
    db: AsyncSession = Depends(get_db),
):
    """返回接口的快照历史列表（按时间倒序）。"""
    from app.models.api_snapshot import ApiSnapshot
    api_svc = ApiService(db)
    await api_svc.get(api_id, project_id)

    query = select(ApiSnapshot).where(ApiSnapshot.api_id == api_id)
    count_q = select(func.count(ApiSnapshot.id)).where(ApiSnapshot.api_id == api_id)
    total = await db.scalar(count_q) or 0
    result = await db.execute(
        query.order_by(ApiSnapshot.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = [
        {
            "id": s.id,
            "api_id": s.api_id,
            "change_type": s.change_type,
            "change_summary": s.change_summary,
            "changed_by": s.changed_by,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
        for s in result.scalars().all()
    ]
    return success({"items": items, "total": total, "page": page, "page_size": page_size})


@router.get("/{api_id}/diff", summary="两版本 diff")
async def diff_api_versions(
    project_id: int,
    api_id: int,
    v1: int = Query(..., ge=1, description="旧快照 ID"),
    v2: int = Query(..., ge=1, description="新快照 ID"),
    current_user: User | None = Depends(get_optional_user),
    _project: Project = Depends(check_read_access),
    db: AsyncSession = Depends(get_db),
):
    """对比两个快照的 snapshot_data，返回 DiffOp 列表 + breaking 检测。"""
    from app.models.api_snapshot import ApiSnapshot
    api_svc = ApiService(db)
    await api_svc.get(api_id, project_id)

    a_res = await db.execute(select(ApiSnapshot).where(ApiSnapshot.id == v1, ApiSnapshot.api_id == api_id))
    b_res = await db.execute(select(ApiSnapshot).where(ApiSnapshot.id == v2, ApiSnapshot.api_id == api_id))
    a = a_res.scalar_one_or_none()
    b = b_res.scalar_one_or_none()
    if not a or not b:
        raise_biz(ErrorCodes.API_NOT_FOUND, "快照不存在或不属于该接口")
    try:
        a_data = safe_json_load(a.snapshot_data, {})
        b_data = safe_json_load(b.snapshot_data, {})
    except Exception as exc:
        raise_biz(ErrorCodes.PARAM_ERROR, f"snapshot_data 解析失败: {exc}")
    from app.services.diff import default_differ
    ops = default_differ.diff(a_data, b_data)
    return success({
        "api_id": api_id,
        "from_snapshot_id": a.id,
        "to_snapshot_id": b.id,
        "ops": default_differ.to_jsonable(ops),
        "summary": default_differ.summarize(ops),
        "breaking": default_differ.is_breaking_change(ops),
    })

