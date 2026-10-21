from datetime import datetime, time, timedelta

import pytest
from helpers import add_attendance, add_leave
from sqlalchemy import select

from movon_hr.core.time import JAKARTA, jakarta_date
from movon_hr.modules.attendance.models import Attendance
from movon_hr.seed import OFFICE_LATITUDE, OFFICE_LONGITUDE

pytestmark = pytest.mark.anyio

EMAIL = "fresh@movon.test"


def at(day, hour: int, minute: int = 0) -> datetime:
    return datetime.combine(day, time(hour, minute), JAKARTA)


async def test_today_lists_the_session_agenda(client, db, login_headers) -> None:
    agenda = [{"title": "Laporan Q3", "status": "done"}, {"title": "Meeting vendor"}]
    await add_attendance(db, EMAIL, checked_in_at=datetime.now(JAKARTA), agenda=agenda)

    response = await client.get("/api/v1/attendance/today", headers=await login_headers(EMAIL))

    assert response.json()["session"]["agenda"] == [
        {"title": "Laporan Q3", "status": "done"},
        {"title": "Meeting vendor", "status": None},
    ]


async def test_today_tolerates_agenda_rows_with_non_string_fields(
    client, db, login_headers
) -> None:
    agenda = [{"title": 1, "status": True}, {"title": ["a"]}]
    await add_attendance(db, EMAIL, checked_in_at=datetime.now(JAKARTA), agenda=agenda)

    response = await client.get("/api/v1/attendance/today", headers=await login_headers(EMAIL))

    assert response.status_code == 200
    assert response.json()["session"]["agenda"] == [
        {"title": None, "status": None},
        {"title": None, "status": None},
    ]


async def test_check_in_rejects_an_agenda_item_without_a_string_title(
    client, login_headers
) -> None:
    response = await client.post(
        "/api/v1/attendance/check-in",
        headers=await login_headers(EMAIL) | {"Idempotency-Key": "bad-agenda"},
        json={
            "latitude": OFFICE_LATITUDE,
            "longitude": OFFICE_LONGITUDE,
            "accuracy_meters": 10,
            "selfie_captured": True,
            "location_share_approved": True,
            "agenda": [{"title": 1}],
        },
    )

    assert response.status_code == 422


async def test_check_in_stores_only_known_agenda_keys(client, db, login_headers) -> None:
    response = await client.post(
        "/api/v1/attendance/check-in",
        headers=await login_headers(EMAIL) | {"Idempotency-Key": "extra-agenda"},
        json={
            "latitude": OFFICE_LATITUDE,
            "longitude": OFFICE_LONGITUDE,
            "accuracy_meters": 10,
            "selfie_captured": True,
            "location_share_approved": True,
            "agenda": [{"title": "Laporan", "priority": "high", "junk": "x" * 10_000}],
        },
    )

    assert response.status_code == 200
    record = await db.scalar(select(Attendance).where(Attendance.id == response.json()["id"]))
    assert record.agenda == [{"title": "Laporan", "priority": "high", "status": None}]


async def test_week_reports_hours_lateness_and_leave_per_workday(client, db, login_headers) -> None:
    monday = jakarta_date() - timedelta(days=jakarta_date().weekday())
    await add_attendance(
        db, EMAIL, checked_in_at=at(monday, 8, 30), checked_out_at=at(monday, 17), agenda=[{}]
    )
    tuesday = monday + timedelta(days=1)
    await add_attendance(
        db, EMAIL, checked_in_at=at(tuesday, 9, 30), checked_out_at=at(tuesday, 11), agenda=[{}]
    )
    await add_leave(
        db, EMAIL, monday + timedelta(days=2), monday + timedelta(days=2), "Cuti", status="approved"
    )

    response = await client.get("/api/v1/attendance/week", headers=await login_headers(EMAIL))

    assert response.status_code == 200
    body = response.json()
    assert body["target_hours"] == 8
    assert [day["date"] for day in body["days"]] == [
        str(monday + timedelta(days=offset)) for offset in range(5)
    ]
    assert body["days"][0] == {"date": str(monday), "hours": 8.5, "late": False, "on_leave": False}
    assert body["days"][1]["hours"] == 1.5
    assert body["days"][1]["late"] is True
    assert body["days"][2]["on_leave"] is True
    assert body["days"][3]["hours"] == 0


async def test_week_counts_an_open_session_up_to_now(client, db, login_headers) -> None:
    checked_in_at = datetime.now(JAKARTA) - timedelta(minutes=30)
    if jakarta_date().weekday() > 4 or jakarta_date(checked_in_at) != jakarta_date():
        pytest.skip("needs a weekday check-in 30 minutes ago on the same date")
    await add_attendance(db, EMAIL, checked_in_at=checked_in_at, agenda=[{}])

    response = await client.get("/api/v1/attendance/week", headers=await login_headers(EMAIL))

    today = next(d for d in response.json()["days"] if d["date"] == str(jakarta_date()))
    assert today["hours"] == pytest.approx(0.5, abs=0.05)


async def test_week_late_only_counts_the_first_check_in_of_the_day(
    client, db, login_headers
) -> None:
    monday = jakarta_date() - timedelta(days=jakarta_date().weekday())
    await add_attendance(
        db, EMAIL, checked_in_at=at(monday, 8), checked_out_at=at(monday, 12), agenda=[{}]
    )
    await add_attendance(
        db, EMAIL, checked_in_at=at(monday, 13), checked_out_at=at(monday, 17), agenda=[{}]
    )

    response = await client.get("/api/v1/attendance/week", headers=await login_headers(EMAIL))

    assert response.json()["days"][0] == {
        "date": str(monday),
        "hours": 8,
        "late": False,
        "on_leave": False,
    }


async def test_week_caps_a_forgotten_open_session_at_the_end_of_its_day(
    client, db, login_headers
) -> None:
    if jakarta_date().weekday() == 0:
        pytest.skip("needs a past weekday in the current week")
    monday = jakarta_date() - timedelta(days=jakarta_date().weekday())
    await add_attendance(db, EMAIL, checked_in_at=at(monday, 20), agenda=[{}])

    response = await client.get("/api/v1/attendance/week", headers=await login_headers(EMAIL))

    assert response.json()["days"][0]["hours"] == 4


async def test_week_caps_a_session_closed_the_next_day_at_the_end_of_its_day(
    client, db, login_headers
) -> None:
    monday = jakarta_date() - timedelta(days=jakarta_date().weekday())
    await add_attendance(
        db,
        EMAIL,
        checked_in_at=at(monday, 20),
        checked_out_at=at(monday + timedelta(days=1), 8),
        agenda=[{}],
    )

    response = await client.get("/api/v1/attendance/week", headers=await login_headers(EMAIL))

    assert response.json()["days"][0]["hours"] == 4
    assert response.json()["days"][1]["hours"] == 0


async def test_today_sums_the_hours_of_every_closed_session_today(
    client, db, login_headers
) -> None:
    now = datetime.now(JAKARTA)
    if jakarta_date(now - timedelta(hours=3)) != jakarta_date():
        pytest.skip("needs three hours of today behind us")
    await add_attendance(
        db,
        EMAIL,
        checked_in_at=now - timedelta(hours=3),
        checked_out_at=now - timedelta(hours=2),
        agenda=[{}],
    )
    await add_attendance(
        db,
        EMAIL,
        checked_in_at=now - timedelta(minutes=90),
        checked_out_at=now - timedelta(minutes=60),
        agenda=[{}],
    )
    await add_attendance(db, EMAIL, checked_in_at=now - timedelta(minutes=30), agenda=[{}])

    response = await client.get("/api/v1/attendance/today", headers=await login_headers(EMAIL))

    assert response.json()["state"] == "checked_in"
    assert response.json()["closed_hours_today"] == 1.5
