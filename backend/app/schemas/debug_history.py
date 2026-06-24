from datetime import datetime
from pydantic import BaseModel


class DebugHistoryOut(BaseModel):
    id: int
    api_id: int
    url: str
    method: str
    request_headers: str = "[]"
    request_body: str = ""
    response_status: int | None = None
    response_headers: str = "[]"
    response_body: str = ""
    duration_ms: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}
