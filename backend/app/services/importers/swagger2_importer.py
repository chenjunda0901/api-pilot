"""Swagger 2.0 导入解析器

Swagger 2.0 与 OpenAPI 3.0 的关键差异：
- definitions 而非 components/schemas
- parameters/response 在顶层或操作级别，而非 components
- body 参数在 parameters 数组中（in: body），而非 requestBody
- securityDefinitions 而非 components/securitySchemes
- produces/consumes 而非 content 的 media type
"""

import json
import logging
from typing import Any, Dict, List, Optional, Tuple

from app.services.format_parsers import (
    HTTP_METHODS,
    _body_type,
    _generate_default_from_schema,
)

logger = logging.getLogger("import.swagger2")


# =============================================================================
#  $ref 解析
# =============================================================================


def _resolve_ref(spec: dict, ref: str) -> Any:
    """解析 Swagger 2.0 的 $ref 引用。

    支持的引用路径:
      - #/definitions/xxx
      - #/parameters/xxx
      - #/responses/xxx
      - #/paths/xxx
    """
    if not ref.startswith("#/"):
        logger.warning("不支持的外部 $ref: %s", ref)
        return {}

    parts = ref[2:].split("/")
    node = spec
    for part in parts:
        part = part.replace("~1", "/").replace("~0", "~")
        if isinstance(node, dict) and part in node:
            node = node[part]
        else:
            logger.warning("$ref 解析失败: %s", ref)
            return {}
    return node


def _resolve_refs_deep(obj: Any, spec: dict, depth: int = 0, max_depth: int = 15) -> Any:
    """递归解析对象中所有 $ref 引用。"""
    if depth > max_depth:
        return obj

    if isinstance(obj, dict):
        if "$ref" in obj:
            resolved = _resolve_ref(spec, obj["$ref"])
            extra = {k: v for k, v in obj.items() if k != "$ref"}
            if extra and isinstance(resolved, dict):
                resolved = {**resolved, **extra}
            return _resolve_refs_deep(resolved, spec, depth + 1, max_depth)
        return {k: _resolve_refs_deep(v, spec, depth + 1, max_depth) for k, v in obj.items()}

    if isinstance(obj, list):
        return [_resolve_refs_deep(item, spec, depth + 1, max_depth) for item in obj]

    return obj


# =============================================================================
#  参数提取
# =============================================================================


def _extract_swagger_parameters(
    operation: dict, path_params: list, spec: dict
) -> Tuple[List[Dict], List[Dict], List[Dict], Optional[Dict]]:
    """提取 Swagger 2.0 参数。

    Swagger 2.0 的 body 参数在 parameters 数组中（in: body），
    与 OpenAPI 3.0 的 requestBody 不同。

    Returns:
        (query_params, headers, path_params_out, body_param)
    """
    merged: Dict[str, dict] = {}
    for p in path_params + operation.get("parameters", []):
        p = _resolve_refs_deep(p, spec) if isinstance(p, dict) and "$ref" in p else p
        if not isinstance(p, dict):
            continue
        key = f"{p.get('in', '')}:{p.get('name', '')}"
        merged[key] = p

    query_params = []
    headers = []
    path_params_out = []
    body_param = None

    for p in merged.values():
        p_in = p.get("in", "query")

        if p_in == "body":
            # Swagger 2.0 body 参数
            schema = p.get("schema", {})
            if isinstance(schema, dict) and "$ref" in schema:
                schema = _resolve_refs_deep(schema, spec)
            body_param = {
                "description": p.get("description", ""),
                "schema": schema,
            }
            continue

        if p_in == "formData":
            # formData 参数 → 转为 form 字段
            query_params.append({
                "key": p.get("name", ""),
                "value": p.get("default", ""),
                "enabled": True,
                "required": p.get("required", False),
                "description": p.get("description", ""),
                "type": p.get("type", "string"),
                "in": "formData",
            })
            continue

        schema = p.get("schema", p)
        if not isinstance(schema, dict):
            schema = {}

        entry = {
            "key": p.get("name", ""),
            "value": p.get("default", schema.get("default", "")),
            "enabled": True,
            "required": p.get("required", False),
            "description": p.get("description", ""),
            "type": schema.get("type", p.get("type", "string")),
        }

        if p_in == "query":
            query_params.append(entry)
        elif p_in == "header":
            headers.append({**entry, "source": "swagger"})
        elif p_in == "path":
            path_params_out.append({**entry, "in": "path"})

    return query_params, headers, path_params_out, body_param


def _build_body_from_swagger(
    body_param: Optional[Dict], operation: dict, spec: dict
) -> Dict:
    """从 Swagger 2.0 body 参数和 consumes 构建 body。"""
    if not body_param:
        return {"type": "none", "content": ""}

    consumes = operation.get("consumes", spec.get("consumes", ["application/json"]))
    if isinstance(consumes, list) and consumes:
        ct = consumes[0]
    else:
        ct = "application/json"

    schema = body_param.get("schema", {})
    if isinstance(schema, dict) and "$ref" in schema:
        schema = _resolve_refs_deep(schema, spec)

    # 从 schema 生成默认内容
    raw_content = ""
    if isinstance(schema, dict):
        raw_content = json.dumps(_generate_default_from_schema(schema), ensure_ascii=False, indent=2)

    body_type = _body_type(ct)
    if not raw_content and body_type in ("form-urlencoded", "form-data"):
        raw_content = "[]"

    return {
        "type": body_type,
        "content_type": ct,
        "content": raw_content,
        "schema": schema,
    }


def _extract_swagger_responses(
    responses: Optional[dict], spec: dict
) -> Tuple[Optional[Dict], List[Dict]]:
    """提取 Swagger 2.0 响应。

    Swagger 2.0 的响应 schema 在 response.schema 中，
    examples 在 response.examples 中。
    """
    if not responses or not isinstance(responses, dict):
        return None, []

    response_schema = None
    response_examples = []

    for status in ("200", "201", "default", *responses.keys()):
        if status not in responses:
            continue
        resp = responses[status]
        if isinstance(resp, dict) and "$ref" in resp:
            resp = _resolve_refs_deep(resp, spec)
        if not isinstance(resp, dict):
            continue

        schema = resp.get("schema")
        if isinstance(schema, dict) and "$ref" in schema:
            schema = _resolve_refs_deep(schema, spec)

        if schema and not response_schema:
            produces = spec.get("produces", ["application/json"])
            ct = produces[0] if isinstance(produces, list) and produces else "application/json"
            response_schema = {
                "status_code": status,
                "content_type": ct,
                "schema": schema,
            }

        # Swagger 2.0 examples 字段
        examples = resp.get("examples", {})
        if isinstance(examples, dict):
            for ct_key, example_val in examples.items():
                response_examples.append({
                    "name": f"{status} 示例 ({ct_key})",
                    "data": json.dumps(example_val, ensure_ascii=False, indent=2) if isinstance(example_val, (dict, list)) else str(example_val),
                })

        break

    return response_schema, response_examples


# =============================================================================
#  主解析函数
# =============================================================================


def parse_swagger2(spec: dict) -> Tuple[List[Dict], List[Dict], Optional[str]]:
    """解析 Swagger 2.0 规范，返回 (categories, apis, project_name)。

    增强特性:
      - 完整 $ref 解析（#/definitions/, #/parameters/, #/responses/）
      - Swagger 2.0 → 内部格式转换（body 参数、formData、consumes/produces）
      - 安全认证信息提取
    """
    info = spec.get("info", {})
    project_name = info.get("title", "")

    paths = spec.get("paths", {})
    if not isinstance(paths, dict):
        return [], [], project_name

    # 全局 security definitions
    security_schemes = {}
    sec_defs = spec.get("securityDefinitions", {})
    if isinstance(sec_defs, dict):
        for name, scheme in sec_defs.items():
            if isinstance(scheme, dict):
                # Swagger 2.0 类型: basic, apiKey, oauth2
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
            cat_ref_cache[tag_name] = f"cat_swagger_{cat_idx}"
            categories.append({
                "name": tag_name,
                "parent_ref": None,
                "depth": 0,
                "apifox_id": f"swagger_{cat_idx}",
            })
        return cat_ref_cache[tag_name]

    apis_idx = 0
    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue

        # 路径级参数
        path_level_params = path_item.get("parameters", [])
        path_level_params = [_resolve_refs_deep(p, spec) if isinstance(p, dict) and "$ref" in p else p for p in path_level_params]

        for method, operation in path_item.items():
            method_upper = method.upper()
            if method_upper not in HTTP_METHODS:
                continue
            if not isinstance(operation, dict):
                continue

            apis_idx += 1
            operation = _resolve_refs_deep(operation, spec) if "$ref" in operation else operation

            # Tags → 分类
            tags = operation.get("tags", ["未分类"])
            if not tags or not isinstance(tags, list):
                tags = ["未分类"]
            cat_ref = get_cat_ref(tags[0])

            # 参数
            query_params, headers, path_params, body_param = _extract_swagger_parameters(
                operation, path_level_params, spec
            )
            all_params = query_params + path_params

            # Body
            body = _build_body_from_swagger(body_param, operation, spec)

            # 如果有 formData 参数但没有 body，构建 form-data body
            form_data_params = [p for p in all_params if p.get("in") == "formData"]
            if form_data_params and body["type"] == "none":
                consumes = operation.get("consumes", spec.get("consumes", []))
                ct = "multipart/form-data"
                if isinstance(consumes, list) and consumes:
                    if "application/x-www-form-urlencoded" in consumes:
                        ct = "application/x-www-form-urlencoded"
                body = {
                    "type": _body_type(ct),
                    "content_type": ct,
                    "content": "[]",
                }
                # formData 参数从 params 中移除，转为 body 的一部分
                all_params = [p for p in all_params if p.get("in") != "formData"]

            # Auth
            auth_config = operation.get("security", global_security)
            auth_type = "none"
            if auth_config:
                for sec_item in auth_config:
                    if isinstance(sec_item, dict):
                        for scheme_name in sec_item:
                            auth_type = security_schemes.get(scheme_name, "apiKey")
                            break
                        break

            # Response
            response_schema, response_examples = _extract_swagger_responses(
                operation.get("responses", {}), spec
            )

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
                "apifox_id": f"swagger_api_{apis_idx}",
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
