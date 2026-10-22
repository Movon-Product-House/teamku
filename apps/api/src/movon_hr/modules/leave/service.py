import logging
import uuid
from datetime import date, timedelta
from urllib.parse import quote

from fastapi import BackgroundTasks, HTTPException
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from movon_hr.core.identity import Employee
from movon_hr.core.mailer import send_email
from movon_hr.core.time import working_days
from movon_hr.modules.audit.service import audit
from movon_hr.modules.employees.service import parse_id
from movon_hr.modules.leave.models import LeaveRequest
from movon_hr.modules.leave.schemas import (
    ApprovalIn,
    ApprovalListOut,
    ApprovalOut,
    LeaveBalanceOut,
    LeaveIn,
    LeaveOut,
)
from movon_hr.modules.notifications.service import notify
from movon_hr.modules.settings import google_calendar
from movon_hr.modules.settings import service as settings_service

logger = logging.getLogger("movon_hr.calendar")

ANNUAL_DAYS = 12  # hardcoded allowance, kept as is (see the plan's scope boundaries)
NOT_FOUND = "Permohonan tidak ditemukan"
EVENTS_URL = "https://www.googleapis.com/calendar/v3/calendars/{calendar}/events"


# --- Read helpers, also used by attendance and dashboard ---


async def has_approved_leave(db: AsyncSession, employee_id: uuid.UUID, day: date) -> bool:
    found = await db.scalar(
        select(LeaveRequest.id).where(
            LeaveRequest.employee_id == employee_id,
            LeaveRequest.status == "approved",
            LeaveRequest.start_date <= day,
            LeaveRequest.end_date >= day,
        )
    )
    return found is not None


async def leave_balance(db: AsyncSession, employee_id: uuid.UUID) -> LeaveBalanceOut:
    approved = await db.execute(
        select(LeaveRequest.start_date, LeaveRequest.end_date).where(
            LeaveRequest.employee_id == employee_id, LeaveRequest.status == "approved"
        )
    )
    used = sum(working_days(start, end) for start, end in approved)
    return LeaveBalanceOut(
        annual_days=ANNUAL_DAYS, used_days=used, remaining_days=max(ANNUAL_DAYS - used, 0)
    )


async def own_requests(db: AsyncSession, user: Employee) -> list[LeaveRequest]:
    """Newest first; ``created_at`` is the transaction time, so the uuidv7 id breaks ties."""
    found = await db.scalars(
        select(LeaveRequest)
        .where(LeaveRequest.employee_id == user.id)
        .order_by(LeaveRequest.created_at.desc(), LeaveRequest.id.desc())
    )
    return list(found)


async def approvals(db: AsyncSession, user: Employee) -> ApprovalListOut:
    """HR sees every request, a manager those of their department."""
    query = (
        select(LeaveRequest, Employee)
        .join(Employee, Employee.id == LeaveRequest.employee_id)
        .order_by(LeaveRequest.created_at.desc(), LeaveRequest.id.desc())
    )
    if user.role == "manager":
        query = query.where(Employee.department == user.department)
    items = [
        ApprovalOut(
            **LeaveOut.model_validate(request).model_dump(),
            employee_name=employee.name,
            department=employee.department,
        )
        for request, employee in (await db.execute(query)).tuples()
    ]
    return ApprovalListOut(items=items, pending=sum(item.status == "pending" for item in items))


# --- Emails (sent after the commit through BackgroundTasks) ---


async def leave_recipients(db: AsyncSession, employee: Employee) -> list[Employee]:
    """Managers of the employee's department, then every active HR admin."""
    found = await db.scalars(
        select(Employee)
        .where(
            or_(
                (Employee.role == "manager") & (Employee.department == employee.department),
                (Employee.role == "hr_admin") & (Employee.status == "active"),
            )
        )
        .order_by(Employee.role != "manager", Employee.id)
    )
    return list(found)


def email_leave(
    background_tasks: BackgroundTasks, recipients: list[Employee], subject: str, body: str
) -> None:
    for recipient in recipients:
        if recipient.email:
            background_tasks.add_task(send_email, recipient.email, subject, body, kind="leave")


# --- Google Calendar (inline: the web reads calendar_sync_status from the response) ---


async def sync_calendar(db: AsyncSession, request: LeaveRequest, employee: Employee) -> None:
    calendar = await settings_service.get_calendar(db)
    if calendar.provider != "google" or not calendar.connected or not calendar.team_calendar_id:
        request.calendar_sync_status = "skipped"
        return
    url = EVENTS_URL.format(calendar=quote(calendar.team_calendar_id, safe=""))
    try:
        event = await google_calendar.calendar_request(
            calendar,
            "POST",
            f"{url}?sendUpdates=all",
            {
                "summary": f"Cuti · {employee.name}",
                "description": f"Permohonan cuti Teamku {request.id}.",
                "start": {"date": request.start_date.isoformat()},
                "end": {"date": (request.end_date + timedelta(days=1)).isoformat()},
                "attendees": [{"email": employee.email}],
                "transparency": "opaque",
            },
        )
    except Exception:
        logger.exception("Google Calendar event creation failed request_id=%s", request.id)
        request.calendar_sync_status = "failed"
        return
    request.team_calendar_event_id = event.get("id")
    request.employee_calendar_event_id = None
    request.calendar_sync_status = "ok" if request.team_calendar_event_id else "failed"


async def remove_calendar(db: AsyncSession, request: LeaveRequest) -> None:
    calendar = await settings_service.get_calendar(db)
    request.calendar_sync_status = "removed"
    if not (
        request.team_calendar_event_id and calendar.provider == "google" and calendar.connected
    ):
        return
    url = EVENTS_URL.format(calendar=quote(calendar.team_calendar_id, safe=""))
    try:
        await google_calendar.calendar_request(
            calendar, "DELETE", f"{url}/{quote(request.team_calendar_event_id, safe='')}"
        )
    except Exception:
        logger.exception("Google Calendar event deletion failed request_id=%s", request.id)
        request.calendar_sync_status = "failed"


# --- Commands ---


async def submit(
    db: AsyncSession, user: Employee, payload: LeaveIn, background_tasks: BackgroundTasks
) -> LeaveRequest:
    if payload.end < payload.start:
        raise HTTPException(422, "Tanggal selesai harus setelah tanggal mulai")
    days = working_days(payload.start, payload.end)
    if days == 0:
        raise HTTPException(422, "Rentang cuti tidak memiliki hari kerja")
    overlap = await db.scalar(
        select(LeaveRequest.id).where(
            LeaveRequest.employee_id == user.id,
            LeaveRequest.status.in_(("pending", "approved")),
            LeaveRequest.start_date <= payload.end,
            LeaveRequest.end_date >= payload.start,
        )
    )
    if overlap is not None:
        raise HTTPException(409, "Permohonan tumpang tindih")
    request = LeaveRequest(
        employee_id=user.id, start_date=payload.start, end_date=payload.end, reason=payload.reason
    )
    db.add(request)
    await db.flush()
    await audit(db, "leave.submitted", user, str(request.id))
    recipients = await leave_recipients(db, user)
    # Managers of the department, any status (as before; HR only gets the email).
    for manager in recipients:
        if manager.role == "manager":
            await notify(
                db,
                manager.id,
                "Permohonan cuti baru",
                f"{user.name} menunggu persetujuan Anda.",
                "/app/approvals",
            )
    email_leave(
        background_tasks,
        recipients,
        "Permohonan cuti baru — Teamku",
        f"{user.name} mengajukan cuti {payload.start} sampai {payload.end} ({days} hari kerja)."
        "\n\nBuka Teamku: /app/approvals",
    )
    return request


async def cancel(
    db: AsyncSession, user: Employee, request_id: str, background_tasks: BackgroundTasks
) -> LeaveRequest:
    parsed = parse_id(request_id)
    request = (
        await db.scalar(
            select(LeaveRequest).where(
                LeaveRequest.id == parsed, LeaveRequest.employee_id == user.id
            )
        )
        if parsed
        else None
    )
    if request is None:
        raise HTTPException(404, NOT_FOUND)
    if request.status not in {"pending", "approved"}:
        raise HTTPException(409, "Permohonan ini tidak dapat dibatalkan")
    request.status = "cancelled"
    if request.calendar_sync_status in {"ok", "failed"}:
        await remove_calendar(db, request)
    await audit(db, "leave.cancelled", user, str(request.id))
    recipients = await leave_recipients(db, user)
    if user.id not in {person.id for person in recipients}:
        recipients.append(user)
    email_leave(
        background_tasks,
        recipients,
        "Permohonan cuti dibatalkan — Teamku",
        f"{user.name} membatalkan permohonan cuti {request.start_date} sampai "
        f"{request.end_date}.\n\nBuka Teamku: /app/time/time-off",
    )
    return request


async def decide(
    db: AsyncSession,
    user: Employee,
    request_id: str,
    payload: ApprovalIn,
    background_tasks: BackgroundTasks,
) -> LeaveRequest:
    parsed = parse_id(request_id)
    found = (
        await db.execute(
            select(LeaveRequest, Employee)
            .join(Employee, Employee.id == LeaveRequest.employee_id)
            .where(LeaveRequest.id == parsed)
        )
        if parsed
        else None
    )
    row = found.tuples().first() if found else None
    if row is None:
        raise HTTPException(404, NOT_FOUND)
    request, employee = row
    if user.role == "manager" and employee.department != user.department:
        raise HTTPException(403, "Permohonan berada di luar cakupan tim Anda")
    if request.employee_id == user.id:
        raise HTTPException(403, "Persetujuan diri sendiri tidak diperbolehkan")
    if request.status != "pending":
        raise HTTPException(409, "Permohonan sudah diproses")
    request.status = payload.decision
    request.approver_comment = payload.comment
    await audit(db, "request." + payload.decision, user, str(request.id))
    await notify(
        db,
        request.employee_id,
        "Status permohonan diperbarui",
        f"Permohonan Anda {payload.decision}.",
        "/app/time/time-off",
    )
    email_leave(
        background_tasks,
        [employee],
        f"Permohonan cuti {payload.decision} — Teamku",
        f"Permohonan cuti Anda ({request.start_date} sampai {request.end_date}) telah "
        f"{payload.decision}.\nCatatan: {payload.comment}\n\nBuka Teamku: /app/time/time-off",
    )
    if payload.decision == "approved":
        await sync_calendar(db, request, employee)
    return request
