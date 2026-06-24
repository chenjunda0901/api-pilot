"""JSON Schema 校验服务。

封装 ``jsonschema``，提供对象 / 字符串双输入支持，统一输出 ``ValidationResult``。

典型用法::

    validator = JSONSchemaValidator()
    result = validator.validate({"name": "a"}, {"type": "object", "required": ["name"]})
    if not result.valid:
        for err in result.errors:
            print(err.path, err.message)
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("service.json_schema")


class JSONSchemaError(Exception):
    """JSON Schema 解析或配置错误。"""


@dataclass
class ValidationError:
    """单条校验错误。"""

    path: str
    message: str
    validator: str = ""
    schema_path: str = ""

    def to_dict(self) -> dict[str, str]:
        return {
            "path": self.path,
            "message": self.message,
            "validator": self.validator,
            "schema_path": self.schema_path,
        }


@dataclass
class ValidationResult:
    """校验结果。"""

    valid: bool
    errors: list[ValidationError] = field(default_factory=list)
    error_count: int = 0

    def __post_init__(self) -> None:
        self.error_count = len(self.errors)


class JSONSchemaValidator:
    """JSON Schema 校验器。"""

    def __init__(self, format_checker: bool = True) -> None:
        self.format_checker = format_checker

    def _build_validator(self, schema: dict[str, Any]) -> Any:
        try:
            from jsonschema import Draft7Validator, Draft202012Validator
        except ImportError as exc:  # pragma: no cover
            raise JSONSchemaError("未安装 jsonschema") from exc
        # 优先 Draft 2020-12，回退到 Draft 7
        cls: Any = Draft202012Validator
        try:
            validator_cls: Any = Draft202012Validator
        except Exception:  # noqa: BLE001
            validator_cls = Draft7Validator
        try:
            return validator_cls(schema)
        except Exception as exc:
            raise JSONSchemaError(f"JSON Schema 不合法: {exc}") from exc

    def validate(self, data: Any, schema: dict[str, Any]) -> ValidationResult:
        """对 Python 对象校验。"""
        if not isinstance(schema, dict):
            raise JSONSchemaError("schema 必须是 dict")
        validator = self._build_validator(schema)
        errors: list[ValidationError] = []
        for err in validator.iter_errors(data):
            errors.append(
                ValidationError(
                    path=self._format_path(list(err.absolute_path)),
                    message=err.message,
                    validator=getattr(err, "validator", ""),
                    schema_path=self._format_path(list(err.absolute_schema_path)),
                )
            )
        return ValidationResult(valid=not errors, errors=errors)

    def validate_str(self, data_json: str, schema_json: str) -> ValidationResult:
        """对字符串形式的 JSON / schema 校验。"""
        try:
            data = json.loads(data_json)
        except json.JSONDecodeError as exc:
            raise JSONSchemaError(f"data JSON 解析失败: {exc}") from exc
        try:
            schema = json.loads(schema_json)
        except json.JSONDecodeError as exc:
            raise JSONSchemaError(f"schema JSON 解析失败: {exc}") from exc
        return self.validate(data, schema)

    def is_valid(self, data: Any, schema: dict[str, Any]) -> bool:
        return self.validate(data, schema).valid

    @staticmethod
    def _format_path(path_list: list[Any]) -> str:
        """把 ``['a', 0, 'b']`` 转成 ``$.a[0].b``。"""
        if not path_list:
            return "$"
        out = "$"
        for p in path_list:
            if isinstance(p, int):
                out += f"[{p}]"
            else:
                # 数字 key 走属性访问更直观
                out += f".{p}"
        return out


default_validator = JSONSchemaValidator()


def validate(data: Any, schema: dict[str, Any]) -> ValidationResult:
    return default_validator.validate(data, schema)
