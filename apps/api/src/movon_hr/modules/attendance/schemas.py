import uuid
from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

from movon_hr.modules.attendance.models import AttendanceAnomaly, LocationEventKind


class AgendaItemIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    priority: str | None = Field(default=None, max_length=20)
    status: str | None = Field(default=None, max_length=20)


class CheckInIn(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    accuracy_meters: float = Field(ge=0, le=10_000)
    selfie_captured: bool
    location_share_approved: bool
    agenda: list[AgendaItemIn] = Field(min_length=1, max_length=5)


class CheckOutIn(BaseModel):
    summary: str = Field(min_length=4, max_length=1000)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    accuracy_meters: float | None = Field(default=None, ge=0, le=10_000)


class ReverifyIn(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    accuracy_meters: float = Field(ge=0, le=10_000)
    selfie_captured: bool


# Response fields with a default are always sent, so the spec must list them as required
# (tests/test_openapi.py): json_schema_serialization_defaults_required on every Out model
# that has defaults.
class AgendaItemOut(BaseModel):
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    title: str | None = None
    status: str | None = None

    @field_validator("title", "status", mode="before")
    @classmethod
    def drop_non_strings(cls, value: object) -> str | None:
        """Rows stored before check-in typed its agenda may hold any JSON here."""
        return value if isinstance(value, str) else None


class SessionOut(BaseModel):
    id: uuid.UUID
    checked_in_at: datetime
    checked_out_at: datetime | None
    anomaly: AttendanceAnomaly | None
    agenda_count: int
    agenda: list[AgendaItemOut]
    summary: str | None


class PendingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    due_at: datetime | None
    kind: LocationEventKind


type AttendanceTodayState = Literal["not_checked_in", "checked_in", "completed"]


class TodayOut(BaseModel):
    state: AttendanceTodayState
    session: SessionOut | None
    pending_reverification: PendingOut | None
    is_remote: bool
    # Sessions already checked out today, so the client can add the open one live.
    closed_hours_today: float


class WeekDayOut(BaseModel):
    date: date
    hours: float
    late: bool
    on_leave: bool


class WeekOut(BaseModel):
    target_hours: int
    days: list[WeekDayOut]


class CheckInOut(BaseModel):
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    result: Literal["created"] = "created"
    id: uuid.UUID
    checked_in_at: datetime
    distance_meters: int
    allowed_radius_meters: int
    anomaly: AttendanceAnomaly | None
    agenda_count: int


class IdempotentOut(BaseModel):
    """A replayed Idempotency-Key: the attendance the first request created."""

    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    result: Literal["idempotent"] = "idempotent"
    id: uuid.UUID
    idempotent: bool


CheckInResult = Annotated[CheckInOut | IdempotentOut, Field(discriminator="result")]


class CheckOutOut(BaseModel):
    id: uuid.UUID
    checked_out_at: datetime
    effective_hours: float


class LocationEventOut(BaseModel):
    model_config = ConfigDict(
        from_attributes=True, json_schema_serialization_defaults_required=True
    )

    id: uuid.UUID
    employee_id: uuid.UUID
    attendance_id: uuid.UUID
    kind: LocationEventKind
    at: datetime
    lat: float | None
    lng: float | None
    accuracy: float | None
    distance_meters: int | None  # always stored rounded; int keeps the old JSON (0, not 0.0)
    inside_geofence: bool | None
    anomaly: AttendanceAnomaly | None
    due_at: datetime | None

    @computed_field
    @property
    def maps_url(self) -> str | None:
        if self.lat is None or self.lng is None:
            return None
        return f"https://www.google.com/maps?q={self.lat},{self.lng}"


class VerifiedEventOut(LocationEventOut):
    """The pending slot, answered."""

    result: Literal["verified"] = "verified"


class SkippedEventOut(LocationEventOut):
    """A remote worker answering a slot scheduled before they became remote."""

    result: Literal["skipped_slot"] = "skipped_slot"
    skipped: bool


class SkippedOut(BaseModel):
    """A remote worker with no slot pending."""

    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    result: Literal["skipped"] = "skipped"
    skipped: bool
    pending_reverification: None


ReverifyResult = Annotated[
    VerifiedEventOut | SkippedEventOut | SkippedOut, Field(discriminator="result")
]


class LocationHistoryOut(BaseModel):
    employee_id: uuid.UUID
    items: list[LocationEventOut]
