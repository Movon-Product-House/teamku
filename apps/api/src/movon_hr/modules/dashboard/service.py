"""Read-only aggregation over the people the caller can see (active only)."""

from datetime import datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from movon_hr.core.identity import Employee
from movon_hr.core.time import JAKARTA, jakarta_date
from movon_hr.modules.attendance.models import Attendance
from movon_hr.modules.dashboard.schemas import DashboardAttendance, DashboardOut
from movon_hr.modules.employees import service as employees_service
from movon_hr.modules.leave.models import LeaveRequest

LATE_AFTER = time(9, 0)  # hardcoded, kept as is (#19)


async def dashboard(db: AsyncSession, user: Employee) -> DashboardOut:
    employees = {
        item.id: item
        for item in await db.scalars(
            employees_service.visible_query(user).where(Employee.status == "active")
        )
    }
    ids = list(employees)
    today = jakarta_date()
    start = datetime.combine(today, time(0), JAKARTA)
    sessions = list(
        await db.scalars(
            select(Attendance)
            .where(
                Attendance.employee_id.in_(ids),
                Attendance.checked_in_at >= start,
                Attendance.checked_in_at < start + timedelta(days=1),
            )
            .order_by(Attendance.checked_in_at.desc())
        )
    )
    requests = (
        await db.execute(
            select(LeaveRequest.employee_id, LeaveRequest.status).where(
                LeaveRequest.employee_id.in_(ids),
                (LeaveRequest.status == "pending")
                | (
                    (LeaveRequest.status == "approved")
                    & (LeaveRequest.start_date <= today)
                    & (LeaveRequest.end_date >= today)
                ),
            )
        )
    ).all()
    pending = sum(status == "pending" for _, status in requests)
    present = {item.employee_id for item in sessions}
    on_leave = {employee_id for employee_id, status in requests if status == "approved"}
    absent = set(ids) - present - on_leave
    late = {
        item.employee_id
        for item in sessions
        if item.checked_in_at.astimezone(JAKARTA).time() >= LATE_AFTER
    }
    agenda = [entry for item in sessions for entry in item.agenda]
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
        agenda_completed=sum(1 for entry in agenda if entry.get("status") == "done"),
        attendance=[
            DashboardAttendance(
                employee=employees[item.employee_id].name,
                department=employees[item.employee_id].department,
                checked_in_at=item.checked_in_at,
                checked_out_at=item.checked_out_at,
                anomaly=item.anomaly,
            )
            for item in sessions
        ],
    )
