"""Pure dashboard rules: what about a team member needs the manager's attention today."""

from datetime import datetime, time

from movon_hr.core.time import JAKARTA
from movon_hr.modules.attendance.rules import is_late
from movon_hr.modules.dashboard.schemas import DashboardAttentionKind


def attention(
    *,
    first_check_in: datetime | None,
    open_from_earlier_day: bool,
    on_leave: bool,
    missed_reverify_at: datetime | None,
    now: datetime,
    work_start: time,
) -> list[tuple[DashboardAttentionKind, datetime | None]]:
    """Today's flags for one member, each with the moment it refers to (none for no check-in)."""
    found: list[tuple[DashboardAttentionKind, datetime | None]] = []
    if first_check_in is not None:
        if is_late(first_check_in, work_start):
            found.append(("late", first_check_in))
    # A night shift still open blocks check-in, so it is not a missing one.
    elif (
        not on_leave and not open_from_earlier_day and now.astimezone(JAKARTA).time() >= work_start
    ):
        found.append(("not_checked_in", None))
    if missed_reverify_at is not None:
        found.append(("missed_reverify", missed_reverify_at))
    return found
