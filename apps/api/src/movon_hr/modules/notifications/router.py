import uuid

from fastapi import APIRouter

from movon_hr.core.auth import CurrentUser
from movon_hr.core.db import DB
from movon_hr.modules.notifications import service
from movon_hr.modules.notifications.schemas import NotificationListOut, NotificationOut, OkOut

router = APIRouter(tags=["notifications"])


@router.get("/notifications")
async def notifications(db: DB, user: CurrentUser) -> NotificationListOut:
    items = [NotificationOut.model_validate(item) for item in await service.list_for(db, user.id)]
    return NotificationListOut(items=items, unread=sum(not item.read for item in items))


@router.post("/notifications/read-all")
async def read_notifications(db: DB, user: CurrentUser) -> OkOut:
    await service.mark_all_read(db, user.id)
    return OkOut(ok=True)


@router.post("/notifications/{notification_id}/read")
async def read_notification(db: DB, user: CurrentUser, notification_id: uuid.UUID) -> OkOut:
    await service.mark_read(db, user.id, notification_id)
    return OkOut(ok=True)
