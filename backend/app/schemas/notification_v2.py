"""通知 v2 Pydantic 模型。"""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel


class NotificationOut(BaseModel):
    """通知输出。"""

    id: int
    type: str
    title: str
    content: Optional[str] = None
    is_read: bool = False
    link: Optional[str] = None
    created_at: Optional[datetime] = None


class NotificationListOut(BaseModel):
    """通知列表输出。"""

    items: list[NotificationOut]
    total: int
    unread: int
    page: int
    page_size: int
