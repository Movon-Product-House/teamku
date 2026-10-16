from datetime import UTC, datetime, timedelta

import pytest
from helpers import add_attendance

from movon_hr.seed import OFFICE_LATITUDE, OFFICE_LONGITUDE, OFFICE_RADIUS_METERS

pytestmark = pytest.mark.anyio


def check_in_payload(**overrides: object) -> dict:
    payload = {
        "latitude": OFFICE_LATITUDE,
        "longitude": OFFICE_LONGITUDE,
        "accuracy_meters": 10,
        "selfie_captured": True,
        "location_share_approved": True,
        "agenda": [{"title": "Kerja di kantor"}],
    }
    payload.update(overrides)
    return payload


async def test_fresh_demo_account_starts_without_a_check_in(client, login_headers) -> None:
    response = await client.get(
        "/api/v1/attendance/today", headers=await login_headers("fresh@movon.test")
    )

    assert response.status_code == 200
    assert response.json() == {
        "state": "not_checked_in",
        "session": None,
        "pending_reverification": None,
        "is_remote": False,
    }


async def test_check_in_requires_location_sharing_approval(client, login_headers) -> None:
    response = await client.post(
        "/api/v1/attendance/check-in",
        headers=await login_headers("fresh@movon.test")
        | {"Idempotency-Key": "location-consent-test"},
        json=check_in_payload(
            location_share_approved=False, agenda=[{"title": "Konfirmasi lokasi"}]
        ),
    )

    assert response.status_code == 422
    assert "persetujuan" in response.json()["detail"].lower()


async def test_check_in_succeeds_inside_office_geofence(client, login_headers) -> None:
    response = await client.post(
        "/api/v1/attendance/check-in",
        headers=await login_headers("fresh@movon.test") | {"Idempotency-Key": "inside-geofence"},
        json=check_in_payload(),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["anomaly"] is None
    assert body["distance_meters"] == 0
    assert body["allowed_radius_meters"] == OFFICE_RADIUS_METERS + 10


async def test_check_in_rejects_location_far_from_office(client, login_headers) -> None:
    # Roughly ~11 km south of Jakarta HQ — typical "check-in from home" attempt.
    response = await client.post(
        "/api/v1/attendance/check-in",
        headers=await login_headers("fresh@movon.test") | {"Idempotency-Key": "outside-geofence"},
        json=check_in_payload(latitude=-6.3, longitude=106.8166),
    )

    assert response.status_code == 403
    detail = response.json()["detail"].lower()
    assert "ditolak" in detail
    assert "radius" in detail
    assert str(OFFICE_RADIUS_METERS) in detail


async def test_check_in_rejects_inflated_accuracy_used_to_bypass_geofence(
    client, login_headers
) -> None:
    # ~550 m away: would pass if accuracy_meters were added uncapped (300 + 500).
    response = await client.post(
        "/api/v1/attendance/check-in",
        headers=await login_headers("fresh@movon.test") | {"Idempotency-Key": "accuracy-bypass"},
        json=check_in_payload(latitude=-6.205, longitude=106.8166, accuracy_meters=500),
    )

    assert response.status_code == 403
    assert "ditolak" in response.json()["detail"].lower()


async def test_today_returns_active_session_instead_of_offering_second_check_in(
    client, db, login_headers
) -> None:
    record = await add_attendance(
        db,
        "employee@movon.test",
        checked_in_at=datetime.now(UTC),
        accuracy_meters=12,
        agenda=[{"title": "Test agenda"}],
    )

    response = await client.get(
        "/api/v1/attendance/today", headers=await login_headers("employee@movon.test")
    )

    assert response.status_code == 200
    assert response.json()["state"] == "checked_in"
    assert response.json()["session"]["id"] == str(record.id)


async def test_check_in_rejects_an_open_session_from_a_prior_day(client, db, login_headers) -> None:
    await add_attendance(
        db,
        "employee@movon.test",
        checked_in_at=datetime.now(UTC) - timedelta(days=1),
        accuracy_meters=12,
        agenda=[{"title": "Agenda kemarin"}],
    )

    response = await client.post(
        "/api/v1/attendance/check-in",
        headers=await login_headers("employee@movon.test") | {"Idempotency-Key": "prior-day-test"},
        json=check_in_payload(agenda=[{"title": "Agenda baru"}]),
    )

    assert response.status_code == 409
    assert "sesi kehadiran" in response.json()["detail"]
