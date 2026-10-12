"""Pure date helpers in the company time zone (Asia/Jakarta)."""

from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

JAKARTA = ZoneInfo("Asia/Jakarta")


def jakarta_date(moment: datetime | None = None) -> date:
    """Calendar date in Jakarta; naive datetimes are treated as UTC."""
    value = moment or datetime.now(JAKARTA)
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(JAKARTA).date()


def working_days(start: date, end: date) -> int:
    """Monday-Friday days from ``start`` to ``end``, both inclusive."""
    return sum(
        1
        for offset in range((end - start).days + 1)
        if (start + timedelta(days=offset)).weekday() < 5
    )
