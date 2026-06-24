"""Export routes for import_export."""

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.models.project import Project
from app.services.export_service import ExportService
from app.services.permission_service import check_read_access
from app.utils.response import success
from app.models.api_category import ApiCategory
from app.models.api_definition import ApiDefinition
from app.models.test_case import TestCase
from app.utils.json_helpers import safe_json_load

logger = logging.getLogger("api_pilot.routers.import_export")

export_router = APIRouter()


@export_router.get("/export/postman", summary="导出 Postman Collection", description="导出项目为 Postman Collection v2.1 格式")
async def export_postman(
    project_id: int,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_read_access),
    db: AsyncSession = Depends(get_db),
):
    s = ExportService(db)
    collection = await s.export_postman(project_id)
    return success(collection)


@export_router.get("/export/pilot", summary="导出 API Pilot 格式", description="导出项目为 API Pilot 标准 JSON 格式")
async def export_pilot(
    project_id: int,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_read_access),
    db: AsyncSession = Depends(get_db),
):
    s = ExportService(db)
    data = await s.export_pilot(project_id)
    return success(data)


@export_router.get("/export/openapi", summary="导出 OpenAPI 3.0", description="导出整个项目为 OpenAPI 3.0 规范 JSON")
async def export_openapi(
    project_id: int,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_read_access),
    db: AsyncSession = Depends(get_db),
):
    s = ExportService(db)
    data = await s.export_openapi(project_id)
    return success(data)


@export_router.get("/export/environments", summary="导出环境变量", description="导出项目环境变量为独立 JSON")
async def export_environments(
    project_id: int,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_read_access),
    db: AsyncSession = Depends(get_db),
):
    s = ExportService(db)
    data = await s.export_environments(project_id)
    return success(data)


@export_router.get("/export/html", summary="导出 HTML 文档", description="导出项目为独立 HTML 文档")
async def export_html(
    project_id: int,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_read_access),
    db: AsyncSession = Depends(get_db),
):
    """生成一份独立的 HTML 文档（含侧边栏与接口详情），可直接保存分发。

    阶段 4 增强：使用 ``StreamingResponse`` 按块流式输出，
    避免大项目下整份 HTML 在内存中拼装。
    """
    from fastapi.responses import StreamingResponse

    # 加载项目下所有接口（不含已删除）
    api_result = await db.execute(
        select(ApiDefinition)
        .where(ApiDefinition.project_id == project_id, ApiDefinition.deleted_at.is_(None))
        .order_by(ApiDefinition.category_id, ApiDefinition.id)
    )
    apis = api_result.scalars().all()

    # 加载用例数
    case_count_q = select(func.count(TestCase.id)).where(
        TestCase.project_id == project_id, TestCase.deleted_at.is_(None)
    )
    case_count = await db.scalar(case_count_q) or 0

    # 拼装 HTML（内联 CSS，单文件可双击打开）
    from html import escape as _e
    sidebar_items = [
        f'<li><a href="#api-{a.id}">{_e(a.method)} {_e(a.path)} — {_e(a.name)}</a></li>'
        for a in apis
    ]

    def _api_block(a) -> str:
        return f"""
        <section id="api-{a.id}" class="api">
          <h2>{_e(a.method)} <code>{_e(a.path)}</code></h2>
          <p><strong>{_e(a.name)}</strong></p>
          <p>{_e(a.description or '')}</p>
          <details><summary>Headers</summary><pre>{_e(a.headers or '[]')}</pre></details>
          <details><summary>Params</summary><pre>{_e(a.params or '[]')}</pre></details>
          <details><summary>Body</summary><pre>{_e(a.body or '')}</pre></details>
        </section>
        """

    head = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>API Pilot 文档 - 项目 {project_id}</title>
  <style>
    body{{font-family: -apple-system, sans-serif; margin: 0; display: flex;}}
    aside{{width: 280px; height: 100vh; overflow-y: auto; background: #f5f6f8; padding: 16px; border-right: 1px solid #e0e2e6;}}
    main{{flex: 1; padding: 24px;}}
    aside ul{{list-style: none; padding: 0;}}
    aside li{{padding: 4px 0; font-size: 13px;}}
    aside a{{color: #2563eb; text-decoration: none;}}
    .api{{padding: 16px 0; border-bottom: 1px solid #eee;}}
    h2 code{{background: #f5f6f8; padding: 2px 6px; border-radius: 3px;}}
    pre{{background: #1f2937; color: #f9fafb; padding: 12px; border-radius: 6px; overflow: auto; font-size: 12px;}}
    details{{margin: 8px 0;}}
    summary{{cursor: pointer; color: #2563eb;}}
  </style>
</head>
<body>
  <aside>
    <h3>接口列表（{len(apis)}）</h3>
    <ul>{''.join(sidebar_items)}</ul>
  </aside>
  <main>
    <h1>API Pilot 文档</h1>
    <p>项目 ID: {project_id} · 用例数: {case_count} · 接口数: {len(apis)}</p>
"""
    foot = """
  </main>
</body>
</html>"""

    async def gen():
        yield head.encode("utf-8")
        for a in apis:
            yield _api_block(a).encode("utf-8")
        yield foot.encode("utf-8")

    return StreamingResponse(gen(), media_type="text/html; charset=utf-8")


# =============================================================================
#  cURL 导入
# =============================================================================


@export_router.get("/export/full", summary="导出完整项目 ZIP", description="导出项目全部数据为 ZIP 压缩包")
async def export_full_zip(
    project_id: int,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_read_access),
    db: AsyncSession = Depends(get_db),
):
    """将项目所有数据打包为 ZIP 流式返回。

    ZIP 内包含：
      project.json / apis.json / scenes.json / cases.json /
      environments.json / mock_rules.json / test_plans.json /
      schemas.json / variables.json
    """
    import io
    import json as _json
    import zipfile
    from datetime import datetime, timezone

    from fastapi.responses import StreamingResponse

    from app.models.environment import Environment as EnvModel
    from app.models.mock_rule import MockRule
    from app.models.api_test_plan import ApiTestPlan, ApiTestPlanStep
    from app.models.data_schema import DataSchema
    from app.models.variable import Variable as VarModel
    from app.models.test_scene import TestScene
    from app.models.scene_step import SceneStep

    # ── 收集数据 ──
    # project.json
    proj = _project
    project_data = {
        "id": proj.id,
        "name": proj.name,
        "description": proj.description,
        "is_public": proj.is_public,
        "created_at": str(proj.created_at) if proj.created_at else None,
    }

    # apis.json（含分类）
    cat_result = await db.execute(
        select(ApiCategory).where(ApiCategory.project_id == project_id).order_by(ApiCategory.sort_order))
    categories = cat_result.scalars().all()
    api_result = await db.execute(
        select(ApiDefinition).where(
            ApiDefinition.project_id == project_id, ApiDefinition.deleted_at.is_(None))
        .order_by(ApiDefinition.category_id, ApiDefinition.id))
    apis = api_result.scalars().all()
    apis_data = {
        "categories": [
            {"id": c.id, "name": c.name, "parent_id": c.parent_id, "sort_order": c.sort_order}
            for c in categories
        ],
        "apis": [
            {
                "id": a.id, "name": a.name, "method": a.method, "path": a.path,
                "category_id": a.category_id, "description": a.description or "",
                "headers": safe_json_load(a.headers, []),
                "params": safe_json_load(a.params, []),
                "body": safe_json_load(a.body, {"type": "none", "content": ""}),
                "auth_type": a.auth_type or "none",
            }
            for a in apis
        ],
    }

    # scenes.json（含步骤）
    scene_result = await db.execute(
        select(TestScene).where(
            TestScene.project_id == project_id, TestScene.deleted_at.is_(None))
        .order_by(TestScene.id))
    scenes = scene_result.scalars().all()
    scene_ids = [s.id for s in scenes]
    steps_by_scene: dict[int, list] = {}
    if scene_ids:
        step_result = await db.execute(
            select(SceneStep).where(SceneStep.scene_id.in_(scene_ids)).order_by(SceneStep.sort_order))
        for step in step_result.scalars().all():
            steps_by_scene.setdefault(step.scene_id, []).append({
                "id": step.id, "node_id": step.node_id, "node_type": step.node_type,
                "label": step.label, "api_id": step.api_id, "test_case_id": step.test_case_id,
                "sort_order": step.sort_order, "enabled": step.enabled,
            })
    scenes_data = [
        {
            "id": s.id, "name": s.name, "description": s.description,
            "env_id": s.env_id, "loop_count": s.loop_count, "thread_count": s.thread_count,
            "on_failure": s.on_failure, "steps": steps_by_scene.get(s.id, []),
        }
        for s in scenes
    ]

    # cases.json
    case_result = await db.execute(
        select(TestCase).where(
            TestCase.project_id == project_id, TestCase.deleted_at.is_(None))
        .order_by(TestCase.id))
    cases_data = [
        {
            "id": c.id, "name": c.name, "api_id": c.api_id,
            "description": c.description, "priority": c.priority,
            "request_body": safe_json_load(c.request_body, None),
            "assertions": safe_json_load(c.assertions, []),
            "extract_vars": safe_json_load(c.extract_vars, []),
        }
        for c in case_result.scalars().all()
    ]

    # environments.json
    env_result = await db.execute(
        select(EnvModel).where(EnvModel.project_id == project_id).order_by(EnvModel.id))
    envs_data = [
        {
            "id": e.id, "name": e.name, "base_url": e.base_url,
            "services": safe_json_load(e.services, []),
            "variables": safe_json_load(e.variables, []),
            "headers": safe_json_load(e.headers, []),
        }
        for e in env_result.scalars().all()
    ]

    # mock_rules.json
    mock_result = await db.execute(
        select(MockRule).where(MockRule.project_id == project_id).order_by(MockRule.id))
    mock_data = [
        {
            "id": m.id, "name": m.name, "enabled": m.enabled, "priority": m.priority,
            "match_method": m.match_method, "match_path": m.match_path,
            "response_status": m.response_status,
            "response_headers": safe_json_load(m.response_headers, {}),
            "response_body": m.response_body,
        }
        for m in mock_result.scalars().all()
    ]

    # test_plans.json
    plan_result = await db.execute(
        select(ApiTestPlan).where(ApiTestPlan.project_id == project_id).order_by(ApiTestPlan.id))
    plans = plan_result.scalars().all()
    plan_ids = [p.id for p in plans]
    steps_by_plan: dict[int, list] = {}
    if plan_ids:
        plan_step_result = await db.execute(
            select(ApiTestPlanStep).where(ApiTestPlanStep.plan_id.in_(plan_ids)).order_by(ApiTestPlanStep.order_index))
        for ps in plan_step_result.scalars().all():
            steps_by_plan.setdefault(ps.plan_id, []).append({
                "id": ps.id, "step_type": ps.step_type, "step_id": ps.step_id,
                "order_index": ps.order_index, "enabled": ps.enabled,
            })
    plans_data = [
        {
            "id": p.id, "name": p.name, "description": p.description,
            "concurrency": p.concurrency, "timeout_seconds": p.timeout_seconds,
            "failure_strategy": p.failure_strategy, "status": p.status,
            "steps": steps_by_plan.get(p.id, []),
        }
        for p in plans
    ]

    # schemas.json
    schema_result = await db.execute(
        select(DataSchema).where(DataSchema.project_id == project_id).order_by(DataSchema.id))
    schemas_data = [
        {
            "id": s.id, "name": s.name, "description": s.description,
            "schema_json": safe_json_load(s.schema_json, {}),
            "example_json": safe_json_load(s.example_json, None),
        }
        for s in schema_result.scalars().all()
    ]

    # variables.json（secret 变量不导出明文）
    var_result = await db.execute(
        select(VarModel).where(VarModel.scope == "project", VarModel.scope_id == project_id)
        .order_by(VarModel.name))
    vars_data = [
        {
            "id": v.id, "name": v.name, "scope": v.scope, "scope_id": v.scope_id,
            "is_secret": bool(v.is_secret),
            "value": "<secret>" if v.is_secret else v.value,
            "description": v.description,
        }
        for v in var_result.scalars().all()
    ]

    # ── 打包 ZIP ──
    file_map = {
        "project.json": project_data,
        "apis.json": apis_data,
        "scenes.json": scenes_data,
        "cases.json": cases_data,
        "environments.json": envs_data,
        "mock_rules.json": mock_data,
        "test_plans.json": plans_data,
        "schemas.json": schemas_data,
        "variables.json": vars_data,
    }

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for filename, data in file_map.items():
            zf.writestr(filename, _json.dumps(data, ensure_ascii=False, indent=2))
    buf.seek(0)

    project_name = proj.name or f"project-{project_id}"
    safe_name = "".join(c if (c.isascii() and c.isalnum()) or c in "-_" else "_" for c in project_name)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    zip_filename = f"{safe_name}_{timestamp}.zip"
    # RFC 5987: 支持 non-ASCII 文件名
    from urllib.parse import quote as _urlquote
    quoted_filename = _urlquote(f"{project_name}_{timestamp}.zip")

    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename=\"{zip_filename}\"; filename*=UTF-8''{quoted_filename}",
        },
    )

