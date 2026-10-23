"""Attendance alerts for one tenant, run by the scheduled job (``movon_hr.jobs``).

Same rules as the old ``evaluate_attendance_alerts()``; idempotent per
(employee, kind, Jakarta day) through the alert_receipts primary key.
"""

import uuid
from datetime import date, datetime
from typing import NamedTuple

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from movon_hr.core.identity import Employee
from movon_hr.core.settings import settings
from movon_hr.core.time import JAKARTA, jakarta_day_bounds, parse_hhmm
from movon_hr.modules.attendance import rules
from movon_hr.modules.attendance.models import AlertReceipt, Attendance, LocationEvent
from movon_hr.modules.attendance.service import open_slot
from movon_hr.modules.leave.service import has_approved_leave
from movon_hr.modules.notifications.service import notify
from movon_hr.modules.settings.models import WorkLocation
from movon_hr.modules.settings.service import primary_location

TARGET = "/app/attendance/today"
ALERT_COPY = {
    "missed_clock_in": ("Belum clock-in", "Anda belum check-in hari ini."),
    "missed_clock_out": (
        "Sesi masih terbuka",
        "Sesi kehadiran Anda masih terbuka. Lakukan check-out.",
    ),
    "limit_reverify": (
        "Re-verifikasi terlewat",
        "Ada permintaan re-verifikasi lokasi yang belum diselesaikan.",
    ),
    "limit_geofence": (
        "Lokasi di luar area kantor",
        "Re-verifikasi lokasi tercatat di luar radius kantor.",
    ),
}
EMAILED = {"missed_clock_in", "missed_clock_out"}
# Location anomaly recorded today -> alert kind (office workers only).
LIMITS = {"missed_reverify": "limit_reverify", "outside_geofence": "limit_geofence"}


class AlertEmail(NamedTuple):
    to: str
    subject: str
    body: str


async def expire_missed_slots(db: AsyncSession, now: datetime) -> None:
    """Mark reverify slots past their grace period as missed."""
    await db.execute(
        update(LocationEvent)
        .where(open_slot(), LocationEvent.due_at <= now - rules.REVERIFY_GRACE)
        .values(anomaly="missed_reverify", at=now)
    )


async def emit(
    db: AsyncSession,
    kind: str,
    employee: Employee,
    employees: list[Employee],
    policy: WorkLocation,
    day: date,
) -> list[AlertEmail]:
    """Notify once per (employee, kind, day); returns the emails to send after commit."""
    inserted = await db.scalar(
        insert(AlertReceipt)
        .values(tenant_id=employee.tenant_id, employee_id=employee.id, kind=kind, local_date=day)
        .on_conflict_do_nothing()
        .returning(AlertReceipt.kind)
    )
    if inserted is None:
        return []
    title, detail = ALERT_COPY[kind]
    await notify(db, employee.id, title, detail, TARGET)
    if policy.alert_managers:
        for recipient in employees:
            if recipient.id == employee.id:
                continue
            same_manager = (
                recipient.role == "manager" and recipient.department == employee.department
            )
            if recipient.role == "hr_admin" or same_manager:
                await notify(db, recipient.id, title, f"{employee.name}: {detail}", TARGET)
    if kind not in EMAILED:
        return []
    link = f"{settings.app_base_url.rstrip('/')}{TARGET}"
    body = f"Halo {employee.name},\n\n{detail}\nBuka presensi: {link}\n"
    return [AlertEmail(employee.email, f"{title} — Teamku", body)]


async def sessions_by_employee(
    db: AsyncSession, start: datetime, end: datetime
) -> dict[uuid.UUID, list[Attendance]]:
    sessions: dict[uuid.UUID, list[Attendance]] = {}
    for record in await db.scalars(
        select(Attendance)
        .where(Attendance.checked_in_at >= start, Attendance.checked_in_at < end)
        .order_by(Attendance.checked_in_at)
    ):
        sessions.setdefault(record.employee_id, []).append(record)
    return sessions


async def evaluate_tenant(db: AsyncSession, now: datetime) -> list[AlertEmail]:
    """Expire missed reverify slots and raise due alerts for the tenant bound to ``db``.

    Safe to run any number of times. The caller commits, then sends the returned emails.
    """
    await expire_missed_slots(db, now)
    policy = await primary_location(db)
    if not policy.alerts_enabled:
        return []
    local_now = now.astimezone(JAKARTA)
    today = local_now.date()
    reminder_in = datetime.combine(today, parse_hhmm(policy.clock_in_reminder_time), JAKARTA)
    start, end = jakarta_day_bounds(today)

    employees = list(
        await db.scalars(select(Employee).where(Employee.status == "active").order_by(Employee.id))
    )
    sessions = await sessions_by_employee(db, start, end)
    # Check-in allows one open session per employee; it may predate today (a night shift).
    open_sessions = {
        record.employee_id: record
        for record in await db.scalars(
            select(Attendance).where(Attendance.checked_out_at.is_(None))
        )
    }
    anomalies = set(
        (
            await db.execute(
                select(LocationEvent.employee_id, LocationEvent.anomaly).where(
                    LocationEvent.at >= start,
                    LocationEvent.at < end,
                    LocationEvent.anomaly.in_(LIMITS),
                )
            )
        ).tuples()
    )

    emails: list[AlertEmail] = []
    for employee in employees:
        todays = sessions.get(employee.id, [])
        open_record = open_sessions.get(employee.id)
        due: list[tuple[str, date]] = []
        if (
            local_now >= reminder_in
            and not todays
            and open_record is None
            and not await has_approved_leave(db, employee.id, today)
        ):
            due.append(("missed_clock_in", today))
        if open_record is not None:
            clock_out_day = rules.clock_out_alert_day(
                open_record.checked_in_at,
                now,
                parse_hhmm(policy.clock_out_reminder_time),
                policy.max_open_hours,
            )
            if clock_out_day is not None:
                due.append(("missed_clock_out", clock_out_day))
        if not employee.is_remote:
            due += [
                (kind, today)
                for anomaly, kind in LIMITS.items()
                if (employee.id, anomaly) in anomalies
            ]
        for kind, day in due:
            emails += await emit(db, kind, employee, employees, policy, day)
    return emails
