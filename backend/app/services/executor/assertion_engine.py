"""断言引擎 — JSONPath 取值与断言执行。

提供两组核心能力：
1. jsonpath_get：从嵌套 JSON 中按路径取值（如 $.data.items[0].id）
2. run_assertions：批量执行断言规则，返回每条断言的结果（passed/actual/expected/diff）

支持断言类型：status（状态码）、header（响应头）、cookie（Cookie）、
body/json（JSON 响应体）、contains（包含）、regex（正则）、
response_time/duration（响应时间）。

类型容错机制：
- JSONPath 提取单元素列表自动解包为标量值
- 数字类型智能对齐（"200" == 200 自动容错）
- 所有数值比较操作符自动尝试类型转换

断言失败时生成 diff 数据结构，用于前端可视化显示差异。
"""

import difflib
import json
import logging
import re
from typing import Any

logger = logging.getLogger("executor")

# 断言类型中文标签
ASSERTION_TYPE_LABELS = {
    "status": "状态码",
    "status_code": "状态码",
    "header": "响应头",
    "cookie": "Cookie",
    "body": "响应体",
    "json": "JSON响应",
    "json_path": "JSON路径",
    "response_body": "响应体",
    "json_extract": "JSON提取",
    "contains": "包含",
    "regex": "正则匹配",
    "response_time": "响应时间",
    "duration": "耗时",
}

# 操作符中文标签
OPERATOR_LABELS = {
    "eq": "等于",
    "neq": "不等于",
    "gt": "大于",
    "gte": "大于等于",
    "lt": "小于",
    "lte": "小于等于",
    "contains": "包含",
    "not_contains": "不包含",
    "regex": "正则匹配",
    "is_null": "为空",
    "is_not_null": "不为空",
}


# ReDoS 防护：正则长度超过 100 字符时拒绝
_MAX_REGEX_LENGTH = 100
# 正则执行超时（秒）
_REGEX_TIMEOUT = 2.0
# 已知的灾难性回溯模式检测
_CATASTROPHIC_PATTERN = re.compile(
    r"\(\w+(?:\.\+\?|\\w\+\?|[+*?][+*?]|\(\.\*\)\+\?)"
)


def _safe_re_search(pattern: str, text: str) -> "re.Match[str] | None":
    """安全正则搜索，防止 ReDoS 攻击。"""
    if len(pattern) > _MAX_REGEX_LENGTH:
        return None
    # 检测嵌套量词等灾难性回溯模式
    if _CATASTROPHIC_PATTERN.search(pattern):
        return None
    try:
        compiled = re.compile(pattern)
        # 使用线程池执行正则，设置超时避免事件循环阻塞
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(compiled.search, text)
            return future.result(timeout=_REGEX_TIMEOUT)
    except concurrent.futures.TimeoutError:
        return None
    except re.error:
        return None


def get_assertion_label(assertion: dict) -> str:
    """生成断言的友好描述文本。

    Args:
        assertion: 断言规则字典

    Returns:
        友好描述字符串，如 "状态码 等于 200"
    """
    atype = assertion.get("type", "")
    operator = assertion.get("operator", "eq")
    expected = assertion.get("value", "")

    # 获取类型标签
    type_label = ASSERTION_TYPE_LABELS.get(atype, atype or "未知")

    # 获取操作符标签
    op_label = OPERATOR_LABELS.get(operator, operator or "等于")

    # 特殊处理header类型
    if atype in ("header",) and assertion.get("header"):
        type_label = f"响应头[{assertion.get('header')}]"

    # 特殊处理body/json类型且有path
    if atype in ("body", "json", "json_path", "json_extract") and assertion.get("path"):
        type_label = f"响应体[{assertion.get('path')}]"

    return f"{type_label} {op_label} {expected}"


def jsonpath_get(obj: Any, path: str) -> Any:
    """从嵌套结构中按路径取值。

    支持的路径格式：
    - $.status → 顶层 key
    - $.data.items[0].id → 嵌套数组元素
    - data.items[0] → 省略开头的 $. 也可

    Args:
        obj: JSON 解析后的 Python 对象（dict/list 嵌套）
        path: 取值路径字符串

    Returns:
        找到的值，或 None（路径不存在时）
    """
    if not path or not path.strip():
        return None  # 空路径或纯空白路径显式返回 None
    path = path.lstrip("$.")
    parts = re.split(r"\.|\[", path)
    current = obj
    for part in parts:
        part = part.rstrip("]")
        if not part:
            continue
        if isinstance(current, dict) and part in current:
            current = current[part]
        elif isinstance(current, (list, tuple)) and part.isdigit():
            idx = int(part)
            if 0 <= idx < len(current):
                current = current[idx]
            else:
                return None
        else:
            return None
    return current


def _unwrap_singleton(val: Any) -> Any:
    """将单元素列表解包为标量值。

    JSONPath 提取结果始终为列表，当只匹配到一个元素时
    自动解包，避免 [10025] == 10025 的断言失败。
    """
    if isinstance(val, list) and len(val) == 1:
        return val[0]
    return val


def _try_coerce_numeric(actual: Any, expected: Any) -> tuple[Any, Any]:
    """智能数字类型对齐。

    当一方为数字另一方为字符串时，尝试将字符串转为数字再比对。
    解决前端输入 "200" 与 API 返回 200 的类型不一致痛点。
    """
    try:
        if isinstance(actual, (int, float)) and not isinstance(expected, (int, float)):
            expected = type(actual)(expected)
        elif isinstance(expected, (int, float)) and not isinstance(actual, (int, float)):
            actual = type(expected)(actual)
    except (ValueError, TypeError):
        pass
    return actual, expected


def _compare(actual: Any, expected: Any, operator: str) -> bool:
    """比较实际值与期望值，按指定操作符执行。

    支持的操作符：
    - eq/neq: 相等/不等
    - gt/gte/lt/lte: 数值大小比较
    - contains/not_contains: 字符串包含
    - regex: 正则匹配
    - is_null/is_not_null: 是否为空
    """
    try:
        if operator in ("eq", "equals"):
            actual, expected = _try_coerce_numeric(actual, expected)
            return actual == expected
        elif operator in ("neq", "not_equals"):
            actual, expected = _try_coerce_numeric(actual, expected)
            return actual != expected
        elif operator == "gt":
            return float(actual) > float(expected)
        elif operator == "gte":
            return float(actual) >= float(expected)
        elif operator == "lt":
            return float(actual) < float(expected)
        elif operator == "lte":
            return float(actual) <= float(expected)
        elif operator == "contains":
            return str(expected) in str(actual)
        elif operator == "not_contains":
            return str(expected) not in str(actual)
        elif operator == "regex":
            return bool(_safe_re_search(str(expected), str(actual)))
        elif operator == "is_null":
            return actual is None
        elif operator == "is_not_null":
            return actual is not None
        # 未知操作符 → 断言失败（而非静默通过），并记录警告
        logger.warning("未知断言操作符: %s，断言将视为失败", operator)
        return False
    except (ValueError, TypeError):
        return False


def generate_assertion_diff(expected: Any, actual: Any, operator: str = "eq") -> dict:
    """生成断言失败的 diff 数据结构，用于前端可视化显示。

    Args:
        expected: 期望值
        actual: 实际值
        operator: 操作符

    Returns:
        diff 数据结构，包含 type 和具体差异信息
    """
    # 将值转为字符串进行比较
    expected_str = str(expected) if expected is not None else ""
    actual_str = str(actual) if actual is not None else ""

    # 如果都是 JSON 字符串，尝试格式化后比较
    if expected_str and actual_str:
        try:
            expected_json = json.loads(expected_str)
            actual_json = json.loads(actual_str)
            # 格式化为标准 JSON 字符串（排序、缩进）
            expected_str = json.dumps(expected_json, sort_keys=True, indent=2, ensure_ascii=False)
            actual_str = json.dumps(actual_json, sort_keys=True, indent=2, ensure_ascii=False)
        except (json.JSONDecodeError, TypeError):
            pass

    # 使用 difflib 生成 unified diff
    diff_lines = list(difflib.unified_diff(
        expected_str.splitlines(keepends=True),
        actual_str.splitlines(keepends=True),
        fromfile="expected",
        tofile="actual",
        lineterm=""
    ))

    diff_text = "\n".join(diff_lines)

    return {
        "type": "unified",
        "expected": expected_str,
        "actual": actual_str,
        "diff": diff_text,
        "operator": operator,
    }


def evaluate_assertion(assertion: dict, response_status: int,
                       response_body: Any, response_headers: dict,
                       response_cookies: dict | None = None) -> tuple[bool, Any, Any, dict | None]:
    """执行单条断言规则，返回 (是否通过, 实际值, 期望值, diff)。

    Args:
        assertion: 断言规则字典，包含 type/operator/value/path/header 等字段
        response_status: HTTP 响应状态码
        response_body: 解析后的响应体（dict/list/str）
        response_headers: 响应头字典
        response_cookies: Cookie 字典（可选）

    Returns:
        (passed, actual, expected, diff) 四元组，diff 仅在失败时返回
    """
    atype = assertion.get("type", "")
    # 别名映射：兼容前端常见类型名称
    type_aliases = {
        "status_code": "status",
        "json_path": "body",
        "response_body": "body",
        "json_extract": "body",
        "duration": "response_time",
    }
    atype = type_aliases.get(atype, atype)
    operator = assertion.get("operator", "eq")
    expected = assertion.get("value")
    actual = None

    if atype == "status":
        actual = response_status
    elif atype == "header":
        header_name = assertion.get("header", "")
        if isinstance(response_headers, dict):
            actual = response_headers.get(header_name) or response_headers.get(header_name.lower())
    elif atype == "cookie":
        cookie_name = assertion.get("cookie", "")
        if response_cookies and isinstance(response_cookies, dict):
            actual = response_cookies.get(cookie_name)
    elif atype == "body":
        path = assertion.get("path", "")
        operator = assertion.get("operator", "eq")
        if path:
            actual = jsonpath_get(response_body, path)
            actual = _unwrap_singleton(actual)
        elif operator in ("contains", "not_contains", "regex"):
            actual = response_body
            if not isinstance(actual, str):
                actual = json.dumps(actual) if actual is not None else ""
        else:
            actual = response_body
            actual = _unwrap_singleton(actual)
    elif atype == "json":
        path = assertion.get("path", "")
        actual = jsonpath_get(response_body, path)
        actual = _unwrap_singleton(actual)
    elif atype == "contains":
        actual = response_body
        if isinstance(actual, str):
            pass
        else:
            actual = json.dumps(actual) if actual is not None else ""
    elif atype == "regex":
        actual = response_body
        if not isinstance(actual, str):
            actual = json.dumps(actual) if actual is not None else ""
    elif atype == "response_time":
        actual = assertion.get("actual")
    else:
        return True, None, expected, None

    passed = _compare(actual, expected, operator)

    # 失败时生成 diff
    diff = None
    if not passed:
        diff = generate_assertion_diff(expected, actual, operator)

    return passed, actual, expected, diff


def run_assertions(assertions: list, response_status: int,
                   response_body: Any, response_headers: dict,
                   duration: float = 0, response_cookies: dict | None = None) -> list[dict]:
    """批量执行断言规则。

    遍历断言列表，执行每条规则后标记 passed/actual/expected/diff。
    对 response_time 类型的断言注入实际 duration 值。
    容错机制：跳过格式不规范的断言规则，记录日志但不中断执行。

    Args:
        assertions: 断言规则列表
        response_status: HTTP 状态码
        response_body: 解析后的响应体
        response_headers: 响应头字典
        duration: 实际请求耗时（ms）
        response_cookies: Cookie 字典（可选）

    Returns:
        每条断言的结果 dict，包含原始字段 + passed/actual/expected/diff
    """
    results = []
    for idx, asc in enumerate(assertions):
        # 验证断言规则格式
        if not isinstance(asc, dict):
            logger.warning("断言规则 #%d 格式不规范（非字典），已跳过", idx)
            continue

        if not asc.get("type"):
            logger.warning("断言规则 #%d 缺少 type 字段，已跳过", idx)
            continue

        asc = dict(asc)
        if asc.get("type") in ("response_time", "duration"):
            asc["actual"] = duration

        try:
            passed, actual, expected, diff = evaluate_assertion(
                asc, response_status, response_body, response_headers, response_cookies)
            # 生成友好描述
            asc["description"] = get_assertion_label(asc)
            result_item = {
                **asc,
                "passed": passed,
                "actual": actual,
                "expected": expected,
            }
            # 仅在失败时添加 diff 字段
            if diff:
                result_item["diff"] = diff
            results.append(result_item)
        except Exception as e:
            logger.error("断言规则 #%d 执行异常: %s", idx, str(e))
            results.append({
                **asc,
                "passed": False,
                "actual": None,
                "expected": asc.get("value"),
                "description": get_assertion_label(asc),
            })
    return results
