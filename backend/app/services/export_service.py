from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.api_definition import ApiDefinition
from app.models.api_category import ApiCategory
import json


class ExportService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def export_postman(self, project_id: int) -> dict:
        """导出 Postman Collection v2.1（完整版：含 headers/body/params/auth）"""
        import json as _json

        categories = await self.db.execute(
            select(ApiCategory).where(
                ApiCategory.project_id == project_id
            ).order_by(ApiCategory.sort_order))
        items = []
        for cat in categories.scalars().all():
            apis = await self.db.execute(
                select(ApiDefinition).where(
                    ApiDefinition.project_id == project_id,
                    ApiDefinition.category_id == cat.id,
                    ApiDefinition.deleted_at.is_(None)))
            api_items = []
            for api in apis.scalars().all():
                # 解析 headers
                headers = []
                raw_headers = _json.loads(api.headers) if api.headers else []
                for h in raw_headers:
                    if isinstance(h, dict) and h.get("enabled", True):
                        headers.append({
                            "key": h.get("key", ""),
                            "value": h.get("value", ""),
                        })

                # 解析 params → Postman query params
                query_params = []
                raw_params = _json.loads(api.params) if api.params else []
                for p in raw_params:
                    if isinstance(p, dict) and p.get("enabled", True):
                        query_params.append({
                            "key": p.get("key", ""),
                            "value": p.get("value", ""),
                        })

                # 构建 URL
                path = api.path or "/"
                url_obj = {
                    "raw": path,
                    "path": [seg for seg in path.split("/") if seg],
                }
                if query_params:
                    url_obj["query"] = query_params

                # 解析 body
                body = None
                raw_body = _json.loads(api.body) if api.body else {}
                if isinstance(raw_body, dict) and raw_body.get("type") != "none":
                    body_type = raw_body.get("type", "raw")
                    body_content = raw_body.get("content", "")
                    if body_type == "json":
                        body = {"mode": "raw", "raw": body_content}
                    elif body_type in ("form-urlencoded", "form-data"):
                        try:
                            form_items = _json.loads(body_content) if isinstance(body_content, str) else body_content
                        except Exception:
                            form_items = []
                        if isinstance(form_items, list):
                            body = {
                                "mode": "urlencoded" if body_type == "form-urlencoded" else "formdata",
                                body_type: [{"key": f.get("key", ""), "value": f.get("value", ""), "enabled": f.get("enabled", True)} for f in form_items],
                            }
                        else:
                            body = {"mode": "raw", "raw": body_content}
                    else:
                        body = {"mode": "raw", "raw": body_content}

                request = {
                    "method": api.method,
                    "header": headers,
                    "url": url_obj,
                }
                if body:
                    request["body"] = body

                api_items.append({"name": api.name, "request": request})

            items.append({"name": cat.name, "item": api_items})

        collection = {
            "info": {
                "name": "API Pilot Export",
                "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
            },
            "item": items,
        }
        return collection

    async def export_pilot(self, project_id: int) -> dict:
        """导出 API Pilot 项目为标准格式"""
        import json as _json

        # 获取分类
        cat_result = await self.db.execute(
            select(ApiCategory).where(
                ApiCategory.project_id == project_id
            ).order_by(ApiCategory.sort_order))
        categories = cat_result.scalars().all()

        # 获取 API 定义
        api_result = await self.db.execute(
            select(ApiDefinition).where(
                ApiDefinition.project_id == project_id, ApiDefinition.deleted_at.is_(None))
            .order_by(ApiDefinition.category_id, ApiDefinition.id))
        apis = api_result.scalars().all()

        # ? category_id ??
        apis_by_cat: dict[int, list] = {}
        for api in apis:
            if api.category_id:
                apis_by_cat.setdefault(api.category_id, []).append(api)

        # 构建分类树
        def build_cat(cat):
            cat_apis = apis_by_cat.get(cat.id, [])
            return {
                "id": cat.id,
                "name": cat.name,
                "parent_id": cat.parent_id,
                "sort_order": cat.sort_order,
                "apis": [{
                    "id": api.id,
                    "name": api.name,
                    "method": api.method,
                    "path": api.path,
                    "description": api.description or "",
                    "headers": _json.loads(api.headers) if api.headers else [],
                    "params": _json.loads(api.params) if api.params else [],
                    "body": _json.loads(api.body) if api.body else {"type": "none", "content": ""},
                    "auth_type": api.auth_type or "none",
                    "response_schema": _json.loads(api.response_schema) if api.response_schema else None,
                    "response_examples": _json.loads(api.response_examples) if api.response_examples else None,
                } for api in cat_apis],
            }

        tree = [build_cat(c) for c in categories]

        return {
            "format": "api_pilot",
            "version": "1.0",
            "project": {"name": "API Pilot Export"},
            "categories": tree,
        }

    async def export_single_api(self, api_id: int, project_id: int, format: str = "apifox") -> dict:
        """导出单个接口为指定格式

        Args:
            api_id: 接口ID
            project_id: 项目ID
            format: 导出格式 (apifox/openapi/postman/curl)

        Returns:
            指定格式的接口数据
        """
        """导出单个接口为指定格式

        Args:
            api_id: 接口ID
            project_id: 项目ID
            format: 导出格式 (apifox/openapi/postman)

        Returns:
            指定格式的接口数据
        """
        # 查询接口
        result = await self.db.execute(
            select(ApiDefinition).where(
                ApiDefinition.id == api_id,
                ApiDefinition.project_id == project_id,
                ApiDefinition.deleted_at.is_(None)
            )
        )
        api = result.scalar_one_or_none()
        if not api:
            raise ValueError(f"接口 {api_id} 不存在")

        # 查询分类
        category_name = ""
        if api.category_id:
            cat_result = await self.db.execute(
                select(ApiCategory).where(ApiCategory.id == api.category_id)
            )
            cat = cat_result.scalar_one_or_none()
            if cat:
                category_name = cat.name

        # 构建基础接口数据
        api_data = {
            "name": api.name,
            "method": api.method,
            "path": api.path,
            "description": api.description or "",
            "headers": json.loads(api.headers) if api.headers else [],
            "params": json.loads(api.params) if api.params else [],
            "body": json.loads(api.body) if api.body else {"type": "none", "content": ""},
            "auth_type": api.auth_type or "none",
            "response_schema": json.loads(api.response_schema) if api.response_schema else None,
            "response_examples": json.loads(api.response_examples) if api.response_examples else None,
        }

        # 根据格式转换
        if format == "apifox":
            return self._to_apifox(api_data, category_name)
        elif format == "openapi":
            return self._to_openapi(api_data, category_name, project_id)
        elif format == "postman":
            return self._to_postman(api_data, category_name)
        elif format == "curl":
            return self._to_curl(api_data)
        else:
            raise ValueError(f"不支持的格式: {format}")

    def _to_apifox(self, api: dict, category_name: str) -> dict:
        """转换为 Apifox 格式"""
        return {
            "type": "api",
            "name": api["name"],
            "method": api["method"],
            "path": api["path"],
            "description": api["description"],
            "category": category_name,
            "headers": api["headers"],
            "params": api["params"],
            "body": api["body"],
            "auth_type": api["auth_type"],
            "response_schema": api["response_schema"],
            "response_examples": api["response_examples"],
        }

    def _to_openapi(self, api: dict, category_name: str, project_id: int) -> dict:
        """转换为 OpenAPI 3.0 格式"""
        # 解析路径参数
        path = api["path"]
        parameters = []
        # 提取路径中的 {param} 参数
        import re
        path_params = re.findall(r'\{(\w+)\}', path)
        for param in path_params:
            parameters.append({
                "name": param,
                "in": "path",
                "required": True,
                "schema": {"type": "string"},
            })

        # 添加查询参数
        if api["params"]:
            for p in api["params"]:
                if p.get("enabled", True):
                    parameters.append({
                        "name": p["key"],
                        "in": "query",
                        "required": False,
                        "schema": {"type": "string"},
                    })

        # 请求体
        request_body = None
        if api["body"]["type"] != "none" and api["body"]["content"]:
            body_content = api["body"]["content"]
            try:
                schema = json.loads(body_content) if isinstance(body_content, str) else body_content
            except Exception:
                schema = {"type": "string"}
            request_body = {
                "content": {
                    "application/json": {
                        "schema": schema,
                    }
                }
            }

        return {
            "openapi": "3.0.0",
            "info": {
                "title": api["name"],
                "version": "1.0.0",
            },
            "paths": {
                path: {
                    api["method"].lower(): {
                        "summary": api["name"],
                        "description": api["description"],
                        "parameters": parameters,
                        "requestBody": request_body,
                        "responses": {
                            "200": {
                                "description": "成功",
                            }
                        },
                        "tags": [category_name] if category_name else [],
                    }
                }
            },
        }

    async def export_openapi(self, project_id: int) -> dict:
        """导出整个项目为 OpenAPI 3.0 规范"""
        import re

        # 获取分类
        cat_result = await self.db.execute(
            select(ApiCategory).where(
                ApiCategory.project_id == project_id
            ).order_by(ApiCategory.sort_order))
        categories = cat_result.scalars().all()

        # 获取所有 API
        api_result = await self.db.execute(
            select(ApiDefinition).where(
                ApiDefinition.project_id == project_id, ApiDefinition.deleted_at.is_(None))
            .order_by(ApiDefinition.category_id, ApiDefinition.id))
        all_apis = api_result.scalars().all()

        # 构建分类映射
        cat_map = {c.id: c.name for c in categories}
        {c.id for c in categories}

        # 路径参数正则
        path_param_re = re.compile(r'\{(\w+)\}')

        paths = {}
        tags = list(cat_map.values())  # 分类名作为 OpenAPI tags

        for api in all_apis:
            path = api.path or "/"
            method = api.method.lower()
            if method not in ("get", "post", "put", "delete", "patch", "head", "options"):
                continue

            parameters = []

            # 路径参数
            for param in path_param_re.findall(path):
                parameters.append({
                    "name": param,
                    "in": "path",
                    "required": True,
                    "schema": {"type": "string"},
                    "description": "",
                })

            # 查询参数
            raw_params = json.loads(api.params) if api.params else []
            for p in raw_params:
                if isinstance(p, dict) and p.get("enabled", True):
                    parameters.append({
                        "name": p.get("key", ""),
                        "in": "query",
                        "required": p.get("required", False),
                        "schema": {"type": "string"},
                        "description": p.get("description", ""),
                    })

            # 请求头
            raw_headers = json.loads(api.headers) if api.headers else []
            for h in raw_headers:
                if isinstance(h, dict) and h.get("enabled", True):
                    parameters.append({
                        "name": h.get("key", ""),
                        "in": "header",
                        "required": h.get("required", False),
                        "schema": {"type": "string"},
                        "description": h.get("description", ""),
                    })

            # 请求体
            request_body = None
            raw_body = json.loads(api.body) if api.body else {}
            if isinstance(raw_body, dict) and raw_body.get("type") != "none" and raw_body.get("content"):
                content = raw_body["content"]
                schema = None
                try:
                    parsed = json.loads(content) if isinstance(content, str) else content
                    schema = {"type": "object", "example": parsed} if isinstance(parsed, dict) else parsed
                except Exception:
                    schema = {"type": "string", "example": content}

                content_type = raw_body.get("content_type", "application/json")
                request_body = {
                    "content": {content_type: {"schema": schema if schema else {"type": "string"}}},
                    "description": "",
                }

            # 响应
            responses = {"200": {"description": "成功"}}
            raw_resp = json.loads(api.response_schema) if api.response_schema else None
            if raw_resp and isinstance(raw_resp, dict):
                responses["200"] = {
                    "description": "成功",
                    "content": {
                        "application/json": {
                            "schema": raw_resp.get("schema") or raw_resp,
                        }
                    },
                }

            # 分类 tag
            api_tags = []
            if api.category_id and api.category_id in cat_map:
                api_tags.append(cat_map[api.category_id])

            # 构造 path item
            if path not in paths:
                paths[path] = {}

            paths[path][method] = {
                "summary": api.name,
                "description": api.description or "",
                "tags": api_tags or ["未分类"],
                "parameters": parameters or [],
                "requestBody": request_body,
                "responses": responses,
            }

        return {
            "openapi": "3.0.3",
            "info": {
                "title": "API Pilot Export",
                "version": "1.0.0",
                "description": f"从 API Pilot 项目导出，共 {len(all_apis)} 个接口",
            },
            "servers": [{"url": "/", "description": "API Server"}],
            "tags": [{"name": t, "description": ""} for t in tags],
            "paths": paths,
        }

    async def export_environments(self, project_id: int) -> dict:
        """导出项目环境变量为独立 JSON"""
        from app.models.environment import Environment as EnvModel

        env_result = await self.db.execute(
            select(EnvModel).where(EnvModel.project_id == project_id))
        environments = []
        for env in env_result.scalars().all():
            environments.append({
                "name": env.name,
                "services": json.loads(env.services) if env.services else [],
                "variables": json.loads(env.variables) if env.variables else [],
                "headers": json.loads(env.headers) if env.headers else [],
            })
        return {
            "format": "api_pilot_env",
            "version": "1.0",
            "project_id": project_id,
            "environments": environments,
        }

    def _to_curl(self, api: dict) -> str:
        """转换为 cURL 命令字符串"""
        parts = ["curl"]
        method = api.get("method", "GET")
        path = api.get("path", "/")
        headers = api.get("headers", [])
        body = api.get("body", {})
        params = api.get("params", [])

        # 拼接 query params
        if params:
            qs = "&".join(f"{p['key']}={p['value']}" for p in params if p.get("enabled", True))
            if qs:
                path = f"{path}?{qs}" if "?" not in path else f"{path}&{qs}"

        # URL（先放，方便阅读）
        parts.append(f"'{path}'")

        # Method（非 GET 才加 -X）
        if method != "GET":
            parts.insert(1, "-X")
            parts.insert(2, method)

        # Headers
        for h in headers:
            if h.get("enabled", True):
                parts.append(f"-H '{h.get('key', '')}: {h.get('value', '')}'")

        # Body
        if body and body.get("type") != "none" and body.get("content"):
            content = body["content"]
            # 尝试用单引号包裹（避免转义）
            parts.append(f"-d '{content}'")

        return " \\\n  ".join(parts)

    def _to_postman(self, api: dict, category_name: str) -> dict:
        """转换为 Postman 格式"""
        # 构建 URL
        url_raw = api["path"]
        path_segments = [seg for seg in url_raw.split("/") if seg]

        # 构建请求头
        headers = []
        if api["headers"]:
            for h in api["headers"]:
                if h.get("enabled", True):
                    headers.append({
                        "key": h.get("key", ""),
                        "value": h.get("value", ""),
                    })

        # 构建请求体
        body = None
        if api["body"]["type"] != "none" and api["body"]["content"]:
            if api["body"]["type"] == "json":
                body = {
                    "mode": "raw",
                    "raw": api["body"]["content"],
                }
            elif api["body"]["type"] in ("form-urlencoded", "form-data"):
                body = {
                    "mode": api["body"]["type"],
                }

        return {
            "info": {
                "name": api["name"],
                "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
            },
            "item": [{
                "name": api["name"],
                "request": {
                    "method": api["method"],
                    "header": headers,
                    "url": {
                        "raw": url_raw,
                        "host": url_raw.split("/"),
                        "path": path_segments,
                    },
                    "body": body,
                },
            }],
            "variable": [],
        }
