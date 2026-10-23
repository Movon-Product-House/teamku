import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel

from movon_hr.modules.attendance.models import AttendanceAnomaly
from movon_hr.modules.attendance.schemas import AgendaItemOut
from movon_hr.modules.employees.schemas import EmployeeOut
from movon_hr.modules.leave.models import LeaveStatus

type DashboardAttentionKind = Literal["late", "not_checked_in", "open_session", "missed_reverify"]


class DashboardAttendanceOut(BaseModel):
    employee_id: uuid.UUID
    employee: str
    department: str
    checked_in_at: datetime
    checked_out_at: datetime | None
    anomaly: AttendanceAnomaly | None


class DashboardAttentionOut(BaseModel):
    employee_id: uuid.UUID
    employee: str
    title: str
    kind: DashboardAttentionKind
    # The late check-in, the open session's check-in or the missed reverify; null for no check-in.
    at: datetime | None


class DashboardAgendaOut(AgendaItemOut):
    employee_id: uuid.UUID
    employee: str


class DashboardLeaveOut(BaseModel):
    employee_id: uuid.UUID
    employee: str
    title: str
    start_date: date
    end_date: date
    status: LeaveStatus


class DashboardOut(BaseModel):
    current_user: EmployeeOut
    headcount: int
    present: int
    # Not present and not on leave: attention not_checked_in plus open_session, once work starts.
    absent: int
    on_leave: int
    late: int
    attendance_rate: int
    pending_approvals: int
    agenda_total: int
    agenda_completed: int
    work_start_time: str
    attendance: list[DashboardAttendanceOut]
    attention: list[DashboardAttentionOut]
    agenda: list[DashboardAgendaOut]
    # Approved or pending, from today to two weeks ahead.
    team_leave: list[DashboardLeaveOut]
