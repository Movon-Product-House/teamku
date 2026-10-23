from datetime import date, datetime, time

from movon_hr.core.time import JAKARTA
from movon_hr.modules.attendance.rules import (
    allowed_check_in_radius_meters,
    clock_out_alert_day,
    haversine_meters,
    is_late,
)
from movon_hr.seed import OFFICE_LATITUDE, OFFICE_LONGITUDE, OFFICE_RADIUS_METERS


def test_haversine_returns_zero_at_same_point() -> None:
    assert (
        haversine_meters(OFFICE_LATITUDE, OFFICE_LONGITUDE, OFFICE_LATITUDE, OFFICE_LONGITUDE) == 0
    )


def test_haversine_finds_nearby_point() -> None:
    assert 100 < haversine_meters(OFFICE_LATITUDE, OFFICE_LONGITUDE, -6.201, OFFICE_LONGITUDE) < 120


def test_accuracy_credit_is_capped_to_prevent_home_check_in() -> None:
    assert allowed_check_in_radius_meters(OFFICE_RADIUS_METERS, 10) == OFFICE_RADIUS_METERS + 10
    assert allowed_check_in_radius_meters(OFFICE_RADIUS_METERS, 500) == OFFICE_RADIUS_METERS + 50


def test_clock_out_alert_waits_for_the_reminder_or_max_open_hours() -> None:
    wednesday = date(2026, 10, 21)

    def due(check_in: tuple[int, int, int], now: tuple[int, int, int]) -> date | None:
        at = [datetime(2026, 10, *moment, tzinfo=JAKARTA) for moment in (check_in, now)]
        return clock_out_alert_day(at[0], at[1], time(18, 15), max_open_hours=10)

    assert due((21, 9, 0), (21, 18, 0)) is None  # day shift, before the reminder
    assert due((21, 9, 0), (21, 18, 15)) == wednesday  # day shift, reminder reached
    # A night shift that starts after the reminder waits for max_open_hours ...
    assert due((21, 20, 0), (21, 20, 30)) is None
    assert due((21, 20, 0), (22, 5, 59)) is None
    # ... and stays keyed to its check-in day past midnight, however old it gets.
    assert due((21, 20, 0), (22, 6, 0)) == wednesday
    assert due((21, 20, 0), (24, 9, 0)) == wednesday


def test_a_check_in_at_or_after_work_start_is_late() -> None:
    def check_in(hour: int, minute: int) -> datetime:
        return datetime(2026, 10, 21, hour, minute, tzinfo=JAKARTA)

    assert is_late(check_in(9, 10), time(9, 0))
    assert is_late(check_in(9, 0), time(9, 0))
    assert not is_late(check_in(8, 55), time(9, 0))
    assert not is_late(check_in(9, 10), time(9, 15))
