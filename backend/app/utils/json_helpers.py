import json
from typing import Any


def safe_json_load(val: Any, default: Any = None) -> Any:
    """Safely parse a JSON string, returning default on failure."""
    if val is None:
        return default if default is not None else {}
    if isinstance(val, (dict, list)):
        return val
    try:
        result = json.loads(val)
        return result if isinstance(result, (dict, list)) else (default if default is not None else {})
    except (json.JSONDecodeError, TypeError) as e:
        import logging
        logging.getLogger("api_pilot").warning(f"safe_json_load 解析失败: {e}, 数据前200字符: {str(val)[:200]}")
        return default if default is not None else {}


def try_parse_json(text: str) -> Any:
    """Attempt to parse a string as JSON, returning the original string on failure."""
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return text


def safe_json_dumps(val: Any) -> str:
    """Safely serialize a value to JSON string."""
    if isinstance(val, str):
        return val
    return json.dumps(val, ensure_ascii=False, default=str)
