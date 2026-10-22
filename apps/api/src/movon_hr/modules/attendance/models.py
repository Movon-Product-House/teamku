import uuid
from datetime import date, datetime
from typing import Literal

from sqlalchemy import ForeignKey, Index, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from movon_hr.core.db import Base, one_of
from movon_hr.core.identity import UUIDV7
from movon_hr.core.tenancy import TenantScoped

type AttendanceAnomaly = Literal["low_accuracy", "missed_reverify", "outside_geofence"]
type LocationEventKind = Literal["check_in", "check_out", "reverify"]


class Attendance(TenantScoped, Base):
    __tablename__ = "attendance"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=UUIDV7)
    employee_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("employees.id"))
    checked_in_at: Mapped[datetime]
    latitude: Mapped[float]
    longitude: Mapped[float]
    accuracy_meters: Mapped[float]
    agenda: Mapped[list[dict]] = mapped_column(JSONB)
    anomaly: Mapped[AttendanceAnomaly | None]
    checked_out_at: Mapped[datetime | None]
    summary: Mapped[str | None]

    __table_args__ = (
        # One open session per employee, race-safe.
        Index(
            "attendance_tenant_id_employee_id_key",
            "tenant_id",
            "employee_id",
            unique=True,
            postgresql_where=text("checked_out_at IS NULL"),
        ),
        one_of("anomaly", AttendanceAnomaly),
    )


class IdempotencyKey(TenantScoped, Base):
    """Check-in idempotency key -> the attendance it created."""

    __tablename__ = "idempotency_keys"

    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), primary_key=True)
    key: Mapped[str] = mapped_column(primary_key=True)
    attendance_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("attendance.id"))


class LocationEvent(TenantScoped, Base):
    __tablename__ = "location_events"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=UUIDV7)
    employee_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("employees.id"))
    attendance_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("attendance.id"))
    kind: Mapped[LocationEventKind]
    at: Mapped[datetime]
    lat: Mapped[float | None]
    lng: Mapped[float | None]
    accuracy: Mapped[float | None]
    distance_meters: Mapped[float | None]
    inside_geofence: Mapped[bool | None]
    anomaly: Mapped[AttendanceAnomaly | None]
    due_at: Mapped[datetime | None]

    __table_args__ = (one_of("kind", LocationEventKind), one_of("anomaly", AttendanceAnomaly))


class AlertReceipt(TenantScoped, Base):
    """An alert already sent; the PK makes the alert job idempotent."""

    __tablename__ = "alert_receipts"

    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), primary_key=True)
    employee_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("employees.id"), primary_key=True)
    kind: Mapped[str] = mapped_column(primary_key=True)
    local_date: Mapped[date] = mapped_column(primary_key=True)
