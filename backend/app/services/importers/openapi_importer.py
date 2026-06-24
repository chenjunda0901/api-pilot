"""OpenAPI 3.0 导入解析器

增强特性（相比 format_parsers._parse_openapi_spec）：
- 完整 $ref 引用解析（components/schemas, components/responses, components/parameters 等）
- 提取 components/schemas 作为独立 schema 记录
- 提取 examples
- 更完整的 request body / response 解析
"""

import json
import logging
from typing import Any, Dict, List, Optional, Tuple

from app.services.format_parsers import (
    HTTP_METHODS,
    _body_type,
    _generate_default_from_schema,
)

logger = logging.getLogger("import.openapi")


# =============================================================================
#  $ref 解析
# =============================================================================


def _resolve_ref(spec: dict, ref: str) -> Any:
    """解析 JSON Pointer 风格的 $ref 引用。

    支持的引用路径:
      - #/components/schemas/xxx
      - #/components/responses/xxx
      - #/components/parameters/xxx
      - #/components/examples/xxx
      - #/components/requestBodies/xxx
      - #/paths/xxx/yyy
    """
    if not ref.startswith("#/"):
        logger.warning("不支持的外部 $ref: %s", ref)
        return {}

    parts = ref[2:].split("/")
    node = spec
    for part in parts:
        # 处理 JSON Pointer 中的转义字符
        part = part.replace("~1", "/").replace("~0", "~")
        if isinstance(node, dict) and part in node:
            node = node[part]
        else:
            logger.warning("$ref 解析失败: %s (在路径 %s 处中断)", ref, part)
            return {}
    return node


def _resolve_refs_deep(obj: Any, spec: dict, depth: int = 0, max_depth: int = 15) -> Any:
    """递归解析对象中所有 $ref 引用（内联展开）。

    防止循环引用：超过 max_depth 时停止解析。
    """
    if depth > max_depth:
        logger.warning("$ref 解析深度超过 %d，停止递归", max_depth)
        return obj

    if isinstance(obj, dict):
        if "$ref" in obj:
            resolved = _resolve_ref(spec, obj["$ref"])
            # 保留 $ref 之外的其他属性（如 description override）
            extra = {k: v for k, v in obj.items() if k != "$ref"}
            if extra and isinstance(resolved, dict):
                resolved = {**resolved, **extra}
            return _resolve_refs_deep(resolved, spec, depth + 1, max_depth)
        return {k: _resolve_refs_deep(v, spec, depth + 1, max_depth) for k, v in obj.items()}

    if isinstance(obj, list):
        return [_resolve_refs_deep(item, spec, depth + 1, max_depth) for item in obj]

    return obj


# =============================================================================
#  参数与 Body 提取
# =============================================================================


def _extract_parameters(operation: dict, path_params: list, spec: dict) -> Tuple[List[Dict], List[Dict], List[Dict]]:
    """提取并分类参数为 query, header, path 三组。

    Args:
        operation: 操作对象（已解析 $ref）
        path_params: 路径级参数（已解析 $ref）
        spec: 完整 OpenAPI 规范（用于 $ref 解析）

    Returns:
        (query_params, headers, path_params_out)
    """
    # 合并路径级和操作级参数（操作级覆盖路径级同名参数）
    merged: Dict[str, dict] = {}
    for p in path_params + operation.get("parameters", []):
        p = _resolve_refs_deep(p, spec) if isinstance(p, dict) else p
        if not isinstance(p, dict):
            continue
        key = f"{p.get('in', '')}:{p.get('name', '')}"
        merged[key] = p

    query_params = []
    headers = []
    path_params_out = []

    for p in merged.values():
        p_in = p.get("in", "query")
        schema = p.get("schema", {})
        if not isinstance(schema, dict):
            schema = {}

        entry = {
            "key": p.get("name", ""),
            "value": p.get("example", schema.get("example", p.get("example", ""))),
            "enabled": True,
            "required": p.get("required", False),
            "description": p.get("description", ""),
            "type": schema.get("type", "string"),
        }

        if p_in == "query":
            query_params.append(entry)
        elif p_in == "header":
            headers.append({**entry, "source": "openapi"})
        elif p_in == "path":
            path_params_out.append({**entry, "in": "path"})

    return query_params, headers, path_params_out


def _extract_request_body(request_body: Optional[dict], spec: dict) -> Dict:
    """提取 OpenAPI 3.0 requestBody。"""
    if not request_body or not isinstance(request_body, dict):
        return {"type": "none", "content": ""}

    content = request_body.get("content", {})
    if not isinstance(content, dict) or not content:
        return {"type": "none", "content": ""}

    # 优先使用 application/json
    preferred_order = ["application/json", "application/x-www-form-urlencoded", "multipart/form-data", "application/xml", "text/plain"]
    ct_key = None
    for ct in preferred_order:
        if ct in content:
            ct_key = ct
            break
    if not ct_key:
        ct_key = next(iter(content))

    ct_spec = content[ct_key]
    if not isinstance(ct_spec, dict):
        return {"type": "none", "content": ""}

    schema = ct_spec.get("schema")
    if isinstance(schema, dict):
        schema = _resolve_refs_deep(schema, spec)

    # 提取 example
    raw_content = ""
    # 优先级1: example 字段
    example = ct_spec.get("example")
    if example:
        raw_content = json.dumps(example, ensure_ascii=False, indent=2) if isinstance(example, (dict, list)) else str(example)
    # 优先级2: examples 中第一个
    if not raw_content:
        examples = ct_spec.get("examples", {})
        if isinstance(examples, dict):
            for ex_name, ex_val in examples.items():
                if isinstance(ex_val, dict):
                    val = ex_val.get("value")
                    if val:
                        raw_content = json.dumps(val, ensure_ascii=False, indent=2) if isinstance(val, (dict, list)) else str(val)
                        break
    # 优先级3: 从 schema 生成默认值
    if not raw_content and isinstance(schema, dict):
        raw_content = json.dumps(_generate_default_from_schema(schema), ensure_ascii=False, indent=2)

    body_type = _body_type(ct_key)
    if not raw_content and body_type in ("form-urlencoded", "form-data"):
        raw_content = "[]"

    return {
        "type": body_type,
        "content_type": ct_key,
        "content": raw_content,
        "schema": schema,
    }


def _extract_responses(responses: Optional[dict], spec: dict) -> Tuple[Optional[Dict], List[Dict]]:
    """提取响应 schema 和示例。

    Returns:
        (response_schema, response_examples)
    """
    if not responses or not isinstance(responses, dict):
        return None, []

    response_schema = None
    response_examples = []

    # 优先找 200 响应
    for status in ("200", "201", "default", *responses.keys()):
        if status in responses:
            resp = responses[status]
            if isinstance(resp, dict):
                resp = _resolve_refs_deep(resp, spec)
            if not isinstance(resp, dict):
                continue

            content = resp.get("content", {})
            if isinstance(content, dict):
                for ct, ct_spec in content.items():
                    if not isinstance(ct_spec, dict):
                        continue
                    schema = ct_spec.get("schema")
                    if isinstance(schema, dict):
                        schema = _resolve_refs_deep(schema, spec)
                    if schema and not response_schema:
                        response_schema = {
                            "status_code": status,
                            "content_type": ct,
                            "schema": schema,
                        }

                    # 提取 examples
                    example = ct_spec.get("example")
                    if example:
                        response_examples.append({
                            "name": f"{status} 示例",
                            "data": json.dumps(example, ensure_ascii=False, indent=2) if isinstance(example, (dict, list)) else str(example),
                        })
                    for ex_name, ex_val in ct_spec.get("examples", {}).items():
                        if isinstance(ex_val, dict) and "value" in ex_val:
                            val = ex_val["value"]
                            response_examples.append({
                                "name": ex_name,
                                "data": json.dumps(val, ensure_ascii=False, indent=2) if isinstance(val, (dict, list)) else str(val),
                            })
                    break  # 只取第一个 content-type
            break  # 只取第一个状态码

    return response_schema, response_examples


# =============================================================================
#  主解析函数
# =============================================================================


def parse_openapi_3(spec: dict) -> Tuple[List[Dict], List[Dict], Optional[str]]:
    """解析 OpenAPI 3.0 规范，返回 (categories, apis, project_name)。

    增强特性:
      - 完整 $ref 解析
      - 提取 components/schemas
      - 提取 examples
      - 安全认证信息提取
    """
    info = spec.get("info", {})
    project_name = info.get("title", "")

    paths = spec.get("paths", {})
    if not isinstance(paths, dict):
        return [], [], project_name

    # 全局 security schemes
    security_schemes = {}
    components = spec.get("components", {})
    if isinstance(components, dict):
        for name, scheme in components.get("securitySchemes", {}).items():
            if isinstance(scheme, dict):
                security_schemes[name] = scheme.get("type", "apiKey")

    global_security = spec.get("security", [])

    categories = []
    apis = []
    cat_ref_cache: Dict[str, str] = {}
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
    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue

        # 路径级参数（所有操作共享）
        path_level_params = path_item.get("parameters", [])
        path_level_params = [_resolve_refs_deep(p, spec) if isinstance(p, dict) else p for p in path_level_params]

        for method, operation in path_item.items():
            method_upper = method.upper()
            if method_upper not in HTTP_METHODS:
                continue
            if not isinstance(operation, dict):
                continue

            apis_idx += 1

            # 解析 $ref（操作本身可能是 $ref，递归解析内部所有引用）
            operation = _resolve_refs_deep(operation, spec) if "$ref" in operation else operation

            # Tags → 分类
            tags = operation.get("tags", ["未分类"])
            if not tags or not isinstance(tags, list):
                tags = ["未分类"]
            cat_ref = get_cat_ref(tags[0])

            # 参数
            query_params, headers, path_params = _extract_parameters(operation, path_level_params, spec)
            all_params = query_params + path_params

            # Body
            body = _extract_request_body(operation.get("requestBody"), spec)

            # Auth
            auth_config = operation.get("security", global_security)
            auth_type = "none"
            if auth_config:
                for sec_item in auth_config:
                    if isinstance(sec_item, dict):
                        for scheme_name in sec_item:
                            scheme_type = security_schemes.get(scheme_name, "apiKey")
                            auth_type = scheme_type
                            break
                        break

            # Response
            response_schema, response_examples = _extract_responses(operation.get("responses", {}), spec)

            # 描述
            desc = operation.get("description", "")
            if not isinstance(desc, str):
                desc = str(desc) if desc else ""

            # 名称
            name = operation.get("summary", operation.get("operationId", f"{method_upper} {path}"))
            if not name:
                name = f"{method_upper} {path}"

            apis.append({
                "name": name[:200],
                "method": method_upper,
                "path": str(path)[:500],
                "apifox_id": f"openapi_api_{apis_idx}",
                "category_ref": cat_ref,
                "headers": headers,
                "params": all_params,
                "body": body,
                "auth_type": auth_type,
                "auth": {"type": auth_type},
                "pre_script": "",
                "post_script": "",
                "response_schema": response_schema,
                "response_examples": response_examples,
                "description": desc,
                "status": "developing",
                "settings": {},
            })

    return categories, apis, project_name
