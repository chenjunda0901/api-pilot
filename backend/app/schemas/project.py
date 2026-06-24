import re
from pydantic import BaseModel, Field, field_validator


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field(default="")
    is_public: bool = False

    @field_validator("name")
    @classmethod
    def sanitize_name(cls, v: str) -> str:
        v = v.strip()
        if re.search(r"<[^>]+>", v):
            raise ValueError("名称不允许包含 HTML 标签")
        return v


class ProjectUpdate(BaseModel):
    name: str = Field(default="", max_length=200)
    description: str = Field(default="")
    is_public: bool | None = None  # None means no change

    @field_validator("name")
    @classmethod
    def sanitize_name(cls, v: str) -> str:
        if v and re.search(r"<[^>]+>", v):
            raise ValueError("名称不允许包含 HTML 标签")
        return v


class GlobalConfigUpdate(BaseModel):
    global_variables: list = []
    global_params: dict = {}


class GlobalVariableUpsert(BaseModel):
    """添加/更新单个全局变量（仅需读权限）。"""
    key: str = Field(..., min_length=1, max_length=200, description="变量名")
    value: str = Field(default="", description="变量值")
