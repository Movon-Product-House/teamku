from datetime import UTC, datetime, timedelta

import pytest
from helpers import location_events, set_employee, set_office_policy
from sqlalchemy import select, update

from movon_hr.modules.attendance.alerts import evaluate_tenant
from movon_hr.modules.attendance.models import LocationEvent
from movon_hr.seed import OFFICE_LATITUDE, OFFICE_LONGITUDE

pytestmark = pytest.mark.anyio


async def enable_immediate_reverify(db, *, count: int = 1) -> None:
    await set_office_policy(
        db,
        reverify_enabled=True,
        reverify_count_per_day=count,
        reverify_window_start_minutes=0,
        reverify_window_end_minutes=1,
    )


@pytest.fixture
def check_in(client, login_headers):
    async def post(email: str, key: str, **overrides: object):
        payload = {
            "latitude": OFFICE_LATITUDE,
            "longitude": OFFICE_LONGITUDE,
            "accuracy_meters": 10,
            "selfie_captured": True,
            "location_share_approved": True,
            "agenda": [{"title": "Reverify flow"}],
        }
        payload.update(overrides)
        return await client.post(
            "/api/v1/attendance/check-in",
            headers=await login_headers(email) | {"Idempotency-Key": key},
            json=payload,
        )

    return post


async def reverify_slots(db, email: str) -> list[LocationEvent]:
    return [item for item in await location_events(db, email) if item.kind == "reverify"]


async def test_office_worker_gets_scheduled_reverify_when_enabled(
    client, db, login_headers, check_in
) -> None:
    await enable_immediate_reverify(db, count=2)

    response = await check_in("fresh@movon.test", "reverify-on")
    assert response.status_code == 200

    today = (
        await client.get(
            "/api/v1/attendance/today", headers=await login_headers("fresh@movon.test")
        )
    ).json()
    assert today["pending_reverification"] is not None
    slots = await reverify_slots(db, "fresh@movon.test")
    assert len(slots) == 2


async def test_remote_worker_never_gets_pending_reverify(
    client, db, login_headers, check_in
) -> None:
    await enable_immediate_reverify(db)
    await set_employee(db, "fresh@movon.test", is_remote=True)

    response = await check_in("fresh@movon.test", "remote-skip", latitude=-6.3)
    assert response.status_code == 200

    today = (
        await client.get(
            "/api/v1/attendance/today", headers=await login_headers("fresh@movon.test")
        )
    ).json()
    assert today["pending_reverification"] is None
    assert today["is_remote"] is True


async def test_outside_geofence_reverify_is_recorded_with_anomaly(
    client, db, login_headers, check_in
) -> None:
    await enable_immediate_reverify(db)
    assert (await check_in("fresh@movon.test", "outside-reverify")).status_code == 200

    submitted = await client.post(
        "/api/v1/attendance/reverify",
        headers=await login_headers("fresh@movon.test"),
        json={
            "latitude": -6.3,
            "longitude": 106.8166,
            "accuracy_meters": 12,
            "selfie_captured": True,
        },
    )
    assert submitted.status_code == 200
    assert submitted.json()["anomaly"] == "outside_geofence"
    assert submitted.json()["inside_geofence"] is False

    today = (
        await client.get(
            "/api/v1/attendance/today", headers=await login_headers("fresh@movon.test")
        )
    ).json()
    assert today["pending_reverification"] is None


async def test_successful_reverify_clears_pending_and_writes_event(
    client, db, login_headers, check_in
) -> None:
    await enable_immediate_reverify(db)
    assert (await check_in("fresh@movon.test", "ok-reverify")).status_code == 200

    submitted = await client.post(
        "/api/v1/attendance/reverify",
        headers=await login_headers("fresh@movon.test"),
        json={
            "latitude": OFFICE_LATITUDE,
            "longitude": OFFICE_LONGITUDE,
            "accuracy_meters": 10,
            "selfie_captured": True,
        },
    )
    assert submitted.status_code == 200
    assert submitted.json()["anomaly"] is None
    assert submitted.json()["kind"] == "reverify"
    assert submitted.json()["result"] == "verified"

    today = (
        await client.get(
            "/api/v1/attendance/today", headers=await login_headers("fresh@movon.test")
        )
    ).json()
    assert today["pending_reverification"] is None


async def test_missed_deadline_creates_missed_reverify_anomaly(
    client, db, login_headers, check_in
) -> None:
    await enable_immediate_reverify(db)
    assert (await check_in("fresh@movon.test", "missed-reverify")).status_code == 200
    slot = (await reverify_slots(db, "fresh@movon.test"))[0]
    due_at = datetime.now(UTC) - timedelta(minutes=20)
    await db.execute(
        update(LocationEvent).where(LocationEvent.id == slot.id).values(due_at=due_at, at=due_at)
    )
    await db.commit()

    today = (
        await client.get(
            "/api/v1/attendance/today", headers=await login_headers("fresh@movon.test")
        )
    ).json()
    assert today["pending_reverification"] is None
    # GET is a pure read now; the attendance-alerts job writes the anomaly (plan R1).
    await evaluate_tenant(db, datetime.now(UTC))
    await db.commit()
    refreshed = await db.scalar(select(LocationEvent.anomaly).where(LocationEvent.id == slot.id))
    assert refreshed == "missed_reverify"
