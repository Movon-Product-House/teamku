import uuid

from pydantic import BaseModel, ConfigDict, Field

from movon_hr.modules.settings.models import (
    CalendarDeliveryMode,
    CalendarProvider,
    CalendarScope,
    StoredCalendarProvider,
)

HHMM = r"^([01]\d|2[0-3]):[0-5]\d$"


class OfficeSettingsIn(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    radius_meters: float = Field(ge=50, le=5_000)
    reverify_enabled: bool | None = None
    reverify_count_per_day: int | None = Field(default=None, ge=1, le=3)
    reverify_window_start_minutes: int | None = Field(default=None, ge=0, le=1_440)
    reverify_window_end_minutes: int | None = Field(default=None, ge=0, le=1_440)
    alerts_enabled: bool | None = None
    clock_in_reminder_time: str | None = Field(default=None, pattern=HHMM)
    clock_out_reminder_time: str | None = Field(default=None, pattern=HHMM)
    max_open_hours: int | None = Field(default=None, ge=1, le=24)
    alert_managers: bool | None = None


class WorkLocationIn(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    radius_meters: float = Field(default=300, ge=50, le=5_000)


class CalendarSettingsIn(BaseModel):
    provider: CalendarProvider
    team_calendar_id: str = Field(min_length=2, max_length=300)
    connected: bool = False
    calendar_name: str = Field(default="Kalender perusahaan", max_length=120)
    scope: CalendarScope = "company"
    division: str = Field(default="", max_length=100)
    delivery_mode: CalendarDeliveryMode = "shared_and_email"


class MapsUrlIn(BaseModel):
    url: str = Field(min_length=4, max_length=2_000)


class LocationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    latitude: float
    longitude: float
    radius_meters: float
    reverify_enabled: bool
    reverify_count_per_day: int
    reverify_window_start_minutes: int
    reverify_window_end_minutes: int
    alerts_enabled: bool
    clock_in_reminder_time: str
    clock_out_reminder_time: str
    max_open_hours: int
    alert_managers: bool
    is_primary: bool


class LocationListOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: list[LocationOut]


class CalendarOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    provider: StoredCalendarProvider
    connected: bool
    team_calendar_id: str
    calendar_name: str
    scope: CalendarScope
    division: str
    delivery_mode: CalendarDeliveryMode


class AuthorizationUrlOut(BaseModel):
    authorization_url: str


class GoogleCalendarOut(BaseModel):
    id: str
    name: str
    primary: bool


class GoogleCalendarListOut(BaseModel):
    items: list[GoogleCalendarOut]


class MapsCoordinatesOut(BaseModel):
    latitude: float
    longitude: float
    resolved_url: str
    maps_url: str
