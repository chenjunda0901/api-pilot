"""
统一导入引擎 - 支持多种 JSON 格式的接口数据导入。

支持的格式:
  - Apifox 项目导出 (完整: apifoxProject 1.0.0)
  - Apifox 接口导出 (单接口/json/collection)
  - Postman Collection v2.0 / v2.1
  - OpenAPI / Swagger 2.0 / 3.0

核心特性:
  - 自动格式检测，无需手动指定
  - 完整字段映射: headers/params/body/auth/scripts/settings/cookies
  - 变量引用 ({{var}}) 原样保留，不做注入拒绝
  - 测试用例导入 (Apifox → API Pilot TestCase)
  - Schema 导入 (JSON Schema 作为响应体结构)
  - 多策略冲突处理: update / skip / rename / keep-both
  - 异常隔离：单条失败不中断整个批次
  - 全事务保护：全部成功或全部回滚
"""

import json
import logging
import time
import yaml
from typing import Any
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import raise_biz, ErrorCodes
from app.models.api_category import ApiCategory
from app.models.api_definition import ApiDefinition
from app.models.environment import Environment
from app.models.project import Project
from app.models.test_case import TestCase

# 从格式解析模块导入
from app.services.format_parsers import (
    ImportFormat,
    MAX_FILE_SIZE,
    detect_format,
    _parse_apifox_servers,
    _parse_apifox_environments,
    _parse_apifox_global_vars,
    _parse_apifox_common_params,
    _walk_apifox_testcases,
    _walk_apifox_collection,
    _parse_apifox_api,
    _parse_apifox_request_collection,
    _parse_apifox_testcase_apis,
    _parse_postman_collection,
    _parse_yapi,
    _parse_eolink,
    _parse_apipost,
    _parse_bruno,
    _parse_curl,
    _parse_general_json,
)
from app.services.importers.openapi_importer import parse_openapi_3
from app.services.importers.swagger2_importer import parse_swagger2
from app.services.importers.har_importer import parse_har as parse_har_enhanced

logger = logging.getLogger("import.uni")


def _strip_bom(text: str) -> str:
    """去除 UTF-8 BOM 头 (U+FEFF)"""
    if text and text[0] == '\ufeff':
        return text[1:]
    return text


def _safe_json_list(val: Any) -> list:
    """安全解析可能为 JSON 字符串或已解析 list 的值"""
    if isinstance(val, list):
        return val
    if isinstance(val, str) and val.strip():
        try:
            result = json.loads(val)
            if isinstance(result, list):
                return result
        except (json.JSONDecodeError, ValueError):
            pass
    return []


def _parse_json_or_yaml(content: str) -> dict:
    """尝试 JSON 解析，失败后尝试 YAML 解析。

    兼容 Apifox / Postman / OpenAPI 等多种导出格式。
    """
    content = _strip_bom(content.strip())
    if not content:
        raise ValueError("文件内容为空")

    # 先尝试 JSON（大多数导出格式都是 JSON）
    try:
        data = json.loads(content)
        if isinstance(data, dict):
            return data
        if isinstance(data, list):
            # 数组格式的 JSON，包装为通用格式
            return {"_raw_list": data}
    except (json.JSONDecodeError, ValueError):
        pass

    # 再尝试 YAML（OpenAPI/Swagger 常见 YAML 格式）
    try:
        data = yaml.safe_load(content)
        if isinstance(data, dict):
            return data
        if isinstance(data, list):
            return {"_raw_list": data}
    except (yaml.YAMLError, ValueError):
        pass

    raise ValueError("无法解析文件: 不是有效的 JSON 或 YAML 格式")


# =============================================================================
#  统一导入器
# =============================================================================


class UniImporter:
    """统一导入器 - 一处调用，自动识别格式并执行导入。"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self._stats = {
            "created_apis": 0, "updated_apis": 0, "skipped_apis": 0,
            "created_categories": 0, "skipped_categories": 0,
            "created_environments": 0, "updated_environments": 0,
            "imported_variables": 0, "imported_headers": 0,
            "created_test_cases": 0, "updated_test_cases": 0, "skipped_test_cases": 0,
            "errors": [],
        }
        self._api_id_map: dict[str, int] = {}  # apifox_id → db_id
        self._structured_errors: list[dict] = []  # 结构化错误列表

    # ====================================
    #  预览
    # ====================================

    async def preview(self, project_id: int, content: str) -> dict:
        """解析文件内容，返回预览数据（不写入数据库）。"""
        if len(content) > MAX_FILE_SIZE:
            raise_biz(ErrorCodes.IMPORT_FILE_TOO_LARGE)

        try:
            data = _parse_json_or_yaml(content)
        except ValueError as e:
            raise_biz(ErrorCodes.IMPORT_PARSE_ERROR, str(e))

        # 处理原始数组格式（通用 JSON 列表）
        if "_raw_list" in data:
            data = {"apis": data["_raw_list"]}

        fmt = detect_format(data)
        if fmt == ImportFormat.UNKNOWN:
            # 降级尝试：使用通用 JSON 解析器
            logger.info("格式检测返回 UNKNOWN，降级尝试通用 JSON 解析")
            fallback_categories, fallback_apis, fallback_name = _parse_general_json(data)
            if fallback_apis:
                fmt = ImportFormat.GENERAL_JSON
                categories = fallback_categories
                apis = fallback_apis
                project_name = fallback_name
                environments = []
                global_vars = []
                global_headers = {"headers": []}
                test_cases = []
            else:
                # 构建详细的诊断错误消息
                top_keys = list(data.keys())[:10]
                preview_text = json.dumps(data, ensure_ascii=False)[:200] if isinstance(data, (dict, list)) else str(data)[:200]
                raise_biz(ErrorCodes.IMPORT_INVALID_FORMAT,
                    f"无法识别文件格式。支持的格式: Apifox/Postman/OpenAPI/YAPI/Eolink/Apipost/Bruno/HAR/cURL。"
                    f"文件顶层字段: {top_keys}，内容预览: {preview_text}")

        categories, apis, project_name, environments, global_vars, global_headers, test_cases = \
            await self._parse_by_format(data, fmt)

        preview_tree = self._build_preview_tree(categories, apis)
        await self._mark_exists(project_id, categories, apis, environments)

        stats = {
            "total_categories": len(categories),
            "total_apis": len(apis),
            "total_environments": len(environments),
            "total_variables": len(global_vars),
            "total_headers": len(global_headers.get("headers", [])),
            "total_test_cases": len(test_cases),
            # 分别统计各来源数量
            "total_request_collections": sum(1 for a in apis if a.get("source") == "requestCollection"),
            "total_test_case_collections": sum(1 for a in apis if a.get("source") == "apiTestCase"),
        }

        return {
            "format": fmt.value,
            "project_name": project_name or "未命名",
            "stats": stats,
            "categories": preview_tree,
            "environments": environments,
            "global_variables": global_vars,
            "global_headers": global_headers.get("headers", []),
            "test_cases": test_cases,
            **({"structured_errors": []}),  # preview 阶段无执行错误
        }

    async def _parse_by_format(self, data: dict, fmt: ImportFormat):
        """根据格式路由到对应的解析器。"""
        categories = []
        apis = []
        project_name = None
        environments = []
        global_vars = []
        global_headers = {"headers": []}
        test_cases = []

        if fmt == ImportFormat.APIFOX_PROJECT:
            project_name = data.get("info", {}).get("name", "")
            servers = _parse_apifox_servers(data.get("projectSetting", {}).get("servers", []))
            environments = _parse_apifox_environments(data.get("environments", []), servers)
            global_vars = _parse_apifox_global_vars(data.get("globalVariables", []))
            global_headers = _parse_apifox_common_params(data.get("commonParameters"))
            tc_collection = data.get("apiTestCaseCollection", [])
            for tc_group in tc_collection:
                if "items" in tc_group:
                    _walk_apifox_testcases([tc_group], test_cases)
            # 传入 test_cases 以提取 API 节点内嵌的测试用例
            for collection in data.get("apiCollection", []):
                _walk_apifox_collection(collection, None, 0, categories, apis, test_cases)
            folder_map = {f"cat_{cat['apifox_id']}": f"cat_{cat['apifox_id']}" for cat in categories}
            for collection in data.get("requestCollection", []):
                cat_apifox_id = collection.get("id")
                cat_ref = f"cat_{cat_apifox_id}" if cat_apifox_id else None
                if cat_apifox_id:
                    effective_cat_id = cat_apifox_id if cat_apifox_id else f"gen_req_{len(categories)}"
                    categories.append({
                        "name": collection.get("name", "未分类请求"),
                        "parent_ref": None, "depth": 0, "apifox_id": effective_cat_id,
                    })
                for item in collection.get("items", []):
                    folder_id = item.get("folderId")
                    effective_ref = cat_ref
                    if folder_id and folder_id != 0 and folder_id in folder_map:
                        effective_ref = folder_map[folder_id]
                    api = _parse_apifox_api({"api": item}, item.get("name", "未命名"), item.get("id"))
                    api["category_ref"] = effective_ref
                    path = api["path"]
                    if path.startswith("http"):
                        parsed = urlparse(path)
                        api["path"] = parsed.path or "/"
                    apis.append(api)

            # === 使用专用解析器处理 requestCollection（更完整的字段提取）===
            for collection in data.get("requestCollection", []):
                if isinstance(collection, dict):
                    req_apis = _parse_apifox_request_collection(collection)
                    for ra in req_apis:
                        # 设置 category_ref
                        ra["category_ref"] = f"cat_{collection.get('id', '')}" if collection.get("id") else None
                        apis.append(ra)

            # === 解析 apiTestCaseCollection 中额外的 API ===
            imported_ids = {a.get("apifox_id") for a in apis if a.get("apifox_id")}
            tc_collections = data.get("apiTestCaseCollection", [])
            if isinstance(tc_collections, list):
                for tc_group in tc_collections:
                    if isinstance(tc_group, dict):
                        tc_apis = _parse_apifox_testcase_apis(tc_group, imported_ids)
                        for ta in tc_apis:
                            ta["category_ref"] = None
                            apis.append(ta)

        elif fmt == ImportFormat.APIFOX_COLLECTION:
            project_name = data.get("info", {}).get("name", "")
            items = data.get("apiCollection", data.get("apiItems", data.get("items", [])))
            if isinstance(items, dict):
                items = [items]
            for item in items:
                if isinstance(item, dict):
                    if "api" in item:
                        api = _parse_apifox_api(item, item.get("name", "未命名"), item.get("id"))
                        api["category_ref"] = None
                        apis.append(api)
                    elif "items" in item:
                        _walk_apifox_collection(item, None, 0, categories, apis)

        elif fmt == ImportFormat.POSTMAN:
            categories, apis, project_name = _parse_postman_collection(data)

        elif fmt == ImportFormat.OPENAPI:
            categories, apis, project_name = parse_openapi_3(data)

        elif fmt == ImportFormat.YAPI:
            categories, apis, project_name = _parse_yapi(data)

        elif fmt == ImportFormat.EOLINK:
            categories, apis, project_name = _parse_eolink(data)

        elif fmt == ImportFormat.APIPOST:
            categories, apis, project_name = _parse_apipost(data)

        elif fmt == ImportFormat.BRUNO:
            categories, apis, project_name = _parse_bruno(data)

        elif fmt == ImportFormat.HAR:
            categories, apis, project_name, har_test_cases = parse_har_enhanced(data)
            test_cases.extend(har_test_cases)

        elif fmt == ImportFormat.API_PILOT:
            # API Pilot 标准格式解析
            project_name = data.get("project", {}).get("name", "API Pilot Import")
            raw_categories = data.get("categories", [])
            for cat in raw_categories:
                if not isinstance(cat, dict):
                    continue
                cat_id = cat.get("id")
                cat_name = cat.get("name", "未命名分类")
                parent_id = cat.get("parent_id")
                sort_order = cat.get("sort_order", 0)

                # 构建分类记录
                categories.append({
                    "name": cat_name,
                    "parent_ref": f"cat_{parent_id}" if parent_id else None,
                    "depth": 0,
                    "apifox_id": cat_id,
                    "sort_order": sort_order,
                })

                # 解析该分类下的 API
                cat_apis = cat.get("apis", [])
                for api in cat_apis:
                    if not isinstance(api, dict):
                        continue
                    api_id = api.get("id")
                    name = api.get("name", "未命名接口")
                    method = (api.get("method") or "GET").upper()
                    path = api.get("path", "/")
                    description = api.get("description", "")
                    headers = api.get("headers", [])
                    params = api.get("params", [])
                    body = api.get("body", {"type": "none", "content": ""})
                    auth_type = api.get("auth_type", "none")

                    apis.append({
                        "name": name,
                        "method": method,
                        "path": path,
                        "description": description,
                        "headers": headers,
                        "params": params,
                        "body": body,
                        "auth_type": auth_type,
                        "category_ref": f"cat_{cat_id}" if cat_id else None,
                        "apifox_id": api_id,
                    })

        elif fmt == ImportFormat.CURL:
            categories, apis, project_name = _parse_curl(data.get("_raw_text", ""))

        elif fmt == ImportFormat.GENERAL_JSON:
            categories, apis, project_name = _parse_general_json(data)

        elif fmt == ImportFormat.SWAGGER:
            # Swagger 2.0 使用增强解析器
            categories, apis, project_name = parse_swagger2(data)

        elif fmt == ImportFormat.UNKNOWN:
            # 降级: 尝试通用 JSON 解析器（execute 阶段统一处理）
            logger.info("_parse_by_format 收到 UNKNOWN 格式，降级尝试通用 JSON 解析")
            categories, apis, project_name = _parse_general_json(data)

        return categories, apis, project_name, environments, global_vars, global_headers, test_cases

    async def _mark_exists(self, project_id: int,
                           categories: list[dict], apis: list[dict],
                           environments: list[dict]) -> None:
        """查库标记各条目是否已存在。
        
        增强检测策略：
        - 分类：支持 name + parent_id 组合匹配（更精确）
        - API：支持 apifox_id、method+path、name 多种匹配方式
        """
        # 1. 分类检测 - 使用 name + parent_id 组合匹配
        # 构建 apifox_ref → 分类名 映射，用于查找父分类的真实名称
        ref_to_name = {f"cat_{c.get('apifox_id', '')}": c["name"] for c in categories}
        for cat in categories:
            query = select(ApiCategory).where(
                ApiCategory.project_id == project_id,
                ApiCategory.name == cat["name"],
            )
            # 如果有 parent_id，也作为匹配条件
            parent_ref = cat.get("parent_ref")
            if parent_ref:
                # 通过映射获取父分类的真实名称，而非使用 apifox_id 数字
                parent_name = ref_to_name.get(parent_ref)
                if parent_name:
                    parent_cat_result = await self.db.execute(
                        select(ApiCategory).where(
                            ApiCategory.project_id == project_id,
                            ApiCategory.name == parent_name,
                        ).limit(1)
                    )
                    parent_cat = parent_cat_result.scalar_one_or_none()
                    if parent_cat:
                        query = query.where(ApiCategory.parent_id == parent_cat.id)
                    else:
                        query = query.where(ApiCategory.parent_id.is_(None))
                else:
                    query = query.where(ApiCategory.parent_id.is_(None))
            else:
                query = query.where(ApiCategory.parent_id.is_(None))
            
            result = await self.db.execute(query.limit(1))
            existing = result.scalar_one_or_none()
            cat["exists"] = existing is not None
            if existing:
                cat["existing_id"] = existing.id

        # 2. API 检测 - 支持多种匹配方式
        for api in apis:
            # 方式1: 通过 apifox_id 匹配（最精确，来自导入工具的ID）
            apifox_id = api.get("apifox_id")
            if apifox_id:
                result = await self.db.execute(
                    select(ApiDefinition).where(
                        ApiDefinition.project_id == project_id,
                        ApiDefinition.apifox_id == str(apifox_id),
                        ApiDefinition.deleted_at.is_(None),
                    ).limit(1)
                )
                existing = result.scalar_one_or_none()
                if existing:
                    api["exists"] = True
                    api["existing_id"] = existing.id
                    api["match_type"] = "apifox_id"
                    continue

            # 方式2: 通过 method + path 匹配（标准匹配）
            result = await self.db.execute(
                select(ApiDefinition).where(
                    ApiDefinition.project_id == project_id,
                    ApiDefinition.method == api["method"],
                    ApiDefinition.path == api["path"],
                    ApiDefinition.deleted_at.is_(None),
                ).limit(1)
            )
            existing = result.scalar_one_or_none()
            if existing:
                api["exists"] = True
                api["existing_id"] = existing.id
                api["match_type"] = "method_path"
                continue

            # 方式3: 通过 name 匹配（兜底匹配）
            result = await self.db.execute(
                select(ApiDefinition).where(
                    ApiDefinition.project_id == project_id,
                    ApiDefinition.name == api["name"],
                    ApiDefinition.deleted_at.is_(None),
                ).limit(1)
            )
            existing = result.scalar_one_or_none()
            if existing:
                api["exists"] = True
                api["existing_id"] = existing.id
                api["match_type"] = "name"
                continue

            # 不存在
            api["exists"] = False
            api["match_type"] = "new"

        # 3. 环境检测
        for env in environments:
            result = await self.db.execute(
                select(Environment).where(
                    Environment.project_id == project_id,
                    Environment.name == env["name"],
                ).limit(1)
            )
            env["exists"] = result.scalar_one_or_none() is not None

    def _build_preview_tree(self, categories: list[dict], apis: list[dict]) -> list[dict]:
        """构建嵌套预览树。"""
        tree = []
        cat_map: dict[str, dict] = {}
        for cat in categories:
            node = {"name": cat["name"], "apifox_id": cat["apifox_id"], "exists": cat.get("exists", False), "children": []}
            cat_map[f"cat_{cat['apifox_id']}"] = node

        for cat in categories:
            node = cat_map.get(f"cat_{cat['apifox_id']}")
            if not node:
                continue
            parent_key = cat.get("parent_ref")
            if parent_key and parent_key in cat_map:
                cat_map[parent_key]["children"].append(node)
            else:
                tree.append(node)

        for api in apis:
            api_node = {
                "name": api["name"], "method": api["method"], "path": api["path"],
                "isApi": True, "exists": api.get("exists", False),
            }
            cat_ref = api.get("category_ref")
            if cat_ref and cat_ref in cat_map:
                cat_map[cat_ref]["children"].append(api_node)
            else:
                tree.append(api_node)

        return tree

    # ====================================
    #  导入执行
    # ====================================

    async def execute(self, project_id: int, content: str, options: dict | None = None) -> dict:
        """执行导入（全事务保护）。"""
        options = options or {}
        opts = {
            "import_variables": options.get("import_variables", options.get("importVariables", True)),
            "import_headers": options.get("import_headers", options.get("importHeaders", True)),
            "import_environments": options.get("import_environments", options.get("importEnvironments", True)),
            "import_test_cases": options.get("import_test_cases", options.get("importTestCases", True)),
            "conflict_strategy": options.get("conflict_strategy", options.get("conflictStrategy", "update")),
            "target_category_id": options.get("target_category_id", options.get("targetCategoryId")),
            "selected_items": options.get("selected_items"),
        }

        if len(content) > MAX_FILE_SIZE:
            raise_biz(ErrorCodes.IMPORT_FILE_TOO_LARGE)

        try:
            data = _parse_json_or_yaml(content)
        except ValueError as e:
            raise_biz(ErrorCodes.IMPORT_PARSE_ERROR, str(e))

        # 处理原始数组格式（通用 JSON 列表）
        if "_raw_list" in data:
            data = {"apis": data["_raw_list"]}

        fmt = detect_format(data)
        if fmt == ImportFormat.UNKNOWN:
            # 降级尝试通用 JSON 解析器
            logger.info("格式检测返回 UNKNOWN，降级尝试通用 JSON 解析（execute 阶段）")
            fallback_cats, fallback_apis, fallback_name = _parse_general_json(data)
            if fallback_apis:
                fmt = ImportFormat.GENERAL_JSON
            else:
                # 构建详细的诊断错误消息
                top_keys = list(data.keys())[:10]
                preview_text = json.dumps(data, ensure_ascii=False)[:200] if isinstance(data, (dict, list)) else str(data)[:200]
                raise_biz(ErrorCodes.IMPORT_INVALID_FORMAT,
                    f"无法识别文件格式。支持的格式: Apifox/Postman/OpenAPI/YAPI/Eolink/Apipost/Bruno/HAR/cURL。"
                    f"文件顶层字段: {top_keys}，内容预览: {preview_text}")

        categories, apis, project_name, environments, global_vars, global_headers, test_cases = \
            await self._parse_by_format(data, fmt)

        # 选择性导入：如果指定了 selected_items，只导入选中的接口
        selected_items = opts.get("selected_items")
        if selected_items and isinstance(selected_items, list) and len(selected_items) > 0:
            selected_set = set(selected_items)
            apis = [a for a in apis if a.get("name") in selected_set]
            # 过滤后可能有些分类为空，清理空分类
            used_cat_refs = {a.get("category_ref") for a in apis if a.get("category_ref")}
            categories = [c for c in categories if c.get("apifox_id") in used_cat_refs or not c.get("apifox_id")]

        self._stats = {
            "created_apis": 0, "updated_apis": 0, "skipped_apis": 0,
            "created_categories": 0, "skipped_categories": 0,
            "created_environments": 0, "updated_environments": 0,
            "imported_variables": 0, "imported_headers": 0,
            "created_test_cases": 0, "updated_test_cases": 0, "skipped_test_cases": 0,
            "errors": [],
        }
        self._api_id_map = {}

        if opts["import_variables"] and global_vars:
            await self._import_global_vars(project_id, global_vars)

        if opts["import_headers"] and global_headers:
            await self._import_global_headers(project_id, global_headers)

        if opts["import_environments"] and environments:
            await self._import_environments(project_id, environments)

        cat_id_map = await self._import_categories_and_apis(
            project_id, categories, apis, opts
        )

        if opts["import_test_cases"] and test_cases:
            await self._import_test_cases(project_id, test_cases, cat_id_map)

        await self.db.flush()

        result = {
            **self._stats,
            "format": fmt.value,
            "project_name": project_name or "未命名",
        }
        # 计算失败数
        result["failed_count"] = len(self._structured_errors)
        result["skipped_count"] = self._stats.get("skipped_apis", 0)
        if self._structured_errors:
            result["structured_errors"] = self._structured_errors
        return result

    async def _import_global_vars(self, project_id: int, variables: list[dict]):
        result = await self.db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        if not project:
            return
        existing_vars = json.loads(project.global_variables) if project.global_variables else []
        existing_keys = {v["key"] for v in existing_vars if isinstance(v, dict)}
        for v in variables:
            if v.get("key") and v["key"] not in existing_keys:
                existing_vars.append({"key": v["key"], "value": v.get("value", ""), "enabled": True})
                self._stats["imported_variables"] += 1
                existing_keys.add(v["key"])
        project.global_variables = json.dumps(existing_vars, ensure_ascii=False)

    async def _import_global_headers(self, project_id: int, gh: dict):
        result = await self.db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        if not project:
            return
        existing_params = json.loads(project.global_params) if project.global_params else {}
        existing_headers = existing_params.get("headers", [])
        existing_keys = {h["key"] for h in existing_headers if isinstance(h, dict)}
        for h in gh.get("headers", []):
            if h.get("key") and h["key"] not in existing_keys:
                existing_headers.append(h)
                self._stats["imported_headers"] += 1
                existing_keys.add(h["key"])
        existing_params["headers"] = existing_headers
        project.global_params = json.dumps(existing_params, ensure_ascii=False)

    async def _import_environments(self, project_id: int, environments: list[dict]):
        for env in environments:
            result = await self.db.execute(
                select(Environment).where(
                    Environment.project_id == project_id,
                    Environment.name == env["name"],
                ).limit(1)
            )
            existing = result.scalar_one_or_none()
            if existing:
                services_raw = _safe_json_list(existing.services)
                existing_urls = {s["url"] for s in services_raw if isinstance(s, dict)}
                for svc in env.get("services", []):
                    if svc["url"] not in existing_urls:
                        services_raw.append(svc)
                existing.services = json.dumps(services_raw, ensure_ascii=False)

                merged_vars = _safe_json_list(existing.variables)
                merged_keys = {v["key"] for v in merged_vars if isinstance(v, dict)}
                for v in env.get("variables", []):
                    if v.get("key") and v["key"] not in merged_keys:
                        merged_vars.append(v)
                existing.variables = json.dumps(merged_vars, ensure_ascii=False)

                # 合并 headers
                merged_headers = _safe_json_list(existing.headers)
                merged_hkeys = {h["key"] for h in merged_headers if isinstance(h, dict)}
                for h in env.get("headers", []):
                    if h.get("key") and h["key"] not in merged_hkeys:
                        merged_headers.append(h)
                existing.headers = json.dumps(merged_headers, ensure_ascii=False)

                self._stats["updated_environments"] += 1
            else:
                new_env = Environment(
                    project_id=project_id,
                    name=env["name"],
                    services=env.get("services", []),
                    variables=env.get("variables", []),
                    headers=env.get("headers", []),
                )
                self.db.add(new_env)
                self._stats["created_environments"] += 1

    async def _import_categories_and_apis(
        self, project_id: int, categories: list[dict], apis: list[dict], opts: dict
    ) -> dict[str, int]:
        """导入接口目录和接口，返回 cat_ref → db_id 映射。"""
        conflict_strategy = opts.get("conflict_strategy", "update")
        target_cat_id = opts.get("target_category_id")

        cat_id_map: dict[str, int] = {}

        # 使用增强的存在检测结果
        for cat in categories:
            parent_db = cat_id_map.get(cat.get("parent_ref")) if cat.get("parent_ref") else None

            # 使用之前标记的 exists 结果
            if cat.get("exists") and cat.get("existing_id"):
                cat_id_map[f"cat_{cat['apifox_id']}"] = cat["existing_id"]
                self._stats["skipped_categories"] += 1
            else:
                new_cat = ApiCategory(
                    project_id=project_id,
                    name=cat["name"],
                    parent_id=parent_db,
                    sort_order=0,
                )
                self.db.add(new_cat)
                await self.db.flush()
                cat_id_map[f"cat_{cat['apifox_id']}"] = new_cat.id
                self._stats["created_categories"] += 1

        for api in apis:
            real_cat_id = target_cat_id or cat_id_map.get(api.get("category_ref"))
            if not real_cat_id:
                real_cat_id = await self._get_or_create_default_cat(project_id)

            # 使用增强的存在检测结果 - 优先使用 existing_id
            existing_id = api.get("existing_id")
            api.get("match_type", "new")

            if existing_id:
                # 找到已存在的 API
                result = await self.db.execute(
                    select(ApiDefinition).where(ApiDefinition.id == existing_id).limit(1)
                )
                existing = result.scalar_one_or_none()

                if existing:
                    if conflict_strategy == "skip":
                        self._stats["skipped_apis"] += 1
                        self._api_id_map[str(api.get("apifox_id", ""))] = existing.id
                        continue
                    elif conflict_strategy == "rename":
                        ts = int(time.time() % 100000)
                        api["name"] = f"{api['name']} (导入于 {ts})"
                        new_api = await self._create_api(project_id, api, real_cat_id)
                        if new_api:
                            self._api_id_map[str(api.get("apifox_id", ""))] = new_api.id
                    elif conflict_strategy == "keep_both":
                        ts = int(time.time() % 100000)
                        api["path"] = f"{api['path']}?imported={ts}"
                        new_api = await self._create_api(project_id, api, real_cat_id)
                        if new_api:
                            self._api_id_map[str(api.get("apifox_id", ""))] = new_api.id
                    else:  # update
                        self._update_existing_api(existing, api)
                        self._stats["updated_apis"] += 1
                        self._api_id_map[str(api.get("apifox_id", ""))] = existing.id
            else:
                # 新 API，直接创建
                new_api = await self._create_api(project_id, api, real_cat_id)
                if new_api:
                    self._api_id_map[str(api.get("apifox_id", ""))] = new_api.id

        return cat_id_map

    def _update_existing_api(self, existing: ApiDefinition, api: dict):
        existing.name = api["name"]
        existing.headers = json.dumps(api["headers"], ensure_ascii=False)
        existing.params = json.dumps(api["params"], ensure_ascii=False)
        existing.body = json.dumps(api["body"], ensure_ascii=False)
        existing.description = api.get("description", "")
        existing.response_schema = json.dumps(api.get("response_schema"), ensure_ascii=False)
        existing.response_examples = json.dumps(api.get("response_examples"), ensure_ascii=False)
        existing.apifox_id = str(api.get("apifox_id", ""))
        existing.pre_script = api.get("pre_script", "")
        existing.post_script = api.get("post_script", "")
        existing.auth = json.dumps(api.get("auth", {"type": "none"}), ensure_ascii=False)
        existing.auth_type = api.get("auth_type", "none")
        existing.settings = json.dumps(api.get("settings", {}), ensure_ascii=False)
        existing.category_id = existing.category_id

    async def _create_api(self, project_id: int, api: dict, cat_id: int):
        try:
            new_api = ApiDefinition(
                project_id=project_id,
                category_id=cat_id,
                name=api["name"],
                method=api["method"],
                path=api["path"],
                description=api.get("description", ""),
                headers=json.dumps(api.get("headers", []), ensure_ascii=False),
                params=json.dumps(api.get("params", []), ensure_ascii=False),
                body=json.dumps(api.get("body", {"type": "none", "content": ""}), ensure_ascii=False),
                response_schema=json.dumps(api.get("response_schema"), ensure_ascii=False),
                response_examples=json.dumps(api.get("response_examples", []), ensure_ascii=False),
                apifox_id=str(api.get("apifox_id", "")),
                pre_script=api.get("pre_script", ""),
                post_script=api.get("post_script", ""),
                auth=json.dumps(api.get("auth", {"type": "none"}), ensure_ascii=False),
                auth_type=api.get("auth_type", "none"),
                settings=json.dumps(api.get("settings", {}), ensure_ascii=False),
            )
            self.db.add(new_api)
            self._stats["created_apis"] += 1
            return new_api
        except (ValueError, KeyError, TypeError, IntegrityError) as e:
            err_msg = f"接口 {api.get('method')} {api.get('path')}: {str(e)}"
            self._stats["errors"].append(err_msg)  # 保持向后兼容
            self._structured_errors.append({      # 新增结构化信息
                "name": api.get("name", "未命名"),
                "method": api.get("method", ""),
                "path": api.get("path", ""),
                "reason": str(e),
            })
            logger.warning(f"创建接口失败 [{api.get('method')} {api.get('path')}]: {e}")
            return None

    async def _import_test_cases(self, project_id: int, test_cases: list[dict], cat_id_map: dict[str, int]):
        """导入测试用例。需要先匹配 api_id。"""
        for tc in test_cases:
            try:
                apifox_api_id = tc.get("api_id")
                db_api_id = self._api_id_map.get(str(apifox_api_id))

                if not db_api_id and apifox_api_id:
                    result = await self.db.execute(
                        select(ApiDefinition).where(
                            ApiDefinition.project_id == project_id,
                            ApiDefinition.apifox_id == str(apifox_api_id),
                        ).limit(1)
                    )
                    existing_api = result.scalar_one_or_none()
                    if existing_api:
                        db_api_id = existing_api.id

                if not db_api_id:
                    self._stats["skipped_test_cases"] += 1
                    skip_msg = f"测试用例 '{tc['name']}' 关联接口 {apifox_api_id} 未找到"
                    self._stats["errors"].append(skip_msg)
                    self._structured_errors.append({
                        "name": tc.get("name", "未命名"),
                        "reason": f"关联接口 ID={apifox_api_id} 未找到",
                        "type": "test_case",
                    })
                    continue

                result = await self.db.execute(
                    select(TestCase).where(
                        TestCase.project_id == project_id,
                        TestCase.api_id == db_api_id,
                        TestCase.name == tc["name"],
                    )
                )
                existing_tc = result.scalar_one_or_none()

                if existing_tc:
                    existing_tc.description = tc.get("description", "")
                    existing_tc.assertions = json.dumps(tc.get("assertions", []), ensure_ascii=False)
                    existing_tc.extract_vars = json.dumps(tc.get("extract_vars", []), ensure_ascii=False)
                    existing_tc.priority = tc.get("priority", "P1")
                    existing_tc.tags = str(tc.get("tags", ""))
                    if tc.get("request_body"):
                        existing_tc.request_body = json.dumps(tc["request_body"], ensure_ascii=False)
                    self._stats["updated_test_cases"] += 1
                else:
                    new_tc = TestCase(
                        project_id=project_id,
                        api_id=db_api_id,
                        name=tc["name"],
                        description=tc.get("description", ""),
                        priority=tc.get("priority", "P1"),
                        status="active",
                        assertions=json.dumps(tc.get("assertions", []), ensure_ascii=False),
                        extract_vars=json.dumps(tc.get("extract_vars", []), ensure_ascii=False),
                        tags=str(tc.get("tags", "")),
                        request_body=json.dumps(tc["request_body"], ensure_ascii=False) if tc.get("request_body") else "{}",
                    )
                    self.db.add(new_tc)
                    self._stats["created_test_cases"] += 1
            except (ValueError, KeyError, TypeError) as e:
                err_msg = f"测试用例 '{tc.get('name', '未命名')}': {str(e)}"
                self._stats["errors"].append(err_msg)  # 向后兼容
                self._structured_errors.append({
                    "name": tc.get("name", "未命名"),
                    "reason": str(e),
                    "type": "test_case",
                })
                logger.warning(f"导入测试用例失败: {e}")

    async def _get_or_create_default_cat(self, project_id: int) -> int:
        result = await self.db.execute(
            select(ApiCategory).where(
                ApiCategory.project_id == project_id,
                ApiCategory.name == "未分类",
            ).limit(1)
        )
        cat = result.scalar_one_or_none()
        if cat:
            return cat.id
        cat = ApiCategory(project_id=project_id, name="未分类", parent_id=None, sort_order=9999)
        self.db.add(cat)
        await self.db.flush()
        return cat.id
