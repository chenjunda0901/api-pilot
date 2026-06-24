"""5 层作用域变量路由。"""

import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import ErrorCodes, raise_biz
from app.database import get_db
from app.middleware.auth import get_current_user, get_optional_user
from app.models.user import User
from app.models.variable import Variable
from app.models.environment import Environment
from app.models.test_case import TestCase
from app.schemas.variable import (
    VariableCreate,
    VariableUpdate,
    VariableResolveRequest,
    ImportVariablesRequest,
)
from app.services.permission_service import require_project_access
from app.services.variable_resolver import VariableResolver
from app.utils.response import success

router = APIRouter(prefix="/variables", tags=["Variables"])
logger = logging.getLogger("api_pilot.routers.variables")


async def _resolve_project_id(
    db: AsyncSession, scope: str, scope_id: Optional[int]
) -> Optional[int]:
    """从变量的 scope/scope_id 解析出 project_id。"""
    if scope == "project":
        return scope_id
    if scope == "env" and scope_id:
        from app.models.environment import Environment

        env = await db.get(Environment, scope_id)
        return env.project_id if env else None
    if scope == "case" and scope_id:
        from app.models.test_case import TestCase

        case = await db.get(TestCase, scope_id)
        return case.project_id if case else None
    return None


# ── Fernet 加密工具 ──────────────────────────────────────────────────────


def _get_fernet():
    """获取 Fernet 加密器。"""
    from cryptography.fernet import Fernet
    from app.config import settings

    return Fernet(settings.FERNET_KEY)


def _encrypt_value(value: str) -> str:
    """加密变量值。"""
    if not value:
        return value
    try:
        f = _get_fernet()
        return f.encrypt(value.encode()).decode()
    except Exception:
        # 加密失败时保留明文（降级处理）
        return value


def _decrypt_value(encrypted: str) -> str:
    """解密变量值。"""
    if not encrypted:
        return encrypted
    try:
        f = _get_fernet()
        return f.decrypt(encrypted.encode()).decode()
    except Exception:
        # 解密失败时返回原值（可能是未加密的旧数据）
        return encrypted


def _is_encrypted(value: str) -> bool:
    """检测值是否已被 Fernet 加密。"""
    if not value:
        return False
    try:
        f = _get_fernet()
        f.decrypt(value.encode())
        return True
    except Exception:
        return False


def _mask_secret(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 4:
        return "****"
    return f"{value[:2]}****{value[-2:]}"


def _to_dict(v: Variable) -> dict:
    """输出：secret 类型仅显示掩码。"""
    return {
        "id": v.id,
        "scope": v.scope,
        "scope_id": v.scope_id,
        "name": v.name,
        "value": _mask_secret(v.value) if v.is_secret else (v.value or ""),
        "is_secret": bool(v.is_secret),
        "description": v.description,
        "created_at": v.created_at.isoformat() if v.created_at else None,
    }


# ── 列表 ──────────────────────────────────────────────────────────────────


@router.get("", summary="变量列表")
async def list_variables(
    project_id: int = Query(..., ge=1),
    scope: Optional[str] = Query(None, description="global / project / env / case"),
    scope_id: Optional[int] = Query(None, ge=1),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    await require_project_access(db, project_id, current_user, require_write=False)
    query = select(Variable).where(
        Variable.scope == "project", Variable.scope_id == project_id
    )
    count_q = select(func.count(Variable.id)).where(
        Variable.scope == "project", Variable.scope_id == project_id
    )
    if scope:
        query = query.where(Variable.scope == scope)
        count_q = count_q.where(Variable.scope == scope)
    if scope_id is not None:
        # 验证 scope_id 属于当前项目，防止跨项目泄漏
        if scope == "env":
            env_exists = await db.execute(
                select(1).where(
                    Environment.id == scope_id, Environment.project_id == project_id
                )
            )
            if not env_exists.scalar():
                raise_biz(ErrorCodes.PARAM_ERROR, f"环境 {scope_id} 不属于当前项目")
        elif scope == "case":
            case_exists = await db.execute(
                select(1).where(
                    TestCase.id == scope_id, TestCase.project_id == project_id
                )
            )
            if not case_exists.scalar():
                raise_biz(ErrorCodes.PARAM_ERROR, f"用例 {scope_id} 不属于当前项目")
        query = query.where(Variable.scope_id == scope_id)
        count_q = count_q.where(Variable.scope_id == scope_id)
    total = await db.scalar(count_q) or 0
    result = await db.execute(
        query.order_by(Variable.scope, Variable.name)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = [_to_dict(v) for v in result.scalars().all()]
    return success(
        {"items": items, "total": total, "page": page, "page_size": page_size}
    )


# ── 创建 ──────────────────────────────────────────────────────────────────


@router.post("", summary="创建变量")
async def create_variable(
    req: VariableCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建变量；secret 类型使用 Fernet 加密存储。"""
    project_id = await _resolve_project_id(db, req.scope, req.scope_id)
    if project_id is not None:
        await require_project_access(db, project_id, current_user, require_write=True)
    elif req.scope != "global":
        raise_biz(
            ErrorCodes.PARAM_ERROR,
            f"无法解析 scope={req.scope} scope_id={req.scope_id} 对应的项目",
        )
    else:
        from app.middleware.auth import require_admin

        await require_admin(current_user)
    stored_value = req.value
    if req.is_secret and req.value:
        stored_value = _encrypt_value(req.value)
    v = Variable(
        scope=req.scope,
        scope_id=req.scope_id,
        name=req.name,
        value=stored_value,
        is_secret=1 if req.is_secret else 0,
        description=req.description,
    )
    db.add(v)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise_biz(
            ErrorCodes.PROJECT_NAME_EXISTS, f"同作用域下已存在同名变量 {req.name}"
        )
    return success(_to_dict(v))


# ── 更新 ──────────────────────────────────────────────────────────────────


@router.patch("/{variable_id}", summary="更新变量")
async def update_variable(
    variable_id: int,
    req: VariableUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """更新变量；secret 类型加密存储。"""
    result = await db.execute(select(Variable).where(Variable.id == variable_id))
    v = result.scalar_one_or_none()
    if not v:
        raise_biz(ErrorCodes.API_NOT_FOUND, f"变量 {variable_id} 不存在")
    project_id = await _resolve_project_id(db, v.scope, v.scope_id)
    if project_id is not None:
        await require_project_access(db, project_id, current_user, require_write=True)
    elif v.scope == "global":
        from app.middleware.auth import require_admin

        await require_admin(current_user)
    else:
        raise_biz(ErrorCodes.PROJECT_FORBIDDEN)
    data = req.model_dump(exclude_unset=True)
    # 处理 secret 变量的加密
    if "value" in data and data["value"]:
        if v.is_secret or data.get("is_secret"):
            data["value"] = _encrypt_value(data["value"])
    if v.is_secret and "value" in data and not data["value"]:
        raise_biz(ErrorCodes.PARAM_ERROR, "加密变量不允许设置为空值")
    if "is_secret" in data:
        # 如果从非 secret 变为 secret，需要加密现有值
        if data["is_secret"] and not v.is_secret and v.value:
            data["value"] = _encrypt_value(v.value)
        data["is_secret"] = 1 if data["is_secret"] else 0
    for field, value in data.items():
        setattr(v, field, value)
    await db.flush()
    return success(_to_dict(v))


# ── 删除 ──────────────────────────────────────────────────────────────────


@router.delete("/{variable_id}", summary="删除变量")
async def delete_variable(
    variable_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Variable).where(Variable.id == variable_id))
    v = result.scalar_one_or_none()
    if not v:
        raise_biz(ErrorCodes.API_NOT_FOUND, f"变量 {variable_id} 不存在")
    project_id = await _resolve_project_id(db, v.scope, v.scope_id)
    if project_id is not None:
        await require_project_access(db, project_id, current_user, require_write=True)
    elif v.scope == "global":
        from app.middleware.auth import require_admin

        await require_admin(current_user)
    else:
        raise_biz(ErrorCodes.PROJECT_FORBIDDEN)
    await db.delete(v)
    await db.flush()
    return success(message="变量已删除")


# ── 解析 ──────────────────────────────────────────────────────────────────


@router.post("/resolve", summary="解析变量引用")
async def resolve_variable(
    req: VariableResolveRequest,
    project_id: int = Query(..., ge=1),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """根据 scope_stack 解析变量名对应的值。"""
    await require_project_access(db, project_id, current_user, require_write=False)
    # 把 scope_stack 里的 scope_id → 从 DB 拉变量映射成 dict
    normalized: list[tuple[str, Any]] = []
    for entry in req.scope_stack:
        scope = entry.get("scope")
        payload = entry.get("payload")
        if scope in ("project", "case") and isinstance(payload, int):
            stmt = select(Variable).where(
                Variable.scope == scope, Variable.scope_id == payload
            )
            rows = (await db.execute(stmt)).scalars().all()
            normalized.append(
                (
                    scope,
                    {
                        r.name: {"__secret__": bool(r.is_secret), "value": r.value}
                        if r.is_secret
                        else r.value
                        for r in rows
                    },
                )
            )
        elif scope in ("global", "env"):
            stmt = select(Variable).where(Variable.scope == scope)
            if scope == "env" and isinstance(payload, int):
                stmt = stmt.where(Variable.scope_id == payload)
            rows = (await db.execute(stmt)).scalars().all()
            normalized.append(
                (
                    scope,
                    {
                        r.name: {"__secret__": bool(r.is_secret), "value": r.value}
                        if r.is_secret
                        else r.value
                        for r in rows
                    },
                )
            )
        else:
            normalized.append((scope, payload or {}))

    resolver = VariableResolver(
        key=settings.FERNET_KEY.encode()
        if isinstance(settings.FERNET_KEY, str)
        else settings.FERNET_KEY
    )
    try:
        value = resolver.resolve(req.name, normalized)
        masked = False
        return success(
            {"name": req.name, "value": value, "found": True, "masked": masked}
        )
    except Exception:
        return success(
            {"name": req.name, "value": None, "found": False, "masked": False}
        )


# ── 导出 / 导入 ────────────────────────────────────────────────────────────


@router.get("/export", summary="导出变量（JSON）")
async def export_variables(
    project_id: int = Query(..., ge=1),
    scope: Optional[str] = Query(None),
    scope_id: Optional[int] = Query(None, ge=1),
    current_user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """导出变量为 JSON；secret 标记 + 占位符（不导出明文）。"""
    await require_project_access(db, project_id, current_user, require_write=False)
    query = select(Variable).where(
        Variable.scope == "project", Variable.scope_id == project_id
    )
    if scope:
        query = query.where(Variable.scope == scope)
    if scope_id is not None:
        query = query.where(Variable.scope_id == scope_id)
    result = await db.execute(query)
    items = []
    for v in result.scalars().all():
        items.append(
            {
                "scope": v.scope,
                "scope_id": v.scope_id,
                "name": v.name,
                "is_secret": bool(v.is_secret),
                "value": "<secret>" if v.is_secret else v.value,
                "description": v.description,
            }
        )
    return success({"items": items, "total": len(items)})


@router.post("/import", summary="导入变量（JSON）")
async def import_variables(
    payload: ImportVariablesRequest,
    project_id: int = Query(..., ge=1),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """导入变量；secret 类型仍按明文存储（依赖 is_secret 标记显示时脱敏）。"""
    await require_project_access(db, project_id, current_user, require_write=True)
    created = 0
    updated = 0
    for item in payload.items:
        existing = await db.execute(
            select(Variable).where(
                Variable.scope == item.scope,
                Variable.scope_id == item.scope_id,
                Variable.name == item.name,
            )
        )
        v = existing.scalar_one_or_none()
        if v:
            v.value = item.value
            v.is_secret = 1 if item.is_secret else 0
            v.description = item.description
            updated += 1
        else:
            db.add(
                Variable(
                    scope=item.scope,
                    scope_id=item.scope_id,
                    name=item.name,
                    value=item.value,
                    is_secret=1 if item.is_secret else 0,
                    description=item.description,
                )
            )
            created += 1
    await db.flush()
    return success({"created": created, "updated": updated})


# ── Reveal 接口 ──────────────────────────────────────────────────────────


@router.get("/{variable_id}/reveal", summary="获取加密变量明文")
async def reveal_variable(
    variable_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """返回加密变量的明文值。仅对 is_secret=True 的变量有效。需要项目写权限。"""
    result = await db.execute(select(Variable).where(Variable.id == variable_id))
    v = result.scalar_one_or_none()
    if not v:
        raise_biz(ErrorCodes.API_NOT_FOUND, f"变量 {variable_id} 不存在")
    project_id = await _resolve_project_id(db, v.scope, v.scope_id)
    if project_id is not None:
        await require_project_access(db, project_id, current_user, require_write=True)
    elif v.scope == "global":
        from app.middleware.auth import require_admin

        await require_admin(current_user)
    else:
        raise_biz(ErrorCodes.PROJECT_FORBIDDEN)
    if not v.is_secret:
        return success(
            {
                "id": v.id,
                "name": v.name,
                "value": v.value or "",
                "is_secret": False,
            }
        )
    # 解密
    plain_value = v.value
    if _is_encrypted(v.value):
        plain_value = _decrypt_value(v.value)
    return success(
        {
            "id": v.id,
            "name": v.name,
            "value": plain_value,
            "is_secret": True,
        }
    )
