"""JSONPath 解析服务。

基于 ``jsonpath-ng`` 提供 ``extract`` / ``set_value``，并对路径编译做 LRU 缓存。

典型用法::

    jp = JSONPathService()
    vals = jp.extract({"a": {"b": [1, 2]}}, "$.a.b[*]")
    jp.set_value({"x": 1}, "$.x", 99)
"""

from __future__ import annotations

import copy
import logging
from functools import lru_cache
from typing import Any

logger = logging.getLogger("service.jsonpath")


class JSONPathError(Exception):
    """JSONPath 解析失败。"""


@lru_cache(maxsize=512)
def _compile_path(path: str) -> Any:
    """编译并缓存 JSONPath 表达式。"""
    try:
        from jsonpath_ng.ext import parse as _parse
    except ImportError as exc:  # pragma: no cover
        raise JSONPathError("未安装 jsonpath-ng，请执行 `pip install jsonpath-ng`") from exc
    if not path or not isinstance(path, str):
        raise JSONPathError("JSONPath 表达式不能为空")
    try:
        return _parse(path)
    except Exception as exc:
        raise JSONPathError(f"JSONPath 不合法: {path}") from exc


class JSONPathService:
    """JSONPath 解析服务。"""

    def extract(self, json_obj: Any, path: str) -> list[Any]:
        """提取路径下所有匹配值。"""
        expr = _compile_path(path)
        try:
            matches = expr.find(json_obj)
        except Exception as exc:
            raise JSONPathError(f"JSONPath 解析失败: {path} -> {exc}") from exc
        return [m.value for m in matches]

    def extract_first(self, json_obj: Any, path: str, default: Any = None) -> Any:
        """提取路径下第一个匹配值；无匹配返回 ``default``。"""
        vals = self.extract(json_obj, path)
        return vals[0] if vals else default

    def set_value(self, json_obj: Any, path: str, value: Any) -> Any:
        """设置路径对应字段；返回新对象（不修改入参）。"""
        expr = _compile_path(path)
        # 复制后再改，避免污染入参
        target = copy.deepcopy(json_obj)
        try:
            expr.update(target, value)
        except Exception as exc:
            raise JSONPathError(f"JSONPath set 失败: {path} -> {exc}") from exc
        return target

    def exists(self, json_obj: Any, path: str) -> bool:
        """判断路径是否存在（至少一个匹配）。"""
        try:
            return len(self.extract(json_obj, path)) > 0
        except JSONPathError:
            return False

    def compile(self, path: str) -> Any:
        """显式编译（主要给单元测试用）。"""
        return _compile_path(path)


# 模块级单例，便于复用缓存
default_service = JSONPathService()


def extract(json_obj: Any, path: str) -> list[Any]:
    return default_service.extract(json_obj, path)


def set_value(json_obj: Any, path: str, value: Any) -> Any:
    return default_service.set_value(json_obj, path, value)
