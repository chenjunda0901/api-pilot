from typing import Optional, Any, Literal
from pydantic import BaseModel, Field

Priority = Literal["P0", "P1", "P2", "P3"]
CaseStatus = Literal["active", "inactive"]
CaseType = Literal["positive", "negative", "boundary", "functional", "other"]


class CaseCreate(BaseModel):
    api_id: int
    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field(default="")
    priority: Priority = Field(default="P2")
    status: CaseStatus = Field(default="active")
    case_type: CaseType = Field(default="other")
    tags: str = Field(default="")
    request_body: Optional[str] = None
    assertions: list = []
    extract_vars: list = []


class CaseUpdate(BaseModel):
    name: str = Field(default="", max_length=200)
    description: str = Field(default="")
    priority: Priority = Field(default="P2")
    status: CaseStatus = Field(default="active")
    case_type: CaseType = Field(default="other")
    tags: str = Field(default="")
    request_body: Optional[str] = None
    assertions: list = []
    extract_vars: list = []


class AssertionCreate(BaseModel):
    assertion_type: str = Field(..., description="断言类型: jsonpath/jsonschema/regex/duration/header/cookie")
    expression: str = Field(default="", description="断言表达式")
    operator: str = Field(default="eq", description="比较器: eq/ne/gt/lt/in/contains/regex/exists")
    expected_value: str = Field(default="", description="期望值")
    enabled: bool = Field(default=True, description="是否启用")
    order_index: int = Field(default=0, description="排序索引")


class AssertionUpdate(BaseModel):
    assertion_type: str | None = Field(default=None, description="断言类型")
    expression: str | None = Field(default=None, description="断言表达式")
    operator: str | None = Field(default=None, description="比较器")
    expected_value: str | None = Field(default=None, description="期望值")
    enabled: bool | None = Field(default=None, description="是否启用")
    order_index: int | None = Field(default=None, description="排序索引")


class AssertionTestRequest(BaseModel):
    """用例断言临时测试请求"""
    response_json: Optional[Any] = Field(default=None, description="响应 JSON 数据")
    response_headers: Optional[dict[str, str]] = Field(default=None, description="响应头")
    duration_ms: Optional[int] = Field(default=None, ge=0, description="响应耗时(ms)")
