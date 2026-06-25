"""订阅 Pydantic 模型。"""

from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class SubscriptionCreate(BaseModel):
    """创建订阅请求。"""

    resource_type: str = Field(..., description="资源类型: api / case / scene / report / plan")
    resource_id: int = Field(..., ge=1)

    @field_validator("resource_type")
    @classmethod
    def validate_resource(cls, v: str) -> str:
        allowed = {"api", "case", "scene", "report", "plan"}
        if v not in allowed:
            raise ValueError(f"resource_type 必须是 {', '.join(sorted(allowed))} 之一")
        return v


class SubscriptionOut(BaseModel):
    """订阅输出。"""

    id: int
    user_id: int
    resource_type: str
    resource_id: int
    created_at: datetime | None = None
