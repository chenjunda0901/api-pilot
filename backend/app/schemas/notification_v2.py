"""通知 v2 Pydantic 模型。"""

from datetime import datetime
from pydantic import BaseModel


class NotificationOut(BaseModel):
    """通知输出。"""

    id: int
    type: str
    title: str
    content: str | None = None
    is_read: bool = False
    link: str | None = None
    created_at: datetime | None = None


class NotificationListOut(BaseModel):
    """通知列表输出。"""

    items: list[NotificationOut]
    total: int
    unread: int
    page: int
    page_size: int
