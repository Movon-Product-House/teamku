from datetime import datetime, time, timedelta

import pytest
from helpers import add_attendance, add_leave

from movon_hr.core.time import JAKARTA, jakarta_date

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
    if jakarta_date().weekday() > 4:
        pytest.skip("the week only covers Monday to Friday")
    await add_attendance(
        db, EMAIL, checked_in_at=datetime.now(JAKARTA) - timedelta(minutes=30), agenda=[{}]
    )

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
