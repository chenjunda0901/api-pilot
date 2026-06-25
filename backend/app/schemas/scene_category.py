from pydantic import BaseModel, Field


class CategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    parent_id: int | None = None


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=100)
