"""Pure attendance rules: geofence distance, allowed radius, reverify slots, day bounds."""

from datetime import date, datetime, time, timedelta
from math import asin, cos, radians, sin, sqrt
from random import uniform

from movon_hr.core.time import JAKARTA, jakarta_date

# GPS uncertainty may expand the allowed radius slightly, but never enough to check in from home.
MAX_ACCURACY_CREDIT_METERS = 50
LOW_ACCURACY_METERS = 100
# A reverify slot counts as missed this long after it is due.
REVERIFY_GRACE = timedelta(minutes=15)
TARGET_HOURS_PER_DAY = 8  # ponytail: fixed until shifts exist; per-office setting when they do


def haversine_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6_371_000
    d_lat, d_lon = radians(lat2 - lat1), radians(lon2 - lon1)
    value = sin(d_lat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(d_lon / 2) ** 2
    return 2 * radius * asin(sqrt(value))


def allowed_check_in_radius_meters(radius_meters: float, accuracy_meters: float) -> float:
    return radius_meters + min(max(accuracy_meters, 0), MAX_ACCURACY_CREDIT_METERS)


def reverify_offsets_minutes(count: int, window_start: int, window_end: int) -> list[float]:
    """Minutes after check-in: the first slot at the window start, the rest jittered per span."""
    span = max(window_end - window_start, 1)
    offsets: list[float] = [window_start] if count > 0 else []
    for index in range(1, count):
        low = window_start + span * index / count
        high = window_start + span * (index + 1) / count
        offsets.append(uniform(low, high))  # noqa: S311 - scheduling jitter, not security
    return offsets


def is_missed(due_at: datetime, now: datetime) -> bool:
    return now >= due_at + REVERIFY_GRACE


def is_late(checked_in_at: datetime, work_start: time) -> bool:
    return checked_in_at.astimezone(JAKARTA).time() >= work_start


def parse_hhmm(value: str) -> time:
    hour, minute = value.split(":")
    return time(int(hour), int(minute))


def jakarta_day_bounds(day: date) -> tuple[datetime, datetime]:
    """[start, end) of a Jakarta calendar day, for timestamptz range filters."""
    start = datetime.combine(day, time(0), JAKARTA)
    return start, start + timedelta(days=1)


def clock_out_alert_day(
    checked_in_at: datetime, now: datetime, reminder_time: time, max_open_hours: int
) -> date | None:
    """Day to key the open-session alert to, or None while it is not due.

    Due once the session has been open max_open_hours, or once the clock-out reminder of its
    check-in day passes; a session opened after that reminder (a night shift) only waits for
    max_open_hours. Keyed to the check-in day, so a session alerts once even across midnight.
    """
    day = jakarta_date(checked_in_at)
    reminder = datetime.combine(day, reminder_time, JAKARTA)
    hours_open = (now - checked_in_at).total_seconds() / 3600
    if hours_open >= max_open_hours or checked_in_at < reminder <= now:
        return day
    return None
