"""U11: dashboard numbers on the demo seed (7 check-ins from 08:50, every 4 minutes)."""

from datetime import datetime, timedelta

import pytest
from helpers import (
    add_attendance,
    add_leave,
    add_location_event,
    location_events,
)

from movon_hr.core.time import JAKARTA

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


async def manager_dashboard(client, login_headers) -> dict:
    response = await client.get(
        "/api/v1/dashboard", headers=await login_headers("manager@movon.test")
    )
    assert response.status_code == 200
    return response.json()


def flags(body: dict) -> set[tuple[str, str]]:
    return {(item["employee"], item["kind"]) for item in body["attention"]}


async def test_manager_sees_who_needs_attention_today(
    client, db, login_headers, employee_id
) -> None:
    ayu_session = (await location_events(db, "ayu@movon.test"))[0].attendance_id
    missed_at = datetime(2026, 10, 21, 9, 45, tzinfo=JAKARTA)
    await add_location_event(
        db,
        "ayu@movon.test",
        ayu_session,
        kind="reverify",
        at=missed_at,
        anomaly="missed_reverify",
    )

    body = await manager_dashboard(client, login_headers)

    # 10:00 WIB, work starts 09:00: Ayu 09:10 and Gilang 09:14 are late, three never came.
    assert flags(body) == {
        ("Ayu Maharani", "late"),
        ("Ayu Maharani", "missed_reverify"),
        ("Gilang Ramadhan", "late"),
        ("Sinta Lestari", "not_checked_in"),
        ("Rani Prasetyo", "not_checked_in"),
        ("Dian Permata", "not_checked_in"),
    }
    missed = next(item for item in body["attention"] if item["kind"] == "missed_reverify")
    assert missed["employee_id"] == str(await employee_id("ayu@movon.test"))
    assert missed["title"] == "QA Engineer"
    assert datetime.fromisoformat(missed["at"]) == missed_at
    assert body["work_start_time"] == "09:00"
    rows = {row["employee"]: row["employee_id"] for row in body["attendance"]}
    assert rows["Gilang Ramadhan"] == str(await employee_id("gilang@movon.test"))


async def test_late_follows_the_work_start_time_setting(client, login_headers) -> None:
    hr = await login_headers("hr@movon.test")
    office = (await client.get("/api/v1/settings/office", headers=hr)).json()
    saved = await client.put(
        "/api/v1/settings/office",
        headers=hr,
        json={key: office[key] for key in ("name", "latitude", "longitude", "radius_meters")}
        | {"work_start_time": "09:12"},
    )
    assert saved.status_code == 200
    assert saved.json()["work_start_time"] == "09:12"

    body = await manager_dashboard(client, login_headers)

    assert body["late"] == 1
    assert {name for name, kind in flags(body) if kind == "late"} == {"Gilang Ramadhan"}


async def test_only_the_first_session_of_the_day_decides_late(client, db, login_headers) -> None:
    morning = datetime(2026, 10, 21, 8, 30, tzinfo=JAKARTA)
    await add_attendance(
        db,
        "employee@movon.test",
        checked_in_at=morning,
        checked_out_at=morning + timedelta(minutes=10),
        agenda=[{}],
    )
    await add_attendance(
        db, "employee@movon.test", checked_in_at=morning + timedelta(hours=1), agenda=[{}]
    )

    body = await manager_dashboard(client, login_headers)

    assert not {kind for name, kind in flags(body) if name == "Sinta Lestari"}
    assert body["late"] == 2


async def test_team_agenda_lists_each_item_with_its_owner(client, login_headers) -> None:
    body = await manager_dashboard(client, login_headers)

    assert len(body["agenda"]) == body["agenda_total"] == 3
    assert {item["employee"] for item in body["agenda"]} == {
        "Raka Pratama",
        "Ayu Maharani",
        "Gilang Ramadhan",
    }
    assert {item["title"] for item in body["agenda"]} == {"Prioritas utama"}


async def test_team_leave_covers_the_next_two_weeks(client, db, login_headers) -> None:
    today = datetime(2026, 10, 21, tzinfo=JAKARTA).date()
    day = timedelta(days=1)
    await add_leave(db, "employee@movon.test", today - day, today + day, "Sakit", status="approved")
    await add_leave(db, "fresh@movon.test", today - 3 * day, today - day, "Lalu", status="approved")
    await add_leave(
        db, "fresh@movon.test", today + 20 * day, today + 21 * day, "Jauh", status="approved"
    )
    await add_leave(
        db, "gilang@movon.test", today + 2 * day, today + 3 * day, "Tolak", status="rejected"
    )
    await add_leave(db, "andi@movon.test", today + day, today + day, "Lain tim", status="approved")

    body = await manager_dashboard(client, login_headers)

    # The seed's pending request (Ayu, in 7 days) shows too, so the manager sees it coming.
    assert [
        (item["employee"], item["title"], item["start_date"], item["end_date"], item["status"])
        for item in body["team_leave"]
    ] == [
        ("Sinta Lestari", "Frontend Engineer", str(today - day), str(today + day), "approved"),
        ("Ayu Maharani", "QA Engineer", str(today + 7 * day), str(today + 8 * day), "pending"),
    ]
