"""HAR (HTTP Archive) 导入解析器

增强特性（相比 format_parsers._parse_har）：
- 按 domain/path prefix 分组
- 从 request/response 对生成测试用例
- 提取更完整的请求/响应信息
- 去重相同 method+path 的请求
"""

import json
import logging
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

from app.services.format_parsers import HTTP_METHODS, _body_type

logger = logging.getLogger("import.har")


def _parse_har_headers(headers_list: list) -> List[Dict]:
    """解析 HAR headers 数组，去重同名 header（保留第一个）。"""
    result = []
    seen_keys = set()
    for h in headers_list:
        if not isinstance(h, dict):
            continue
        key = h.get("name", "")
        if not key:
            continue
        lower_key = key.lower()
        # 跳过浏览器自动添加的无关 header
        if lower_key in (":method", ":authority", ":scheme", ":path"):
            continue
        if lower_key not in seen_keys:
            seen_keys.add(lower_key)
            result.append({
                "key": key,
                "value": h.get("value", ""),
                "enabled": True,
            })
    return result


def _parse_har_query_string(qs_list: list) -> List[Dict]:
    """解析 HAR queryString 数组。"""
    result = []
    for q in qs_list:
        if not isinstance(q, dict):
            continue
        result.append({
            "key": q.get("name", ""),
            "value": q.get("value", ""),
            "enabled": True,
        })
    return result


def _parse_har_post_data(post_data: Optional[dict]) -> Dict:
    """解析 HAR postData 字段。"""
    if not post_data or not isinstance(post_data, dict):
        return {"type": "none", "content": ""}

    mime = post_data.get("mimeType", "")
    text = post_data.get("text", "")

    if not text:
        # 尝试 params（form-data）
        params = post_data.get("params", [])
        if params:
            form_items = []
            for p in params:
                if isinstance(p, dict):
                    form_items.append({
                        "key": p.get("name", ""),
                        "value": p.get("value", ""),
                    })
            text = json.dumps(form_items, ensure_ascii=False)

    if not text:
        return {"type": "none", "content": ""}

    content_type = _body_type(mime)
    return {
        "type": content_type,
        "content_type": mime or "application/octet-stream",
        "content": text,
    }


def _extract_response_info(response: Optional[dict]) -> Dict:
    """从 HAR response 中提取信息，用于生成测试用例的断言。"""
    if not response or not isinstance(response, dict):
        return {}

    status = response.get("status")
    content = response.get("content", {})
    mime = content.get("mimeType", "") if isinstance(content, dict) else ""
    text = content.get("text", "") if isinstance(content, dict) else ""

    return {
        "status": status,
        "content_type": mime,
        "body": text,
    }


def _generate_test_case_from_entry(
    entry: dict, api_name: str, idx: int
) -> Optional[Dict]:
    """从 HAR entry 的 request/response 对生成测试用例。"""
    req = entry.get("request", {})
    resp = entry.get("response", {})

    if not isinstance(req, dict) or not isinstance(resp, dict):
        return None

    resp_info = _extract_response_info(resp)
    status = resp_info.get("status")

    # 基本断言：状态码
    assertions = []
    if status:
        assertions.append({
            "type": "status",
            "expression": "",
            "expected": str(status),
            "comparator": "eq",
        })

    # 如果响应是 JSON，添加 body_contains 断言
    resp_body = resp_info.get("body", "")
    if resp_body and "json" in resp_info.get("content_type", ""):
        try:
            parsed = json.loads(resp_body)
            if isinstance(parsed, dict):
                # 对前 3 个顶层 key 添加存在性断言
                for i, key in enumerate(list(parsed.keys())[:3]):
                    assertions.append({
                        "type": "jsonpath",
                        "expression": f"$.{key}",
                        "expected": "exists",
                        "comparator": "exists",
                    })
        except (json.JSONDecodeError, ValueError):
            pass

    # 响应时间断言
    time_ms = entry.get("time")
    if time_ms and isinstance(time_ms, (int, float)):
        assertions.append({
            "type": "response_time",
            "expression": "",
            "expected": str(int(time_ms)),
            "comparator": "lt",
        })

    if not assertions:
        return None

    # 请求 body 作为测试用例的 request_body
    request_body = None
    post_data = req.get("postData")
    if isinstance(post_data, dict) and post_data.get("text"):
        request_body = {"type": _body_type(post_data.get("mimeType", "")), "content": post_data["text"]}

    return {
        "name": f"{api_name} - 录制用例",
        "api_id": None,  # 后续由 UniImporter 关联
        "description": f"从 HAR 录制自动生成 (Entry #{idx})",
        "priority": "P2",
        "status": "active",
        "pre_script": "",
        "post_script": "",
        "assertions": assertions,
        "extract_vars": [],
        "request_body": request_body,
        "tags": "har-imported",
    }


# =============================================================================
#  主解析函数
# =============================================================================


def parse_har(data: dict) -> Tuple[List[Dict], List[Dict], Optional[str], List[Dict]]:
    """解析 HAR 格式，返回 (categories, apis, project_name, test_cases)。

    增强特性:
      - 按 domain 分组为分类
      - 相同 method+path 去重（保留最后一个）
      - 从 request/response 对生成测试用例
    """
    log = data.get("log", {})
    project_name = ""
    creator = log.get("creator", {})
    if isinstance(creator, dict):
        project_name = creator.get("name", "HAR Import")
    if not project_name:
        project_name = "HAR Import"

    entries = log.get("entries", [])
    if not isinstance(entries, list):
        return [], [], project_name, []

    categories = []
    apis = []
    test_cases = []

    # 按 host 分组
    host_categories: Dict[str, str] = {}  # host → cat_ref
    # 去重：method+path → api index
    seen_apis: Dict[str, int] = {}

    for i, entry in enumerate(entries):
        req = entry.get("request", {})
        if not isinstance(req, dict):
            continue

        method = req.get("method", "GET").upper()
        if method not in HTTP_METHODS:
            method = "GET"

        url = req.get("url", "")
        try:
            parsed = urlparse(url)
        except Exception:
            parsed = None

        path = parsed.path if parsed and parsed.path else "/"
        host = parsed.hostname if parsed else "unknown"
        scheme = parsed.scheme if parsed else "https"

        # 去重
        dedup_key = f"{method} {path}"
        if dedup_key in seen_apis:
            # 替换已有条目（保留最新的请求）
            existing_idx = seen_apis[dedup_key]
            # 更新已有 API 的 headers/body
            apis[existing_idx]["headers"] = _parse_har_headers(req.get("headers", []))
            apis[existing_idx]["params"] = _parse_har_query_string(req.get("queryString", []))
            apis[existing_idx]["body"] = _parse_har_post_data(req.get("postData"))
            # 也更新测试用例
            tc = _generate_test_case_from_entry(entry, apis[existing_idx]["name"], i)
            if tc:
                tc["api_id"] = apis[existing_idx]["apifox_id"]
                test_cases.append(tc)
            continue

        # 分类
        cat_ref = f"cat_{host}"
        if host not in host_categories:
            host_categories[host] = cat_ref
            categories.append({
                "name": f"{scheme}://{host}",
                "parent_ref": None,
                "depth": 0,
                "apifox_id": host,
            })

        # 参数
        params = _parse_har_query_string(req.get("queryString", []))
        headers = _parse_har_headers(req.get("headers", []))
        body = _parse_har_post_data(req.get("postData"))

        api_name = f"{method} {path}" if path != "/" else f"HAR Entry {i}"

        api = {
            "name": api_name[:200],
            "method": method,
            "path": str(path)[:500],
            "apifox_id": f"har_{i}",
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

        seen_apis[dedup_key] = len(apis)
        apis.append(api)

        # 生成测试用例
        tc = _generate_test_case_from_entry(entry, api_name, i)
        if tc:
            tc["api_id"] = api["apifox_id"]
            test_cases.append(tc)

    return categories, apis, project_name, test_cases
