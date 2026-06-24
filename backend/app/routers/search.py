from fastapi import APIRouter, Depends, Query
from typing import Optional
from sqlalchemy import select, or_, delete
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.database import get_db
from app.middleware.auth import get_optional_user, get_current_user
from app.models.user import User
from app.models.project import Project
from app.models.api_definition import ApiDefinition
from app.models.test_case import TestCase
from app.models.test_scene import TestScene
from app.models.test_report import TestReport
from app.models.mock_rule import MockRule
from app.models.environment import Environment
from app.models.search_history import SearchHistory
from app.services.permission_service import check_read_access
from app.limiter import limiter
from fastapi import Request
from app.utils.response import success

router = APIRouter(prefix="/projects/{project_id}/search", tags=["Global Search"])

# 每组最多返回的条目数
PER_GROUP_LIMIT = 5


@router.get("", summary="全局搜索", description="在项目中搜索接口、场景、用例、报告、Mock规则等资源，支持类型过滤，结果按类型分组")
@limiter.limit("30/minute")
async def global_search(
    project_id: int,
    keyword: str = Query(..., min_length=1),
    type: Optional[str] = Query(None, description="过滤类型: api/case/scene/report/mock_rule/environment"),
    include_deleted: bool = Query(False, description="是否包含已删除的资源"),
    request: Request = None,
    current_user: User | None = Depends(get_optional_user),
    _project: Project = Depends(check_read_access),
    db: AsyncSession = Depends(get_db)):

    escaped = keyword.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
    kw = f"%{escaped}%"

    results: dict = {"apis": [], "scenes": [], "cases": [], "reports": [], "mock_rules": [], "environments": []}

    # 搜索接口（名称 + 路径 + 描述）
    if not type or type == "api":
        api_query = select(ApiDefinition).where(
            ApiDefinition.project_id == project_id,
            or_(
                ApiDefinition.name.ilike(kw),
                ApiDefinition.path.ilike(kw),
                ApiDefinition.description.ilike(kw),
            )
        )
        if not include_deleted:
            api_query = api_query.where(ApiDefinition.deleted_at.is_(None))
        apis_result = await db.execute(api_query.limit(PER_GROUP_LIMIT))
        results["apis"] = [
            {"type": "api", "id": a.id, "title": a.name,
             "subtitle": f"{a.method} {a.path}",
             "match": _get_match_reason(keyword, a.name, f"{a.method} {a.path}", a.description)}
            for a in apis_result.scalars().all()
        ]

    # 搜索场景（名称 + 描述）
    if not type or type == "scene":
        scene_query = select(TestScene).where(
            TestScene.project_id == project_id,
            or_(
                TestScene.name.ilike(kw),
                TestScene.description.ilike(kw),
            )
        )
        if not include_deleted:
            scene_query = scene_query.where(TestScene.deleted_at.is_(None))
        scenes_result = await db.execute(scene_query.limit(PER_GROUP_LIMIT))
        results["scenes"] = [
            {"type": "scene", "id": s.id, "title": s.name,
             "subtitle": s.description or '',
             "match": _get_match_reason(keyword, s.name, s.description)}
            for s in scenes_result.scalars().all()
        ]

    # 搜索用例（名称 + 描述 + 标签）
    if not type or type == "case":
        case_query = select(TestCase).where(
            TestCase.project_id == project_id,
            or_(
                TestCase.name.ilike(kw),
                TestCase.description.ilike(kw),
                TestCase.tags.ilike(kw),
            )
        )
        if not include_deleted:
            case_query = case_query.where(TestCase.deleted_at.is_(None))
        cases_result = await db.execute(case_query.limit(PER_GROUP_LIMIT))
        results["cases"] = [
            {"type": "case", "id": c.id, "title": c.name,
             "subtitle": f"P{_extract_priority(c.priority)} | {c.case_type or 'other'}",
             "match": _get_match_reason(keyword, c.name, c.description, c.tags)}
            for c in cases_result.scalars().all()
        ]

    # 搜索报告（名称 + 标签）
    if not type or type == "report":
        report_query = select(TestReport).where(
            TestReport.project_id == project_id,
            or_(
                TestReport.name.ilike(kw),
                TestReport.tags.ilike(kw),
            )
        )
        reports_result = await db.execute(report_query.limit(PER_GROUP_LIMIT))
        results["reports"] = [
            {"type": "report", "id": r.id, "title": r.name or f"报告 #{r.id}",
             "subtitle": f"{r.status} | {r.pass_count}✓ {r.fail_count}✗ {r.skip_count}⊘",
             "match": _get_match_reason(keyword, r.name, r.tags)}
            for r in reports_result.scalars().all()
        ]

    # 搜索 Mock 规则（名称 + 路径）
    if not type or type == "mock_rule":
        mock_query = select(MockRule).where(
            MockRule.project_id == project_id,
            or_(
                MockRule.name.ilike(kw),
                MockRule.match_path.ilike(kw),
            )
        )
        mock_result = await db.execute(mock_query.limit(PER_GROUP_LIMIT))
        results["mock_rules"] = [
            {"type": "mock_rule", "id": m.id, "title": m.name,
             "subtitle": f"{m.match_method} {m.match_path}",
             "match": _get_match_reason(keyword, m.name, m.match_path)}
            for m in mock_result.scalars().all()
        ]

    # 搜索环境（名称 + 变量值/变量名）
    if not type or type == "environment":
        envs_result = await db.execute(
            select(Environment).where(
                Environment.project_id == project_id,
                or_(
                    Environment.name.ilike(kw),
                    Environment.variables.ilike(kw),
                )
            ).limit(PER_GROUP_LIMIT))
        results["environments"] = [
            {"type": "environment", "id": e.id, "title": e.name,
             "subtitle": f"{(e.variables or '').count(':') + 1} 个变量",
             "match": _get_match_reason(keyword, e.name)}
            for e in envs_result.scalars().all()
        ]

    # 添加结果统计
    total = sum(len(v) for v in results.values())
    return success({"results": results, "total": total, "keyword": keyword})


def _get_match_reason(keyword: str, *fields: str) -> str:
    """返回匹配原因，帮助用户理解为什么搜到这个结果"""
    kw_lower = keyword.lower()
    for field in fields:
        if field and kw_lower in field.lower():
            return field
    return ""


def _extract_priority(p: str) -> str:
    """从优先级字段提取数字"""
    if not p:
        return "2"
    # P0, P1, P2, P3 → 0, 1, 2, 3
    return p.replace("P", "") if "P" in p else p


# ── 搜索历史 ──────────────────────────────────────────────

class SaveHistoryBody(BaseModel):
    query: str


@router.post("/history", summary="保存搜索历史")
async def save_search_history(
    project_id: int,
    body: SaveHistoryBody,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = body.query.strip()
    if not q:
        return success([])
    # 同一用户同一 query 去重：存在则更新 created_at
    existing = await db.execute(
        select(SearchHistory).where(
            SearchHistory.user_id == current_user.id,
            SearchHistory.query == q,
        )
    )
    record = existing.scalar_one_or_none()
    if record:
        from datetime import datetime, timezone
        record.created_at = datetime.now(timezone.utc)
    else:
        db.add(SearchHistory(user_id=current_user.id, query=q))
    await db.flush()
    return success(None)


@router.get("/history", summary="获取最近搜索历史")
async def get_search_history(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SearchHistory)
        .where(SearchHistory.user_id == current_user.id)
        .order_by(SearchHistory.created_at.desc())
        .limit(10)
    )
    items = [
        {"id": h.id, "query": h.query, "created_at": h.created_at.isoformat() if h.created_at else None}
        for h in result.scalars().all()
    ]
    return success(items)


@router.delete("/history", summary="清除搜索历史")
async def clear_search_history(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await db.execute(
        delete(SearchHistory).where(SearchHistory.user_id == current_user.id)
    )
    await db.flush()
    return success(None)
