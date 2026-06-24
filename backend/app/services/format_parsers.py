"""
格式解析模块 - 支持多种 JSON 格式的接口数据解析。

支持的格式:
  - Apifox 项目导出 (完整: apifoxProject 1.0.0)
  - Apifox 接口导出 (单接口/json/collection)
  - Postman Collection v2.0 / v2.1
  - OpenAPI / Swagger 2.0 / 3.0
  - YAPI 导出格式
  - Eolink 导出格式
  - Apipost 导出格式
  - 通用 JSON 格式 (简单数组或对象)

本模块仅负责解析，不涉及数据库操作。
"""

import json
import logging
import re
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

logger = logging.getLogger("import.format_parsers")

# =============================================================================
#  常量与枚举
# =============================================================================

MAX_RECURSION_DEPTH = 15
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

HTTP_METHODS = {"GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS", "TRACE", "CONNECT"}


class ImportFormat(Enum):
    APIFOX_PROJECT = "apifox_project"
    APIFOX_COLLECTION = "apifox_collection"
    POSTMAN = "postman"
    OPENAPI = "openapi"
    YAPI = "yapi"
    EOLINK = "eolink"
    APIPOST = "apipost"
    BRUNO = "bruno"
    CURL = "curl"  # cURL 命令格式
    SWAGGER = "swagger"  # Swagger 2.0
    HAR = "har"  # HTTP Archive (HAR) 格式
    API_PILOT = "api_pilot"  # API Pilot 标准格式
    GENERAL_JSON = "general_json"  # 通用JSON格式
    UNKNOWN = "unknown"


class ConflictStrategy(Enum):
    UPDATE = "update"
    SKIP = "skip"
    RENAME = "rename"
    KEEP_BOTH = "keep_both"


# =============================================================================
#  格式检测
# =============================================================================


def _detect_apifox_project(data: dict) -> bool:
    """通过多种特征识别 Apifox 项目导出（v1/v2/v3 全版本兼容）。"""
    if not isinstance(data, dict):
        return False

    # 1. 顶层 apifoxProject 字段（v1-v3）
    if "apifoxProject" in data:
        return True

    # 2. $schema 特征
    schema = data.get("$schema")
    if isinstance(schema, dict):
        if schema.get("app") == "apifox" or schema.get("type") == "project":
            return True

    # 3. 兜底：包含 apiCollection 或 requestCollection
    if "apiCollection" in data or "requestCollection" in data:
        return True

    return False


def detect_format(data: dict, filename: str = "") -> ImportFormat:
    """自动检测导入数据的格式。

    检测优先级（从最具体到最通用）:
      1. Apifox 项目导出: 通过 _detect_apifox_project 多特征识别
      2. Apifox 接口导出: 有 apiItems
      3. Postman: 有 info.schema (postman collection schema)
      4. OpenAPI: 有 openapi 或 swagger 版本号
      5. YAPI: 有 projects 或 list 字段
      6. Eolink: 有 projectName 或 apiList
      7. Apipost: 有 apipost 或 collections
      8. Bruno: 有 bru 文件格式
      9. 通用JSON: 尝试检测简单数组或对象结构
      10. 未知: 尝试所有解析器直到成功

    Args:
        data: 解析后的 JSON 数据
        filename: 文件名（可选，已废弃，格式检测基于内容）
    """
    # 1. Apifox project（兼容所有版本）
    if _detect_apifox_project(data):
        return ImportFormat.APIFOX_PROJECT

    # 2. Apifox 旧版: 顶层有 apiItems
    if "apiItems" in data and isinstance(data["apiItems"], list):
        return ImportFormat.APIFOX_COLLECTION

    # 3. Postman: info.schema 包含 postman collection schema URL
    info = data.get("info", {})
    if isinstance(info, dict):
        info_schema = info.get("schema", "")
        if isinstance(info_schema, str) and "postman" in info_schema.lower():
            return ImportFormat.POSTMAN
    # Postman: 顶层有 item 且 item 内有 request 字段（严格匹配）
    if "item" in data and isinstance(data["item"], list) and data["item"]:
        first_item = data["item"][0]
        if isinstance(first_item, dict) and "request" in first_item:
            return ImportFormat.POSTMAN

    # 5. OpenAPI: openapi 或 swagger 字段
    if "openapi" in data or "swagger" in data:
        if data.get("openapi", "").startswith("3."):
            return ImportFormat.OPENAPI
        return ImportFormat.SWAGGER
    if "paths" in data and isinstance(data["paths"], dict):
        return ImportFormat.OPENAPI

    # 6. YAPI 检测
    if _detect_yapi(data):
        return ImportFormat.YAPI

    # 7. Eolink 检测
    if _detect_eolink(data):
        return ImportFormat.EOLINK

    # 8. Apipost 检测
    if _detect_apipost(data):
        return ImportFormat.APIPOST

    # 9. Bruno 检测
    if _detect_bruno(data):
        return ImportFormat.BRUNO

    # HAR: 有 log 字段且 log.entries 和 log.version
    if "log" in data and isinstance(data["log"], dict):
        log = data["log"]
        if "entries" in log and isinstance(log["entries"], list) and log.get("version"):
            return ImportFormat.HAR

    # API Pilot: 有 format="api_pilot" 和 categories 字段
    if data.get("format") == "api_pilot" and "categories" in data:
        return ImportFormat.API_PILOT

    # 10. 通用JSON格式检测
    if _detect_general_json(data):
        return ImportFormat.GENERAL_JSON

    return ImportFormat.UNKNOWN


def _detect_yapi(data: dict) -> bool:
    """检测 YAPI 导出格式"""
    # YAPI 典型特征: 有 catid、project_id、interface_type 等特有字段
    if "catid" in data or "project_id" in data:
        return True
    if "interfaces" in data and isinstance(data["interfaces"], list):
        # 检查 items 是否有 YAPI 特有字段
        items = data["interfaces"]
        if items and isinstance(items[0], dict):
            first = items[0]
            if any(k in first for k in ("catid", "project_id", "interface_type", "method_path")):
                return True
    if "list" in data and isinstance(data.get("list"), list):
        items = data["list"]
        if items and isinstance(items[0], dict):
            first = items[0]
            if any(k in first for k in ("catid", "project_id", "interface_type", "title")):
                return True
    return False


def _detect_eolink(data: dict) -> bool:
    """检测 Eolink 导出格式"""
    if data.get("projectName") or data.get("apiList"):
        return True
    if "project" in data and isinstance(data.get("project"), dict):
        p = data["project"]
        if p.get("apiTree") or p.get("apiList"):
            return True
    # 不仅靠 "apis" 判断，需要 Eolink 特有字段，避免误判通用格式
    return False


def _detect_apipost(data: dict) -> bool:
    """检测 Apipost 导出格式"""
    if data.get("apipost") or data.get("apipost_version"):
        return True
    if "projectInfo" in data and isinstance(data.get("projectInfo"), dict):
        return True
    # Apipost collections 需要有 apiList 子数组（Apipost 特有结构）
    if "collections" in data and isinstance(data.get("collections"), list):
        items = data["collections"]
        if items and isinstance(items[0], dict):
            first = items[0]
            if "apiList" in first or "apipost_id" in first:
                return True
    return False


def _detect_bruno(data: dict) -> bool:
    """检测 Bruno 格式"""
    if data.get("version") and data.get("name"):
        # Bruno 的 bruno.json 格式
        if "collections" in data or "requests" in data:
            return True
    return False


def _detect_general_json(data: dict) -> bool:
    """检测是否为通用JSON格式（简单API列表）"""
    # 简单API数组格式: [{"name": "...", "method": "...", "url": "..."}]
    for key in ("apis", "items", "apiList", "endpoints", "routes", "operations"):
        val = data.get(key)
        if isinstance(val, list) and val:
            # 检查第一项是否为API结构
            if isinstance(val[0], dict):
                first = val[0]
                if any(k in first for k in ("method", "url", "path", "apiPath", "requestUrl", "endpoint", "httpMethod")):
                    return True
    return False


# =============================================================================
#  Body 与 Schema 处理
# =============================================================================

_CONTENT_TYPE_MAP = {
    "application/json": "json",
    "application/x-www-form-urlencoded": "form-urlencoded",
    "multipart/form-data": "form-data",
    "application/xml": "xml",
    "text/plain": "raw",
    "text/html": "raw",
    "application/octet-stream": "binary",
    # Apifox 有些版本直接用 type 名代替 content-type
    "form": "form-urlencoded",
    "form-data": "form-data",
    "json": "json",
    "xml": "xml",
    "raw": "raw",
    "binary": "binary",
}


def _body_type(content_type: str) -> str:
    return _CONTENT_TYPE_MAP.get(content_type, "raw")


def _generate_default_from_schema(schema: Optional[Dict]) -> Any:
    """根据 JSON Schema 递归生成默认值。"""
    if not schema:
        return ""
    t = schema.get("type", "string")
    if t == "object":
        props = schema.get("properties", {})
        if props:
            return {k: _generate_default_from_schema(v) for k, v in props.items()}
        return {}
    if t == "array":
        return []
    if t == "integer":
        return 0
    if t == "number":
        return 0.0
    if t == "boolean":
        return False
    return ""


def _extract_body(request_body: Optional[Dict]) -> Dict:
    """从请求体定义中提取 body 内容。

    优先级: examples[0].value > example > data > jsonSchema生成 > 空

    重要: form-urlencoded/form-data 的空内容必须是 [] 而非 {}，
    否则前端 BodyEditor/FormTable 会因 JSON.parse("{}") 得到对象而崩溃。
    """
    if not request_body:
        return {"type": "none", "content": ""}

    content_type = request_body.get("type", "application/json")
    body_type = _body_type(content_type)
    raw_content = ""

    examples = request_body.get("examples", [])
    if examples and isinstance(examples[0], dict):
        val = examples[0].get("value", "")
        if val:
            raw_content = val if isinstance(val, str) else json.dumps(val, ensure_ascii=False)
    if not raw_content:
        ex = request_body.get("example")
        if ex:
            raw_content = ex if isinstance(ex, str) else json.dumps(ex, ensure_ascii=False)
    if not raw_content:
        d = request_body.get("data")
        if d:
            raw_content = d if isinstance(d, str) else json.dumps(d, ensure_ascii=False)
    if not raw_content:
        # Apifox 有时把 body 内容放在 body 字段
        b = request_body.get("body")
        if b:
            raw_content = b if isinstance(b, str) else json.dumps(b, ensure_ascii=False)
    if not raw_content:
        schema = request_body.get("jsonSchema")
        if schema and isinstance(schema, dict):
            raw_content = json.dumps(
                _generate_default_from_schema(schema), ensure_ascii=False, indent=2
            )

    # 关键修复: form-urlencoded/form-data 的空内容必须是 [] 而非 {}
    if not raw_content and body_type in ("form-urlencoded", "form-data"):
        raw_content = "[]"

    return {
        "type": body_type,
        "content_type": content_type if content_type in _CONTENT_TYPE_MAP else "application/json",
        "content": raw_content,
        "schema": request_body.get("jsonSchema"),
    }


# =============================================================================
#  变量处理
# =============================================================================

_VAR_PATTERN = re.compile(r'\{\{(.+?)\}\}')


def extract_variable_references(text: str) -> List[str]:
    """提取文本中所有 {{var}} 引用。"""
    return _VAR_PATTERN.findall(text)


# =============================================================================
#  格式: Apifox 项目导出
# =============================================================================


def _parse_apifox_servers(servers: List[Dict]) -> List[Dict]:
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
        })
    return result


def _parse_apifox_environments(env_list: List[Dict], servers: List[Dict]) -> List[Dict]:
    result = []
    for env in env_list:
        services = []
        base_url = env.get("baseUrl", "")
        if base_url:
            services.append({
                "module": "主服务",
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


def _parse_apifox_global_vars(gv_list: List[Dict]) -> List[Dict]:
    """解析 Apifox 全局变量（外层是数组，内层才是 variables）。"""
    variables = []
    for gv_group in gv_list:
        for v in gv_group.get("variables", []):
            variables.append({
                "key": v.get("name"),
                "value": v.get("value", ""),
                "description": v.get("description", ""),
            })
    return variables


def _parse_apifox_common_params(cp: Optional[Dict]) -> Dict:
    """解析公共参数（Header/Query/Body）。"""
    result = {"headers": [], "query": [], "body": []}
    if not cp:
        return result
    params = cp.get("parameters", {})
    for h in params.get("header", []):
        result["headers"].append({
            "key": h.get("name"),
            "value": h.get("defaultValue", h.get("value", "")),
            "enabled": h.get("defaultEnable", True),
            "description": h.get("description", ""),
        })
    for q in params.get("query", []):
        result["query"].append({
            "key": q.get("name"),
            "value": q.get("defaultValue", q.get("value", "")),
            "enabled": q.get("defaultEnable", True),
        })
    return result


def _parse_apifox_scripts(data: Dict) -> Tuple[str, str]:
    """解析前置/后置脚本。"""
    pre = ""
    post = ""
    for p in data.get("preProcessors", []):
        if p.get("type") == "customScript" and p.get("data"):
            pre = p["data"]
    for p in data.get("postProcessors", []):
        if p.get("type") == "customScript" and p.get("data"):
            post = p["data"]
    return pre, post


def _parse_apifox_api(node: Dict, display_name: str, apifox_id: Any) -> Optional[Dict]:
    """完整解析单个 Apifox 接口，返回全字段 dict。

    增强: 对 parameters 字段做类型保护 (可能为 dict / list / None)，
    对所有嵌套字段做安全访问，避免 KeyError / AttributeError。
    外层 try/except 保证单个接口解析失败不影响整体导入。
    """
    # 增强容错：非 dict 类型直接跳过
    if not isinstance(node, dict):
        logger.warning("跳过非字典类型节点: type=%s, name=%s", type(node).__name__, display_name)
        return None

    try:
        api = node.get("api", node)

        # 空 dict 检查
        if not isinstance(api, dict) or not api:
            logger.warning("跳过空API节点: %s", display_name)
            return None

        # 如果外层没有 id，尝试从内层 api 对象获取（有些格式 api 节点的 id 在内层）
        if not apifox_id:
            apifox_id = api.get("id")

        # 安全获取 parameters (可能是 dict / list / None)
        raw_params = api.get("parameters")
        if isinstance(raw_params, list):
            # 某些版本直接是列表，全部视为 query params
            params_list = raw_params
            header_list = []
            path_list = []
        elif isinstance(raw_params, dict):
            params_list = raw_params.get("query", [])
            header_list = raw_params.get("header", [])
            path_list = raw_params.get("path", [])
        else:
            params_list = []
            header_list = []
            path_list = []

        # Headers
        headers = []
        for h in header_list:
            if not isinstance(h, dict):
                continue
            headers.append({
                "key": h.get("name", ""),
                "value": h.get("example", h.get("value", "")),
                "enabled": h.get("enable", True),
                "required": h.get("required", False),
                "description": h.get("description", ""),
                "source": "interface",
            })
        existing_keys = {h["key"] for h in headers if h.get("key")}
        raw_common = api.get("commonParameters")
        if isinstance(raw_common, dict):
            for h in raw_common.get("header", []):
                if isinstance(h, dict) and h.get("name") and h["name"] not in existing_keys:
                    headers.append({
                        "key": h["name"], "value": h.get("value", ""), "enabled": True, "source": "common",
                    })

        # Query params
        params = []
        for p in params_list:
            if not isinstance(p, dict):
                continue
            params.append({
                "key": p.get("name", ""),
                "value": p.get("example", p.get("value", "")),
                "enabled": p.get("enable", True),
                "type": p.get("type", "string"),
                "required": p.get("required", False),
                "description": p.get("description", ""),
            })

        # Path params
        for p in path_list:
            if not isinstance(p, dict):
                continue
            params.append({
                "key": p.get("name", ""),
                "value": p.get("example", p.get("value", "")),
                "enabled": True,
                "type": p.get("type", "string"),
                "required": True,
                "in": "path",
            })

        body = _extract_body(api.get("requestBody"))

        # Auth
        raw_auth = api.get("auth")
        if isinstance(raw_auth, dict):
            auth = raw_auth.get("type", "none")
            auth_config = raw_auth
        else:
            auth = "none"
            auth_config = {"type": "none"}

        # Scripts
        pre_script, post_script = _parse_apifox_scripts(api)

        # Response
        response_schema = None
        responses = api.get("responses", [])
        if isinstance(responses, list) and responses:
            resp = responses[0]
            if isinstance(resp, dict):
                response_schema = {
                    "status_code": resp.get("code"),
                    "name": resp.get("name"),
                    "content_type": resp.get("contentType", "application/json"),
                    "schema": resp.get("jsonSchema"),
                }

        # Response examples
        response_examples = []
        for ex in api.get("responseExamples", []):
            if isinstance(ex, dict):
                response_examples.append({
                    "name": ex.get("name", "示例"),
                    "data": ex.get("data", ""),
                })

        # Settings
        settings = api.get("advancedSettings", api.get("settings", {}))
        if not isinstance(settings, dict):
            settings = {}

        # 提取 method，安全处理
        method = api.get("method", "GET")
        if not method or not isinstance(method, str):
            method = "GET"
        else:
            method = method.upper()

        # 安全提取 path
        path = api.get("path", "/")
        if not path or not isinstance(path, str):
            path = "/"
        else:
            path = path.strip()
            if not path:
                path = "/"

        # 安全提取 description
        desc = api.get("description", "")
        if not isinstance(desc, str):
            desc = str(desc) if desc else ""

        return {
            "name": display_name or "未命名",
            "method": method,
            "path": path,
            "apifox_id": apifox_id,
            "headers": headers,
            "params": params,
            "body": body,
            "auth_type": auth,
            "auth": auth_config,
            "pre_script": pre_script,
            "post_script": post_script,
            "response_schema": response_schema,
            "response_examples": response_examples,
            "description": desc,
            "status": api.get("status", "developing"),
            "settings": settings,
        }
    except Exception as e:
        logger.warning("解析接口失败 [%s]: %s", display_name, e, exc_info=True)
        return None


def _parse_apifox_request_collection(req_col: Optional[Dict]) -> List[Dict]:
    """解析 Apifox requestCollection（HTTP 请求集）。
    
    requestCollection 中的 items 是直接的 HTTP 请求（非 API 定义），
    每个请求有 url/method/headers/body 等字段。
    """
    if not isinstance(req_col, dict):
        return []
    
    items = req_col.get("items", [])
    if not isinstance(items, list):
        return []
    
    apis = []
    for item in items:
        if not isinstance(item, dict):
            continue
        
        try:
            # 提取 request 信息
            req = item.get("request", item)
            if not isinstance(req, dict):
                req = item
            
            url = req.get("url", "")
            method = req.get("method", "GET")
            if isinstance(method, str):
                method = method.upper()
            else:
                method = "GET"
            
            # 从完整 URL 提取 path
            if "://" in url:
                parsed = urlparse(url)
                path = parsed.path or "/"
                if parsed.query:
                    path += "?" + parsed.query
            else:
                path = url if url else "/"
            
            name = item.get("name", item.get("displayName", "未命名请求"))
            
            # Headers
            headers = []
            raw_headers = req.get("headers", [])
            if isinstance(raw_headers, list):
                for h in raw_headers:
                    if isinstance(h, dict):
                        headers.append({
                            "key": h.get("name", h.get("key", "")),
                            "value": h.get("value", h.get("defaultValue", "")),
                            "enabled": h.get("enable", True),
                            "source": "requestCollection",
                        })
            
            # Body
            body = _extract_body(req.get("requestBody", req.get("body")))
            
            apis.append({
                "name": name,
                "method": method,
                "path": path,
                "headers": headers,
                "params": [],
                "body": body,
                "auth_type": "none",
                "auth": {"type": "none"},
                "description": req.get("description", item.get("description", "")),
                "source": "requestCollection",
                "apifox_id": item.get("id"),
            })
        except Exception as e:
            logger.warning("解析 requestCollection 项失败 [%s]: %s", 
                          item.get("name", "unknown") if isinstance(item, dict) else "unknown", e)
            continue
    
    return apis


def _parse_apifox_testcase_apis(tc_col: Optional[Dict], imported_ids: Optional[set] = None) -> List[Dict]:
    """解析 Apifox apiTestCaseCollection（测试用例集），提取关联的 API 接口信息。
    
    从测试用例中提取关联的 API 接口信息。
    imported_ids: 已导入的 apifox_id 集合，用于去重。
    """
    if not isinstance(tc_col, dict):
        return []
    
    if imported_ids is None:
        imported_ids = set()
    
    items = tc_col.get("items", [])
    if not isinstance(items, list):
        return []
    
    apis = []
    for item in items:
        if not isinstance(item, dict):
            continue
        
        try:
            # 测试用例可能包含 api 引用
            api_ref = item.get("api")
            if isinstance(api_ref, dict):
                api_id = api_ref.get("id")
                if api_id and api_id in imported_ids:
                    continue  # 已从 apiCollection 导入，跳过
                if api_id:
                    imported_ids.add(api_id)
                
                name = item.get("name", api_ref.get("name", "未命名"))
                method = api_ref.get("method", "GET")
                if isinstance(method, str):
                    method = method.upper()
                path = api_ref.get("path", "/")
                
                apis.append({
                    "name": name,
                    "method": method,
                    "path": path,
                    "headers": [],
                    "params": [],
                    "body": {"type": "none", "content": ""},
                    "auth_type": "none",
                    "auth": {"type": "none"},
                    "description": item.get("description", ""),
                    "source": "apiTestCase",
                    "apifox_id": api_id,
                })
            else:
                # 没有 api 引用，尝试从测试用例自身提取
                tc_req = item.get("request")
                if isinstance(tc_req, dict):
                    name = item.get("name", "未命名")
                    method = tc_req.get("method", "GET")
                    if isinstance(method, str):
                        method = method.upper()
                    path = tc_req.get("url", "/")
                    
                    apis.append({
                        "name": name,
                        "method": method,
                        "path": path,
                        "headers": [],
                        "params": [],
                        "body": {"type": "none", "content": ""},
                        "auth_type": "none",
                        "auth": {"type": "none"},
                        "description": item.get("description", ""),
                        "source": "apiTestCase",
                        "apifox_id": item.get("id"),
                    })
        except Exception as e:
            logger.warning("解析测试用例失败 [%s]: %s",
                          item.get("name", "unknown") if isinstance(item, dict) else "unknown", e)
            continue
    
    return apis


# =============================================================================
#  Apifox 目录树递归解析
# =============================================================================


def _walk_apifox_collection(
    node: Dict, parent_id: Any, depth: int,
    categories: List, apis: List,
    test_cases: Optional[List] = None,
) -> None:
    """递归遍历 apiCollection 节点树。

    增强: 同时提取 API 节点中内嵌的测试用例 (cases 字段)。
    """
    if depth > MAX_RECURSION_DEPTH:
        logger.warning("Apifox collection depth > %d, stopping at: %s", MAX_RECURSION_DEPTH, node.get("name"))
        return

    name = node.get("name", "未命名")
    apifox_id = node.get("id")

    if "api" in node:
        api = _parse_apifox_api(node, name, apifox_id)
        api["category_ref"] = parent_id
        apis.append(api)

        # 提取 API 节点中内嵌的测试用例 (cases 字段)
        if test_cases is not None:
            api_data = node.get("api", {})
            # 使用 API 的实际 ID（可能在 api 对象内部）
            actual_api_id = apifox_id or api_data.get("id")
            for tc in api_data.get("cases", []):
                if not isinstance(tc, dict):
                    continue
                tc_name = tc.get("name", "未命名")
                if not tc_name:
                    continue
                # 内嵌用例的 api_id 就是当前 API 的 ID
                test_cases.append({
                    "name": tc_name,
                    "api_id": actual_api_id,
                    "description": tc.get("description", ""),
                    "priority": "P1",
                    "status": "active",
                    "pre_script": "",
                    "post_script": "",
                    "assertions": [],
                    "extract_vars": [],
                    "request_body": None,
                    "tags": str(tc.get("tagIds", "")),
                })
        return

    # 也检查没有 "api" 包裹的节点是否直接有 method/path（某些 Apifox 版本）
    if "method" in node and "path" in node and "items" not in node:
        api = _parse_apifox_api({"api": node}, name, apifox_id)
        api["category_ref"] = parent_id
        apis.append(api)
        return

    # 跳过无 api/items/method/path 的节点（如测试用例 httpApiCase 节点）
    if not node.get("items"):
        return

    if "items" in node:
        if name == "根目录" and depth == 0:
            for child in node.get("items", []):
                if not isinstance(child, dict):
                    continue
                try:
                    _walk_apifox_collection(child, None, depth + 1, categories, apis, test_cases)
                except Exception as e:
                    logger.warning("遍历根目录子节点失败 (name=%s): %s", child.get("name"), e)
                    continue
            return

        effective_id = apifox_id if apifox_id else f"gen_{depth}_{len(categories)}"
        cat = {
            "name": name,
            "parent_ref": parent_id,
            "depth": depth,
            "apifox_id": effective_id,
            "children_count": len(node.get("items", [])),
        }
        categories.append(cat)
        cat_ref = f"cat_{effective_id}"
        for child in node.get("items", []):
            if not isinstance(child, dict):
                logger.warning("跳过非字典子节点: %s", type(child).__name__)
                continue
            try:
                _walk_apifox_collection(child, cat_ref, depth + 1, categories, apis, test_cases)
            except RecursionError:
                logger.warning("Apifox collection 嵌套过深，停止递归 (depth=%d, name=%s)", depth + 1, child.get("name"))
                break
            except Exception as e:
                logger.warning("遍历子节点失败 (name=%s): %s", child.get("name"), e)
                continue


# =============================================================================
#  格式: Postman Collection
# =============================================================================


def _parse_postman_collection(data: dict) -> Tuple[List[Dict], List[Dict], Optional[str]]:
    """解析 Postman Collection v2.x。

    返回: (categories, apis, project_name)
    """
    info = data.get("info", {})
    project_name = info.get("name", "")
    items = data.get("item", [])

    categories = []
    apis = []

    def walk_postman(items_list, parent_ref=None, depth=0):
        for idx, item in enumerate(items_list):
            if "item" in item:
                # 这是一个文件夹
                cat = {
                    "name": item.get("name", f"Folder {idx}"),
                    "parent_ref": parent_ref,
                    "depth": depth,
                    "apifox_id": f"postman_{depth}_{idx}",
                }
                categories.append(cat)
                cat_ref = f"cat_{cat['apifox_id']}"
                walk_postman(item["item"], cat_ref, depth + 1)
            elif "request" in item:
                req = item["request"]
                method = req.get("method", "GET").upper()
                if method not in HTTP_METHODS:
                    method = "GET"

                url_raw = req.get("url", {})
                if isinstance(url_raw, str):
                    path_url = url_raw
                elif isinstance(url_raw, dict):
                    raw = url_raw.get("raw", "/")
                    path_url = raw.split("?")[0] if "?" in raw else raw
                else:
                    path_url = "/"

                # Headers
                headers = []
                for h in req.get("header", []):
                    headers.append({
                        "key": h.get("key", ""),
                        "value": h.get("value", ""),
                        "enabled": not h.get("disabled", False),
                    })

                # Query params
                params = []
                if isinstance(url_raw, dict):
                    for q in url_raw.get("query", []):
                        params.append({
                            "key": q.get("key", ""),
                            "value": q.get("value", ""),
                            "enabled": not q.get("disabled", False),
                        })

                # Body
                body_data = req.get("body", {})
                body_mode = body_data.get("mode", "none")
                body = {"type": body_mode, "content": body_data.get(body_mode, "")}

                # Auth
                auth_data = req.get("auth", {})
                auth_type = auth_data.get("type", "none")

                apis.append({
                    "name": item.get("name", f"{method} {path_url}"),
                    "method": method,
                    "path": path_url,
                    "apifox_id": f"postman_api_{depth}_{idx}",
                    "category_ref": parent_ref,
                    "headers": headers,
                    "params": params,
                    "body": body,
                    "auth_type": auth_type,
                    "auth": auth_data,
                    "pre_script": "",
                    "post_script": "",
                    "response_schema": None,
                    "response_examples": [],
                    "description": item.get("description", req.get("description", "")),
                    "status": "developing",
                    "settings": {},
                })

    walk_postman(items)
    return categories, apis, project_name


# =============================================================================
#  格式: OpenAPI / Swagger
# =============================================================================


def _parse_openapi_spec(spec: dict) -> Tuple[List[Dict], List[Dict], Optional[str]]:
    """解析 OpenAPI/Swagger 规范。

    返回: (categories, apis, project_name)
    """
    info = spec.get("info", {})
    project_name = info.get("title", "")

    paths = spec.get("paths", {})
    if not isinstance(paths, dict):
        return [], [], project_name

    # 收集所有 tag，作为分类
    tag_names = []
    for tag in spec.get("tags", []):
        if isinstance(tag, dict) and "name" in tag:
            tag_names.append(tag["name"])

    # 从全局 security scheme 提取认证信息
    security_schemes = {}
    components = spec.get("components", spec.get("securityDefinitions", {}))
    if isinstance(components, dict):
        for name, scheme in components.get("securitySchemes", components.get("securityDefinitions", {})).items():
            if isinstance(scheme, dict):
                security_schemes[name] = scheme.get("type", "apiKey")

    global_security = spec.get("security", [])
    
    categories = []
    apis = []
    cat_ref_cache = {}
    cat_idx = 0

    def get_cat_ref(tag_name: str) -> str:
        nonlocal cat_idx
        if tag_name not in cat_ref_cache:
            cat_idx += 1
            cat_ref_cache[tag_name] = f"cat_openapi_{cat_idx}"
            categories.append({
                "name": tag_name,
                "parent_ref": None,
                "depth": 0,
                "apifox_id": f"openapi_{cat_idx}",
            })
        return cat_ref_cache[tag_name]

    apis_idx = 0
    for path, methods in paths.items():
        if not isinstance(methods, dict):
            continue

        for method, detail in methods.items():
            method_upper = method.upper()
            if method_upper not in HTTP_METHODS:
                continue
            if not isinstance(detail, dict):
                continue

            apis_idx += 1
            tags = detail.get("tags", ["未分类"])
            if not tags:
                tags = ["未分类"]
            cat_ref = get_cat_ref(tags[0])

            # Parameters
            params = []
            for p in detail.get("parameters", []):
                if not isinstance(p, dict):
                    continue
                p_in = p.get("in", "query")
                if p_in in ("query", "path"):
                    schema = p.get("schema", {})
                    params.append({
                        "key": p.get("name", ""),
                        "value": p.get("example", schema.get("example", "")),
                        "enabled": p.get("required", False),
                        "required": p.get("required", False),
                        "description": p.get("description", ""),
                        "type": schema.get("type", "string") if isinstance(schema, dict) else "string",
                        "in": p_in,
                    })

            # Headers
            headers = []
            for p in detail.get("parameters", []):
                if isinstance(p, dict) and p.get("in") == "header":
                    headers.append({
                        "key": p.get("name", ""),
                        "value": p.get("example", p.get("schema", {}).get("example", "")),
                        "enabled": p.get("required", False),
                    })

            # Body
            body = {"type": "none", "content": ""}
            request_body = detail.get("requestBody", {})
            if isinstance(request_body, dict):
                content = request_body.get("content", {})
                for ct, ct_spec in content.items():
                    if isinstance(ct_spec, dict):
                        example = ct_spec.get("example")
                        if example:
                            body = {
                                "type": _body_type(ct),
                                "content_type": ct,
                                "content": json.dumps(example, ensure_ascii=False, indent=2) if isinstance(example, (dict, list)) else str(example),
                                "schema": ct_spec.get("schema"),
                            }
                            break

            # Auth
            auth_config = detail.get("security", global_security)
            auth_type = "none"
            if auth_config:
                for sec_item in auth_config:
                    if isinstance(sec_item, dict):
                        for scheme_name in sec_item:
                            auth_type = security_schemes.get(scheme_name, "apiKey")
                            break
                        break

            # Response schema
            response_schema = None
            responses = detail.get("responses", {})
            for status, resp_detail in responses.items():
                if isinstance(resp_detail, dict):
                    content = resp_detail.get("content", {})
                    for ct, ct_spec in content.items():
                        if isinstance(ct_spec, dict):
                            response_schema = {
                                "status_code": status,
                                "content_type": ct,
                                "schema": ct_spec.get("schema"),
                            }
                            break
                    break

            apis.append({
                "name": detail.get("summary", detail.get("operationId", f"{method_upper} {path}")),
                "method": method_upper,
                "path": path,
                "apifox_id": f"openapi_api_{apis_idx}",
                "category_ref": cat_ref,
                "headers": headers,
                "params": params,
                "body": body,
                "auth_type": auth_type,
                "auth": {"type": auth_type},
                "pre_script": "",
                "post_script": "",
                "response_schema": response_schema,
                "response_examples": [],
                "description": detail.get("description", ""),
                "status": "developing",
                "settings": {},
            })

    return categories, apis, project_name


# =============================================================================
#  Apifox 测试用例解析
# =============================================================================


def _parse_apifox_test_cases(data: dict) -> List[Dict]:
    """解析 Apifox 文件中的测试用例。

    Apifox 测试用例结构:
      - apiTestCaseCollection[]: 每个是分组
        - children[]: 子分组
        - items[]: 用例项
          - apiId: 关联的接口 ID
          - name: 用例名称
          - request: {params, headers, body, auth} 覆盖
          - response: {statusCode, responseTime, responseJson}
          - scripts: {preOperation, postOperation}
          - extractVariables: [{name, expression, extractType}]
          - assertions: [{type, expression, expected, comparator}]
    """
    test_cases = []
    tc_collection = data.get("apiTestCaseCollection", [])

    for tc_group in tc_collection:
        if isinstance(tc_group, dict) and "items" in tc_group:
            _walk_apifox_testcases([tc_group], test_cases)

    return test_cases


def _walk_apifox_testcases(items: List[Dict], result: List[Dict], parent_name: str = "") -> None:
    """递归遍历 Apifox 测试用例树。

    支持三种格式:
      - 文件夹节点: 有 items/children 但无 apiId 和 steps → 递归子节点
      - 单接口用例: 直接有 apiId
      - 场景用例: 有 steps[]，使用第一个 step 的 bindId 作为关联的 API
    """
    for item in items:
        if not isinstance(item, dict):
            continue
        name = item.get("name", "未命名")
        full_name = f"{parent_name}/{name}" if parent_name else name

        has_steps = "steps" in item and isinstance(item["steps"], list)
        has_api_id = item.get("apiId") is not None

        # 文件夹节点：有 children/items 但无 apiId 和 steps → 只递归
        if not has_api_id and not has_steps:
            if "children" in item:
                _walk_apifox_testcases(item["children"], result, full_name)
            if "items" in item:
                _walk_apifox_testcases(item["items"], result, full_name)
            continue

        # 场景用例：有 steps
        if has_steps:
            api_id = None
            request_body = None
            assertions = []
            extract_vars = []

            # 取第一个步骤的 API 引用
            for step in item["steps"]:
                if isinstance(step, dict) and step.get("bindType") == "API":
                    api_id = step.get("bindId")
                    break

            # 将 Apifox priority 数字转为 P0/P1/P2 格式
            raw_priority = item.get("priority", "P1")
            if isinstance(raw_priority, int):
                priority = f"P{raw_priority}"
            else:
                priority = str(raw_priority) if raw_priority else "P1"

            result.append({
                "name": name,
                "api_id": api_id,
                "description": item.get("description", ""),
                "priority": priority,
                "status": "active",
                "pre_script": "",
                "post_script": "",
                "assertions": assertions,
                "extract_vars": extract_vars,
                "request_body": None,
                "tags": json.dumps(item.get("tags", []), ensure_ascii=False) if isinstance(item.get("tags"), list) else str(item.get("tags", "")),
            })
            # 场景用例也可能有子节点
            if "children" in item:
                _walk_apifox_testcases(item["children"], result, full_name)
            if "items" in item:
                _walk_apifox_testcases(item["items"], result, full_name)
            continue

        # 单接口用例：直接有 apiId
        api_id = item.get("apiId")

        # 断言
        assertions = []
        for a in item.get("assertions", []):
            if isinstance(a, dict):
                assertions.append({
                    "type": a.get("type", "jsonpath"),
                    "expression": a.get("expression", ""),
                    "expected": a.get("expected", ""),
                    "comparator": a.get("comparator", "eq"),
                })

        # 提取变量
        extract_vars = []
        for ev in item.get("extractVariables", []):
            if isinstance(ev, dict):
                extract_vars.append({
                    "name": ev.get("name", ""),
                    "expression": ev.get("expression", ""),
                    "type": ev.get("extractType", "jsonpath"),
                })

        # Scripts
        scripts = item.get("scripts", {})
        if not isinstance(scripts, dict):
            scripts = {}

        # 自定义请求覆盖
        request_body = None
        tc_request = item.get("request", {})
        if isinstance(tc_request, dict):
            request_body = _extract_body(tc_request.get("requestBody"))

        result.append({
            "name": name,
            "api_id": api_id,
            "description": item.get("description", ""),
            "priority": "P1",
            "status": "active",
            "pre_script": scripts.get("preOperation", ""),
            "post_script": scripts.get("postOperation", ""),
            "assertions": assertions,
            "extract_vars": extract_vars,
            "request_body": request_body,
            "tags": str(item.get("tags", "")),
        })

        # 递归处理子节点
        if "children" in item:
            _walk_apifox_testcases(item["children"], result, full_name)
        if "items" in item:
            _walk_apifox_testcases(item["items"], result, full_name)


# =============================================================================
#  格式: YAPI 导出
# =============================================================================


def _parse_yapi(data: dict) -> Tuple[List[Dict], List[Dict], Optional[str]]:
    """解析 YAPI 导出的 JSON 格式。

    YAPI 典型结构:
    {
        "project": {"name": "项目名", "description": "..."},
        "menu": [{"name": "分类", "list": [...]}],
        "list": [{API对象}]
    }
    或:
    {
        "interfaces": [{API对象}],
        "cat": [{分类对象}]
    }
    """
    categories = []
    apis = []
    project_name = data.get("project", {}).get("name") or data.get("name", "YAPI项目")

    # 方式1: menu + list 结构
    menu = data.get("menu", [])
    if menu:
        for cat in menu:
            cat_name = cat.get("name", "未命名")
            cat_id = f"cat_{cat.get('_id', cat_name)}"
            categories.append({
                "name": cat_name,
                "parent_ref": None,
                "depth": 0,
                "apifox_id": cat_id,
            })

            for api_item in cat.get("list", []):
                api = _parse_yapi_item(api_item, cat_id)
                if api:
                    apis.append(api)

    # 方式2: interfaces + cat 结构
    interfaces = data.get("interfaces", [])
    for api_item in interfaces:
        cat_name = api_item.get("catname", "默认分类")
        cat_id = f"cat_{api_item.get('catid', 'default')}"
        if not any(c["name"] == cat_name for c in categories):
            categories.append({
                "name": cat_name,
                "parent_ref": None,
                "depth": 0,
                "apifox_id": cat_id,
            })
        api = _parse_yapi_item(api_item, cat_id)
        if api:
            apis.append(api)

    # 方式3: 顶层 list 结构
    list_items = data.get("list", [])
    for api_item in list_items:
        api = _parse_yapi_item(api_item, None)
        if api:
            apis.append(api)

    return categories, apis, project_name


def _parse_yapi_item(item: dict, category_ref: Optional[str]) -> Optional[Dict]:
    """解析 YAPI 单个接口项"""
    if not isinstance(item, dict):
        return None

    method = item.get("method", "GET").upper()
    if method not in HTTP_METHODS:
        method = "GET"

    path = item.get("path", item.get("url", "/"))
    if path.startswith("http"):
        parsed = urlparse(path)
        path = parsed.path or "/"

    # 解析 headers
    headers = []
    for h in item.get("req_headers", []):
        if isinstance(h, dict):
            headers.append({
                "key": h.get("name", ""),
                "value": h.get("value", ""),
                "enabled": h.get("enable", True),
            })

    # 解析 params
    params = []
    for p in item.get("req_params", []):
        if isinstance(p, dict):
            params.append({
                "key": p.get("name", ""),
                "value": p.get("value", ""),
                "enabled": True,
            })

    # 解析 body
    body = {"type": "none", "content": ""}
    req_body = item.get("req_body_other", item.get("req_body_form", item.get("req_body_type")))
    if req_body:
        body_type = "json"
        if item.get("req_body_is_json_params") == 1:
            body_type = "form"
        body = {
            "type": body_type,
            "content_type": "application/json",
            "content": str(req_body) if isinstance(req_body, str) else json.dumps(req_body, ensure_ascii=False),
        }

    return {
        "name": item.get("title", item.get("name", "未命名")),
        "method": method,
        "path": path,
        "apifox_id": f"yapi_{item.get('_id', item.get('id', ''))}",
        "category_ref": category_ref,
        "headers": headers,
        "params": params,
        "body": body,
        "auth_type": "none",
        "auth": {"type": "none"},
        "pre_script": item.get("req_script", ""),
        "post_script": item.get("res_script", ""),
        "response_schema": None,
        "response_examples": [],
        "description": item.get("desc", ""),
        "status": "developing",
        "settings": {},
    }


# =============================================================================
#  格式: Eolink 导出
# =============================================================================


def _parse_eolink(data: dict) -> Tuple[List[Dict], List[Dict], Optional[str]]:
    """解析 Eolink 导出的 JSON 格式。

    Eolink 典型结构:
    {
        "projectName": "项目名",
        "apiList": [{API对象}]
    }
    或:
    {
        "project": {"name": "...", "apiTree": [...]}
    }
    """
    categories = []
    apis = []
    project_name = data.get("projectName", "Eolink项目")

    # 获取 API 列表
    api_list = data.get("apiList", [])
    if not api_list and "project" in data:
        project = data["project"]
        project_name = project.get("name", project_name)
        api_list = project.get("apiList", project.get("apiTree", []))

    for item in api_list:
        if not isinstance(item, dict):
            continue

        cat_name = item.get("apiClassificationName", item.get("groupName", "默认分类"))
        cat_id = f"cat_{item.get('apiClassificationId', cat_name)}"
        if not any(c["name"] == cat_name for c in categories):
            categories.append({
                "name": cat_name,
                "parent_ref": None,
                "depth": 0,
                "apifox_id": cat_id,
            })

        api = _parse_eolink_item(item, cat_id)
        if api:
            apis.append(api)

    return categories, apis, project_name


def _parse_eolink_item(item: dict, category_ref: Optional[str]) -> Optional[Dict]:
    """解析 Eolink 单个接口项"""
    if not isinstance(item, dict):
        return None

    method = item.get("apiProtocol", item.get("method", "GET")).upper()
    if method not in HTTP_METHODS:
        method = "GET"

    path = item.get("apiURI", item.get("path", item.get("url", "/")))
    if path.startswith("http"):
        parsed = urlparse(path)
        path = parsed.path or "/"

    headers = []
    for h in item.get("apiRequestParams", {}).get("header", []):
        if isinstance(h, dict):
            headers.append({
                "key": h.get("name", ""),
                "value": h.get("value", ""),
                "enabled": True,
            })

    params = []
    for p in item.get("apiRequestParams", {}).get("query", []):
        if isinstance(p, dict):
            params.append({
                "key": p.get("name", ""),
                "value": p.get("value", ""),
                "enabled": True,
            })

    body = {"type": "none", "content": ""}
    req_body = item.get("apiRequestParam", item.get("requestBody"))
    if req_body:
        body = {
            "type": "json",
            "content_type": "application/json",
            "content": str(req_body) if isinstance(req_body, str) else json.dumps(req_body, ensure_ascii=False),
        }

    return {
        "name": item.get("apiName", item.get("name", "未命名")),
        "method": method,
        "path": path,
        "apifox_id": f"eolink_{item.get('id', '')}",
        "category_ref": category_ref,
        "headers": headers,
        "params": params,
        "body": body,
        "auth_type": "none",
        "auth": {"type": "none"},
        "pre_script": "",
        "post_script": "",
        "response_schema": None,
        "response_examples": [],
        "description": item.get("apiDescription", ""),
        "status": "developing",
        "settings": {},
    }


# =============================================================================
#  格式: Apipost 导出
# =============================================================================


def _parse_apipost(data: dict) -> Tuple[List[Dict], List[Dict], Optional[str]]:
    """解析 Apipost 导出的 JSON 格式。

    Apipost 典型结构:
    {
        "projectInfo": {"name": "项目名"},
        "collections": [{分组}]
    }
    """
    categories = []
    apis = []
    project_name = data.get("projectInfo", {}).get("name", "Apipost项目")

    collections = data.get("collections", [])
    for collection in collections:
        if not isinstance(collection, dict):
            continue

        cat_name = collection.get("name", "未命名")
        cat_id = f"cat_{collection.get('id', cat_name)}"
        categories.append({
            "name": cat_name,
            "parent_ref": None,
            "depth": 0,
            "apifox_id": cat_id,
        })

        for item in collection.get("apiList", collection.get("items", [])):
            api = _parse_apipost_item(item, cat_id)
            if api:
                apis.append(api)

    return categories, apis, project_name


def _parse_apipost_item(item: dict, category_ref: Optional[str]) -> Optional[Dict]:
    """解析 Apipost 单个接口项"""
    if not isinstance(item, dict):
        return None

    method = item.get("method", "GET").upper()
    if method not in HTTP_METHODS:
        method = "GET"

    path = item.get("url", item.get("path", "/"))
    if path.startswith("http"):
        parsed = urlparse(path)
        path = parsed.path or "/"

    headers = []
    for h in item.get("headers", []):
        if isinstance(h, dict):
            headers.append({
                "key": h.get("key", h.get("name", "")),
                "value": h.get("value", ""),
                "enabled": h.get("enabled", True),
            })

    params = []
    for p in item.get("params", []):
        if isinstance(p, dict):
            params.append({
                "key": p.get("key", p.get("name", "")),
                "value": p.get("value", ""),
                "enabled": p.get("enabled", True),
            })

    body = {"type": "none", "content": ""}
    req_body = item.get("body", item.get("requestBody"))
    if req_body:
        body_type = item.get("bodyType", "json")
        body = {
            "type": body_type,
            "content_type": "application/json",
            "content": str(req_body) if isinstance(req_body, str) else json.dumps(req_body, ensure_ascii=False),
        }

    return {
        "name": item.get("name", "未命名"),
        "method": method,
        "path": path,
        "apifox_id": f"apipost_{item.get('id', '')}",
        "category_ref": category_ref,
        "headers": headers,
        "params": params,
        "body": body,
        "auth_type": "none",
        "auth": {"type": "none"},
        "pre_script": "",
        "post_script": "",
        "response_schema": None,
        "response_examples": [],
        "description": item.get("description", ""),
        "status": "developing",
        "settings": {},
    }


# =============================================================================
#  格式: Bruno 导出
# =============================================================================


def _parse_bruno(data: dict) -> Tuple[List[Dict], List[Dict], Optional[str]]:
    """解析 Bruno 导出的 JSON 格式。

    Bruno 典型结构:
    {
        "version": "1",
        "name": "Collection Name",
        "collections": [{请求}]
    }
    """
    categories = []
    apis = []
    project_name = data.get("name", "Bruno项目")

    collections = data.get("collections", [])
    for item in collections:
        if not isinstance(item, dict):
            continue

        api = _parse_bruno_item(item)
        if api:
            apis.append(api)

    return categories, apis, project_name


def _parse_bruno_item(item: dict) -> Optional[Dict]:
    """解析 Bruno 单个请求项"""
    if not isinstance(item, dict):
        return None

    method = item.get("method", item.get("httpMethod", "GET")).upper()
    if method not in HTTP_METHODS:
        method = "GET"

    path = item.get("url", item.get("path", "/"))
    if path.startswith("http"):
        parsed = urlparse(path)
        path = parsed.path or "/"

    headers = []
    for h in item.get("headers", []):
        if isinstance(h, dict):
            headers.append({
                "key": h.get("key", ""),
                "value": h.get("value", ""),
                "enabled": h.get("enabled", True),
            })

    params = []
    for p in item.get("query", []):
        if isinstance(p, dict):
            params.append({
                "key": p.get("key", ""),
                "value": p.get("value", ""),
                "enabled": p.get("enabled", True),
            })

    body = {"type": "none", "content": ""}
    req_body = item.get("body", item.get("requestBody"))
    if req_body:
        body = {
            "type": "json",
            "content_type": "application/json",
            "content": str(req_body) if isinstance(req_body, str) else json.dumps(req_body, ensure_ascii=False),
        }

    return {
        "name": item.get("name", "未命名"),
        "method": method,
        "path": path,
        "apifox_id": f"bruno_{item.get('uid', item.get('id', ''))}",
        "category_ref": None,
        "headers": headers,
        "params": params,
        "body": body,
        "auth_type": "none",
        "auth": {"type": "none"},
        "pre_script": item.get("script", ""),
        "post_script": "",
        "response_schema": None,
        "response_examples": [],
        "description": "",
        "status": "developing",
        "settings": {},
    }


# =============================================================================
#  格式: HAR (HTTP Archive)
# =============================================================================


def _parse_har(data: dict) -> Tuple[List[Dict], List[Dict], Optional[str]]:
    """解析 HAR (HTTP Archive) 格式。

    HAR 是浏览器 DevTools 导出的标准格式，结构:
    {
      "log": {
        "version": "1.2",
        "entries": [
          {
            "request": {
              "method": "GET",
              "url": "https://api.example.com/path?q=1",
              "headers": [...],
              "queryString": [...],
              "postData": { "mimeType": "application/json", "text": "{}" }
            },
            "response": { ... }
          }
        ]
      }
    }
    """
    from urllib.parse import urlparse
    project_name = data.get("log", {}).get("creator", {}).get("name", "HAR Import")
    categories = []
    apis = []
    entries = data.get("log", {}).get("entries", [])

    host_categories = {}
    for i, entry in enumerate(entries):
        req = entry.get("request", {})
        if not req:
            continue

        method = req.get("method", "GET").upper()
        url = req.get("url", "")

        # 解析 URL
        try:
            parsed = urlparse(url)
        except Exception:
            parsed = None
        path = parsed.path if parsed else "/"
        host = parsed.hostname if parsed else "unknown"
        scheme = parsed.scheme if parsed else "https"

        # Query params
        params = []
        for q in req.get("queryString", []):
            if isinstance(q, dict):
                params.append({
                    "key": q.get("name", ""),
                    "value": q.get("value", ""),
                    "enabled": True,
                })

        # Headers
        headers = []
        seen_keys = set()
        for h in req.get("headers", []):
            if isinstance(h, dict):
                key = h.get("name", "")
                if key and key.lower() not in seen_keys:
                    seen_keys.add(key.lower())
                    headers.append({
                        "key": key,
                        "value": h.get("value", ""),
                        "enabled": True,
                    })

        # Body
        body = {"type": "none", "content": ""}
        post_data = req.get("postData")
        if post_data and isinstance(post_data, dict):
            mime = post_data.get("mimeType", "")
            text = post_data.get("text", "")
            if text:
                content_type = "json"
                if "x-www-form-urlencoded" in mime:
                    content_type = "form-urlencoded"
                elif "form-data" in mime:
                    content_type = "form-data"
                body = {
                    "type": content_type,
                    "content_type": mime,
                    "content": text,
                }

        category_name = f"{scheme}://{host}"
        cat_ref = f"cat_{host}" if host else None

        api = {
            "name": f"{method} {path}" or f"HAR Entry {i}",
            "method": method,
            "path": path,
            "apifox_id": f"har_{i}_{entry.get('startedDateTime', '')}",
            "category_ref": cat_ref,
            "headers": headers,
            "params": params,
            "body": body,
            "auth_type": "none",
            "auth": {"type": "none"},
            "pre_script": "",
            "post_script": "",
            "response_schema": None,
            "response_examples": [],
            "description": f"从 HAR 导入: {url}",
            "status": "developing",
            "settings": {},
        }
        apis.append(api)

        if host and host not in host_categories:
            host_categories[host] = {"name": host, "count": 0}
        if host in host_categories:
            host_categories[host]["count"] += 1

    # 按 host 创建分类
    for host, info in host_categories.items():
        cat_ref = f"cat_{host}"
        categories.append({
            "name": info["name"],
            "parent_ref": None,
            "depth": 0,
            "apifox_id": host,
        })
        # 设置 API 的 category_ref
        for api in apis:
            if api["category_ref"] == cat_ref:
                api["category_ref"] = cat_ref

    return categories, apis, project_name


# =============================================================================
#  格式: cURL 命令
# =============================================================================


def _parse_curl(text: str) -> Tuple[List[Dict], List[Dict], Optional[str]]:
    """解析 cURL 命令字符串为 API 定义。

    支持:
      curl -X POST https://api.example.com/path \\
        -H "Content-Type: application/json" \\
        -d '{"key": "value"}'
      curl https://api.example.com/path (默认 GET)
      curl url -X GET --data 'body' --header 'Key: Value'
    """
    from urllib.parse import urlparse, unquote_plus
    project_name = "cURL Import"
    categories = []
    apis = []

    if not text or not text.strip():
        return categories, apis, project_name

    text = text.strip()
    # 移除开头的 curl
    if text.startswith("curl "):
        text = text[5:]

    method = "GET"
    url = ""
    headers = []
    body_data = ""

    # 简单的参数解析
    args = []
    current = ""
    in_single_quote = False
    in_double_quote = False
    i = 0
    while i < len(text):
        ch = text[i]
        if ch == "'" and not in_double_quote:
            in_single_quote = not in_single_quote
            current += ch
        elif ch == '"' and not in_single_quote:
            in_double_quote = not in_double_quote
            current += ch
        elif (ch in ' \\n\\r\\t') and not in_single_quote and not in_double_quote:
            if current.strip():
                args.append(current.strip())
            current = ""
        else:
            current += ch
        i += 1
    if current.strip():
        args.append(current.strip())

    skip_next = False
    for j, arg in enumerate(args):
        if skip_next:
            skip_next = False
            continue
        if arg in ("-X", "--request"):
            if j + 1 < len(args):
                method = args[j + 1].upper()
                skip_next = True
        elif arg in ("-H", "--header"):
            if j + 1 < len(args):
                hl = args[j + 1]
                if hl.startswith("'") and hl.endswith("'"):
                    hl = hl[1:-1]
                elif hl.startswith('"') and hl.endswith('"'):
                    hl = hl[1:-1]
                if ":" in hl:
                    k, v = hl.split(":", 1)
                    headers.append({"key": k.strip(), "value": v.strip(), "enabled": True})
                skip_next = True
        elif arg in ("-d", "--data", "--data-raw", "--data-binary"):
            if j + 1 < len(args):
                body_data = args[j + 1]
                if body_data.startswith("'") and body_data.endswith("'"):
                    body_data = body_data[1:-1]
                elif body_data.startswith('"') and body_data.endswith('"'):
                    body_data = body_data[1:-1]
                skip_next = True
        elif arg == "--compressed" or arg.startswith("-"):
            continue
        elif not arg.startswith("-"):
            # URL
            url = arg
            if url.startswith("'") and url.endswith("'"):
                url = url[1:-1]
            elif url.startswith('"') and url.endswith('"'):
                url = url[1:-1]

    if not url:
        return categories, apis, project_name

    try:
        parsed = urlparse(url)
    except Exception:
        parsed = None

    path = parsed.path if parsed else "/"
    if not path:
        path = "/"

    # Query params
    params = []
    if parsed and parsed.query:
        for q in parsed.query.split("&"):
            if "=" in q:
                k, v = q.split("=", 1)
                params.append({"key": unquote_plus(k), "value": unquote_plus(v), "enabled": True})

    # Body
    body = {"type": "none", "content": ""}
    if body_data:
        ct = "application/json"
        for h in headers:
            if h["key"].lower() == "content-type":
                ct = h["value"]
                break
        body_type = "json"
        if "x-www-form-urlencoded" in ct:
            body_type = "form-urlencoded"
        elif "form-data" in ct:
            body_type = "form-data"
        body = {"type": body_type, "content_type": ct, "content": body_data}

    api = {
        "name": f"{method} {path}",
        "method": method,
        "path": path,
        "apifox_id": f"curl_{hash(text) % (2**31)}",
        "category_ref": None,
        "headers": headers,
        "params": params,
        "body": body,
        "auth_type": "none",
        "auth": {"type": "none"},
        "pre_script": "",
        "post_script": "",
        "response_schema": None,
        "response_examples": [],
        "description": f"从 cURL 导入: {method} {url}",
        "status": "developing",
        "settings": {},
    }
    apis.append(api)

    return categories, apis, project_name


# =============================================================================
#  格式: 通用 JSON 格式
# =============================================================================


def _parse_general_json(data: dict) -> Tuple[List[Dict], List[Dict], Optional[str]]:
    """解析通用 JSON 格式。

    支持的格式:
    - 数组格式: [{"name": "...", "method": "...", "url": "..."}]
    - 对象格式: {"apis": [...], "project": "项目名"}
    """
    categories = []
    apis = []
    project_name = data.get("project", data.get("name", "通用项目"))

    # 获取 API 列表（支持多种键名）
    api_list = (
        data.get("apis") or data.get("items") or data.get("apiList")
        or data.get("endpoints") or data.get("routes") or data.get("operations")
        or []
    )

    # 如果是顶层数组直接使用
    if isinstance(data, list):
        api_list = data

    for item in api_list:
        if not isinstance(item, dict):
            continue

        api = _parse_general_json_item(item)
        if api:
            apis.append(api)

    return categories, apis, project_name


def _parse_general_json_item(item: dict) -> Optional[Dict]:
    """解析通用 JSON 单个接口项"""
    if not isinstance(item, dict):
        return None

    # 尝试多种字段名
    method = (
        item.get("method") or
        item.get("httpMethod") or
        item.get("requestMethod") or
        item.get("verb") or
        item.get("type", "GET")
    )
    if not isinstance(method, str):
        method = "GET"
    method = method.upper()
    if method not in HTTP_METHODS:
        method = "GET"

    path = (
        item.get("url") or
        item.get("path") or
        item.get("apiPath") or
        item.get("requestUrl") or
        item.get("endpoint") or
        item.get("uri") or
        item.get("route", "/")
    )
    if not path:
        path = "/"
    if path.startswith("http"):
        parsed = urlparse(path)
        path = parsed.path or "/"

    headers = []
    raw_headers = item.get("headers", item.get("header", []))
    if isinstance(raw_headers, list):
        for h in raw_headers:
            if isinstance(h, dict):
                headers.append({
                    "key": str(h.get("key", h.get("name", ""))),
                    "value": str(h.get("value", "")),
                    "enabled": True,
                })

    params = []
    raw_params = item.get("params", item.get("query", item.get("queryParams", [])))
    if isinstance(raw_params, list):
        for p in raw_params:
            if isinstance(p, dict):
                params.append({
                    "key": str(p.get("key", p.get("name", ""))),
                    "value": str(p.get("value", "")),
                    "enabled": True,
                })

    body = {"type": "none", "content": ""}
    req_body = (
        item.get("body") or
        item.get("requestBody") or
        item.get("data") or
        item.get("payload")
    )
    if req_body:
        body = {
            "type": "json",
            "content_type": "application/json",
            "content": str(req_body) if isinstance(req_body, str) else json.dumps(req_body, ensure_ascii=False),
        }

    return {
        "name": item.get("name", item.get("title", item.get("apiName", item.get("summary", "未命名")))),
        "method": method,
        "path": path,
        "apifox_id": f"general_{item.get('id', item.get('_id', ''))}",
        "category_ref": None,
        "headers": headers,
        "params": params,
        "body": body,
        "auth_type": "none",
        "auth": {"type": "none"},
        "pre_script": "",
        "post_script": "",
        "response_schema": None,
        "response_examples": [],
        "description": item.get("description", item.get("desc", "")),
        "status": "developing",
        "settings": {},
    }


