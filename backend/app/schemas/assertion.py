"""断言库 Pydantic 模型。"""

from typing import Any
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class AssertionBase(BaseModel):
    """断言基类。"""

    owner_type: str = Field(..., description="挂载对象类型: api / case")
    owner_id: int = Field(..., ge=1)
    assertion_type: str = Field(..., description="断言类型: jsonpath / jsonschema / regex / duration / header / cookie")
    expression: str = Field(..., min_length=1, description="断言表达式，如 $.data[0].name")
    operator: str = Field(..., description="比较操作符: eq / ne / gt / lt / in / contains / regex / exists")
    expected_value: str = Field(default="", description="期望值（字符串形式存储，复杂值用 JSON 字符串）")
    enabled: bool = Field(default=True)
    order_index: int = Field(default=0, ge=0)

    @field_validator("owner_type")
    @classmethod
    def validate_owner(cls, v: str) -> str:
        if v not in ("api", "case"):
            raise ValueError("owner_type 必须是 api 或 case")
        return v

    @field_validator("assertion_type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        allowed = {"jsonpath", "jsonschema", "regex", "duration", "header", "cookie"}
        if v not in allowed:
            raise ValueError(f"assertion_type 必须是 {', '.join(sorted(allowed))} 之一")
        return v

    @field_validator("operator")
    @classmethod
    def validate_operator(cls, v: str) -> str:
        allowed = {"eq", "ne", "gt", "lt", "ge", "le", "in", "contains", "regex", "exists"}
        if v not in allowed:
            raise ValueError(f"operator 必须是 {', '.join(sorted(allowed))} 之一")
        return v


class AssertionCreate(AssertionBase):
    """创建断言请求。"""


class AssertionUpdate(BaseModel):
    """更新断言请求。"""

    assertion_type: str | None = None
    expression: str | None = Field(default=None, min_length=1)
    operator: str | None = None
    expected_value: str | None = None
    enabled: bool | None = None
    order_index: int | None = Field(default=None, ge=0)


class AssertionOut(AssertionBase):
    """断言输出。"""

    id: int
    created_at: datetime | None = None


class AssertionTestRequest(BaseModel):
    """临时测试断言请求。"""

    response_json: Any = Field(..., description="响应数据（任意 JSON 类型）")
    response_headers: dict[str, str] | None = Field(default=None, description="响应头（header 断言需要）")
    response_cookies: dict[str, str] | None = Field(default=None, description="响应 cookies（cookie 断言需要）")
    duration_ms: float | None = Field(default=None, description="请求耗时（duration 断言需要）")
    assertions: list[dict[str, Any]] = Field(..., min_length=1, description="待测试断言列表（结构同 AssertionCreate）")


class AssertionTestResult(BaseModel):
    """单条断言临时测试结果。"""

    expression: str
    operator: str
    expected: Any
    actual: Any
    passed: bool
    error: str = ""
    diff: dict[str, Any] = Field(default_factory=dict)


class AssertionTestResponse(BaseModel):
    """断言临时测试响应。"""

    total: int
    passed: int
    failed: int
    results: list[AssertionTestResult]


class AssertionReorderRequest(BaseModel):
    """批量重排断言顺序请求。"""

    items: list[dict[str, Any]] = Field(..., min_length=1, description="[{id, order_index}]")
