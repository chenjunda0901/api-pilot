"""cURL 命令解析器。

将 cURL 命令字符串解析为结构化的接口定义对象，支持：
  - 请求方法（-X / --request）
  - URL（第一个非选项参数）
  - 请求头（-H / --header）
  - 请求体（-d / --data / --data-raw / --data-binary）
  - 认证信息（-u / --user）
  - Cookie（-b / --cookie）
  - 单引号/双引号包裹的值
  - 转义字符
  - 多行 cURL（反斜杠续行）
  - $variable 占位替换
"""

from __future__ import annotations

import json
import re
import shlex
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse, parse_qs


@dataclass
class ParsedCurl:
    """cURL 解析结果。"""
    method: str = "GET"
    url: str = ""
    path: str = "/"
    headers: list[dict[str, str]] = field(default_factory=list)
    params: list[dict[str, str]] = field(default_factory=list)
    body: dict[str, Any] = field(default_factory=lambda: {"type": "none", "content": ""})
    auth: dict[str, Any] = field(default_factory=lambda: {"type": "none"})
    cookies: list[dict[str, str]] = field(default_factory=list)
    name: str = ""


def _preprocess(raw: str) -> str:
    """预处理 cURL 命令：合并多行、清理。"""
    # 去除行尾反斜杠续行
    text = raw.replace("\\\n", " ").replace("\\\r\n", " ")
    # 去除首尾空白
    text = text.strip()
    return text


def _tokenize(text: str) -> list[str]:
    """将 cURL 命令拆分为 token 列表。

    使用 shlex 进行 shell 风格分词，但增加对常见 cURL 写法的容错处理。
    """
    # 尝试 shlex 分词（正确处理引号嵌套）
    try:
        tokens = shlex.split(text, posix=True)
    except ValueError:
        # shlex 解析失败（如不匹配的引号），降级为简单分词
        tokens = _simple_tokenize(text)
    return tokens


def _simple_tokenize(text: str) -> list[str]:
    """简单分词：处理单引号/双引号包裹的值，但不处理嵌套。"""
    tokens: list[str] = []
    current = ""
    in_single = False
    in_double = False
    i = 0
    while i < len(text):
        ch = text[i]
        if ch == "'" and not in_double:
            in_single = not in_single
            i += 1
            continue
        if ch == '"' and not in_single:
            in_double = not in_double
            i += 1
            continue
        if ch == " " and not in_single and not in_double:
            if current:
                tokens.append(current)
                current = ""
            i += 1
            continue
        current += ch
        i += 1
    if current:
        tokens.append(current)
    return tokens


def _replace_variables(value: str) -> str:
    """将 $variable 或 ${variable} 替换为 {{variable}} 格式。"""
    # ${VAR} → {{VAR}}
    value = re.sub(r"\$\{(\w+)\}", r"{{\1}}", value)
    # $VAR (后面不是 { 和字母数字) → {{VAR}}
    value = re.sub(r"\$(\w+)", r"{{\1}}", value)
    return value


def _parse_url(url: str) -> tuple[str, list[dict[str, str]]]:
    """从完整 URL 提取 path 和 query params。"""
    url = _replace_variables(url)
    parsed = urlparse(url)
    path = parsed.path or "/"
    params: list[dict[str, str]] = []
    if parsed.query:
        qs = parse_qs(parsed.query, keep_blank_values=True)
        for key, values in qs.items():
            for v in values:
                params.append({"key": key, "value": v, "enabled": True, "description": ""})
    return path, params


def _detect_body_type(content: str, content_type: str = "") -> dict[str, Any]:
    """根据内容推断 body 类型。"""
    ct_lower = content_type.lower()
    if ct_lower.startswith("application/json"):
        return {"type": "json", "content": content}
    if ct_lower.startswith("application/x-www-form-urlencoded"):
        # 尝试解析为 form fields
        fields: list[dict[str, str]] = []
        try:
            qs = parse_qs(content, keep_blank_values=True)
            for key, values in qs.items():
                for v in values:
                    fields.append({"key": key, "value": v, "enabled": True})
        except Exception:
            pass
        if fields:
            return {"type": "form", "content": "", "fields": fields}
        return {"type": "raw", "content": content}
    if ct_lower.startswith("multipart/form-data"):
        return {"type": "form-data", "content": content}
    if ct_lower.startswith("application/xml") or ct_lower.startswith("text/xml"):
        return {"type": "xml", "content": content}
    # 尝试 JSON 探测
    stripped = content.strip()
    if stripped and stripped[0] in ("{", "["):
        try:
            json.loads(stripped)
            return {"type": "json", "content": content}
        except (json.JSONDecodeError, ValueError):
            pass
    return {"type": "raw", "content": content}


def parse_curl(raw: str) -> ParsedCurl:
    """解析 cURL 命令字符串，返回结构化接口定义。

    Args:
        raw: cURL 命令字符串

    Returns:
        ParsedCurl 解析结果

    Raises:
        ValueError: 命令无法解析
    """
    text = _preprocess(raw)
    if not text:
        raise ValueError("cURL 命令为空")

    tokens = _tokenize(text)

    # 跳过开头的 curl 命令
    idx = 0
    if tokens and tokens[0].lower() == "curl":
        idx = 1

    method = "GET"
    url = ""
    headers: list[dict[str, str]] = []
    body_content = ""
    body_content_type = ""
    auth_user = ""
    auth_pass = ""
    cookie_str = ""
    has_data = False

    while idx < len(tokens):
        tok = tokens[idx]

        # -X / --request
        if tok in ("-X", "--request"):
            idx += 1
            if idx < len(tokens):
                method = tokens[idx].upper()
            idx += 1
            continue

        # -H / --header
        if tok in ("-H", "--header"):
            idx += 1
            if idx < len(tokens):
                header_val = _replace_variables(tokens[idx])
                # 解析 "Key: Value" 格式
                colon_pos = header_val.find(":")
                if colon_pos > 0:
                    key = header_val[:colon_pos].strip()
                    value = header_val[colon_pos + 1:].strip()
                    if key.lower() == "content-type":
                        body_content_type = value
                    elif key.lower() == "cookie":
                        cookie_str = value
                    else:
                        headers.append({"key": key, "value": value, "enabled": True, "description": ""})
            idx += 1
            continue

        # -d / --data / --data-raw / --data-binary
        if tok in ("-d", "--data", "--data-raw", "--data-binary"):
            idx += 1
            if idx < len(tokens):
                body_content = _replace_variables(tokens[idx])
                has_data = True
                # 有 -d 但没指定 -X 时，方法默认为 POST
                if method == "GET":
                    method = "POST"
            idx += 1
            continue

        # -u / --user
        if tok in ("-u", "--user"):
            idx += 1
            if idx < len(tokens):
                user_val = tokens[idx]
                if ":" in user_val:
                    auth_user, auth_pass = user_val.split(":", 1)
                else:
                    auth_user = user_val
            idx += 1
            continue

        # -b / --cookie
        if tok in ("-b", "--cookie"):
            idx += 1
            if idx < len(tokens):
                cookie_str = _replace_variables(tokens[idx])
            idx += 1
            continue

        # --url
        if tok == "--url":
            idx += 1
            if idx < len(tokens):
                url = tokens[idx]
            idx += 1
            continue

        # 忽略的选项（不带值的）
        if tok in ("-k", "--insecure", "-L", "--location", "-s", "--silent",
                    "-S", "--show-error", "-v", "--verbose", "-i", "--include",
                    "-I", "--head", "--compressed", "-g", "--globoff"):
            idx += 1
            continue

        # 忽略的选项（带 1 个值的）
        if tok in ("--connect-timeout", "--max-time", "-m", "--retry",
                    "--retry-delay", "--retry-max-time", "-o", "--output",
                    "-w", "--write-out", "--cert", "--key", "--cacert",
                    "--capath", "-E", "--cert-type", "-F", "--form",
                    "--form-string", "--limit-rate", "--max-filesize",
                    "--max-redirs", "-n", "--netrc", "--no-keepalive",
                    "-p", "--proxy", "--proxy-user", "-U",
                    "--proxy-header", "-x", "--resolve", "-e", "--referer",
                    "-A", "--user-agent", "--accept", "-T", "--upload-file"):
            idx += 2  # 跳过选项和值
            continue

        # 非选项参数 → URL
        if not tok.startswith("-"):
            url = _replace_variables(tok)
            idx += 1
            continue

        # 未知选项：跳过
        idx += 1

    if not url:
        raise ValueError("未找到请求 URL")

    # 解析 URL 为 path + params
    path, params = _parse_url(url)

    # 解析 body
    body = _detect_body_type(body_content, body_content_type) if has_data else {"type": "none", "content": ""}

    # 解析 auth
    auth: dict[str, Any] = {"type": "none"}
    if auth_user:
        auth = {"type": "basic", "username": auth_user, "password": auth_pass}

    # 解析 cookies
    cookies: list[dict[str, str]] = []
    if cookie_str:
        for pair in cookie_str.split(";"):
            pair = pair.strip()
            if "=" in pair:
                ck_key, ck_val = pair.split("=", 1)
                cookies.append({"key": ck_key.strip(), "value": ck_val.strip()})

    # 生成接口名称
    name = f"{method} {path}"

    return ParsedCurl(
        method=method,
        url=url,
        path=path,
        headers=headers,
        params=params,
        body=body,
        auth=auth,
        cookies=cookies,
        name=name,
    )
