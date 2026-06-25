from pydantic import BaseModel, Field


class DatasetCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    project_id: int


class DatasetUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=200)
    description: str | None = None


class BatchRowsRequest(BaseModel):
    rows: list[dict]
