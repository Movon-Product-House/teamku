"""U10: attendance module (pure-read today, check-in races and replays) and the scheduled jobs."""

from datetime import UTC, datetime, timedelta

import pytest
from helpers import add_attendance, add_location_event, count, employee, set_office_policy
from sqlalchemy import func, select

from movon_hr import jobs
from movon_hr.core import mailer
from movon_hr.core.identity import AuthSession
from movon_hr.modules.attendance import service as attendance_service
from movon_hr.modules.attendance.models import AlertReceipt, Attendance, LocationEvent
from movon_hr.modules.audit.models import AuditLog
from movon_hr.modules.auth.models import LoginAttempt, PasswordReset
from movon_hr.modules.auth.service import LOGIN_ATTEMPT_WINDOW
from movon_hr.modules.notifications.models import Notification
from movon_hr.modules.settings.models import OAuthState
from movon_hr.seed import OFFICE_LATITUDE, OFFICE_LONGITUDE

pytestmark = pytest.mark.anyio

FRESH = "fresh@movon.test"
CHECK_IN = {
    "latitude": OFFICE_LATITUDE,
    "longitude": OFFICE_LONGITUDE,
    "accuracy_meters": 10,
    "selfie_captured": True,
    "location_share_approved": True,
    "agenda": [{"title": "Kerja"}],
}


async def test_alert_job_run_twice_sends_one_alert(db) -> None:
    await set_office_policy(db, alerts_enabled=True, clock_in_reminder_time="00:00")
    fresh = await employee(db, FRESH)

    assert await jobs.attendance_alerts(datetime.now(UTC))
    assert await jobs.attendance_alerts(datetime.now(UTC))

    titles = await db.scalars(select(Notification.title).where(Notification.user_id == fresh.id))
    assert list(titles).count("Belum clock-in") == 1
    receipts = await db.scalar(
        select(func.count())
        .select_from(AlertReceipt)
        .where(AlertReceipt.employee_id == fresh.id, AlertReceipt.kind == "missed_clock_in")
    )
    assert receipts == 1
    assert [m.to for m in mailer.outbox].count(FRESH) == 1


async def test_cleanup_deletes_only_expired_rows(db) -> None:
    now = datetime.now(UTC)
    fresh = await employee(db, FRESH)
    past, future = now - timedelta(minutes=1), now + timedelta(hours=1)
    db.add_all(
        [
            AuthSession(token="s-old", employee_id=fresh.id, expires_at=past),
            AuthSession(token="s-new", employee_id=fresh.id, expires_at=future),
            PasswordReset(token="r-old", employee_id=fresh.id, expires_at=past),
            PasswordReset(token="r-used", employee_id=fresh.id, expires_at=future, used_at=now),
            PasswordReset(token="r-new", employee_id=fresh.id, expires_at=future),
            LoginAttempt(email="a@x.test", attempted_at=now - LOGIN_ATTEMPT_WINDOW * 2),
            LoginAttempt(email="b@x.test", attempted_at=now - timedelta(minutes=1)),
            OAuthState(state="o-old", employee_id=fresh.id, expires_at=past),
            OAuthState(state="o-new", employee_id=fresh.id, expires_at=future),
        ]
    )
    await db.commit()

    assert await jobs.cleanup(now)

    assert set(await db.scalars(select(AuthSession.token))) == {"s-new"}
    assert set(await db.scalars(select(PasswordReset.token))) == {"r-new"}
    assert set(await db.scalars(select(LoginAttempt.email))) == {"b@x.test"}
    assert set(await db.scalars(select(OAuthState.state))) == {"o-new"}


async def test_today_is_a_pure_read(client, db, login_headers) -> None:
    await set_office_policy(db, alerts_enabled=True, clock_in_reminder_time="00:00")
    record = await add_attendance(
        db, FRESH, checked_in_at=datetime.now(UTC) - timedelta(hours=1), agenda=[{"title": "A"}]
    )
    due = datetime.now(UTC) - timedelta(minutes=20)
    slot = await add_location_event(db, FRESH, record.id, kind="reverify", at=due, due_at=due)
    headers = await login_headers(FRESH)
    tables = (LocationEvent, Notification, AlertReceipt, AuditLog, Attendance)
    before = [await count(db, table) for table in tables]

    response = await client.get("/api/v1/attendance/today", headers=headers)

    assert response.status_code == 200
    assert response.json()["pending_reverification"] is None  # missed at read time
    assert [await count(db, table) for table in tables] == before
    anomaly = await db.scalar(
        select(LocationEvent.anomaly)
        .where(LocationEvent.id == slot.id)
        .execution_options(populate_existing=True)
    )
    assert anomaly is None


async def test_open_session_race_is_a_409(client, db, login_headers, monkeypatch) -> None:
    await add_attendance(db, FRESH, checked_in_at=datetime.now(UTC), agenda=[{"title": "A"}])

    async def no_open_session(*_args: object) -> None:
        return None  # the concurrent request has not committed yet when we look

    monkeypatch.setattr(attendance_service, "open_session", no_open_session)
    response = await client.post(
        "/api/v1/attendance/check-in",
        headers=await login_headers(FRESH) | {"Idempotency-Key": "race"},
        json=CHECK_IN,
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Anda masih memiliki sesi kehadiran yang terbuka"


async def test_check_in_replay_returns_the_first_attendance(client, db, login_headers) -> None:
    headers = await login_headers(FRESH) | {"Idempotency-Key": "replay"}
    before = await count(db, Attendance)

    first = await client.post("/api/v1/attendance/check-in", headers=headers, json=CHECK_IN)
    second = await client.post("/api/v1/attendance/check-in", headers=headers, json=CHECK_IN)

    assert first.status_code == 200
    assert second.json() == {"id": first.json()["id"], "idempotent": True}
    assert await count(db, Attendance) == before + 1
