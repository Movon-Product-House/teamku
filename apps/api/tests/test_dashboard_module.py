"""U11: dashboard numbers on the demo seed (7 check-ins from 08:50, every 4 minutes)."""

import pytest

pytestmark = pytest.mark.anyio

NUMBERS = (
    "headcount",
    "present",
    "absent",
    "on_leave",
    "late",
    "attendance_rate",
    "pending_approvals",
    "agenda_total",
    "agenda_completed",
)


async def numbers(client, headers: dict[str, str]) -> tuple[int, ...]:
    body = (await client.get("/api/v1/dashboard", headers=headers)).json()
    return tuple(body[key] for key in NUMBERS)


async def test_dashboard_numbers_per_role(client, login_headers) -> None:
    # 19 active, 7 present, check-ins from 09:02 are late, the seed request is pending.
    assert await numbers(client, await login_headers("hr@movon.test")) == (
        19, 7, 12, 0, 4, 37, 1, 7, 4
    )  # fmt: skip
    # Engineering: 6 people, 3 present (manager 08:50, Ayu 09:10, Gilang 09:14).
    assert await numbers(client, await login_headers("manager@movon.test")) == (
        6, 3, 3, 0, 2, 50, 1, 3, 1
    )  # fmt: skip
    # An employee sees only themselves and never pending approvals.
    assert await numbers(client, await login_headers("employee@movon.test")) == (
        1, 0, 1, 0, 0, 0, 0, 0, 0
    )  # fmt: skip
