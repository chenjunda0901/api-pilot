"""API 文档发布路由 — 发布、分享、公开访问、文档编辑、版本管理"""

from typing import Optional
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.limiter import limiter
from app.middleware.auth import get_current_user, get_optional_user
from app.models.user import User
from app.models.project import Project
from app.services.doc_service import DocService
from app.services.permission_service import check_read_access, check_write_access
from app.utils.response import success

router = APIRouter(prefix="/projects/{project_id}/docs", tags=["API Documentation"])


class DocPublishRequest(BaseModel):
    name: str = Field(default="", description="文档名称")
    description: str = Field(default="", description="文档描述")
    password: str = Field(default="", description="访问密码（可选）")
    expires_in_days: int = Field(default=0, description="过期天数，0 表示永不过期")
    include_categories: list[int] = Field(default=[], description="包含的接口目录 ID 列表，空=全部")
    env_id: Optional[int] = Field(default=None, description="关联环境 ID（可选）")


@router.post("/publish", summary="发布文档", description="将项目 API 发布为在线文档，生成分享链接")
async def publish_docs(
    project_id: int,
    req: DocPublishRequest,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
    db: AsyncSession = Depends(get_db),
):
    """发布 API 文档"""
    s = DocService(db)
    doc = await s.create(
        project_id=project_id,
        user_id=current_user.id,
        name=req.name or f"{_project.name} API 文档",
        description=req.description,
        password=req.password,
        expires_in_days=req.expires_in_days,
        include_categories=req.include_categories,
        env_id=req.env_id,
    )
    return success({
        **s.to_dict(doc),
        "share_url": f"/shared-docs/{doc.share_token}",
    })


@router.get("/list", summary="文档列表", description="获取项目的已发布文档列表")
async def list_docs(
    project_id: int,
    current_user: User | None = Depends(get_optional_user),
    _project: Project = Depends(check_read_access),
    db: AsyncSession = Depends(get_db),
):
    s = DocService(db)
    return success(await s.list_by_project(project_id))


@router.post("/{doc_id}/revoke", summary="撤销文档", description="撤销已发布的 API 文档分享链接")
async def revoke_doc(
    project_id: int,
    doc_id: int,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
    db: AsyncSession = Depends(get_db),
):
    s = DocService(db)
    await s.revoke(doc_id, project_id)
    return success(message="文档已撤销")


@router.delete("/{doc_id}", summary="删除文档", description="删除文档发布记录")
async def delete_doc(
    project_id: int,
    doc_id: int,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
    db: AsyncSession = Depends(get_db),
):
    s = DocService(db)
    await s.delete(doc_id, project_id)
    return success(message="文档已删除")


# ── API 文档编辑端点 ──────────────────────────────────────────────

class ApiDocSaveRequest(BaseModel):
    description: str = Field(default="", description="Markdown 格式的接口描述")
    param_docs: list[dict] | None = Field(default=None, description="参数文档列表 [{name, type, required, description}]")
    request_examples: list[dict] | None = Field(default=None, description="请求示例列表 [{name, body}]")
    response_examples: list[dict] | None = Field(default=None, description="响应示例列表 [{name, status_code, body}]")
    is_draft: bool = Field(default=True, description="是否为草稿，false 时创建版本快照")


@router.get("/api/{api_id}", summary="获取接口文档", description="获取单个 API 的文档数据")
async def get_api_doc(
    project_id: int,
    api_id: int,
    current_user: User | None = Depends(get_optional_user),
    _project: Project = Depends(check_read_access),
    db: AsyncSession = Depends(get_db),
):
    s = DocService(db)
    return success(await s.get_api_doc(project_id, api_id))


@router.put("/api/{api_id}", summary="保存接口文档", description="保存单个 API 的文档数据，支持草稿和发布")
async def save_api_doc(
    project_id: int,
    api_id: int,
    req: ApiDocSaveRequest,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
    db: AsyncSession = Depends(get_db),
):
    s = DocService(db)
    result = await s.save_api_doc(
        project_id=project_id,
        api_id=api_id,
        user_id=current_user.id,
        description=req.description,
        param_docs=req.param_docs,
        request_examples=req.request_examples,
        response_examples=req.response_examples,
        is_draft=req.is_draft,
    )
    return success(result, message="草稿已保存" if req.is_draft else "文档已发布")


# ── 文档版本管理端点 ──────────────────────────────────────────────

@router.get("/api/{api_id}/versions", summary="文档版本历史", description="获取 API 文档的版本历史列表")
async def list_doc_versions(
    project_id: int,
    api_id: int,
    current_user: User | None = Depends(get_optional_user),
    _project: Project = Depends(check_read_access),
    db: AsyncSession = Depends(get_db),
):
    s = DocService(db)
    return success(await s.list_versions(api_id))


@router.post("/api/{api_id}/versions/{version_id}/rollback", summary="回滚文档版本", description="回滚到指定的文档版本")
async def rollback_doc_version(
    project_id: int,
    api_id: int,
    version_id: int,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
    db: AsyncSession = Depends(get_db),
):
    s = DocService(db)
    result = await s.rollback_version(api_id, version_id, current_user.id)
    return success(result, message="已回滚到指定版本")


# 公开共享文档路由（无需认证，放在公共前缀下）
shared_router = APIRouter(prefix="/shared", tags=["Shared Docs"])


class DocAccessRequest(BaseModel):
    password: str = Field(default="", description="文档访问密码")


@shared_router.get("/docs/{token}")
@limiter.limit("60/minute")
async def get_shared_doc(
    token: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """通过分享令牌获取 API 文档数据（公开，无需登录，仅限无密码文档）"""
    s = DocService(db)
    result = await s.get_by_token(token, "")
    return success(result)


@shared_router.post("/docs/{token}")
@limiter.limit("60/minute")
async def get_shared_doc_with_password(
    token: str,
    request: Request,
    body: DocAccessRequest,
    db: AsyncSession = Depends(get_db),
):
    """通过分享令牌和密码获取 API 文档数据（公开，无需登录，用于密码保护文档）"""
    s = DocService(db)
    result = await s.get_by_token(token, body.password)
    return success(result)
