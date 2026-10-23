from datetime import datetime, time

from movon_hr.core.time import JAKARTA
from movon_hr.modules.dashboard.rules import attention

WORK_START = time(9, 0)
NOW = datetime(2026, 10, 21, 10, 0, tzinfo=JAKARTA)


def at(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 10, 21, hour, minute, tzinfo=JAKARTA)


def member(**overrides: object) -> list:
    values = {
        "first_check_in": None,
        "open_from_earlier_day": False,
        "on_leave": False,
        "missed_reverify_at": None,
        "now": NOW,
        "work_start": WORK_START,
    }
    return attention(**(values | overrides))


def test_first_check_in_at_or_after_work_start_is_late() -> None:
    assert member(first_check_in=at(9, 10)) == [("late", at(9, 10))]
    assert member(first_check_in=at(9, 0)) == [("late", at(9, 0))]
    assert member(first_check_in=at(8, 55)) == []
    assert member(first_check_in=at(9, 10), work_start=time(9, 15)) == []


def test_no_check_in_counts_only_once_work_has_started() -> None:
    assert member() == [("not_checked_in", None)]
    assert member(now=at(8, 30)) == []


def test_leave_or_a_night_shift_still_open_is_not_a_missing_check_in() -> None:
    assert member(on_leave=True) == []
    assert member(open_from_earlier_day=True) == []


def test_missed_reverify_is_listed_with_its_time() -> None:
    assert member(first_check_in=at(8, 50), missed_reverify_at=at(9, 45)) == [
        ("missed_reverify", at(9, 45))
    ]
    assert member(first_check_in=at(9, 5), missed_reverify_at=at(9, 45)) == [
        ("late", at(9, 5)),
        ("missed_reverify", at(9, 45)),
    ]
