"""API 文档发布服务 — 发布、分享、访问控制、文档编辑、版本管理"""

import json
import secrets
import logging
from datetime import datetime, timedelta, UTC

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import raise_biz, ErrorCodes
from app.models.api_document import ApiDocument
from app.models.api_definition import ApiDefinition
from app.models.api_category import ApiCategory
from app.models.doc_version import DocVersion
from app.utils.password import hash_password, verify_password

logger = logging.getLogger("doc_service")


class DocService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def to_dict(self, doc: ApiDocument) -> dict:
        return {
            "id": doc.id,
            "project_id": doc.project_id,
            "name": doc.name,
            "description": doc.description,
            "share_token": doc.share_token,
            "has_password": bool(doc.password_hash),
            "expires_at": str(doc.expires_at) if doc.expires_at else None,
            "is_enabled": doc.is_enabled,
            "view_count": doc.view_count,
            "include_categories": doc.include_categories,
            "created_by": doc.created_by,
            "created_at": str(doc.created_at),
            "updated_at": str(doc.updated_at),
        }

    async def create(
        self,
        project_id: int,
        user_id: int,
        name: str = "",
        description: str = "",
        password: str = "",
        expires_in_days: int = 0,
        include_categories: list[int] | None = None,
        env_id: int | None = None,
    ) -> ApiDocument:
        """发布 API 文档"""
        # 生成唯一分享令牌
        share_token = secrets.token_urlsafe(32)
        # 确保 token 唯一
        while True:
            existing = await self.db.execute(
                select(ApiDocument).where(ApiDocument.share_token == share_token)
            )
            if not existing.scalar_one_or_none():
                break
            share_token = secrets.token_urlsafe(32)

        password_hash = hash_password(password) if password else None

        expires_at = None
        if expires_in_days > 0:
            expires_at = datetime.now(UTC) + timedelta(days=expires_in_days)

        doc = ApiDocument(
            project_id=project_id,
            name=name,
            description=description,
            share_token=share_token,
            password_hash=password_hash,
            expires_at=expires_at,
            include_categories=json.dumps(include_categories or []),
            env_id=env_id,
            created_by=user_id,
        )
        self.db.add(doc)
        await self.db.flush()
        await self.db.refresh(doc)
        return doc

    async def get_by_token(self, token: str, password: str = "") -> dict:
        """通过分享令牌获取文档数据（公开访问，无需登录）"""
        result = await self.db.execute(
            select(ApiDocument).where(
                ApiDocument.share_token == token,
                ApiDocument.is_enabled.is_(True),
            )
        )
        doc = result.scalar_one_or_none()
        if not doc:
            raise_biz(ErrorCodes.DOC_NOT_FOUND, "文档不存在或已失效")

        # 检查过期
        if doc.expires_at and datetime.now(UTC) > doc.expires_at.replace(tzinfo=UTC):
            raise_biz(ErrorCodes.DOC_EXPIRED, "文档已过期")

        # 密码验证
        if doc.password_hash:
            if not password:
                return {"need_password": True, "doc_id": doc.id, "name": doc.name}
            if not verify_password(password, doc.password_hash):
                raise_biz(ErrorCodes.DOC_PASSWORD_WRONG, "密码错误")

        # 增加浏览次数
        doc.view_count = (doc.view_count or 0) + 1
        await self.db.flush()

        # 加载 API 数据
        api_result = await self.db.execute(
            select(ApiDefinition).where(
                ApiDefinition.project_id == doc.project_id,
                ApiDefinition.deleted_at.is_(None),
            ).order_by(ApiDefinition.id)
        )
        apis = []
        for a in api_result.scalars().all():
            # 解析 settings 获取 request_examples
            try:
                api_settings = json.loads(a.settings) if a.settings else {}
            except (json.JSONDecodeError, TypeError):
                api_settings = {}

            apis.append({
                "id": a.id,
                "category_id": a.category_id,
                "name": a.name,
                "method": a.method,
                "path": a.path,
                "description": a.description,
                "description_md": a.description_md,
                "headers": a.headers,
                "params": a.params,
                "body": a.body,
                "auth_type": a.auth_type,
                "response_schema": a.response_schema,
                "response_examples": a.response_examples,
                "request_examples": api_settings.get("request_examples", []),
            })

        # 加载目录树
        cat_result = await self.db.execute(
            select(ApiCategory).where(
                ApiCategory.project_id == doc.project_id
            ).order_by(ApiCategory.sort_order)
        )
        categories = []
        for c in cat_result.scalars().all():
            categories.append({
                "id": c.id,
                "name": c.name,
                "parent_id": c.parent_id,
                "sort_order": c.sort_order,
            })

        return {
            "doc_id": doc.id,
            "name": doc.name,
            "description": doc.description,
            "project_id": doc.project_id,
            "apis": apis,
            "categories": categories,
            "created_at": str(doc.created_at),
        }

    async def list_by_project(self, project_id: int) -> list[dict]:
        """获取项目的文档发布列表"""
        result = await self.db.execute(
            select(ApiDocument)
            .where(ApiDocument.project_id == project_id)
            .order_by(ApiDocument.created_at.desc())
        )
        return [self.to_dict(d) for d in result.scalars().all()]

    async def revoke(self, doc_id: int, project_id: int):
        """撤销文档发布"""
        result = await self.db.execute(
            select(ApiDocument).where(
                ApiDocument.id == doc_id,
                ApiDocument.project_id == project_id,
            )
        )
        doc = result.scalar_one_or_none()
        if not doc:
            raise_biz(ErrorCodes.DOC_NOT_FOUND)
        doc.is_enabled = False
        await self.db.flush()

    async def delete(self, doc_id: int, project_id: int):
        """删除文档发布记录"""
        result = await self.db.execute(
            select(ApiDocument).where(
                ApiDocument.id == doc_id,
                ApiDocument.project_id == project_id,
            )
        )
        doc = result.scalar_one_or_none()
        if not doc:
            raise_biz(ErrorCodes.DOC_NOT_FOUND)
        await self.db.delete(doc)
        await self.db.flush()

    # ── API 文档编辑（单个接口的文档数据） ──────────────────────────

    async def save_api_doc(
        self,
        project_id: int,
        api_id: int,
        user_id: int,
        description: str = "",
        param_docs: list | None = None,
        request_examples: list | None = None,
        response_examples: list | None = None,
        is_draft: bool = True,
    ) -> dict:
        """保存单个 API 的文档数据到 api_definitions 表，并创建版本快照"""
        result = await self.db.execute(
            select(ApiDefinition).where(
                ApiDefinition.id == api_id,
                ApiDefinition.project_id == project_id,
                ApiDefinition.deleted_at.is_(None),
            )
        )
        api = result.scalar_one_or_none()
        if not api:
            raise_biz(ErrorCodes.API_NOT_FOUND, "接口不存在")

        # 更新 description_md 字段（复用已有字段存储 Markdown 描述）
        if description is not None:
            api.description_md = description

        # 将 param_docs / request_examples / response_examples 存入 JSON 字段
        # 复用 api_definition 已有的 params / response_examples 字段扩展
        # param_docs: 附加到 params 的 description 字段（params 本身是 JSON 数组）
        if param_docs is not None:
            try:
                existing_params = json.loads(api.params) if api.params else []
            except (json.JSONDecodeError, TypeError):
                existing_params = []
            # 合并 param_docs 到 existing_params
            param_doc_map = {p.get("name"): p for p in param_docs if p.get("name")}
            for p in existing_params:
                name = p.get("key") or p.get("name")
                if name in param_doc_map:
                    doc_item = param_doc_map[name]
                    p["description"] = doc_item.get("description", "")
                    p["type"] = doc_item.get("type", p.get("type", "string"))
                    p["required"] = doc_item.get("required", p.get("required", False))
            api.params = json.dumps(existing_params)

        # request_examples: 存入新字段（扩展 body 旁的文档数据）
        # 存入 api.settings JSON 中追加 request_examples / response_examples
        try:
            settings = json.loads(api.settings) if api.settings else {}
        except (json.JSONDecodeError, TypeError):
            settings = {}

        if request_examples is not None:
            settings["request_examples"] = request_examples
        if response_examples is not None:
            # 同时更新 response_examples 字段（保持兼容）
            api.response_examples = json.dumps(response_examples)
            settings["doc_response_examples"] = response_examples

        settings["doc_is_draft"] = is_draft
        api.settings = json.dumps(settings)

        await self.db.flush()
        await self.db.refresh(api)

        # 非草稿时创建版本快照
        if not is_draft:
            await self._create_version(api_id, user_id, "发布文档")

        return await self.get_api_doc(project_id, api_id)

    async def get_api_doc(self, project_id: int, api_id: int) -> dict:
        """获取单个 API 的文档数据"""
        result = await self.db.execute(
            select(ApiDefinition).where(
                ApiDefinition.id == api_id,
                ApiDefinition.project_id == project_id,
                ApiDefinition.deleted_at.is_(None),
            )
        )
        api = result.scalar_one_or_none()
        if not api:
            raise_biz(ErrorCodes.API_NOT_FOUND, "接口不存在")

        try:
            params = json.loads(api.params) if api.params else []
        except (json.JSONDecodeError, TypeError):
            params = []

        try:
            settings = json.loads(api.settings) if api.settings else {}
        except (json.JSONDecodeError, TypeError):
            settings = {}

        # 构建 param_docs
        param_docs = []
        for p in params:
            param_docs.append({
                "name": p.get("key") or p.get("name", ""),
                "type": p.get("type", "string"),
                "required": p.get("required", False),
                "description": p.get("description", ""),
            })

        # 构建 request_examples / response_examples
        request_examples = settings.get("request_examples", [])
        try:
            resp_examples = json.loads(api.response_examples) if api.response_examples else []
        except (json.JSONDecodeError, TypeError):
            resp_examples = settings.get("doc_response_examples", [])

        return {
            "api_id": api.id,
            "name": api.name,
            "method": api.method,
            "path": api.path,
            "description": api.description,
            "description_md": api.description_md,
            "param_docs": param_docs,
            "request_examples": request_examples,
            "response_examples": resp_examples,
            "is_draft": settings.get("doc_is_draft", True),
        }

    # ── 文档版本管理 ──────────────────────────────────────────────

    async def _create_version(
        self, api_id: int, user_id: int, change_summary: str = ""
    ) -> DocVersion:
        """创建文档版本快照（内部方法）"""
        result = await self.db.execute(
            select(ApiDefinition).where(ApiDefinition.id == api_id)
        )
        api = result.scalar_one_or_none()
        if not api:
            return None

        version_data = json.dumps({
            "description_md": api.description_md,
            "params": api.params,
            "settings": api.settings,
            "response_examples": api.response_examples,
        })

        version = DocVersion(
            api_id=api_id,
            version_data=version_data,
            change_summary=change_summary,
            changed_by=user_id,
        )
        self.db.add(version)
        await self.db.flush()
        await self.db.refresh(version)
        return version

    async def list_versions(self, api_id: int) -> list[dict]:
        """获取 API 文档的版本历史"""
        result = await self.db.execute(
            select(DocVersion)
            .where(DocVersion.api_id == api_id)
            .order_by(DocVersion.created_at.desc())
        )
        versions = []
        for v in result.scalars().all():
            versions.append({
                "id": v.id,
                "api_id": v.api_id,
                "change_summary": v.change_summary,
                "changed_by": v.changed_by,
                "created_at": str(v.created_at),
            })
        return versions

    async def rollback_version(self, api_id: int, version_id: int, user_id: int) -> dict:
        """回滚到指定文档版本"""
        # 查找目标版本
        ver_result = await self.db.execute(
            select(DocVersion).where(
                DocVersion.id == version_id,
                DocVersion.api_id == api_id,
            )
        )
        version = ver_result.scalar_one_or_none()
        if not version:
            raise_biz(ErrorCodes.DOC_NOT_FOUND, "版本不存在")

        # 回滚前先保存当前版本
        await self._create_version(api_id, user_id, "回滚前自动保存")

        # 解析版本数据并恢复
        try:
            data = json.loads(version.version_data)
        except (json.JSONDecodeError, TypeError):
            raise_biz(ErrorCodes.INTERNAL_ERROR, "版本数据损坏")

        result = await self.db.execute(
            select(ApiDefinition).where(ApiDefinition.id == api_id)
        )
        api = result.scalar_one_or_none()
        if not api:
            raise_biz(ErrorCodes.API_NOT_FOUND, "接口不存在")

        if "description_md" in data:
            api.description_md = data["description_md"]
        if "params" in data:
            api.params = data["params"]
        if "settings" in data:
            api.settings = data["settings"]
        if "response_examples" in data:
            api.response_examples = data["response_examples"]

        await self.db.flush()
        await self.db.refresh(api)

        return await self.get_api_doc(api.project_id, api_id)
