"""Read-only aggregation over the people the caller can see (active only)."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from movon_hr.core.identity import Employee
from movon_hr.core.time import jakarta_date, jakarta_day_bounds, parse_hhmm
from movon_hr.modules.attendance.models import Attendance, LocationEvent
from movon_hr.modules.attendance.service import is_late
from movon_hr.modules.dashboard import rules
from movon_hr.modules.dashboard.schemas import (
    DashboardAgendaOut,
    DashboardAttendanceOut,
    DashboardAttentionOut,
    DashboardLeaveOut,
    DashboardOut,
)
from movon_hr.modules.employees import service as employees_service
from movon_hr.modules.leave.models import LeaveRequest
from movon_hr.modules.settings import service as settings_service

TEAM_LEAVE_DAYS = 14


async def dashboard(db: AsyncSession, user: Employee) -> DashboardOut:
    employees = {
        item.id: item
        for item in await db.scalars(
            employees_service.visible_query(user).where(Employee.status == "active")
        )
    }
    if user.role == "manager":
        # A manager's team is the rest of the department, not themselves.
        employees.pop(user.id, None)
    ids = list(employees)
    now = datetime.now(UTC)
    today = jakarta_date(now)
    start, end = jakarta_day_bounds(today)
    office = await settings_service.primary_location(db)
    work_start = parse_hhmm(office.work_start_time)
    sessions = list(
        await db.scalars(
            select(Attendance)
            .where(
                Attendance.employee_id.in_(ids),
                Attendance.checked_in_at >= start,
                Attendance.checked_in_at < end,
            )
            .order_by(Attendance.checked_in_at.desc())
        )
    )
    open_from_earlier_day = dict(
        (
            await db.execute(
                select(Attendance.employee_id, Attendance.checked_in_at).where(
                    Attendance.employee_id.in_(ids),
                    Attendance.checked_out_at.is_(None),
                    Attendance.checked_in_at < start,
                )
            )
        )
        .tuples()
        .all()
    )
    missed_reverify = {
        employee_id: at
        for employee_id, at in (
            await db.execute(
                select(LocationEvent.employee_id, func.min(LocationEvent.at))
                .where(
                    LocationEvent.employee_id.in_(ids),
                    LocationEvent.at >= start,
                    LocationEvent.at < end,
                    LocationEvent.anomaly == "missed_reverify",
                )
                .group_by(LocationEvent.employee_id)
            )
        ).tuples()
    }
    leave_until = today + timedelta(days=TEAM_LEAVE_DAYS - 1)
    requests = list(
        await db.scalars(
            select(LeaveRequest)
            .where(
                LeaveRequest.employee_id.in_(ids),
                (LeaveRequest.status == "pending")
                | (
                    (LeaveRequest.status == "approved")
                    & (LeaveRequest.end_date >= today)
                    & (LeaveRequest.start_date <= leave_until)
                ),
            )
            .order_by(LeaveRequest.start_date, LeaveRequest.id)
        )
    )
    pending = sum(item.status == "pending" for item in requests)
    present = {item.employee_id for item in sessions}
    on_leave = {
        item.employee_id
        for item in requests
        if item.status == "approved" and item.start_date <= today
    }
    absent = set(ids) - present - on_leave
    # Newest first, so the earliest check-in of each person is written last.
    first_check_in = {item.employee_id: item.checked_in_at for item in sessions}
    late = {key for key, at in first_check_in.items() if is_late(at, work_start)}
    agenda = [(item, entry) for item in sessions for entry in item.agenda]
    return DashboardOut(
        current_user=(await employees_service.to_out(db, [user]))[0],
        headcount=len(ids),
        present=len(present),
        absent=len(absent),
        on_leave=len(on_leave),
        late=len(late),
        attendance_rate=round(len(present) / len(ids) * 100) if ids else 0,
        pending_approvals=pending if user.role in {"manager", "hr_admin"} else 0,
        agenda_total=len(agenda),
        agenda_completed=sum(1 for _, entry in agenda if entry.get("status") == "done"),
        work_start_time=office.work_start_time,
        attendance=[
            DashboardAttendanceOut(
                employee_id=item.employee_id,
                employee=employees[item.employee_id].name,
                department=employees[item.employee_id].department,
                checked_in_at=item.checked_in_at,
                checked_out_at=item.checked_out_at,
                anomaly=item.anomaly,
            )
            for item in sessions
        ],
        attention=[
            DashboardAttentionOut(
                employee_id=member.id,
                employee=member.name,
                title=member.title,
                kind=kind,
                at=at,
            )
            for member in sorted(employees.values(), key=lambda item: item.name)
            for kind, at in rules.attention(
                first_check_in=first_check_in.get(member.id),
                late=member.id in late,
                open_since=open_from_earlier_day.get(member.id),
                on_leave=member.id in on_leave,
                missed_reverify_at=missed_reverify.get(member.id),
                now=now,
                work_start=work_start,
            )
        ],
        agenda=[
            DashboardAgendaOut.model_validate(
                entry
                | {"employee_id": item.employee_id, "employee": employees[item.employee_id].name}
            )
            for item, entry in agenda
        ],
        team_leave=[
            DashboardLeaveOut(
                employee_id=item.employee_id,
                employee=employees[item.employee_id].name,
                title=employees[item.employee_id].title,
                start_date=item.start_date,
                end_date=item.end_date,
                status=item.status,
            )
            for item in requests
            if item.end_date >= today and item.start_date <= leave_until
        ],
    )
