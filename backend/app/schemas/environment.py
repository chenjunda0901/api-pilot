from pydantic import BaseModel, Field
from typing import Any, Optional


class AuthConfig(BaseModel):
    """认证配置。"""
    type: str = Field(..., description="认证类型: bearer / basic / apikey")
    token: Optional[str] = Field(default=None, description="Bearer Token")
    username: Optional[str] = Field(default=None, description="Basic Auth 用户名")
    password: Optional[str] = Field(default=None, description="Basic Auth 密码")
    key: Optional[str] = Field(default=None, description="API Key 名称")
    value: Optional[str] = Field(default=None, description="API Key 值")
    in_: Optional[str] = Field(
        default=None, alias="in",
        description="API Key 位置: header / query",
    )


class EnvironmentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    base_url: Optional[str] = Field(default=None, max_length=500)
    auth_config: Optional[dict[str, Any]] = None
    services: list[dict[str, Any]] = []
    variables: list[dict[str, Any]] = []
    headers: list[dict[str, Any]] = []


class EnvironmentUpdate(BaseModel):
    name: str = Field(default="", max_length=100)
    base_url: Optional[str] = Field(default=None, max_length=500)
    auth_config: Optional[dict[str, Any]] = None
    services: list[dict[str, Any]] = []
    variables: list[dict[str, Any]] = []
    headers: list[dict[str, Any]] = []


class VariableUpsert(BaseModel):
    """添加或更新单个环境变量（提取变量专用）。"""
    key: str = Field(..., min_length=1, max_length=200, description="变量名")
    value: str = Field(default="", description="变量值")
