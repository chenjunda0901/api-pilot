"""6 类断言执行器。

接收 ``httpx.Response`` 与 ``list[ApiAssertion]``，逐条执行并返回 ``AssertionResult``。
失败时自动通过 ``jsonpath.extract`` 拉取实际值写入差异。

6 类断言：
  - jsonpath
  - jsonschema
  - regex
  - duration（响应耗时）
  - header（响应头）
  - cookie（响应 cookie）

典型用法::

    runner = AssertionRunner()
    results = await runner.run(response, assertions)
    for r in results:
        if not r.passed:
            print(r.actual, r.expected, r.diff)
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("service.assertion_runner")


# ── 数据结构 ────────────────────────────────────────────────────────────


@dataclass
class AssertionResult:
    """单条断言结果。"""

    assertion_id: int | None
    assertion_type: str
    expression: str
    operator: str
    expected_value: str
    actual_value: Any = None
    passed: bool = False
    error: str = ""
    diff: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "assertion_id": self.assertion_id,
            "type": self.assertion_type,
            "expression": self.expression,
            "operator": self.operator,
            "expected": self.expected_value,
            "actual": self.actual_value,
            "passed": self.passed,
            "error": self.error,
            "diff": self.diff,
        }


# ── 轻量断言协议（duck-typed）────────────────────────────────────────


class _AssertionLike:
    """duck-type 协议：runner 只用这些字段。"""

    id: int | None
    assertion_type: str
    expression: str
    operator: str
    expected_value: str
    enabled: bool


def _to_dict(obj: Any) -> _AssertionLike:
    """支持 ORM 实例或 dict。"""
    if isinstance(obj, dict):
        return obj  # type: ignore[return-value]
    # ORM 对象：通过属性访问
    return obj  # type: ignore[return-value]


# ── 断言执行器 ──────────────────────────────────────────────────────────


class AssertionRunner:
    """6 类断言执行器。"""

    def __init__(self) -> None:
        # 延迟构造 jsonpath service，避开循环依赖
        self._jsonpath = None

    @property
    def jsonpath(self) -> Any:
        if self._jsonpath is None:
            from app.services.jsonpath import JSONPathService

            self._jsonpath = JSONPathService()
        return self._jsonpath

    @property
    def schema_validator(self) -> Any:
        from app.services.json_schema_validator import JSONSchemaValidator

        return JSONSchemaValidator()

    # ── 公共入口 ────────────────────────────────────────────────

    async def run(
        self,
        response: Any,
        assertions: list[Any],
        duration_ms: float | None = None,
    ) -> list[AssertionResult]:
        results: list[AssertionResult] = []
        for a in assertions:
            ar = _to_dict(a)
            if isinstance(ar, dict):
                if not ar.get("enabled", True):
                    continue
            else:
                if not getattr(ar, "enabled", 1):
                    continue
            try:
                result = await self._run_one(response, ar, duration_ms)
            except Exception as exc:  # noqa: BLE001
                logger.exception("assertion crashed: %s", exc)
                result = AssertionResult(
                    assertion_id=self._get_id(ar),
                    assertion_type=self._get(ar, "assertion_type"),
                    expression=self._get(ar, "expression"),
                    operator=self._get(ar, "operator"),
                    expected_value=self._get(ar, "expected_value"),
                    passed=False,
                    error=str(exc),
                )
            results.append(result)
        return results

    # ── 单条断言分发 ─────────────────────────────────────────────

    async def _run_one(
        self,
        response: Any,
        assertion: Any,
        duration_ms: float | None,
    ) -> AssertionResult:
        atype = self._get(assertion, "assertion_type")
        handler = {
            "jsonpath": self._run_jsonpath,
            "jsonschema": self._run_jsonschema,
            "regex": self._run_regex,
            "duration": self._run_duration,
            "header": self._run_header,
            "cookie": self._run_cookie,
        }.get(atype)
        if handler is None:
            return AssertionResult(
                assertion_id=self._get_id(assertion),
                assertion_type=atype or "",
                expression=self._get(assertion, "expression"),
                operator=self._get(assertion, "operator"),
                expected_value=self._get(assertion, "expected_value"),
                passed=False,
                error=f"不支持的断言类型: {atype}",
            )
        if atype == "duration":
            return await handler(response, assertion, duration_ms)
        return await handler(response, assertion)

    # ── 各类型实现 ──────────────────────────────────────────────

    async def _run_jsonpath(self, response: Any, a: Any) -> AssertionResult:
        body = self._safe_json(response)
        path = self._get(a, "expression")
        op = self._get(a, "operator")
        expected = self._parse_expected(self._get(a, "expected_value"))
        result = AssertionResult(
            assertion_id=self._get_id(a),
            assertion_type="jsonpath",
            expression=path,
            operator=op,
            expected_value=self._get(a, "expected_value"),
        )
        try:
            actual_list = self.jsonpath.extract(body, path)
        except Exception as exc:  # noqa: BLE001
            result.passed = False
            result.error = str(exc)
            return result
        actual = actual_list[0] if actual_list else None
        result.actual_value = actual
        result.passed = self._compare(op, actual, expected)
        if not result.passed:
            result.diff = {"expected": expected, "actual": actual, "path": path}
        return result

    async def _run_jsonschema(self, response: Any, a: Any) -> AssertionResult:
        body = self._safe_json(response)
        result = AssertionResult(
            assertion_id=self._get_id(a),
            assertion_type="jsonschema",
            expression=self._get(a, "expression"),
            operator=self._get(a, "operator"),
            expected_value=self._get(a, "expected_value"),
        )
        try:
            schema = json.loads(
                self._get(a, "expected_value") or self._get(a, "expression")
            )
        except json.JSONDecodeError as exc:
            result.error = f"schema 解析失败: {exc}"
            return result
        try:
            v = self.schema_validator.validate(body, schema)
        except Exception as exc:  # noqa: BLE001
            result.error = str(exc)
            return result
        result.passed = v.valid
        result.actual_value = v.error_count
        if not v.valid:
            result.diff = {"errors": [e.to_dict() for e in v.errors[:5]]}
            result.error = result.error or f"{v.error_count} 处校验错误"
        return result

    async def _run_regex(self, response: Any, a: Any) -> AssertionResult:
        body = self._safe_json(response)
        text = self._coerce_to_text(body)
        pattern = self._get(a, "expression")
        result = AssertionResult(
            assertion_id=self._get_id(a),
            assertion_type="regex",
            expression=pattern,
            operator=self._get(a, "operator"),
            expected_value=self._get(a, "expected_value"),
        )
        try:
            m = re.search(pattern, text)
        except re.error as exc:
            result.error = f"正则不合法: {exc}"
            return result
        result.actual_value = m.group(0) if m else None
        if self._get(a, "operator") == "exists":
            result.passed = m is not None
        else:
            expected = self._get(a, "expected_value")
            result.passed = m is not None and (m.group(0) == expected)
        if not result.passed:
            result.diff = {
                "expected": self._get(a, "expected_value"),
                "actual": result.actual_value,
            }
        return result

    async def _run_duration(
        self,
        response: Any,
        a: Any,
        duration_ms: float | None,
    ) -> AssertionResult:
        result = AssertionResult(
            assertion_id=self._get_id(a),
            assertion_type="duration",
            expression=self._get(a, "expression"),
            operator=self._get(a, "operator"),
            expected_value=self._get(a, "expected_value"),
            actual_value=duration_ms,
        )
        op = self._get(a, "operator")
        try:
            threshold = float(self._get(a, "expected_value"))
        except (TypeError, ValueError):
            result.error = "duration 断言 expected_value 必须是数字（毫秒）"
            return result
        if duration_ms is None:
            result.error = "未提供 duration_ms"
            return result
        if op == "lt":
            result.passed = duration_ms < threshold
        elif op == "gt":
            result.passed = duration_ms > threshold
        elif op == "le":
            result.passed = duration_ms <= threshold
        elif op == "ge":
            result.passed = duration_ms >= threshold
        elif op == "eq":
            result.passed = abs(duration_ms - threshold) < 1.0
        else:
            result.passed = False
            result.error = f"duration 不支持的操作符: {op}"
        if not result.passed:
            result.diff = {"threshold_ms": threshold, "actual_ms": duration_ms}
        return result

    async def _run_header(self, response: Any, a: Any) -> AssertionResult:
        result = AssertionResult(
            assertion_id=self._get_id(a),
            assertion_type="header",
            expression=self._get(a, "expression"),
            operator=self._get(a, "operator"),
            expected_value=self._get(a, "expected_value"),
        )
        header_name = self._get(a, "expression")
        actual = self._get_header(response, header_name)
        result.actual_value = actual
        result.passed = self._compare(
            self._get(a, "operator"),
            actual,
            self._parse_expected(self._get(a, "expected_value")),
        )
        if not result.passed:
            result.diff = {"expected": self._get(a, "expected_value"), "actual": actual}
        return result

    async def _run_cookie(self, response: Any, a: Any) -> AssertionResult:
        result = AssertionResult(
            assertion_id=self._get_id(a),
            assertion_type="cookie",
            expression=self._get(a, "expression"),
            operator=self._get(a, "operator"),
            expected_value=self._get(a, "expected_value"),
        )
        cookie_name = self._get(a, "expression")
        actual = self._get_cookie(response, cookie_name)
        result.actual_value = actual
        result.passed = self._compare(
            self._get(a, "operator"),
            actual,
            self._parse_expected(self._get(a, "expected_value")),
        )
        if not result.passed:
            result.diff = {"expected": self._get(a, "expected_value"), "actual": actual}
        return result

    # ── 工具 ────────────────────────────────────────────────────

    @staticmethod
    def _safe_json(response: Any) -> Any:
        try:
            return response.json()
        except Exception:  # noqa: BLE001
            return None

    @staticmethod
    def _coerce_to_text(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        try:
            return json.dumps(value, ensure_ascii=False, default=str)
        except (TypeError, ValueError):
            return str(value)

    @staticmethod
    def _get_header(response: Any, name: str) -> str | None:
        try:
            return response.headers.get(name)
        except Exception:  # noqa: BLE001
            return None

    @staticmethod
    def _get_cookie(response: Any, name: str) -> str | None:
        """获取响应 cookie 值。httpx 已内置正确解析，无需手动 fallback。"""
        try:
            return response.cookies.get(name)
        except Exception:  # noqa: BLE001
            logger.warning("获取 cookie %s 失败", name)
            return None

    @staticmethod
    def _parse_expected(raw: str) -> Any:
        if raw is None:
            return None
        if not isinstance(raw, str):
            return raw
        s = raw.strip()
        # 尝试 JSON
        if (
            s.startswith(("{", "[", '"', "-"))
            or s.lower() in ("true", "false", "null")
            or s.isdigit()
        ):
            try:
                return json.loads(s)
            except json.JSONDecodeError:
                return raw
        return raw

    @staticmethod
    def _compare(op: str, actual: Any, expected: Any) -> bool:
        if op == "eq":
            return actual == expected
        if op == "ne":
            return actual != expected
        if op in ("gt", "lt", "ge", "le"):
            try:
                a, b = float(actual), float(expected)  # type: ignore[arg-type]
            except (TypeError, ValueError):
                return False
            if op == "gt":
                return a > b
            if op == "lt":
                return a < b
            if op == "ge":
                return a >= b
            if op == "le":
                return a <= b
        if op == "in":
            if isinstance(expected, str):
                try:
                    expected = json.loads(expected)
                except json.JSONDecodeError:
                    expected = [expected]
            if not isinstance(expected, (list, tuple, set)):
                return False
            return actual in expected
        if op == "contains":
            try:
                return str(expected) in str(actual)
            except Exception:  # noqa: BLE001
                return False
        if op == "regex":
            try:
                return bool(re.search(str(expected), str(actual)))
            except re.error:
                return False
        if op == "exists":
            return actual is not None
        return False

    @staticmethod
    def _get(obj: Any, key: str) -> Any:
        if isinstance(obj, dict):
            return obj.get(key)
        return getattr(obj, key, None)

    @staticmethod
    def _get_id(obj: Any) -> int | None:
        if isinstance(obj, dict):
            return obj.get("id")
        return getattr(obj, "id", None)
