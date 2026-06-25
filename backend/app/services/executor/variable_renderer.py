"""变量渲染引擎 — 模板变量替换。

核心能力：
- render_template：替换字符串中的 {{key}} 模板变量（仅双花括号格式）
- render_dict：递归渲染字典中的所有字符串值
- find_undefined_variables：检测模板中未定义的变量，返回明确的错误信息

支持点号路径：{{user.name}} 会从 variables["user"]["name"] 取值。
未找到的变量返回空字符串（或指定的 default 值）。

安全机制：
- 循环引用防护：通过最大深度限制（MAX_DEPTH=10）防止变量相互引用导致无限递归
"""

import logging
import re
from typing import Any

logger = logging.getLogger("executor")

# 匹配 {{variable}} 占位符
VARIABLE_PATTERN = re.compile(r"\{\{\s*(\w+(?:\.\w+)*)\s*\}\}")

# 防止循环引用的最大递归深度
MAX_DEPTH = 10


def find_undefined_variables(template: str, variables: dict[str, Any]) -> list[str]:
    """检测模板字符串中未定义的变量名列表。

    Args:
        template: 包含 {{variable}} 占位符的模板字符串
        variables: 当前变量字典

    Returns:
        未定义的变量名列表，如 ["base_url", "version"]
    """
    if not template or not isinstance(template, str):
        return []

    undefined = []
    for match in VARIABLE_PATTERN.finditer(template):
        var_name = match.group(1)
        if not var_name:
            continue
        # 检查变量是否存在（支持点号路径）
        path = var_name.split(".")
        value = variables
        found = True
        for key in path:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                found = False
                break
        if not found:
            undefined.append(var_name)
    return undefined


def render_template_with_check(template: str, variables: dict[str, Any],
                                default: str = "") -> tuple[str, list[str]]:
    """渲染模板并返回未定义变量列表。

    Args:
        template: 模板字符串
        variables: 变量字典
        default: 未定义变量的默认值

    Returns:
        (渲染后的字符串, 未定义变量名列表)
    """
    undefined = find_undefined_variables(template, variables)
    rendered = render_template(template, variables, default)
    return rendered, undefined


def format_undefined_error(var_name: str) -> str:
    """生成变量未定义的友好错误信息。

    Args:
        var_name: 未定义的变量名

    Returns:
        错误信息字符串
    """
    return f"变量 {{{{{var_name}}}}} 未定义，请检查变量配置"


def _resolve_value(var_name: str, variables: dict[str, Any], default: str = "",
                  _depth: int = 0, _visited: set | None = None) -> str:
    """从变量字典中解析变量值，支持点号路径和引用链。

    安全机制：
    - 最大递归深度限制，防止 A→B→A 循环引用导致栈溢出
    - 超过深度限制时返回当前已解析的值（而非 default），避免截断正常变量链

    Args:
        var_name: 变量名（支持点号路径如 user.name）
        variables: 变量字典
        default: 变量不存在时的默认值
        _depth: 当前递归深度（内部使用，外部调用勿传）

    Returns:
        解析后的字符串值
    """
    if _visited is None:
        _visited = set()
    # 循环引用检测：当前变量已在解析链中
    if var_name in _visited:
        logger.warning(
            "变量渲染检测到循环引用: %s，返回默认值",
            var_name)
        return default
    _visited.add(var_name)

    # 先解析变量路径
    path = var_name.split(".")
    value = variables
    for key in path:
        if isinstance(value, dict):
            value = value.get(key, default)
        else:
            return default

    if value is None:
        return default

    # 如果值本身也是字符串且包含模板变量，需要递归解析（引用链）
    if isinstance(value, str) and VARIABLE_PATTERN.search(value):
        if _depth >= MAX_DEPTH:
            logger.warning(
                "变量渲染达到最大深度限制(%d)，可能存在循环引用: %s → %s",
                MAX_DEPTH, var_name, str(value)[:200])
            # 返回当前已解析的值，而非 default（空字符串）
            _visited.discard(var_name)
            return str(value)
        result = render_template(value, variables, default, _depth=_depth + 1,
                                _visited=_visited)
        _visited.discard(var_name)
        return result

    _visited.discard(var_name)
    return str(value)


def render_template(template: str, variables: dict[str, Any], default: str = "",
                    _depth: int = 0, _visited: set | None = None) -> str:
    """替换字符串中的 {{key}} 模板变量。

    Args:
        template: 包含 {{variable}} 占位符的模板字符串
        variables: 变量字典，支持点号路径如 {"user": {"name": "Alice"}}
        default: 变量不存在时的默认值（默认空字符串）
        _depth: 当前递归深度（内部使用）

    Returns:
        替换后的字符串。template 为 None 时返回 ""，
        template 为 "" 时返回 ""（保留空字符串用于后续拼接）。
    """
    # 对 None 和 "" 统一返回 ""，但保留两种情况的语义说明
    # 调用方依赖空字符串返回用于后续拼接（如 URL 组装）
    if template is None or template == "":
        return ""

    try:
        def _replacer(match):
            var_name = match.group(1)
            if not var_name:
                return default
            try:
                return _resolve_value(var_name, variables, default, _depth=_depth, _visited=_visited)
            except Exception as e:
                logger.warning(
                    "变量渲染异常: %s, 错误: %s, 返回默认值",
                    var_name, str(e))
                return default

        return VARIABLE_PATTERN.sub(_replacer, template)
    except Exception as e:
        logger.error("模板渲染失败: %s, 错误: %s", template[:200], str(e))
        return template


def render_dict(data: dict, variables: dict[str, Any]) -> dict:
    """递归渲染字典中所有字符串值的模板变量。

    Args:
        data: 包含模板变量的字典（可能嵌套）
        variables: 变量字典

    Returns:
        所有字符串值已渲染的新字典
    """
    result = {}
    for key, value in data.items():
        if isinstance(value, str):
            result[key] = render_template(value, variables)
        elif isinstance(value, dict):
            result[key] = render_dict(value, variables)
        elif isinstance(value, list):
            result[key] = [render_template(v, variables) if isinstance(v, str) else v for v in value]
        else:
            result[key] = value
    return result
