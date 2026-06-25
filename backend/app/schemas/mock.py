from typing import Literal
from pydantic import BaseModel, Field

MatchMethod = Literal["*", "GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]


class MockCondition(BaseModel):
    field: str = Field(..., description="字段路径如 query.user_id, header.Content-Type, body.name")
    operator: str = Field(default="equals", description="操作符: equals/not_equals/contains/not_contains/greater_than/less_than/regex/in/exists")
    value: str = Field(default="", description="期望值")


class MockRuleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    enabled: bool = Field(default=True)
    priority: int = Field(default=0)
    match_method: MatchMethod = Field(default="*")
    match_path: str = Field(default="/")
    response_status: int = Field(default=200)
    response_headers: dict = Field(default={})
    response_body: str = Field(default="")
    response_delay: int = Field(default=0)
    conditions: list[MockCondition] | None = Field(default=None)
    script: str | None = Field(default=None)


class MockRuleUpdate(BaseModel):
    name: str = Field(default="", max_length=200)
    enabled: bool = Field(default=True)
    priority: int = Field(default=0)
    match_method: MatchMethod = Field(default="*")
    match_path: str = Field(default="/")
    response_status: int = Field(default=200)
    response_headers: dict = Field(default={})
    response_body: str = Field(default="")
    response_delay: int = Field(default=0)
    conditions: list[MockCondition] | None = Field(default=None)
    script: str | None = Field(default=None)


class MockTestRequest(BaseModel):
    project_id: int
    path: str
    method: str = "GET"
    query_params: dict | None = {}
    headers: dict | None = {}
    body: dict | None = None


class MockTestResponse(BaseModel):
    matched: bool
    rule: dict | None = None
    response: dict | None = None
    duration_ms: float


class SchemaMockRequest(BaseModel):
    """JSON Schema Mock 数据生成请求"""
    json_schema: dict = Field(..., description="JSON Schema 对象")


class MockCallLogQuery(BaseModel):
    """Mock 调用日志查询参数"""
    rule_id: int | None = Field(default=None, description="按规则 ID 过滤")
    start_date: str | None = Field(default=None, description="开始日期 (YYYY-MM-DD)")
    end_date: str | None = Field(default=None, description="结束日期 (YYYY-MM-DD)")
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
