import uuid
from datetime import date, datetime
from typing import Literal

from sqlalchemy import ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from movon_hr.core.db import Base, one_of
from movon_hr.core.identity import UUIDV7
from movon_hr.core.tenancy import TenantScoped

LeaveType = Literal["time_off"]
Decision = Literal["approved", "rejected", "revision_requested"]
LeaveStatus = Literal["pending", "cancelled", "approved", "rejected", "revision_requested"]
CalendarSyncStatus = Literal["not_applicable", "skipped", "ok", "failed", "removed"]


class LeaveRequest(TenantScoped, Base):
    __tablename__ = "leave_requests"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=UUIDV7)
    employee_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("employees.id"))
    start_date: Mapped[date]
    end_date: Mapped[date]
    reason: Mapped[str]
    request_type: Mapped[LeaveType] = mapped_column(default="time_off")
    status: Mapped[LeaveStatus] = mapped_column(default="pending")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    approver_comment: Mapped[str | None]
    calendar_sync_status: Mapped[CalendarSyncStatus] = mapped_column(
        default="not_applicable", server_default="not_applicable"
    )
    employee_calendar_event_id: Mapped[str | None]
    team_calendar_event_id: Mapped[str | None]

    __table_args__ = (
        one_of("request_type", LeaveType),
        one_of("status", LeaveStatus),
        one_of("calendar_sync_status", CalendarSyncStatus),
    )
