"""Pure dashboard rules: what about a team member needs the manager's attention today."""

from datetime import datetime, time

from movon_hr.core.time import JAKARTA
from movon_hr.modules.dashboard.schemas import DashboardAttentionKind


def attention(
    *,
    first_check_in: datetime | None,
    late: bool,
    open_since: datetime | None,
    on_leave: bool,
    missed_reverify_at: datetime | None,
    now: datetime,
    work_start: time,
) -> list[tuple[DashboardAttentionKind, datetime | None]]:
    """Today's flags for one member, each with the moment it refers to (none for no check-in).

    open_since is a session still open from an earlier day: it blocks check-in, so it is
    listed on its own instead of as a missing check-in.
    """
    found: list[tuple[DashboardAttentionKind, datetime | None]] = []
    if first_check_in is not None:
        if late:
            found.append(("late", first_check_in))
    # ponytail: one office-wide work start, so a night-shift worker reads as not checked in
    # until they come; per-employee shifts fix this when they exist.
    elif not on_leave and now.astimezone(JAKARTA).time() >= work_start:
        found.append(("open_session", open_since) if open_since else ("not_checked_in", None))
    if missed_reverify_at is not None:
        found.append(("missed_reverify", missed_reverify_at))
    return found
