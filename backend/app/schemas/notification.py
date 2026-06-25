from pydantic import BaseModel, Field


class NotificationCreate(BaseModel):
    user_id: int
    type: str = Field(..., description="task_complete/report_ready/mock_error/system")
    title: str = Field(..., max_length=200)
    content: str | None = None
    link: str | None = None
