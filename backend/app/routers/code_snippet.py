from fastapi import APIRouter, Depends
from app.middleware.auth import get_current_user
from app.services.permission_service import check_read_access
from app.services.api_service import ApiService
from app.database import get_db
from app.schemas.code_snippet import CodeSnippetRequest, CodeSnippetResponse
from app.services.code_snippet_service import generate_code_snippet
from app.services.executor.variable_renderer import render_template
from app.utils.json_helpers import safe_json_load
from sqlalchemy import select
from app.models.environment import Environment
from app.models.project import Project

router = APIRouter(prefix="/projects/{project_id}", tags=["code-snippet"])


async def _load_variables(project_id: int, environment_id: int | None, db):
    """加载环境变量和项目全局变量，environment_id 为空时只加载全局变量。"""
    variables = {}

    # 项目全局变量
    try:
        proj_result = await db.execute(select(Project).where(Project.id == project_id))
        proj = proj_result.scalar_one_or_none()
        if proj and proj.global_variables:
            gv_list = safe_json_load(proj.global_variables, [])
            for v in gv_list:
                if isinstance(v, dict) and v.get("key") and v.get("enabled", True):
                    variables[v["key"]] = v.get("value", "")
    except (ValueError, KeyError, TypeError):
        pass

    # 环境变量（覆盖同名全局变量）
    if environment_id:
        try:
            env_result = await db.execute(select(Environment).where(Environment.id == environment_id))
            env = env_result.scalar_one_or_none()
            if env:
                env_vars = safe_json_load(env.variables, [])
                for v in env_vars:
                    if isinstance(v, dict) and v.get("key"):
                        variables[v["key"]] = v.get("value", "")
                services = safe_json_load(env.services, [])
                if services:
                    variables["base_url"] = services[0].get("url", "")
        except (ValueError, KeyError, TypeError):
            pass

    return variables


@router.post("/apis/{api_id}/code-snippet", response_model=CodeSnippetResponse)
async def get_code_snippet(
    project_id: int, api_id: int, req: CodeSnippetRequest,
    db=Depends(get_db),
    _=Depends(get_current_user),
    _project=Depends(check_read_access),
):
    service = ApiService(db)
    api = await service.get(api_id)
    api_dict = service.to_dict(api)

    # 解析模板变量
    variables = await _load_variables(project_id, req.environment_id, db)
    if variables:
        # 解析 path
        api_dict["path"] = render_template(api_dict["path"], variables)
        # 解析 headers 的 key 和 value
        headers = api_dict.get("headers", [])
        for h in headers:
            if isinstance(h, dict) and h.get("key"):
                h["key"] = render_template(h["key"], variables)
                h["value"] = render_template(h.get("value", ""), variables)
        # 解析 params
        params = api_dict.get("params", [])
        for p in params:
            if isinstance(p, dict) and p.get("key"):
                p["key"] = render_template(p["key"], variables)
                p["value"] = render_template(p.get("value", ""), variables)
        # 解析 body
        body = api_dict.get("body", {})
        if isinstance(body, dict) and body.get("content"):
            body["content"] = render_template(body["content"], variables)
        # fields (form-data)
        if isinstance(body, dict) and body.get("fields"):
            for f in body["fields"]:
                if isinstance(f, dict) and f.get("key"):
                    f["key"] = render_template(f["key"], variables)
                    f["value"] = render_template(f.get("value", ""), variables)

    code = generate_code_snippet(api_dict, req.language)
    return CodeSnippetResponse(code=code, language=req.language)
