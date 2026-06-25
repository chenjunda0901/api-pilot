"""数据模型 / JSON Schema 库 Pydantic 模型。"""

from datetime import datetime
from pydantic import BaseModel, Field


class DataSchemaBase(BaseModel):
    """数据模型基类。"""

    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field(default="")
    schema_json: str = Field(..., min_length=2, description="JSON Schema 字符串")


class DataSchemaCreate(DataSchemaBase):
    """创建数据模型请求。"""


class DataSchemaUpdate(BaseModel):
    """更新数据模型请求。"""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    schema_json: str | None = Field(default=None, min_length=2)


class DataSchemaOut(DataSchemaBase):
    """数据模型输出。"""

    id: int
    project_id: int
    example_json: str | None = None
    created_by: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class DataSchemaPreviewRequest(BaseModel):
    """用数据模型生成示例数据请求。"""

    count: int = Field(default=1, ge=1, le=100, description="生成示例数量")
