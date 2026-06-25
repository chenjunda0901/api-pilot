from __future__ import annotations

import json
from datetime import datetime, UTC
from app.utils.json_helpers import safe_json_load


from sqlalchemy import select, func

from app.core.exceptions import ErrorCodes
from app.utils.url_validator import validate_request_url
from app.services.executor.variable_renderer import render_template
from app.models.api_definition import ApiDefinition
from app.schemas.api import ApiCreate, ApiUpdate
from app.services.base import BaseService


class ApiService(BaseService):
    async def get(self, api_id: int, project_id: int | None = None) -> ApiDefinition:
        from sqlalchemy import and_

        conditions = [ApiDefinition.id == api_id, ApiDefinition.deleted_at.is_(None)]
        if project_id is not None:
            conditions.append(ApiDefinition.project_id == project_id)
        result = await self.db.execute(select(ApiDefinition).where(and_(*conditions)))
        api = result.scalar_one_or_none()
        if not api:
            self._raise(ErrorCodes.API_NOT_FOUND)
        return api

    async def get_include_deleted(self, api_id: int) -> ApiDefinition:
        """查接口（包括已删除），用于恢复操作"""
        result = await self.db.execute(
            select(ApiDefinition).where(ApiDefinition.id == api_id)
        )
        api = result.scalar_one_or_none()
        if not api:
            self._raise(ErrorCodes.API_NOT_FOUND)
        return api

    def to_dict(self, api: ApiDefinition) -> dict:
        return {
            "id": api.id,
            "project_id": api.project_id,
            "category_id": api.category_id,
            "name": api.name,
            "method": api.method,
            "path": api.path,
            "description": api.description,
            "description_md": api.description_md or "",
            "auth_type": api.auth_type,
            "headers": self._safe_json(api.headers, []),
            "params": self._safe_json(api.params, []),
            "body": self._safe_json(api.body, {"type": "none", "content": ""}),
            "pre_script": api.pre_script or "",
            "post_script": api.post_script or "",
            "cookies": self._safe_json(api.cookies, []),
            "auth": self._safe_json(api.auth, {"type": "none"}),
            "settings": self._safe_json(
                api.settings,
                {"follow_redirects": True, "verify_ssl": True, "timeout": 30},
            ),
            "extract_vars": self._safe_json(api.extract_vars, []),
            "response_schema": api.response_schema or "",
            "response_examples": self._safe_json(api.response_examples, []),
            "is_starred": bool(api.is_starred),
            "sort_order": api.sort_order or 0,
            "created_at": str(api.created_at),
            "updated_at": str(api.updated_at),
            "case_count": 0,
            "tags": [],
        }

    def _safe_json(self, val, default=None):
        """（已弃用）请直接使用 safe_json_load(val, default)，保留此方法仅为向后兼容。"""
        return safe_json_load(val, default)

    async def list(
        self,
        project_id: int,
        category_id: int | None = None,
        page: int = 1,
        page_size: int = 20,
        method: str | None = None,
        status: str | None = None,
        keyword: str | None = None,
        tag: str | None = None,
    ) -> tuple:
        query = select(ApiDefinition).where(
            ApiDefinition.project_id == project_id, ApiDefinition.deleted_at.is_(None)
        )
        count_query = select(func.count(ApiDefinition.id)).where(
            ApiDefinition.project_id == project_id, ApiDefinition.deleted_at.is_(None)
        )
        if category_id is not None:
            query = query.where(ApiDefinition.category_id == category_id)
            count_query = count_query.where(ApiDefinition.category_id == category_id)
        if method:
            query = query.where(ApiDefinition.method == method.upper())
            count_query = count_query.where(ApiDefinition.method == method.upper())
        if status:
            query = query.where(ApiDefinition.status == status)
            count_query = count_query.where(ApiDefinition.status == status)
        if keyword:
            escaped = keyword.replace("%", "\\%").replace("_", "\\_")
            like = f"%{escaped}%"
            query = query.where(
                ApiDefinition.name.like(like) | ApiDefinition.path.like(like)
            )
            count_query = count_query.where(
                ApiDefinition.name.like(like) | ApiDefinition.path.like(like)
            )
        if tag:
            from app.models.api_tag import ApiTag, ApiTagRelation

            tagged_api_ids = (
                select(ApiTagRelation.api_id)
                .join(ApiTag, ApiTag.id == ApiTagRelation.tag_id)
                .where(ApiTag.project_id == project_id, ApiTag.name == tag)
            )
            query = query.where(ApiDefinition.id.in_(tagged_api_ids))
            count_query = count_query.where(ApiDefinition.id.in_(tagged_api_ids))
        total = await self.db.scalar(count_query) or 0
        result = await self.db.execute(
            query.order_by(
                ApiDefinition.is_starred.desc(),
                ApiDefinition.sort_order.asc(),
                ApiDefinition.updated_at.desc(),
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        api_list = result.scalars().all()

        # 批量查询 case_count
        api_ids = [a.id for a in api_list]
        case_count_map: dict[int, int] = {}
        tag_map: dict[int, list[str]] = {}
        if api_ids:
            from app.models.test_case import TestCase

            case_counts = await self.db.execute(
                select(TestCase.api_id, func.count(TestCase.id))
                .where(TestCase.api_id.in_(api_ids))
                .group_by(TestCase.api_id)
            )
            case_count_map = dict(case_counts.all())

            # 批量查询标签
            from app.models.api_tag import ApiTag, ApiTagRelation

            tag_rows = await self.db.execute(
                select(ApiTagRelation.api_id, ApiTag.name)
                .join(ApiTag, ApiTag.id == ApiTagRelation.tag_id)
                .where(ApiTagRelation.api_id.in_(api_ids))
            )
            for api_id_val, tag_name in tag_rows.all():
                tag_map.setdefault(api_id_val, []).append(tag_name)

        items = []
        for api in api_list:
            d = self.to_dict(api)
            d["case_count"] = case_count_map.get(api.id, 0)
            d["tags"] = tag_map.get(api.id, [])
            items.append(d)

        return items, total

    async def create(self, project_id: int, req: ApiCreate) -> ApiDefinition:
        api = ApiDefinition(
            project_id=project_id,
            name=req.name,
            method=req.method,
            path=req.path,
            category_id=req.category_id,
            description=req.description,
            description_md=req.description_md,
            headers=json.dumps(req.headers),
            params=json.dumps(req.params),
            body=json.dumps(req.body),
            auth_type=req.auth_type,
            pre_script=req.pre_script,
            post_script=req.post_script,
            cookies=json.dumps(req.cookies),
            auth=json.dumps(req.auth),
            settings=json.dumps(req.settings),
            extract_vars=json.dumps(req.extract_vars),
            response_examples=json.dumps(req.response_examples)
            if req.response_examples is not None
            else None,
            response_schema=req.response_schema,
            is_starred=req.is_starred,
            sort_order=req.sort_order,
        )
        self.db.add(api)
        await self.db.flush()
        await self.db.refresh(api)
        # 处理标签
        if req.tags:
            await self._sync_tags(api.project_id, api.id, req.tags)
        # 自动落盘快照
        await self._write_snapshot(api, change_type="create", user_id=req.created_by)
        return api

    async def update(
        self, api_id: int, req: ApiUpdate, project_id: int | None = None
    ) -> ApiDefinition:
        api = await self.get(api_id, project_id)

        # 乐观锁：检查版本号（使用完整时间戳，不截断微秒）
        if req.updated_at and api.updated_at:
            if req.updated_at != api.updated_at:
                self._raise(ErrorCodes.CONFLICT, "数据已被其他人修改，请刷新后重试")

        api.name = req.name or api.name
        api.method = req.method or api.method
        api.path = req.path or api.path
        api.category_id = req.category_id
        api.description = req.description
        api.description_md = req.description_md
        api.headers = json.dumps(req.headers)
        api.params = json.dumps(req.params)
        api.body = json.dumps(req.body)
        api.auth_type = req.auth_type
        api.pre_script = req.pre_script
        api.post_script = req.post_script
        api.cookies = json.dumps(req.cookies)
        api.auth = json.dumps(req.auth)
        api.settings = json.dumps(req.settings)
        api.extract_vars = json.dumps(req.extract_vars)
        if req.response_examples is not None:
            api.response_examples = json.dumps(req.response_examples)
        if req.response_schema is not None:
            api.response_schema = req.response_schema
        if req.is_starred is not None:
            api.is_starred = req.is_starred
        if req.sort_order is not None:
            api.sort_order = req.sort_order

        # 唯一性校验：同项目同目录下不允许同名/同路径+方法（排除自身）
        cat_cond = (
            ApiDefinition.category_id == api.category_id
            if api.category_id
            else ApiDefinition.category_id.is_(None)
        )
        # 名称唯一性校验（仅当名称被修改时）
        if req.name:
            name_dup = await self.db.execute(
                select(ApiDefinition).where(
                    ApiDefinition.project_id == api.project_id,
                    cat_cond,
                    ApiDefinition.name == api.name,
                    ApiDefinition.deleted_at.is_(None),
                    ApiDefinition.id != api_id,
                )
            )
            if name_dup.scalar_one_or_none():
                self._raise(ErrorCodes.API_NAME_DUPLICATE, "该目录下已存在同名接口")

        # 路径+方法唯一性校验（仅当路径或方法被修改时）
        if req.path or req.method:
            path_dup = await self.db.execute(
                select(ApiDefinition).where(
                    ApiDefinition.project_id == api.project_id,
                    cat_cond,
                    ApiDefinition.path == api.path,
                    ApiDefinition.method == api.method,
                    ApiDefinition.deleted_at.is_(None),
                    ApiDefinition.id != api_id,
                )
            )
            if path_dup.scalar_one_or_none():
                self._raise(
                    ErrorCodes.API_PATH_DUPLICATE, "该目录下已存在相同路径和方法的接口"
                )

        await self.db.flush()
        await self.db.refresh(api)
        # 处理标签
        if req.tags is not None:
            await self._sync_tags(api.project_id, api.id, req.tags)
        # 自动落盘快照
        await self._write_snapshot(
            api, change_type="update", user_id=getattr(req, "created_by", None)
        )
        return api

    async def _sync_tags(
        self, project_id: int, api_id: int, tag_names: list[str]
    ) -> None:
        """同步接口标签：根据名称列表自动创建不存在的标签并建立关联"""
        from app.models.api_tag import ApiTag, ApiTagRelation

        # 获取项目已有标签
        result = await self.db.execute(
            select(ApiTag).where(ApiTag.project_id == project_id)
        )
        existing_tags = {t.name: t for t in result.scalars().all()}

        # 创建不存在的标签
        for name in tag_names:
            if name not in existing_tags:
                new_tag = ApiTag(project_id=project_id, name=name)
                self.db.add(new_tag)
                await self.db.flush()
                existing_tags[name] = new_tag

        # 清除旧关联
        from sqlalchemy import delete as sa_delete

        await self.db.execute(
            sa_delete(ApiTagRelation).where(ApiTagRelation.api_id == api_id)
        )

        # 建立新关联
        for name in tag_names:
            tag = existing_tags.get(name)
            if tag:
                self.db.add(ApiTagRelation(api_id=api_id, tag_id=tag.id))
        await self.db.flush()

    async def _write_snapshot(
        self,
        api: ApiDefinition,
        change_type: str,
        user_id: int | None = None,
        change_summary: str = "",
    ) -> None:
        """写入一条 ApiSnapshot 记录（内部使用，不抛异常以免影响主流程）。"""
        try:
            from app.models.api_snapshot import ApiSnapshot

            snap = ApiSnapshot(
                api_id=api.id,
                snapshot_data=json.dumps(
                    self.to_dict(api), ensure_ascii=False, default=str
                ),
                change_type=change_type,
                change_summary=change_summary,
                changed_by=user_id,
            )
            self.db.add(snap)
            await self.db.flush()
        except Exception as exc:
            self.logger.warning(
                "写入 api 快照失败（不影响主流程）: %s: %s", type(exc).__name__, exc
            )

    async def delete(self, api_id: int, project_id: int | None = None):
        """软删除：标记 deleted_at 而非物理删除"""
        from datetime import datetime

        api = await self.get(api_id, project_id)
        api.deleted_at = datetime.now(UTC)
        await self.db.flush()

    async def list_deleted(self, project_id: int) -> list:
        """列出已删除的接口"""
        from sqlalchemy import select

        result = await self.db.execute(
            select(ApiDefinition)
            .where(
                ApiDefinition.project_id == project_id,
                ApiDefinition.deleted_at.isnot(None),
            )
            .order_by(ApiDefinition.deleted_at.desc())
        )
        items = []
        for api in result.scalars().all():
            d = self.to_dict(api)
            d["deleted_at"] = str(api.deleted_at) if api.deleted_at else None
            items.append(d)
        return items

    async def restore(self, api_id: int, project_id: int):
        """恢复软删除的接口，同时恢复关联的测试用例"""
        api = await self.get_include_deleted(api_id)
        if api.project_id != project_id:
            self._raise(ErrorCodes.PROJECT_FORBIDDEN, "资源不属于该项目")
        if api.deleted_at is None:
            return  # already restored

        # 检查分类是否仍存在（未删除）
        parent_exists = True
        if api.category_id:
            from app.models.api_category import ApiCategory

            cat_result = await self.db.execute(
                select(ApiCategory).where(ApiCategory.id == api.category_id)
            )
            cat = cat_result.scalar_one_or_none()
            if not cat:
                parent_exists = False
                # 分类不存在时，将接口移至根级（清除 category_id）
                api.category_id = None

        api.deleted_at = None

        # 同时恢复关联的已删除测试用例
        from app.models.test_case import TestCase

        case_result = await self.db.execute(
            select(TestCase).where(
                TestCase.api_id == api_id,
                TestCase.deleted_at.isnot(None),
            )
        )
        restored_cases = 0
        for case in case_result.scalars().all():
            case.deleted_at = None
            restored_cases += 1

        await self.db.flush()
        return {"parent_exists": parent_exists, "restored_cases": restored_cases}

    async def permanent_delete(self, api_id: int, project_id: int):
        """永久物理删除"""
        api = await self.get_include_deleted(api_id)
        if api.project_id != project_id:
            self._raise(ErrorCodes.PROJECT_FORBIDDEN, "资源不属于该项目")
        await self.db.delete(api)
        await self.db.flush()

    async def duplicate(self, api_id: int) -> ApiDefinition:
        api = await self.get(api_id)
        new = ApiDefinition(
            project_id=api.project_id,
            name=api.name + "_副本",
            method=api.method,
            path=api.path,
            category_id=api.category_id,
            description=api.description,
            headers=api.headers,
            params=api.params,
            body=api.body,
            auth_type=api.auth_type,
            response_examples=api.response_examples,
            response_schema=api.response_schema,
            pre_script=api.pre_script,
            post_script=api.post_script,
            cookies=api.cookies,
            auth=api.auth,
            settings=api.settings,
            extract_vars=api.extract_vars,
        )
        # 重复检测：同项目下相同 method+path 已存在时追加时间戳
        dup_check = await self.db.execute(
            select(ApiDefinition).where(
                ApiDefinition.project_id == api.project_id,
                ApiDefinition.method == api.method,
                ApiDefinition.path == api.path,
                ApiDefinition.deleted_at.is_(None),
            )
        )
        if dup_check.scalar_one_or_none():
            new.name = f"{api.name}_副本_{int(datetime.now().timestamp())}"
        self.db.add(new)
        await self.db.flush()
        await self.db.refresh(new)

        # 同步复制原 API 的标签
        from app.models.api_tag import ApiTag, ApiTagRelation

        tag_result = await self.db.execute(
            select(ApiTag.name)
            .join(ApiTagRelation, ApiTagRelation.tag_id == ApiTag.id)
            .where(ApiTagRelation.api_id == api_id)
        )
        original_tags = [row[0] for row in tag_result.all()]
        if original_tags:
            await self._sync_tags(api.project_id, new.id, original_tags)

        return new

    async def move(self, api_id: int, category_id: int | None):
        api = await self.get(api_id)
        api.category_id = category_id
        await self.db.flush()

    async def test_api(
        self,
        api_id: int,
        env_id: int,
        overrides: dict = None,
        extract_vars: list = None,
    ) -> dict:
        """在线调试：发送 HTTP 请求并返回完整请求/响应信息"""
        import httpx
        import time

        api = await self.get(api_id)
        from app.models.environment import Environment

        result = await self.db.execute(
            select(Environment).where(Environment.id == env_id)
        )
        env = result.scalar_one_or_none()
        base_url = ""
        variables = {}
        global_headers_extra: list = []

        # 加载项目全局变量（环境变量会覆盖同名全局变量）
        try:
            from app.models.project import Project

            proj_result = await self.db.execute(
                select(Project).where(Project.id == api.project_id)
            )
            proj = proj_result.scalar_one_or_none()
            if proj:
                gv_raw = proj.global_variables
                if gv_raw:
                    gv_list = self._safe_json(gv_raw, [])
                    for v in gv_list:
                        if (
                            isinstance(v, dict)
                            and v.get("key")
                            and v.get("enabled", True)
                        ):
                            variables[v["key"]] = v.get("value", "")
                # 全局公共 Headers
                gp_raw = proj.global_params
                if gp_raw:
                    gp = self._safe_json(gp_raw, {})
                    if isinstance(gp, dict):
                        for h in gp.get("headers", []):
                            if (
                                isinstance(h, dict)
                                and h.get("key")
                                and h.get("enabled", True)
                            ):
                                global_headers_extra.append(h)
        except (ValueError, KeyError, TypeError) as e:
            self.logger.warning("全局请求头解析失败: %s: %s", type(e).__name__, e)

        headers_list = self._safe_json(api.headers, []) + global_headers_extra
        if env:
            services = self._safe_json(env.services, [])
            raw_base_url = services[0].get("url", "") if services else ""
            base_url = render_template(raw_base_url, variables) if raw_base_url else ""
            env_headers = self._safe_json(env.headers, [])
            for h in env_headers:
                if isinstance(h, dict) and h.get("key"):
                    headers_list.append(h)
            env_vars = self._safe_json(env.variables, [])
            for v in env_vars:
                if isinstance(v, dict) and v.get("key"):
                    variables[v["key"]] = v.get("value", "")

        ov = overrides or {}
        # 优先使用 overrides 中的 base_url
        if ov.get("base_url"):
            base_url = render_template(ov["base_url"], variables)
        # 未保存发送：前端传入完整字段时，替换 DB 中的数据
        if ov.get("method"):
            api_method = ov["method"]
        else:
            api_method = api.method
        if ov.get("path") is not None:
            api_path = ov["path"]
        else:
            api_path = api.path
        if "method" in ov and isinstance(ov.get("headers"), list):
            # 完整替换模式（前端传了完整 apiData）
            headers_list = ov["headers"]
        else:
            for h in ov.get("headers", []):
                headers_list.append(h)
        if isinstance(ov.get("params"), list):
            params_list = ov["params"]
        else:
            params_list = self._safe_json(api.params, [])
        body_override = ov.get("body")
        req_body = self._safe_json(api.body, {"type": "none", "content": ""})
        if body_override:
            if isinstance(body_override, str):
                import json as _json

                try:
                    req_body = _json.loads(body_override)
                except (_json.JSONDecodeError, TypeError) as e:
                    self.logger.warning(
                        "请求体重写JSON解析失败: %s: %s", type(e).__name__, e
                    )
            else:
                req_body = body_override

        headers = {}
        for h in headers_list:
            if isinstance(h, dict) and h.get("key") and h.get("enabled", True):
                key = render_template(h["key"], variables)
                value = render_template(h.get("value", ""), variables)
                if key and value:
                    headers[key] = value

        query_params = {}
        for p in params_list:
            if isinstance(p, dict) and p.get("key") and p.get("enabled", True):
                key = render_template(p["key"], variables)
                value = render_template(p.get("value", ""), variables)
                if key and value:
                    query_params[key] = value

        path = render_template(api_path, variables)
        url = f"{base_url}{path}"
        # SSRF 防护：校验 URL 安全性
        try:
            await validate_request_url(url)
        except ValueError as e:
            result = {
                "request_url": url,
                "request_method": api_method,
                "request_body": "",
                "response_status": 0,
                "request_headers": {},
                "response_headers": {},
                "response_body": "",
                "error": str(e),
                "duration": 0,
            }
            await self._save_debug_history(api, url, api_method, headers, "", result, 0)
            return result
        method = api_method
        body_content = req_body.get("content", "") if isinstance(req_body, dict) else ""

        # 执行前置操作（可修改请求参数）
        pre_script = ov.get("pre_script") or api.pre_script or ""
        if pre_script.strip():
            from app.services.executor.script_executor import execute_pre_script

            pre_result = await execute_pre_script(
                pre_script,
                api_method,
                api_path,
                headers_list,
                params_list,
                req_body,
                {"type": "none"},
                variables,
            )
            if pre_result:
                api_method = pre_result.get("method", api_method)
                api_path = pre_result.get("path", api_path)
                headers_list = pre_result.get("headers", headers_list)
                params_list = pre_result.get("params", params_list)
                req_body = pre_result.get("body", req_body)
                body_content = (
                    req_body.get("content", "") if isinstance(req_body, dict) else ""
                )

        # 读取 API 设置
        if isinstance(ov.get("settings"), dict):
            api_settings = ov["settings"]
        else:
            api_settings = self._safe_json(api.settings, {})
        follow_redirects = api_settings.get("follow_redirects", True)
        verify_ssl = api_settings.get("verify_ssl", True)
        timeout = api_settings.get("timeout", 30)

        start = time.time()
        try:
            async with httpx.AsyncClient(timeout=timeout, verify=verify_ssl) as client:
                resp = await client.request(
                    method=method,
                    url=url,
                    headers=headers or None,
                    params=query_params or None,
                    content=body_content
                    if method in ("POST", "PUT", "PATCH")
                    else None,
                    follow_redirects=follow_redirects,
                )
            duration = time.time() - start
            result = {
                "request_url": str(resp.url),
                "request_method": method,
                "request_headers": dict(resp.request.headers),
                "request_body": body_content,
                "response_status": resp.status_code,
                "response_headers": dict(resp.headers),
                "response_body": resp.text,
                "duration": round(duration, 3),
            }
        except httpx.HTTPError as e:
            duration = time.time() - start
            result = {
                "request_url": url,
                "request_method": method,
                "request_body": body_content,
                "response_status": 0,
                "request_headers": {},
                "response_body": "",
                "error": f"{type(e).__name__}: {e}",
                "duration": round(duration, 3),
            }
        await self._save_debug_history(
            api, url, method, headers, body_content, result, duration
        )
        # 执行后置操作
        post_script = ov.get("post_script") or api.post_script or ""
        if post_script.strip():
            from app.services.executor.script_executor import execute_post_script

            script_vars = await execute_post_script(
                post_script,
                result,
                variables,
            )
            if script_vars:
                # 将脚本提取的变量更新到环境变量
                try:
                    from app.models.environment import Environment

                    env_result = await self.db.execute(
                        select(Environment).where(Environment.id == env_id)
                    )
                    script_env = env_result.scalar_one_or_none()
                    if script_env:
                        existing = self._safe_json(script_env.variables, [])
                        # 更新/新增
                        existing_keys = {
                            v.get("key"): i
                            for i, v in enumerate(existing)
                            if v.get("key")
                        }
                        for k, v in script_vars.items():
                            if k in existing_keys:
                                existing[existing_keys[k]]["value"] = str(v)
                            else:
                                existing.append(
                                    {"key": k, "value": str(v), "enabled": True}
                                )
                        script_env.variables = json.dumps(existing)
                        await (
                            self.db.flush()
                        )  # flush 即可，事务由 FastAPI get_db 依赖统一 commit
                except (ValueError, KeyError, TypeError) as e:
                    self.logger.warning("局部变量更新失败: %s: %s", type(e).__name__, e)
                # 也更新全局变量
                try:
                    from app.models.project import Project

                    proj_result2 = await self.db.execute(
                        select(Project).where(Project.id == api.project_id)
                    )
                    script_proj = proj_result2.scalar_one_or_none()
                    if script_proj:
                        gv = self._safe_json(script_proj.global_variables, [])
                        gv_keys = {
                            v.get("key"): i for i, v in enumerate(gv) if v.get("key")
                        }
                        for k, v in script_vars.items():
                            if k in gv_keys:
                                gv[gv_keys[k]]["value"] = str(v)
                            else:
                                gv.append({"key": k, "value": str(v), "enabled": True})
                        script_proj.global_variables = json.dumps(gv)
                        await (
                            self.db.flush()
                        )  # flush 即可，事务由 FastAPI get_db 依赖统一 commit
                except (ValueError, KeyError, TypeError) as e:
                    self.logger.warning("全局变量更新失败: %s: %s", type(e).__name__, e)
        # 自动提取变量
        extracted = self._extract_variables(extract_vars or [], result, env)
        if extracted:
            result["extracted_vars"] = extracted

        return result

    def _extract_variables(self, rules: list, result: dict, env) -> dict:
        """根据提取规则从响应中提取变量，并更新到环境变量"""
        if not rules:
            return {}
        import json as _json
        from app.services.executor.assertion_engine import jsonpath_get

        response_body_raw = result.get("response_body", "")
        response_headers = result.get("response_headers", {})

        # 解析响应体
        response_body = response_body_raw
        if isinstance(response_body_raw, str):
            try:
                response_body = _json.loads(response_body_raw)
            except (_json.JSONDecodeError, TypeError) as e:
                self.logger.warning(
                    "响应体JSON解析失败，使用原始文本: %s: %s", type(e).__name__, e
                )
                response_body = response_body_raw

        extracted = {}
        need_update_env = False

        for rule in rules:
            if not isinstance(rule, dict):
                continue
            variable = rule.get("variable") or rule.get("var_name", "")
            if not variable:
                continue
            source = rule.get("source", "body")
            expression = rule.get("expression") or rule.get("path", "")
            rule_type = rule.get("type", "jsonpath")
            val = None

            if source == "header":
                if expression:
                    val = response_headers.get(expression)
            elif source == "status":
                val = str(result.get("response_status", ""))
            else:
                # body
                if rule_type == "regex" and expression:
                    import re

                    match = re.search(expression, str(response_body_raw))
                    if match:
                        try:
                            val = match.group(1)
                        except IndexError:
                            val = match.group(0)
                elif expression:
                    val = jsonpath_get(response_body, expression)
                    if val is not None and not isinstance(val, str):
                        val = _json.dumps(val, ensure_ascii=False)

            if val is not None:
                val = str(val)
                extracted[variable] = val
                # 更新环境变量
                if env:
                    env_vars = self._safe_json(env.variables, [])
                    found = False
                    for v in env_vars:
                        if isinstance(v, dict) and v.get("key") == variable:
                            v["value"] = val
                            found = True
                            break
                    if not found:
                        env_vars.append(
                            {"key": variable, "value": val, "enabled": True}
                        )
                    env.variables = _json.dumps(env_vars, ensure_ascii=False)
                    need_update_env = True

        if need_update_env:
            try:
                self.db.flush()
            except (OSError, ValueError) as e:
                self.logger.warning("变量提取保存失败: %s: %s", type(e).__name__, e)

        return extracted

    async def batch_move(self, api_ids, target_category_id, project_id):
        from app.core.exceptions import BizError

        moved = 0
        for aid in api_ids:
            try:
                api = await self.get(aid)
                if api.project_id == project_id:
                    api.category_id = target_category_id
                    moved += 1
            except (BizError, Exception) as e:
                self.logger.warning("batch_move: 跳过 API %s: %s", aid, e)
                continue
        if moved:
            await self.db.flush()
        return moved

    async def batch_copy(self, api_ids, target_category_id, project_id):
        from app.core.exceptions import BizError

        copied = 0
        for aid in api_ids:
            try:
                api = await self.get(aid)
                if api.project_id == project_id:
                    new = ApiDefinition(
                        project_id=api.project_id,
                        name=api.name + "_copy",
                        method=api.method,
                        path=api.path,
                        category_id=target_category_id,
                        description=api.description,
                        headers=api.headers,
                        params=api.params,
                        body=api.body,
                        auth_type=api.auth_type,
                        response_examples=api.response_examples,
                        response_schema=api.response_schema,
                        pre_script=api.pre_script,
                        post_script=api.post_script,
                        cookies=api.cookies,
                        auth=api.auth,
                        settings=api.settings,
                    )
                    self.db.add(new)
                    copied += 1
            except (BizError, Exception) as e:
                self.logger.warning("batch_copy: 跳过 API %s: %s", aid, e)
                continue
        if copied:
            await self.db.flush()
        return copied

    async def _save_debug_history(
        self,
        api,
        url: str,
        method: str,
        headers: dict,
        body_content: str,
        result: dict,
        duration: float,
    ):
        """保存调试请求历史"""
        try:
            from app.services.debug_history_service import DebugHistoryService
            import json

            req_headers_json = json.dumps(
                [{"key": k, "value": v} for k, v in headers.items()], ensure_ascii=False
            )
            resp_headers_json = json.dumps(
                [
                    {"key": k, "value": v}
                    for k, v in result.get("response_headers", {}).items()
                ],
                ensure_ascii=False,
            )
            svc = DebugHistoryService(self.db)
            await svc.create(
                project_id=api.project_id,
                api_id=api.id,
                url=url,
                method=method,
                duration_ms=int(duration * 1000),
                request_headers=req_headers_json,
                request_body=body_content,
                response_status=result.get("response_status"),
                response_headers=resp_headers_json,
                response_body=result.get("response_body", ""),
            )
        except (OSError, ValueError) as e:
            self.logger.warning("调试历史保存失败: %s: %s", type(e).__name__, e)

    async def _save_test_history(
        self,
        api,
        env_id: int,
        user_id: int | None,
        url: str,
        method: str,
        headers: dict,
        body_content: str,
        result: dict,
        duration: float,
    ):
        """保存接口测试历史记录"""
        try:
            import json
            from app.models.api_test_history import ApiTestHistory

            # 确定测试状态
            status = "unknown"
            if result.get("error"):
                status = "error"
            elif result.get("response_status", 0) >= 400:
                status = "failed"
            elif result.get("response_status", 0) > 0:
                status = "success"

            # 序列化请求/响应数据
            req_headers_json = json.dumps(
                [{"key": k, "value": v} for k, v in headers.items()], ensure_ascii=False
            )
            resp_headers_json = json.dumps(
                [
                    {"key": k, "value": v}
                    for k, v in result.get("response_headers", {}).items()
                ],
                ensure_ascii=False,
            )

            history = ApiTestHistory(
                project_id=api.project_id,
                api_id=api.id,
                environment_id=env_id,
                executor_id=user_id,
                request_url=url,
                request_method=method,
                request_headers=req_headers_json,
                request_body=body_content,
                response_status=result.get("response_status", 0),
                response_headers=resp_headers_json,
                response_body=result.get("response_body", ""),
                duration=duration,
                error=result.get("error"),
                status=status,
            )
            self.db.add(history)
            await self.db.flush()
            self.logger.info(
                "接口测试历史已保存: api_id=%s, status=%s, duration=%.3fs",
                api.id,
                status,
                duration,
            )
        except (OSError, ValueError) as e:
            self.logger.warning("保存接口测试历史失败: %s: %s", type(e).__name__, e)
