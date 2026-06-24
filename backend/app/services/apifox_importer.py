import json
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.api_category import ApiCategory
from app.models.api_definition import ApiDefinition
from app.models.environment import Environment
from app.models.project import Project
from app.core.exceptions import raise_biz, ErrorCodes
from app.services.importers.base_importer import BaseApiImporter

logger = logging.getLogger("import.apifox")

MAX_RECURSION_DEPTH = 10
MAX_FILE_SIZE_CHARS = 10_485_760  # 10MB


# =============================================================================
#  辅助函数
# =============================================================================


def _generate_default_from_schema(schema: Optional[Dict]) -> Any:
    """根据 JSON Schema 生成默认值。"""
    if not schema:
        return ""
    t = schema.get("type", "string")
    props = schema.get("properties", {})
    if t == "object" and props:
        return {k: _generate_default_from_schema(v) for k, v in props.items()}
    elif t == "array":
        return []
    elif t == "integer":
        return 0
    elif t == "number":
        return 0.0
    elif t == "boolean":
        return False
    else:
        return ""


def _content_type_to_body_type(content_type: str) -> str:
    mapping = {
        "application/json": "json",
        "application/x-www-form-urlencoded": "form-urlencoded",
        "multipart/form-data": "form-data",
        "application/xml": "xml",
        "text/plain": "raw",
    }
    return mapping.get(content_type, "raw")


def _extract_body(request_body: Optional[Dict]) -> Dict:
    """
    提取 Body 内容。
    优先级: examples[0].value > example(单数字段) > data > jsonSchema 生成 > 空
    """
    if not request_body:
        return {"type": "none", "content": ""}

    content_type = request_body.get("type", "application/json")
    body_type = _content_type_to_body_type(content_type)

    raw_content = ""
    # 优先级1: examples 数组
    examples = request_body.get("examples", [])
    if examples and examples[0].get("value"):
        raw_content = examples[0]["value"]
    # 优先级2: example 单数字段（Apifox 1.x requestCollection 格式）
    if not raw_content:
        raw_content = request_body.get("example") or ""
    # 优先级3: data 字段（Apifox 实际发送数据）
    if not raw_content:
        raw_content = request_body.get("data") or ""
    # 优先级4: 从 jsonSchema 生成默认值
    if not raw_content:
        schema = request_body.get("jsonSchema")
        if schema:
            raw_content = json.dumps(
                _generate_default_from_schema(schema), ensure_ascii=False, indent=2
            )

    # 关键修复: form-urlencoded/form-data 的空内容必须是 [] 而非 {}
    if not raw_content and body_type in ("form-urlencoded", "form-data"):
        raw_content = "[]"

    return {
        "type": body_type,
        "content_type": content_type,
        "content": raw_content,
        "schema": request_body.get("jsonSchema"),
    }


# =============================================================================
#  解析函数
# =============================================================================


def _parse_servers(servers: List[Dict]) -> List[Dict]:
    """解析 projectSetting.servers，过滤掉 default 和非 URL 条目。"""
    result = []
    for s in servers:
        if s.get("id") == "default":
            continue
        url = s.get("name", "")
        if not url.startswith("http"):
            continue
        result.append({
            "name": url,
            "url": url,
            "module_id": s.get("moduleId"),
            "apifox_server_id": s.get("id"),
        })
    return result


def _parse_environments(env_list: List[Dict], servers: List[Dict]) -> List[Dict]:
    """解析环境列表，注入前置 services。"""
    result = []
    for env in env_list:
        services = []
        base_url = env.get("baseUrl", "")

        if base_url:
            services.append({
                "module": "默认模块",
                "service_name": "主服务",
                "url": base_url,
                "is_base_url": True,
            })

        for svr in servers:
            if svr["url"] != base_url:
                services.append({
                    "module": "前置服务",
                    "service_name": svr["url"],
                    "url": svr["url"],
                    "is_base_url": False,
                })

        variables = [
            {"key": v.get("name"), "value": v.get("value", ""),
             "initial_value": v.get("initialValue", ""), "enabled": True}
            for v in env.get("variables", [])
        ]

        headers = [
            {"key": h.get("name"), "value": h.get("value", h.get("defaultValue", ""))}
            for h in env.get("parameters", {}).get("header", [])
        ]

        result.append({
            "name": env.get("name"),
            "apifox_env_id": env.get("id"),
            "base_url": base_url,
            "services": services,
            "variables": variables,
            "headers": headers,
        })
    return result


def _parse_global_variables(gv_list: List[Dict]) -> List[Dict]:
    """解析全局变量（外层是数组，内层才是 variables）。"""
    variables = []
    for gv_group in gv_list:
        for v in gv_group.get("variables", []):
            variables.append({
                "key": v.get("name"),
                "value": v.get("value", ""),
                "description": v.get("description", ""),
            })
    return variables


def _parse_common_parameters(cp: Optional[Dict]) -> Dict:
    """解析公共参数，只提取 header 类型。"""
    if not cp:
        return {"headers": []}
    headers = []
    for h in cp.get("parameters", {}).get("header", []):
        headers.append({
            "key": h.get("name"),
            "value": h.get("defaultValue", ""),
            "enabled": h.get("defaultEnable", True),
            "description": h.get("description", ""),
        })
    return {"headers": headers}


def _parse_single_api(api: Dict, display_name: str, category_id: Any, apifox_id: str) -> Dict:
    """解析单个接口定义的所有字段。"""
    headers = []

    # 1. 接口私有 headers
    for h in api.get("parameters", {}).get("header", []):
        headers.append({
            "key": h.get("name"),
            "value": h.get("example", h.get("value", "")),
            "enabled": h.get("enable", True),
            "required": h.get("required", False),
            "description": h.get("description", ""),
            "source": "interface",
        })

    # 2. 公共 headers（合并，检查重复）
    existing_keys = {hdr["key"] for hdr in headers}
    for h in api.get("commonParameters", {}).get("header", []):
        h_name = h.get("name")
        if h_name and h_name not in existing_keys:
            headers.append({
                "key": h_name,
                "value": "",
                "enabled": True,
                "source": "common",
            })
            existing_keys.add(h_name)

    # Query Params
    params = []
    for p in api.get("parameters", {}).get("query", []):
        params.append({
            "key": p.get("name"),
            "value": p.get("example", ""),
            "enabled": p.get("enable", True),
            "type": p.get("type", "string"),
        })

    body = _extract_body(api.get("requestBody"))

    # Response schema
    response_schema = None
    responses = api.get("responses", [])
    if responses:
        resp = responses[0]
        response_schema = {
            "status_code": resp.get("code"),
            "name": resp.get("name"),
            "content_type": resp.get("contentType", "json"),
            "schema": resp.get("jsonSchema"),
        }

    # Response examples
    response_examples = []
    for ex in api.get("responseExamples", []):
        response_examples.append({
            "name": ex.get("name", "示例"),
            "data": ex.get("data", ""),
        })

    return {
        "name": display_name,
        "method": api.get("method", "GET").upper(),
        "path": api.get("path", "/"),
        "category_id": category_id,
        "apifox_id": apifox_id,
        "headers": headers,
        "params": params,
        "body": body,
        "response_schema": response_schema,
        "response_examples": response_examples,
        "description": api.get("description", ""),
        "status": api.get("status", "developing"),
    }


def _build_folder_id_map(parsed_categories):
    """从解析的分类列表构建 apifox_id → category_key 的映射。
    用于 requestCollection 的 folderId 映射到实际分类。
    """
    folder_map = {}
    for cat in parsed_categories:
        apifox_id = cat.get("apifox_id")
        if apifox_id:
            folder_map[apifox_id] = f"cat_{apifox_id}"
    return folder_map


# =============================================================================
#  接口目录树解析
# =============================================================================


def _parse_api_collection_node(
    node: Dict, parent_id: Any, depth: int,
    categories: List, apis: List,
) -> None:
    """递归处理单个 apiCollection 节点（接口目录或接口）。"""
    if depth > MAX_RECURSION_DEPTH:
        logger.warning(
            "Apifox collection recursion depth > %d, stopping at node: %s",
            MAX_RECURSION_DEPTH, node.get("name", "unknown"),
        )
        return

    node_name = node.get("name", "未命名")
    apifox_id = node.get("id")

    if "api" in node:
        api_data = node["api"]
        parsed_api = _parse_single_api(api_data, node_name, parent_id, apifox_id)
        apis.append(parsed_api)

    elif "items" in node:
        # 接口目录节点：只有顶级 depth===0 且名为"根目录"才跳过
        if node_name == "根目录" and depth == 0:
            for child in node.get("items", []):
                _parse_api_collection_node(
                    child, parent_id=None, depth=depth + 1,
                    categories=categories, apis=apis,
                )
            return

        cat_record = {
            "name": node_name,
            "parent_id": parent_id,
            "depth": depth,
            "apifox_id": apifox_id,
            "children_count": len(node.get("items", [])),
        }
        categories.append(cat_record)

        current_cat_id = f"cat_{apifox_id}"

        for child in node.get("items", []):
            _parse_api_collection_node(
                child, parent_id=current_cat_id, depth=depth + 1,
                categories=categories, apis=apis,
            )


def _parse_request_collection_node(
    collection: Dict, folder_id_map: Dict[int, str], categories: List, apis: List,
) -> None:
    """解析 requestCollection（Apifox 扁平的请求列表）。
    利用 folder_id_map 将 folderId 映射到 apiCollection 中的分类。
    """
    apifox_id = collection.get("id")
    if apifox_id:
        cat_record = {
            "name": collection.get("name", "未分类请求"),
            "parent_id": None,
            "depth": 0,
            "apifox_id": apifox_id,
            "children_count": len(collection.get("items", [])),
        }
        categories.append(cat_record)
        current_cat_id = f"cat_{apifox_id}"
    else:
        current_cat_id = None

    for item in collection.get("items", []):
        item_name = item.get("name", "未命名")
        # 尝试用 folderId 映射到 apiCollection 的分类
        folder_id = item.get("folderId")
        effective_cat_id = current_cat_id
        if folder_id and folder_id != 0 and folder_id in folder_id_map:
            effective_cat_id = folder_id_map[folder_id]

        # 修复: requestCollection 的 path 可能是完整 URL，提取路径部分
        path = item.get("path", "/")
        if path.startswith("http"):
            from urllib.parse import urlparse
            parsed = urlparse(path)
            path = parsed.path or "/"

        api = _parse_single_api(item, item_name, effective_cat_id, item.get("id"))
        # 覆盖解析后的 path 和 name（去除完整 URL）
        api["path"] = path
        if api["name"].startswith("http"):
            api["name"] = api["name"].rsplit("/", 1)[-1] if "/" in api["name"] else api["name"]
        apis.append(api)



def _build_preview_tree(parsed_categories: List[Dict], parsed_apis: List[Dict]) -> List[Dict]:
    """将扁平的接口目录+接口列表构建为嵌套树，供前端 `<el-tree>` 渲染。"""
    tree: List[Dict] = []

    # 接口目录字典: apifox_id -> node
    cat_map: Dict[str, Dict] = {}
    for cat in parsed_categories:
        node: Dict = {
            "name": cat["name"],
            "apifox_id": cat["apifox_id"],
            "exists": False,
            "children": [],
        }
        cat_map[f"cat_{cat['apifox_id']}"] = node

    # 挂载接口目录到父级
    for cat in parsed_categories:
        node = cat_map.get(f"cat_{cat['apifox_id']}")
        if not node:
            continue
        parent_key = cat.get("parent_id")
        if parent_key and parent_key in cat_map:
            cat_map[parent_key]["children"].append(node)
        else:
            tree.append(node)

    # 将接口挂到接口目录下
    for api in parsed_apis:
        api_node: Dict = {
            "name": api["name"],
            "method": api["method"],
            "path": api["path"],
            "isApi": True,
            "exists": False,
        }
        cat_key = api.get("category_id")
        if cat_key and cat_key in cat_map:
            cat_map[cat_key]["children"].append(api_node)
        else:
            tree.append(api_node)

    return tree


# =============================================================================
#  ImportService
# =============================================================================


class ImportService(BaseApiImporter):
    """Apifox 文件导入服务，提供 preview（只读）和 import（写入）两个模式。"""

    def __init__(self, db: AsyncSession):
        super().__init__(db)

    async def import_data(
        self,
        project_id: int,
        raw_data: Any,
        content: str = "",
        **options,
    ) -> dict:
        """实现 BaseApiImporter 抽象接口：转发到 import_apifox。

        约定：
        - raw_data：可由调用方预先解析的 dict；为 None 时用 content 重新解析
        - content：Apifox 原始 JSON 字符串（与 import_apifox 兼容）
        - **options：透传给 import_apifox 的 import_options
        """
        if content and not raw_data:
            raw_data = self._parse_json(content)
        import_options = options or None
        # raw_data 透传主要给后续分析/审计使用；底层 import_apifox 仍以 content 为准
        if not content and isinstance(raw_data, str):
            content = raw_data
        return await self.import_apifox(project_id, content, import_options)

    # ------------------------------------------------
    #  preview: 解析 + 查库标记 exists，不写库
    # ------------------------------------------------

    async def preview_apifox(self, project_id: int, content: str) -> dict:
        """解析 Apifox JSON 文件，返回预览数据（查库标记 exists，不 INSERT/UPDATE）。"""
        if len(content) > MAX_FILE_SIZE_CHARS:
            raise_biz(ErrorCodes.IMPORT_FILE_TOO_LARGE)

        data = self._parse_json(content)

        schema = data.get("$schema", {})
        if not isinstance(schema, dict) or schema.get("type") != "project":
            raise_biz(ErrorCodes.IMPORT_INVALID_FORMAT, "missing $schema.type === 'project'")

        servers = _parse_servers(data.get("projectSetting", {}).get("servers", []))
        environments = _parse_environments(data.get("environments", []), servers)
        global_variables = _parse_global_variables(data.get("globalVariables", []))
        global_headers = _parse_common_parameters(data.get("commonParameters"))

        parsed_categories: List[Dict] = []
        parsed_apis: List[Dict] = []
        for collection in data.get("apiCollection", []):
            _parse_api_collection_node(
                collection, parent_id=None, depth=0,
                categories=parsed_categories, apis=parsed_apis,
            )
        # 建立 apiCollection 节点 ID → 分类的映射（用于 requestCollection 的 folderId）
        folder_id_map = _build_folder_id_map(parsed_categories)
        # 处理 requestCollection（Apifox 扁平化请求列表）
        for collection in data.get("requestCollection", []):
            _parse_request_collection_node(
                collection, folder_id_map,
                categories=parsed_categories, apis=parsed_apis,
            )

        preview_tree = _build_preview_tree(parsed_categories, parsed_apis)

        # 查库标记 exists
        await self._mark_existing_apis(project_id, parsed_apis)

        stats = {
            "total_categories": len(parsed_categories),
            "total_apis": len(parsed_apis),
            "total_environments": len(environments),
            "total_variables": len(global_variables),
            "total_headers": len(global_headers["headers"]),
            "total_servers": len(servers),
        }

        return {
            "project_name": data.get("info", {}).get("name", "未知项目"),
            "stats": stats,
            "categories": preview_tree,
            "environments": environments,
            "global_variables": global_variables,
            "global_headers": global_headers["headers"],
        }

    async def _mark_exists(self, project_id: int,
                           parsed_categories: List[Dict],
                           parsed_apis: List[Dict],
                           environments: List[Dict]) -> None:
        """查询数据库，标记各个条目是否存在（批量查询优化，避免 N+1）。"""
        # 批量查询分类
        cat_names = list({cat["name"] for cat in parsed_categories})
        if cat_names:
            result = await self.db.execute(
                select(ApiCategory).where(
                    ApiCategory.project_id == project_id,
                    ApiCategory.name.in_(cat_names),
                )
            )
            existing_cat_names = {cat.name for cat in result.scalars().all()}
        else:
            existing_cat_names = set()
        for cat in parsed_categories:
            cat["exists"] = cat["name"] in existing_cat_names

        # 批量查询接口
        if parsed_apis:
            all_apis_result = await self.db.execute(
                select(ApiDefinition).where(
                    ApiDefinition.project_id == project_id,
                )
            )
            all_apis = all_apis_result.scalars().all()
            api_keys = {(api.method, api.path) for api in all_apis}
        else:
            api_keys = set()
        for api in parsed_apis:
            api["exists"] = (api["method"], api["path"]) in api_keys

        # 批量查询环境
        env_names = [env["name"] for env in environments]
        if env_names:
            result = await self.db.execute(
                select(Environment).where(
                    Environment.project_id == project_id,
                    Environment.name.in_(env_names),
                )
            )
            existing_env_names = {env.name for env in result.scalars().all()}
        else:
            existing_env_names = set()
        for env in environments:
            env["exists"] = env["name"] in existing_env_names

    # ------------------------------------------------
    #  import: 全量事务写入
    # ------------------------------------------------

    async def import_apifox(self, project_id: int, content: str,
                            import_options: Optional[Dict] = None) -> dict:
        """
        执行导入。全量事务，任何步骤失败全部回滚。

        import_options:
            import_variables (bool): 是否导入全局变量，默认 true
            import_headers (bool): 是否导入公共 Headers，默认 true
            import_environments (bool): 是否导入环境，默认 true
            conflict_strategy (str): "update" 覆盖更新 / "skip" 跳过已存在接口
        """
        if import_options is None:
            import_options = {}
        options = {
            "import_variables": import_options.get("import_variables") or import_options.get("importVariables", True),
            "import_headers": import_options.get("import_headers") or import_options.get("importHeaders", True),
            "import_environments": import_options.get("import_environments") or import_options.get("importEnvironments", True),
            "conflict_strategy": import_options.get("conflict_strategy") or import_options.get("conflictStrategy", "update"),
            "target_category_id": import_options.get("target_category_id") or import_options.get("targetCategoryId"),
        }

        if len(content) > MAX_FILE_SIZE_CHARS:
            raise_biz(ErrorCodes.IMPORT_FILE_TOO_LARGE)

        data = self._parse_json(content)
        schema = data.get("$schema", {})
        if not isinstance(schema, dict) or schema.get("type") != "project":
            raise_biz(ErrorCodes.IMPORT_INVALID_FORMAT)

        servers = _parse_servers(data.get("projectSetting", {}).get("servers", []))
        environments = _parse_environments(data.get("environments", []), servers)
        global_variables = _parse_global_variables(data.get("globalVariables", []))
        global_headers = _parse_common_parameters(data.get("commonParameters"))

        parsed_categories: List[Dict] = []
        parsed_apis: List[Dict] = []
        for collection in data.get("apiCollection", []):
            _parse_api_collection_node(
                collection, parent_id=None, depth=0,
                categories=parsed_categories, apis=parsed_apis,
            )
        # 建立 apiCollection 节点 ID → 分类的映射（用于 requestCollection 的 folderId）
        folder_id_map = _build_folder_id_map(parsed_categories)
        # 处理 requestCollection（Apifox 扁平化请求列表）
        for collection in data.get("requestCollection", []):
            _parse_request_collection_node(
                collection, folder_id_map,
                categories=parsed_categories, apis=parsed_apis,
            )
        stats = {
            "created_apis": 0,
            "updated_apis": 0,
            "skipped_apis": 0,
            "created_categories": 0,
            "skipped_categories": 0,
            "created_environments": 0,
            "updated_environments": 0,
            "imported_variables": 0,
            "imported_headers": 0,
            "errors": [],
        }

        # ---- 1. 全局变量 ----
        if options["import_variables"]:
            result = await self.db.execute(
                select(Project).where(Project.id == project_id)
            )
            project = result.scalar_one_or_none()
            if project:
                existing_vars = json.loads(project.global_variables) if project.global_variables else []
                existing_keys = {v["key"] for v in existing_vars if isinstance(v, dict)}
                for var in global_variables:
                    if var["key"] not in existing_keys:
                        existing_vars.append({
                            "key": var["key"],
                            "value": var["value"],
                            "enabled": True,
                        })
                        stats["imported_variables"] += 1
                        existing_keys.add(var["key"])
                project.global_variables = json.dumps(existing_vars, ensure_ascii=False)

        # ---- 2. 全局 Headers ----
        if options["import_headers"]:
            result = await self.db.execute(
                select(Project).where(Project.id == project_id)
            )
            project = result.scalar_one_or_none()
            if project:
                existing_params = json.loads(project.global_params) if project.global_params else {}
                existing_headers = existing_params.get("headers", [])
                existing_keys = {h["key"] for h in existing_headers if isinstance(h, dict)}
                for h in global_headers["headers"]:
                    if h["key"] not in existing_keys:
                        existing_headers.append(h)
                        stats["imported_headers"] += 1
                        existing_keys.add(h["key"])
                existing_params["headers"] = existing_headers
                project.global_params = json.dumps(existing_params, ensure_ascii=False)

        # ---- 3. 环境 ----
        if options["import_environments"]:
            for env in environments:
                result = await self.db.execute(
                    select(Environment).where(
                        Environment.project_id == project_id,
                        Environment.name == env["name"],
                    )
                )
                existing_env = result.scalar_one_or_none()
                if existing_env:
                    existing_env.services = json.dumps(env["services"], ensure_ascii=False)
                    merged_vars_raw = json.loads(existing_env.variables) if existing_env.variables else []
                    merged_keys = {v["key"] for v in merged_vars_raw if isinstance(v, dict)}
                    for var in env["variables"]:
                        if var["key"] not in merged_keys:
                            merged_vars_raw.append(var)
                    existing_env.variables = json.dumps(merged_vars_raw, ensure_ascii=False)
                    stats["updated_environments"] += 1
                else:
                    new_env = Environment(
                        project_id=project_id,
                        name=env["name"],
                        services=json.dumps(env["services"], ensure_ascii=False),
                        variables=json.dumps(env["variables"], ensure_ascii=False),
                        headers=json.dumps(env["headers"], ensure_ascii=False),
                    )
                    self.db.add(new_env)
                    stats["created_environments"] += 1

        # ---- 4. 接口目录树 ----
        cat_id_map: Dict[str, int] = {}
        # 批量查询已存在的分类（避免 N+1）
        cat_names = list({cat["name"] for cat in parsed_categories})
        existing_cats_result = await self.db.execute(
            select(ApiCategory).where(
                ApiCategory.project_id == project_id,
                ApiCategory.name.in_(cat_names),
            )
        )
        existing_cats_by_name = {cat.name: cat for cat in existing_cats_result.scalars().all()}

        for cat in parsed_categories:
            parent_db_id = None
            parent_key = cat.get("parent_id")
            if parent_key and parent_key in cat_id_map:
                parent_db_id = cat_id_map[parent_key]

            existing_cat = existing_cats_by_name.get(cat["name"])
            if existing_cat:
                cat_db_id = existing_cat.id
                stats["skipped_categories"] += 1
            else:
                new_cat = ApiCategory(
                    project_id=project_id,
                    name=cat["name"],
                    parent_id=parent_db_id,
                    sort_order=0,
                )
                self.db.add(new_cat)
                await self.db.flush()
                cat_db_id = new_cat.id
                stats["created_categories"] += 1

            cat_id_map[f"cat_{cat['apifox_id']}"] = cat_db_id

        # ---- 5. 接口 ----
        # 批量查询项目下所有接口（避免 N+1）
        all_apis_result = await self.db.execute(
            select(ApiDefinition).where(
                ApiDefinition.project_id == project_id,
            )
        )
        all_apis = all_apis_result.scalars().all()
        api_lookup = {(api.method, api.path): api for api in all_apis}

        # 预查询"未分类"目录（避免循环内重复查询）
        default_cat = None
        default_cat_result = await self.db.execute(
            select(ApiCategory).where(
                ApiCategory.project_id == project_id,
                ApiCategory.name == "未分类",
            ).limit(1)
        )
        default_cat = default_cat_result.scalar_one_or_none()

        for api in parsed_apis:
            # 当接口未关联接口目录且指定了目标接口目录时，使用目标接口目录
            if api["category_id"] is None and options.get("target_category_id"):
                real_cat_id = options["target_category_id"]
            else:
                real_cat_id = cat_id_map.get(api["category_id"])
            if not real_cat_id:
                if default_cat:
                    real_cat_id = default_cat.id
                else:
                    new_cat = ApiCategory(
                        project_id=project_id,
                        name="未分类",
                        parent_id=None,
                        sort_order=9999,
                    )
                    self.db.add(new_cat)
                    await self.db.flush()
                    real_cat_id = new_cat.id
                    default_cat = new_cat
                stats.setdefault("created_categories", 0)
                stats["created_categories"] += 1

            existing_api = api_lookup.get((api["method"], api["path"]))

            if existing_api:
                if options["conflict_strategy"] == "update":
                    existing_api.name = api["name"]
                    existing_api.headers = json.dumps(api["headers"], ensure_ascii=False)
                    existing_api.params = json.dumps(api["params"], ensure_ascii=False)
                    existing_api.body = json.dumps(api["body"], ensure_ascii=False)
                    existing_api.description = api.get("description", "")
                    existing_api.response_schema = json.dumps(api.get("response_schema"), ensure_ascii=False)
                    existing_api.response_examples = json.dumps(api.get("response_examples"), ensure_ascii=False)
                    existing_api.apifox_id = api.get("apifox_id")
                    stats["updated_apis"] += 1
                else:
                    stats["skipped_apis"] += 1
            else:
                new_api = ApiDefinition(
                    project_id=project_id,
                    category_id=real_cat_id,
                    name=api["name"],
                    method=api["method"],
                    path=api["path"],
                    description=api.get("description", ""),
                    headers=json.dumps(api["headers"], ensure_ascii=False),
                    params=json.dumps(api["params"], ensure_ascii=False),
                    body=json.dumps(api["body"], ensure_ascii=False),
                    response_schema=json.dumps(api.get("response_schema"), ensure_ascii=False),
                    response_examples=json.dumps(api.get("response_examples"), ensure_ascii=False),
                    apifox_id=api.get("apifox_id"),
                )
                self.db.add(new_api)
                stats["created_apis"] += 1

        await self.db.flush()
        return stats
