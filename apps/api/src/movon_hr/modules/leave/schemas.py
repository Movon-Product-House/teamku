import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field

from movon_hr.core.time import working_days
from movon_hr.modules.leave.models import CalendarSyncStatus, Decision, LeaveStatus, LeaveType


class LeaveIn(BaseModel):
    start: date
    end: date
    reason: str = Field(min_length=4, max_length=500)


class ApprovalIn(BaseModel):
    decision: Decision
    comment: str = Field(min_length=3, max_length=500)


class LeaveOut(BaseModel):
    """JSON keeps the old ``start``/``end`` names; the columns are start_date/end_date."""

    model_config = ConfigDict(from_attributes=True, validate_by_name=True)

    id: uuid.UUID
    employee_id: uuid.UUID
    start: date = Field(validation_alias="start_date")
    end: date = Field(validation_alias="end_date")
    reason: str
    request_type: LeaveType
    status: LeaveStatus
    created_at: datetime
    approver_comment: str | None
    calendar_sync_status: CalendarSyncStatus
    employee_calendar_event_id: str | None
    team_calendar_event_id: str | None


class LeaveDaysOut(LeaveOut):
    @computed_field
    @property
    def days(self) -> int:
        return working_days(self.start, self.end)


class ApprovalOut(LeaveDaysOut):
    employee_name: str
    department: str


class LeaveBalanceOut(BaseModel):
    annual_days: int
    used_days: int
    remaining_days: int


class LeaveListOut(BaseModel):
    items: list[LeaveDaysOut]
    balance: LeaveBalanceOut


class ApprovalListOut(BaseModel):
    items: list[ApprovalOut]
    pending: int
