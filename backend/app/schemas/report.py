from pydantic import BaseModel, Field


class ReportQuery(BaseModel):
    scene_id: int | None = None
    status: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
