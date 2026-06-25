"""评论 Pydantic 模型。"""

from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class CommentBase(BaseModel):
    """评论基类。"""

    resource_type: str = Field(..., description="资源类型: api / case / scene / report")
    resource_id: int = Field(..., ge=1)
    content_md: str = Field(..., min_length=1, max_length=10000)
    parent_id: int | None = Field(default=None, ge=1, description="父评论 ID（回复场景）")

    @field_validator("resource_type")
    @classmethod
    def validate_resource(cls, v: str) -> str:
        allowed = {"api", "case", "scene", "report"}
        if v not in allowed:
            raise ValueError(f"resource_type 必须是 {', '.join(sorted(allowed))} 之一")
        return v


class CommentCreate(BaseModel):
    """创建评论请求。"""

    project_id: int = Field(..., ge=1)
    resource_type: str
    resource_id: int = Field(..., ge=1)
    content_md: str = Field(..., min_length=1, max_length=10000)
    parent_id: int | None = Field(default=None, ge=1)
    mentions: list[int] = Field(default_factory=list, description="@ 提及的用户 ID 列表")

    @field_validator("resource_type")
    @classmethod
    def validate_resource(cls, v: str) -> str:
        allowed = {"api", "case", "scene", "report"}
        if v not in allowed:
            raise ValueError(f"resource_type 必须是 {', '.join(sorted(allowed))} 之一")
        return v


class CommentUpdate(BaseModel):
    """更新评论请求。"""

    content_md: str = Field(..., min_length=1, max_length=10000)


class CommentOut(BaseModel):
    """评论输出。"""

    id: int
    project_id: int
    resource_type: str
    resource_id: int
    user_id: int
    content_md: str
    mentions: list[int] = Field(default_factory=list)
    status: str = Field(default="open", description="状态: open / resolved")
    parent_id: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class MentionSearchResponse(BaseModel):
    """@ 自动完成搜索响应。"""

    items: list[dict[str, int | str]]
