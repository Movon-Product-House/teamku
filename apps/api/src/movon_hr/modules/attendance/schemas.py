import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field


class CheckIn(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    accuracy_meters: float = Field(ge=0, le=10_000)
    selfie_captured: bool
    location_share_approved: bool
    agenda: list[dict] = Field(min_length=1, max_length=5)


class CheckOut(BaseModel):
    summary: str = Field(min_length=4, max_length=1000)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    accuracy_meters: float | None = Field(default=None, ge=0, le=10_000)


class ReverifyInput(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    accuracy_meters: float = Field(ge=0, le=10_000)
    selfie_captured: bool


class SessionOut(BaseModel):
    id: uuid.UUID
    checked_in_at: datetime
    checked_out_at: datetime | None
    anomaly: str | None
    agenda_count: int
    summary: str | None


class PendingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    due_at: datetime | None
    kind: str


class TodayOut(BaseModel):
    state: str
    session: SessionOut | None
    pending_reverification: PendingOut | None
    is_remote: bool


class CheckInOut(BaseModel):
    id: uuid.UUID
    checked_in_at: datetime
    distance_meters: int
    allowed_radius_meters: int
    anomaly: str | None
    agenda_count: int


class IdempotentOut(BaseModel):
    id: uuid.UUID
    idempotent: bool


class CheckOutOut(BaseModel):
    id: uuid.UUID
    checked_out_at: datetime
    effective_hours: float


class LocationEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    employee_id: uuid.UUID
    attendance_id: uuid.UUID
    kind: str
    at: datetime
    lat: float | None
    lng: float | None
    accuracy: float | None
    distance_meters: int | None  # always stored rounded; int keeps the old JSON (0, not 0.0)
    inside_geofence: bool | None
    anomaly: str | None
    due_at: datetime | None

    @computed_field
    @property
    def maps_url(self) -> str | None:
        if self.lat is None or self.lng is None:
            return None
        return f"https://www.google.com/maps?q={self.lat},{self.lng}"


class SkippedEventOut(LocationEventOut):
    """A remote worker answering a slot scheduled before they became remote."""

    skipped: bool  # required, so the response union never picks it for a plain event


class SkippedOut(BaseModel):
    skipped: bool
    pending_reverification: None


class LocationHistory(BaseModel):
    employee_id: uuid.UUID
    items: list[LocationEventOut]
