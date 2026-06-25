"""HTTP 请求构建器 — 从 linear_executor.py 提取的 URL/Body/Header 构建逻辑。

职责：
- build_url: 组装 base_url + path + query_params，支持变量渲染
- build_headers: 合并环境级+步骤级请求头，支持变量渲染
- parse_body: 解析 BodyEditor 格式 {type, content}，返回待发送的 body/data/files
- truncate_response: 安全截断响应体，避免内存爆炸
"""

import json
import os
import urllib.parse
from typing import Any

from app.utils.http_client import validate_request_url


_MAX_RESPONSE_SIZE = 100 * 1024  # 100KB


def build_url(
    base_url: str,
    path: str,
    query_params: list,
    variables: dict,
) -> str:
    """组装完整 URL（base + path + query params），支持变量渲染。"""
    # 先渲染双花括号格式 {{variable}}
    rendered_path = _render_str(path, variables)

    # 再渲染单花括号格式 {variable}（RESTful 路径参数）
    rendered_path = _render_path_params(rendered_path, variables)

    # URL 路径安全引用：对 base_url 和 rendered_path 分别进行 path 级 quote，
    # 防止通过变量注入 ?、#、@、: 等 URL 结构破坏字符（SSRF 防护）。
    # 移除 @ 防止 credential 注入，移除 : 防止 port/scheme 注入。
    safe_base = urllib.parse.quote(base_url, safe="/!")
    safe_rendered_path = urllib.parse.quote(rendered_path, safe="/!")
    url = f"{safe_base}{safe_rendered_path}"

    # SSRF 防护：验证目标 URL 是否在白名单中
    try:
        validate_request_url(url)
    except ValueError as e:
        raise ValueError(f"SSRF 防护拒绝请求: {e}")

    if query_params:
        param_parts = []
        for qp in query_params:
            if isinstance(qp, dict) and qp.get("key") and qp.get("enabled", True):
                k = _render_str(qp["key"], variables)
                v = _render_str(qp.get("value", ""), variables)
                param_parts.append(f"{urllib.parse.quote(k)}={urllib.parse.quote(v)}")
        if param_parts:
            separator = "&" if "?" in url else "?"
            url = f"{url}{separator}{'&'.join(param_parts)}"
    return url


def build_headers(
    step_headers: list,
    env_headers: list,
    variables: dict,
) -> dict:
    """合并环境级+步骤级请求头，返回已渲染的 dict。"""
    headers = {}
    all_headers = list(env_headers) + list(step_headers)
    for h in all_headers:
        if isinstance(h, dict) and h.get("key") and h.get("enabled", True):
            k = _render_str(h["key"], variables)
            v = _render_str(h.get("value", ""), variables)
            headers[k] = v
    return headers


def _validate_file_path(file_path: str, base_dir: str = "") -> str:
    """校验文件路径安全性，防范路径遍历攻击。

    安全规则：
    1. 拒绝 URL 编码的 ..%2F
    2. 规范化路径后拒绝包含 .. 的路径（防 ../ 遍历）
    3. 使用 pathlib.resolve() 解析符号链接和实际路径
    4. 检查解析后的路径是否仍在基础目录内

    Args:
        file_path: 用户输入的文件路径
        base_dir: 基础目录，用于边界检查。为空时不检查。

    Returns:
        规范化后的安全文件路径

    Raises:
        ValueError: 路径不安全
    """
    import pathlib as _pathlib
    from urllib.parse import unquote

    # 规则0：拒绝 URL 编码的路径遍历
    decoded = unquote(file_path)
    if ".." in decoded.lower() or "%2e%2e" in decoded.lower():
        raise ValueError(f"不安全文件路径: {file_path}")

    # 规则1：使用 pathlib 规范化路径（解析 . 和 ..）
    # PurePosixPath/PureWindowsPath 只做规范化，不访问文件系统
    is_windows = os.name == "nt"
    if is_windows:
        raw_path = _pathlib.PureWindowsPath(file_path)
    else:
        raw_path = _pathlib.PurePosixPath(file_path)

    # 规则2：拒绝绝对路径
    if raw_path.is_absolute() and not str(raw_path).startswith("//?/"):
        raise ValueError(f"不允许使用绝对路径，仅支持相对路径: {file_path}")

    # 转换为字符串并使用 os.path 解析符号链接
    raw_str = str(raw_path)
    try:
        real_path = os.path.realpath(os.path.normpath(raw_str))
    except OSError:
        raise ValueError(f"无法解析文件路径: {file_path}")

    # 规则3：如果指定了 base_dir，检查解析后的路径是否在允许范围内
    if base_dir:
        base_real = os.path.realpath(os.path.normpath(base_dir))
        real_path_obj = _pathlib.Path(real_path)
        base_path_obj = _pathlib.Path(base_real)
        try:
            real_path_obj.relative_to(base_path_obj)
        except ValueError:
            raise ValueError(f"文件路径必须在基础目录内: {file_path}")

    return real_path


def parse_body(
    body_raw: str, variables: dict
) -> tuple[str | None, dict | None, dict | None]:
    """解析 BodyEditor 格式 {type, content}，返回 (body_send, data_send, files_send)。

    Returns:
        (body_send, data_send, files_send) — 三个值只有一个非 None

    安全：
    - 文件路径经过路径遍历校验，仅允许项目目录下的文件
    - 打开的文件句柄由调用方负责关闭（见 linear_executor.py 的 files_send 清理逻辑）
    """
    data_send: dict | None = None
    files_send: dict | None = None

    if not body_raw:
        return None, None, None

    try:
        body_obj = json.loads(body_raw)
    except (json.JSONDecodeError, TypeError):
        return body_raw, None, None

    if not (
        isinstance(body_obj, dict)
        and body_obj.get("type")
        and body_obj.get("content") is not None
    ):
        return body_raw, None, None

    btype = body_obj.get("type", "")
    raw_content = body_obj.get("content", "")

    if btype == "none":
        return None, None, None
    elif btype in ("form-data", "x-www-form-urlencoded"):
        fields = raw_content
        if isinstance(fields, str):
            try:
                fields = json.loads(fields)
            except (json.JSONDecodeError, TypeError):
                fields = []
        if isinstance(fields, list):
            d = {}
            f = {}
            opened_files = []  # 跟踪已打开的文件句柄，异常时回滚关闭
            try:
                for field in fields:
                    if not isinstance(field, dict) or field.get("enabled") is False:
                        continue
                    key = _render_str(str(field.get("key", "")), variables)
                    if not key:
                        continue
                    field_type = field.get("type", "string")
                    val = _render_str(str(field.get("value", "")), variables)
                    if field_type == "file" and val:
                        # 先校验路径安全性（防路径遍历），再检查文件是否存在
                        safe_path = _validate_file_path(val)
                        if os.path.isfile(safe_path):
                            file_handle = open(safe_path, "rb")
                            opened_files.append(file_handle)
                            f[key] = (os.path.basename(safe_path), file_handle)
                        else:
                            # 文件不存在时降级为普通字段
                            d[key] = val
                    elif val:
                        d[key] = val
            except (OSError, ValueError, KeyError):
                # 发生异常时关闭已打开的文件句柄，防止泄漏
                for fh in opened_files:
                    try:
                        fh.close()
                    except (OSError, AttributeError):
                        pass
                raise
            if f:
                data_send, files_send = d, f
            elif d:
                data_send = d
        return None, data_send, files_send
    else:
        return _render_str(raw_content, variables), None, None


def truncate_response(raw_bytes: bytes) -> tuple[str, Any]:
    """安全截断响应体字节流，返回 (stored_body, parsed_body)。"""
    original_size = len(raw_bytes)
    if original_size > _MAX_RESPONSE_SIZE:
        truncated = raw_bytes[:_MAX_RESPONSE_SIZE]
        stored = truncated.decode("utf-8", errors="replace")
        stored += f"...（响应体已截断，原始大小 {original_size} 字节）"
    else:
        stored = raw_bytes.decode("utf-8", errors="replace")
    return stored, _try_parse_json(stored)


def _render_str(text: str, variables: dict) -> str:
    """单行字符串变量渲染（供内部使用）。"""
    from app.services.executor.variable_renderer import render_template

    return render_template(text, variables)


def _render_path_params(path: str, variables: dict) -> str:
    """渲染 RESTful 路径参数 {variable} 格式。

    将路径中的 {key} 替换为 variables 中对应的值。
    例如：/api/users/{id} + {"id": 123} -> /api/users/123

    Args:
        path: 包含 {variable} 占位符的路径字符串
        variables: 变量字典

    Returns:
        替换后的路径字符串
    """
    import re

    # 匹配单花括号格式 {variable}，但不匹配双花括号 {{variable}}
    # 使用负向先行断言排除双花括号
    pattern = r"(?<!\{)\{(\w+)\}(?!\})"

    def replacer(match):
        var_name = match.group(1)
        value = variables.get(var_name, "")
        # 如果值是变量引用（如 {{token}}），先渲染它
        if isinstance(value, str) and "{{" in value:
            value = _render_str(value, variables)
        return str(value) if value else match.group(0)

    return re.sub(pattern, replacer, path)


def _try_parse_json(text: str) -> Any:
    """安全 JSON 解析，失败返回原文本。"""
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return text
