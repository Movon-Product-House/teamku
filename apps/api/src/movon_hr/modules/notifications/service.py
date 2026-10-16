import uuid
from collections.abc import Sequence

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from movon_hr.modules.notifications.models import Notification


async def notify(
    db: AsyncSession, user_id: uuid.UUID, title: str, detail: str, target: str
) -> None:
    db.add(Notification(user_id=user_id, title=title, detail=detail, target=target))


async def list_for(db: AsyncSession, user_id: uuid.UUID) -> Sequence[Notification]:
    """Newest first; ``created_at`` is the transaction time, so the uuidv7 id breaks ties."""
    found = await db.scalars(
        select(Notification)
        .where(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc(), Notification.id.desc())
    )
    return found.all()


async def mark_all_read(db: AsyncSession, user_id: uuid.UUID) -> None:
    await db.execute(update(Notification).where(Notification.user_id == user_id).values(read=True))
