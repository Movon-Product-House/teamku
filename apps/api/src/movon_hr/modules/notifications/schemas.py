import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    detail: str
    target: str
    created_at: datetime
    read: bool


class NotificationListOut(BaseModel):
    items: list[NotificationOut]
    unread: int


class OkOut(BaseModel):
    ok: bool
