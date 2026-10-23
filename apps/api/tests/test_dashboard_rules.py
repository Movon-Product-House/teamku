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
        "late": False,
        "open_since": None,
        "on_leave": False,
        "missed_reverify_at": None,
        "now": NOW,
        "work_start": WORK_START,
    }
    return attention(**(values | overrides))


def test_a_late_first_check_in_is_listed_with_its_time() -> None:
    assert member(first_check_in=at(9, 10), late=True) == [("late", at(9, 10))]
    assert member(first_check_in=at(8, 55)) == []


def test_no_check_in_counts_only_once_work_has_started() -> None:
    assert member() == [("not_checked_in", None)]
    assert member(now=at(8, 30)) == []


def test_leave_is_not_a_missing_check_in() -> None:
    assert member(on_leave=True) == []


def test_a_session_open_from_an_earlier_day_is_listed_instead_of_a_missing_check_in() -> None:
    yesterday = datetime(2026, 10, 20, 22, 0, tzinfo=JAKARTA)
    assert member(open_since=yesterday) == [("open_session", yesterday)]
    assert member(open_since=yesterday, now=at(8, 30)) == []


def test_missed_reverify_is_listed_with_its_time() -> None:
    assert member(first_check_in=at(8, 50), missed_reverify_at=at(9, 45)) == [
        ("missed_reverify", at(9, 45))
    ]
    assert member(first_check_in=at(9, 5), late=True, missed_reverify_at=at(9, 45)) == [
        ("late", at(9, 5)),
        ("missed_reverify", at(9, 45)),
    ]
