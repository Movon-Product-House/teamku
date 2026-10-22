from datetime import datetime

from pydantic import BaseModel

from movon_hr.modules.attendance.models import Anomaly
from movon_hr.modules.employees.schemas import EmployeeOut


class DashboardAttendanceOut(BaseModel):
    employee: str
    department: str
    checked_in_at: datetime
    checked_out_at: datetime | None
    anomaly: Anomaly | None


class DashboardOut(BaseModel):
    current_user: EmployeeOut
    headcount: int
    present: int
    absent: int
    on_leave: int
    late: int
    attendance_rate: int
    pending_approvals: int
    agenda_total: int
    agenda_completed: int
    attendance: list[DashboardAttendanceOut]
