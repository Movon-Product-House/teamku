"""DB setup and read-back helpers; ``db`` is the conftest session (demo tenant bound)."""

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from movon_hr.core.identity import Employee
from movon_hr.modules.attendance.models import Attendance, LocationEvent
from movon_hr.modules.leave.models import LeaveRequest
from movon_hr.modules.notifications.models import Notification
from movon_hr.modules.settings.models import WorkLocation
from movon_hr.seed import OFFICE_LATITUDE, OFFICE_LONGITUDE

FRESH = {"populate_existing": True}  # read what requests wrote, not the identity map


async def employee(db: AsyncSession, email: str) -> Employee:
    found = await db.execute(
        select(Employee).where(Employee.email == email).execution_options(**FRESH)
    )
    return found.scalar_one()


async def set_employee(db: AsyncSession, email: str, **values: Any) -> None:
    await db.execute(update(Employee).where(Employee.email == email).values(**values))
    await db.commit()


async def office(db: AsyncSession) -> WorkLocation:
    """The primary work location, which carries the office policy."""
    found = await db.execute(
        select(WorkLocation).where(WorkLocation.is_primary).execution_options(**FRESH)
    )
    return found.scalar_one()


async def set_office_policy(db: AsyncSession, **values: Any) -> None:
    await db.execute(update(WorkLocation).where(WorkLocation.is_primary).values(**values))
    await db.commit()


async def add_attendance(
    db: AsyncSession,
    email: str,
    *,
    checked_in_at: datetime,
    agenda: list[dict],
    accuracy_meters: float = 10,
    checked_out_at: datetime | None = None,
) -> Attendance:
    record = Attendance(
        employee_id=(await employee(db, email)).id,
        checked_in_at=checked_in_at,
        latitude=OFFICE_LATITUDE,
        longitude=OFFICE_LONGITUDE,
        accuracy_meters=accuracy_meters,
        agenda=agenda,
        checked_out_at=checked_out_at,
    )
    db.add(record)
    await db.commit()
    return record


async def add_location_event(
    db: AsyncSession, email: str, attendance_id: uuid.UUID, **values: Any
) -> LocationEvent:
    event = LocationEvent(
        employee_id=(await employee(db, email)).id, attendance_id=attendance_id, **values
    )
    db.add(event)
    await db.commit()
    return event


async def location_events(db: AsyncSession, email: str) -> list[LocationEvent]:
    found = await db.scalars(
        select(LocationEvent)
        .join(Employee, Employee.id == LocationEvent.employee_id)
        .where(Employee.email == email)
        .order_by(LocationEvent.at, LocationEvent.id)
        .execution_options(**FRESH)
    )
    return list(found)


async def add_leave(
    db: AsyncSession, email: str, start: date, end: date, reason: str, *, status: str
) -> LeaveRequest:
    request = LeaveRequest(
        employee_id=(await employee(db, email)).id,
        start_date=start,
        end_date=end,
        reason=reason,
        status=status,
    )
    db.add(request)
    await db.commit()
    return request


async def notifications_for(db: AsyncSession, email: str) -> list[Notification]:
    found = await db.scalars(
        select(Notification)
        .join(Employee, Employee.id == Notification.user_id)
        .where(Employee.email == email)
        .order_by(Notification.created_at, Notification.id)
        .execution_options(**FRESH)
    )
    return list(found)


async def count(db: AsyncSession, model: type) -> int:
    return await db.scalar(select(func.count()).select_from(model)) or 0
