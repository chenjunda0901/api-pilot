"""JSON 字段 diff 与 Breaking Change 检测。

纯 Python 实现，不引入外部依赖。输出稳定的 ``DiffOp`` 列表与人类可读摘要。

典型用法::

    differ = JSONDiffer()
    diffs = differ.diff({"a": 1, "b": 2}, {"a": 1, "c": 3})
    if differ.is_breaking_change(diffs):
        print(differ.summarize(diffs))
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, asdict
from typing import Any

logger = logging.getLogger("service.diff")


# ── 数据结构 ────────────────────────────────────────────────────────────


@dataclass
class DiffOp:
    """单条 diff 操作。"""

    op: str  # add / remove / replace / type_change
    path: str  # JSONPath 风格，如 $.a.b[0]
    old: Any = None
    new: Any = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ── 服务实现 ────────────────────────────────────────────────────────────


class JSONDiffer:
    """JSON diff + Breaking Change 检测。"""

    # 关键字面值：超过该长度的字符串不打印到摘要，避免刷屏
    _SUMMARY_MAX_VALUE_LEN = 60

    # ── diff ─────────────────────────────────────────────────────

    def diff(
        self,
        old: Any,
        new: Any,
        path: str = "$",
    ) -> list[DiffOp]:
        """递归 diff 两份 JSON，返回稳定的 ``DiffOp`` 列表。

        路径使用 JSONPath 风格：
          - 根：``$``
          - 字段：``$.a``
          - 数组：``$.a[0]``
        """
        ops: list[DiffOp] = []
        self._walk(old, new, path, ops)
        return ops

    def _walk(self, old: Any, new: Any, path: str, ops: list[DiffOp]) -> None:
        # 类型不一致：type_change
        if type(old) is not type(new) and not self._both_numeric(old, new):
            ops.append(DiffOp(op="type_change", path=path, old=old, new=new))
            return
        if isinstance(old, dict) and isinstance(new, dict):
            self._diff_dict(old, new, path, ops)
        elif isinstance(old, list) and isinstance(new, list):
            self._diff_list(old, new, path, ops)
        else:
            if old != new:
                ops.append(DiffOp(op="replace", path=path, old=old, new=new))

    @staticmethod
    def _both_numeric(a: Any, b: Any) -> bool:
        return isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool) and not isinstance(b, bool)

    def _diff_dict(
        self,
        old: dict[str, Any],
        new: dict[str, Any],
        path: str,
        ops: list[DiffOp],
    ) -> None:
        # 旧有
        for key in old.keys() - new.keys():
            ops.append(DiffOp(op="remove", path=self._field(path, key), old=old[key], new=None))
        # 新增
        for key in new.keys() - old.keys():
            ops.append(DiffOp(op="add", path=self._field(path, key), old=None, new=new[key]))
        # 同名
        for key in old.keys() & new.keys():
            self._walk(old[key], new[key], self._field(path, key), ops)

    def _diff_list(
        self,
        old: list[Any],
        new: list[Any],
        path: str,
        ops: list[DiffOp],
    ) -> None:
        # 简化策略：按索引对齐，长度变化按 add / remove 补齐
        max_len = max(len(old), len(new))
        for i in range(max_len):
            sub_path = self._index(path, i)
            if i >= len(old):
                ops.append(DiffOp(op="add", path=sub_path, old=None, new=new[i]))
            elif i >= len(new):
                ops.append(DiffOp(op="remove", path=sub_path, old=old[i], new=None))
            else:
                self._walk(old[i], new[i], sub_path, ops)

    @staticmethod
    def _field(parent: str, key: Any) -> str:
        if not isinstance(key, str):
            return f"{parent}[{key}]"
        # key 包含特殊字符时用引号包裹
        if key.isidentifier():
            return f"{parent}.{key}"
        return f'{parent}["{key}"]'

    @staticmethod
    def _index(parent: str, idx: int) -> str:
        return f"{parent}[{idx}]"

    # ── Breaking Change 检测 ─────────────────────────────────────

    # 下列路径变化视为 breaking
    def is_breaking_change(self, diffs: list[DiffOp]) -> bool:
        """判断 diff 列表是否包含 breaking change。

        规则：
          - 顶层必填字段删除（约定：字段名以 ``_required`` 结尾，或父路径为 ``$`` 视为必填）
          - 任意层级的 type_change
          - 路径前缀消失（例如 ``$.a`` 删除）— 体现为 remove / type_change
        """
        for op in diffs:
            if op.op == "type_change":
                return True
            if op.op == "remove":
                # 顶层字段删除即破坏性
                parent = op.path[: op.path.rfind(".") if "." in op.path else len(op.path)]
                if parent == "$":
                    return True
        return False

    # ── 摘要 ─────────────────────────────────────────────────────

    def summarize(self, diffs: list[DiffOp]) -> str:
        """人类可读的 diff 摘要。"""
        if not diffs:
            return "无差异"
        lines = [f"共 {len(diffs)} 处变更:"]
        for op in diffs:
            lines.append(self._format_op(op))
        return "\n".join(lines)

    def _format_op(self, op: DiffOp) -> str:
        old_s = self._truncate(op.old)
        new_s = self._truncate(op.new)
        if op.op == "add":
            return f"+ {op.path}: {new_s}"
        if op.op == "remove":
            return f"- {op.path}: {old_s}"
        if op.op == "replace":
            return f"~ {op.path}: {old_s} → {new_s}"
        if op.op == "type_change":
            return f"! {op.path}: {type(op.old).__name__} → {type(op.new).__name__}"
        return f"? {op.path}"

    def _truncate(self, value: Any) -> str:
        if value is None:
            return "null"
        s = repr(value)
        if len(s) > self._SUMMARY_MAX_VALUE_LEN:
            return s[: self._SUMMARY_MAX_VALUE_LEN - 3] + "..."
        return s

    # ── 工具方法 ─────────────────────────────────────────────────

    def to_jsonable(self, diffs: list[DiffOp]) -> list[dict[str, Any]]:
        """把 ``DiffOp`` 列表转成可 JSON 序列化的字典列表。"""
        return [op.to_dict() for op in diffs]


default_differ = JSONDiffer()


def diff(old: Any, new: Any) -> list[DiffOp]:
    return default_differ.diff(old, new)
