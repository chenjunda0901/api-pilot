from typing import Optional, Literal
from datetime import datetime
import re
from pydantic import BaseModel, Field, field_validator


ApiStatus = Literal["draft", "published", "deprecated"]


class ApiCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    method: str = Field(default="GET")
    path: str = Field(default="/", max_length=2000)
    category_id: Optional[int] = None
    description: str = Field(default="")
    description_md: str = Field(default="")
    headers: list = []
    params: list = []
    body: dict = {"type": "none", "content": ""}
    auth_type: str = Field(default="none")
    pre_script: str = Field(default="")
    post_script: str = Field(default="")
    cookies: list = []
    auth: dict = {"type": "none"}
    settings: dict = {"follow_redirects": True, "verify_ssl": True, "timeout": 30}
    response_examples: Optional[list] = None
    response_schema: Optional[str] = None
    extract_vars: list = []
    is_starred: bool = Field(default=False, description="是否收藏")
    sort_order: int = Field(default=0, description="排序权重")
    tags: list[str] = Field(default=[], description="标签名称列表")
    status: ApiStatus = Field(
        default="draft", description="API 状态: draft/published/deprecated"
    )
    version: str = Field(default="v1.0", description="版本号")
    created_by: Optional[int] = Field(None, description="创建者用户 ID")

    @field_validator("name")
    @classmethod
    def sanitize_name(cls, v: str) -> str:
        v = v.strip()
        if re.search(r"<[^>]+>", v):
            raise ValueError("名称不允许包含 HTML 标签")
        return v

    @field_validator("method")
    @classmethod
    def validate_method(cls, v: str) -> str:
        allowed = {"GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"}
        v_upper = v.upper().strip()
        if not v_upper or v_upper not in allowed:
            raise ValueError(f"请求方法必须是 {', '.join(sorted(allowed))} 之一")
        return v_upper

    @field_validator("path")
    @classmethod
    def validate_path(cls, v: str) -> str:
        v = v.strip()
        if not v:
            v = "/"
        if not v.startswith("/"):
            v = "/" + v
        return v


class ApiUpdate(BaseModel):
    name: str = Field(default="", max_length=200)
    method: str = Field(default="")
    path: str = Field(default="", max_length=2000)
    category_id: Optional[int] = None
    description: str = Field(default="")
    description_md: str = Field(default="")
    headers: list = []
    params: list = []
    body: dict = {"type": "none", "content": ""}
    auth_type: str = Field(default="none")
    pre_script: str = Field(default="")
    post_script: str = Field(default="")
    cookies: list = []
    auth: dict = {"type": "none"}
    settings: dict = {"follow_redirects": True, "verify_ssl": True, "timeout": 30}
    extract_vars: list = []
    response_examples: Optional[list] = None
    response_schema: Optional[str] = None
    is_starred: Optional[bool] = Field(default=None, description="是否收藏")
    sort_order: Optional[int] = Field(default=None, description="排序权重")
    tags: list[str] = Field(default=[], description="标签名称列表")
    status: ApiStatus = Field(
        default="draft", description="API 状态: draft/published/deprecated"
    )
    version: str = Field(default="v1.0", description="版本号")
    created_by: Optional[int] = Field(None, description="创建者用户 ID")
    updated_at: Optional[datetime] = Field(
        None, description="最后更新时间戳（乐观锁版本号）"
    )

    @field_validator("name")
    @classmethod
    def sanitize_name(cls, v: str) -> str:
        if v and re.search(r"<[^>]+>", v):
            raise ValueError("名称不允许包含 HTML 标签")
        return v

    @field_validator("method")
    @classmethod
    def validate_method(cls, v: str) -> str:
        if not v or not v.strip():
            return v  # 允许空字符串，service 层会用 or 保留原值
        allowed = {"GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"}
        v_upper = v.upper().strip()
        if v_upper not in allowed:
            raise ValueError(f"请求方法必须是 {', '.join(sorted(allowed))} 之一")
        return v_upper

    @field_validator("path")
    @classmethod
    def validate_path(cls, v: str) -> str:
        v = v.strip()
        if not v:
            return v  # 允许空字符串，service 层会用 or 保留原值
        if not v.startswith("/"):
            v = "/" + v
        return v


class ApiMove(BaseModel):
    category_id: Optional[int] = None


class BatchMoveRequest(BaseModel):
    api_ids: list[int] = Field(..., min_length=1, max_length=200)
    target_category_id: Optional[int] = None


class BatchCopyRequest(BaseModel):
    api_ids: list[int] = Field(..., min_length=1, max_length=200)
    target_category_id: Optional[int] = None


class ExtractVarRule(BaseModel):
    variable: str = ""
    source: str = "body"
    type: str = "jsonpath"
    expression: str = ""


class ApiTestRequest(BaseModel):
    env_id: int
    overrides: dict = {}
    extract_vars: list[ExtractVarRule] = []


class BatchIdsRequest(BaseModel):
    ids: list[int] = Field(
        ..., min_length=1, max_length=200, description="ID list (max 200)"
    )
