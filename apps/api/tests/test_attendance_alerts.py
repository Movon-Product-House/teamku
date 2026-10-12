from datetime import UTC, datetime, timedelta

import pytest
from helpers import (
    add_attendance,
    add_leave,
    add_location_event,
    count,
    notifications_for,
    set_employee,
    set_office_policy,
)

from movon_hr.core.mailer import last_email_to
from movon_hr.core.time import JAKARTA
from movon_hr.modules.notifications.models import Notification

pytestmark = pytest.mark.anyio
ALERT_TITLES = {
    "Belum clock-in",
    "Sesi masih terbuka",
    "Re-verifikasi terlewat",
    "Lokasi di luar area kantor",
}


async def enable_alerts(db, **overrides: object) -> None:
    policy = {
        "alerts_enabled": True,
        "clock_in_reminder_time": "00:00",
        "clock_out_reminder_time": "23:59",
        "max_open_hours": 10,
        "alert_managers": False,
    }
    await set_office_policy(db, **(policy | overrides))


async def attendance_alerts_for(db, email: str) -> list:
    return [item for item in await notifications_for(db, email) if item.title in ALERT_TITLES]


async def test_disabled_policy_creates_no_attendance_alerts(client, db, login_headers) -> None:
    await set_office_policy(db, alerts_enabled=False)
    before = await count(db, Notification)

    await client.get("/api/v1/notifications", headers=await login_headers("fresh@movon.test"))

    assert await count(db, Notification) == before
    assert await attendance_alerts_for(db, "fresh@movon.test") == []


async def test_missed_clock_in_notifies_employee_once_per_day(client, db, login_headers) -> None:
    await enable_alerts(db)

    first = await client.get(
        "/api/v1/notifications", headers=await login_headers("fresh@movon.test")
    )
    second = await client.get(
        "/api/v1/notifications", headers=await login_headers("fresh@movon.test")
    )

    titles = [item["title"] for item in first.json()["items"]]
    assert titles.count("Belum clock-in") == 1
    assert [item["title"] for item in second.json()["items"]].count("Belum clock-in") == 1
    assert last_email_to("fresh@movon.test") is not None


async def test_approved_leave_skips_missed_clock_in(client, db, login_headers) -> None:
    await enable_alerts(db)
    today = datetime.now(JAKARTA).date()
    await add_leave(db, "fresh@movon.test", today, today, "Cuti hari ini", status="approved")

    await client.get("/api/v1/notifications", headers=await login_headers("fresh@movon.test"))

    assert await attendance_alerts_for(db, "fresh@movon.test") == []


async def test_open_session_past_max_hours_notifies_employee(client, db, login_headers) -> None:
    await enable_alerts(db, max_open_hours=1)
    await add_attendance(
        db,
        "fresh@movon.test",
        checked_in_at=datetime.now(UTC) - timedelta(hours=3),
        agenda=[{"title": "Sesi panjang"}],
    )

    await client.get("/api/v1/attendance/today", headers=await login_headers("fresh@movon.test"))

    titles = [item.title for item in await attendance_alerts_for(db, "fresh@movon.test")]
    assert "Sesi masih terbuka" in titles


async def test_alert_managers_notifies_department_manager_and_hr(client, db, login_headers) -> None:
    await enable_alerts(db, alert_managers=True)

    await client.get("/api/v1/notifications", headers=await login_headers("fresh@movon.test"))

    assert any(
        item.title == "Belum clock-in"
        for item in await attendance_alerts_for(db, "fresh@movon.test")
    )
    assert any(
        item.title == "Belum clock-in" and "Rani" in item.detail
        for item in await notifications_for(db, "manager@movon.test")
    )
    assert any(
        item.title == "Belum clock-in" and "Rani" in item.detail
        for item in await notifications_for(db, "hr@movon.test")
    )


async def test_remote_employee_gets_clock_in_reminder_but_not_geofence_alert(
    client, db, login_headers
) -> None:
    await enable_alerts(db)
    await set_employee(db, "fresh@movon.test", is_remote=True)
    # location_events.attendance_id is a FK now: hang the event on yesterday's closed session.
    yesterday = datetime.now(UTC) - timedelta(days=1)
    earlier = await add_attendance(
        db,
        "fresh@movon.test",
        checked_in_at=yesterday,
        checked_out_at=yesterday + timedelta(hours=1),
        agenda=[{"title": "Kemarin"}],
    )
    await add_location_event(
        db,
        "fresh@movon.test",
        earlier.id,
        kind="reverify",
        at=datetime.now(UTC),
        lat=-6.3,
        lng=106.8166,
        anomaly="outside_geofence",
    )

    await client.get("/api/v1/notifications", headers=await login_headers("fresh@movon.test"))

    titles = [item.title for item in await attendance_alerts_for(db, "fresh@movon.test")]
    assert "Belum clock-in" in titles
    assert "Lokasi di luar area kantor" not in titles


async def test_outside_geofence_creates_accountability_alert_for_office_worker(
    client, db, login_headers
) -> None:
    await enable_alerts(db)
    record = await add_attendance(
        db,
        "fresh@movon.test",
        checked_in_at=datetime.now(UTC),
        agenda=[{"title": "Di kantor"}],
    )
    await add_location_event(
        db,
        "fresh@movon.test",
        record.id,
        kind="reverify",
        at=datetime.now(UTC),
        lat=-6.3,
        lng=106.8166,
        anomaly="outside_geofence",
    )

    await client.get("/api/v1/notifications", headers=await login_headers("fresh@movon.test"))

    titles = [item.title for item in await attendance_alerts_for(db, "fresh@movon.test")]
    assert "Lokasi di luar area kantor" in titles
    assert "Belum clock-in" not in titles


async def test_repeated_notifications_poll_does_not_duplicate_kind_day(
    client, db, login_headers
) -> None:
    await enable_alerts(db)

    await client.get("/api/v1/notifications", headers=await login_headers("fresh@movon.test"))
    await client.get("/api/v1/notifications", headers=await login_headers("fresh@movon.test"))
    await client.get("/api/v1/attendance/today", headers=await login_headers("fresh@movon.test"))

    assert len(await attendance_alerts_for(db, "fresh@movon.test")) == 1
