from fastapi import APIRouter, Depends, Query, UploadFile, File
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user, get_optional_user
from app.models.user import User
from app.models.project import Project
from app.schemas.environment import EnvironmentCreate, EnvironmentUpdate, VariableUpsert
from app.services.env_service import EnvService
from app.services.permission_service import check_read_access, check_write_access
from app.utils.response import success
from app.core.exceptions import raise_biz, ErrorCodes

router = APIRouter(prefix="/projects/{project_id}/environments", tags=["Environments"])


@router.get("", summary="环境列表", description="获取项目的环境配置列表")
async def list_envs(project_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=0, ge=0, le=100),
    current_user: User | None = Depends(get_optional_user),
    _project: Project = Depends(check_read_access),
    db: AsyncSession = Depends(get_db)):
    items, total = await EnvService(db).list(project_id, page, page_size)
    if page_size > 0:
        return success({"items": items, "total": total, "page": page, "page_size": page_size})
    return success(items)


@router.get("/{env_id}", summary="环境详情", description="获取指定环境的完整配置信息")
async def get_env(project_id: int, env_id: int,
    current_user: User | None = Depends(get_optional_user),
    _project: Project = Depends(check_read_access),
    db: AsyncSession = Depends(get_db)):
    return success(EnvService(db).to_dict(await EnvService(db).get(env_id, project_id=project_id)))


@router.post("", summary="创建环境", description="新建环境配置（名称、服务地址、变量等）")
async def create_env(project_id: int, req: EnvironmentCreate,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
    db: AsyncSession = Depends(get_db)):
    # 双通道同步：base_url <-> services[0].url
    if req.base_url:
        if not req.services:
            req.services = [{"name": "默认服务", "module": "default", "url": req.base_url, "is_base": True}]
        elif not req.services[0].get("url"):
            req.services[0]["url"] = req.base_url
    elif req.services and req.services[0].get("url"):
        req.base_url = req.services[0]["url"]
    result = EnvService(db).to_dict(await EnvService(db).create(project_id, req))
    return success(result)


@router.put("/{env_id}", summary="更新环境", description="修改环境配置信息")
async def update_env(project_id: int, env_id: int, req: EnvironmentUpdate,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
    db: AsyncSession = Depends(get_db)):
    # 双通道同步：base_url <-> services[0].url
    if req.base_url is not None:
        if not req.services:
            req.services = [{"name": "默认服务", "module": "default", "url": req.base_url, "is_base": True}]
        elif not req.services[0].get("url"):
            req.services[0]["url"] = req.base_url
    elif req.services and req.services[0].get("url"):
        req.base_url = req.services[0]["url"]
    result = EnvService(db).to_dict(await EnvService(db).update(env_id, req, project_id=project_id))
    return success(result)


@router.post("/{env_id}/variables", summary="添加/更新环境变量", description="添加或更新单个环境变量")
async def upsert_variable(project_id: int, env_id: int, req: VariableUpsert,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
    db: AsyncSession = Depends(get_db)):
    """添加或更新单个环境变量。"""
    import json
    from app.models.environment import Environment as EnvModel
    result = await db.execute(select(EnvModel).where(EnvModel.id == env_id))
    env = result.scalar_one_or_none()
    if not env:
        raise_biz(ErrorCodes.ENV_NOT_FOUND)
    if env.project_id != project_id:
        raise_biz(ErrorCodes.ENV_FORBIDDEN)
    # 解析现有变量（兼容字符串和列表两种存储格式）
    raw = env.variables
    if isinstance(raw, str):
        try:
            variables = json.loads(raw) if raw else []
        except (json.JSONDecodeError, ValueError):
            variables = []
    elif isinstance(raw, list):
        variables = raw
    else:
        variables = []
    # 查找是否已存在同名变量
    idx = next((i for i, v in enumerate(variables) if v.get("key") == req.key), None)
    if idx is not None:
        variables[idx]["value"] = req.value
    else:
        variables.append({"key": req.key, "value": req.value, "enabled": True})
    # 保存（保持与原始存储格式一致）
    env.variables = json.dumps(variables, ensure_ascii=False) if isinstance(raw, str) else variables
    await db.flush()
    return success({"key": req.key, "value": req.value, "updated": idx is not None})


@router.delete("/{env_id}", summary="删除环境", description="删除指定的环境配置")
async def delete_env(project_id: int, env_id: int,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
    db: AsyncSession = Depends(get_db)):
    await EnvService(db).delete(env_id, project_id=project_id)
    return success(message="环境删除成功")


@router.get("/{env_id}/export", summary="导出环境", description="导出环境配置为 JSON 格式")
async def export_env(project_id: int, env_id: int,
    current_user: User | None = Depends(get_optional_user),
    _project: Project = Depends(check_read_access),
    db: AsyncSession = Depends(get_db)):
    return success(EnvService(db).to_dict(await EnvService(db).get(env_id, project_id=project_id)))


@router.post("/{env_id}/clone", summary="克隆环境", description="克隆环境配置及其所有变量")
async def clone_environment(project_id: int, env_id: int,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
    db: AsyncSession = Depends(get_db)):
    svc = EnvService(db)
    env = await svc.get(env_id, project_id=project_id)
    from app.schemas.environment import EnvironmentCreate
    req = EnvironmentCreate(
        name=env.name + "(副本)",
        base_url=env.base_url,
        auth_config=env.auth_config,
        services=svc.to_dict(env)["services"],
        variables=svc.to_dict(env)["variables"],
        headers=svc.to_dict(env)["headers"],
    )
    new_env = await svc.create(project_id, req)
    return success(svc.to_dict(new_env))


@router.post("/{environment_id}/import-env", summary="Import from .env file")
async def import_env_file(project_id: int, environment_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
    db: AsyncSession = Depends(get_db)):
    import json
    from app.models.environment import Environment
    content = (await file.read()).decode("utf-8")
    result = await db.execute(select(Environment).where(Environment.id == environment_id))
    env = result.scalar_one_or_none()
    if not env:
        raise_biz(ErrorCodes.ENV_NOT_FOUND)
    if env.project_id != project_id:
        raise_biz(ErrorCodes.ENV_FORBIDDEN)
    try:
        existing = json.loads(env.variables) if isinstance(env.variables, str) else []
    except (json.JSONDecodeError, TypeError):
        existing = []
    existing_map = {v.get("key"): i for i, v in enumerate(existing) if v.get("key")}
    count = 0
    for line in content.strip().splitlines():
        stripped = line.strip()
        # 跳过空行和注释行
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        key = key.strip()
        # 去除 export 前缀
        if key.startswith("export "):
            key = key[len("export "):].strip()
        value = value.strip()
        # 去除引号包裹（单引号或双引号）
        if len(value) >= 2 and (
            (value.startswith('"') and value.endswith('"')) or
            (value.startswith("'") and value.endswith("'"))
        ):
            value = value[1:-1]
        if not key:
            continue
        if key in existing_map:
            existing[existing_map[key]]["value"] = value
        else:
            existing.append({"key": key, "value": value, "enabled": True})
        count += 1
    env.variables = json.dumps(existing, ensure_ascii=False)
    await db.flush()
    return success({"imported_count": count})


@router.get("/{environment_id}/export-env", summary="Export as .env")
async def export_env_file(project_id: int, environment_id: int,
    current_user: User | None = Depends(get_optional_user),
    _project: Project = Depends(check_read_access),
    db: AsyncSession = Depends(get_db)):
    import json
    from app.models.environment import Environment
    from fastapi.responses import PlainTextResponse
    result = await db.execute(select(Environment).where(Environment.id == environment_id))
    env = result.scalar_one_or_none()
    if not env:
        raise_biz(ErrorCodes.ENV_NOT_FOUND)
    if env.project_id != project_id:
        raise_biz(ErrorCodes.ENV_FORBIDDEN)
    try:
        variables = json.loads(env.variables) if isinstance(env.variables, str) else []
    except (json.JSONDecodeError, TypeError):
        variables = []
    lines = [f"{v.get('key', '')}={v.get('value', '')}" for v in variables if v.get("key")]
    content = "\n".join(lines)
    return PlainTextResponse(content, media_type="text/plain",
        headers={"Content-Disposition": f"attachment; filename={env.name}.env"})
