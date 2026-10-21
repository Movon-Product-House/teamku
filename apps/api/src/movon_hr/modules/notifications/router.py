import uuid

from fastapi import APIRouter

from movon_hr.core.auth import CurrentUser
from movon_hr.core.db import DB
from movon_hr.modules.notifications import service
from movon_hr.modules.notifications.schemas import NotificationList, NotificationOut, Ok

router = APIRouter()


@router.get("/notifications")
async def notifications(db: DB, user: CurrentUser) -> NotificationList:
    items = [NotificationOut.model_validate(item) for item in await service.list_for(db, user.id)]
    return NotificationList(items=items, unread=sum(not item.read for item in items))


@router.post("/notifications/read-all")
async def read_notifications(db: DB, user: CurrentUser) -> Ok:
    await service.mark_all_read(db, user.id)
    return Ok(ok=True)


@router.post("/notifications/{notification_id}/read")
async def read_notification(db: DB, user: CurrentUser, notification_id: uuid.UUID) -> Ok:
    await service.mark_read(db, user.id, notification_id)
    return Ok(ok=True)
