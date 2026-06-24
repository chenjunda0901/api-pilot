from typing import Optional
from pydantic import BaseModel, Field


class NotificationCreate(BaseModel):
    user_id: int
    type: str = Field(..., description="task_complete/report_ready/mock_error/system")
    title: str = Field(..., max_length=200)
    content: Optional[str] = None
    link: Optional[str] = None
