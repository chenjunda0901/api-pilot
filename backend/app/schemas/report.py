from typing import Optional
from pydantic import BaseModel, Field


class ReportQuery(BaseModel):
    scene_id: Optional[int] = None
    status: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
