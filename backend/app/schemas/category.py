import re
from pydantic import BaseModel, Field, field_validator

_NAME_PATTERN = re.compile(r'^[\u4e00-\u9fff\w\- ]+$')


class CategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    parent_id: int = Field(default=0)
    sort_order: int = Field(default=0)

    @field_validator("name")
    @classmethod
    def sanitize_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("名称不能为纯空格")
        if re.search(r"<[^>]+>", v):
            raise ValueError("名称不允许包含 HTML 标签")
        if not _NAME_PATTERN.match(v):
            raise ValueError("名称仅允许中文、英文、数字、下划线、短横线和空格")
        return v


class CategoryUpdate(BaseModel):
    name: str = Field(default="", max_length=100)
    parent_id: int | None = None
    sort_order: int = Field(default=0)

    @field_validator("name")
    @classmethod
    def sanitize_name(cls, v: str) -> str:
        if not v:
            return v
        stripped = v.strip()
        if not stripped:
            raise ValueError("名称不能为纯空格")
        if re.search(r"<[^>]+>", v):
            raise ValueError("名称不允许包含 HTML 标签")
        if not _NAME_PATTERN.match(stripped):
            raise ValueError("名称仅允许中文、英文、数字、下划线、短横线和空格")
        return v
