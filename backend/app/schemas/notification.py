from datetime import datetime
from pydantic import BaseModel


class NotificationOut(BaseModel):
    id: int
    type: str
    title: str
    body: str | None
    link: str | None
    read: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationListOut(BaseModel):
    items: list[NotificationOut]
    unread_count: int
