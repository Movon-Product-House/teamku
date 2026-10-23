from datetime import UTC, datetime, timedelta

import pytest
from helpers import add_attendance

from movon_hr.core.time import jakarta_date
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
        "closed_hours_today": 0,
        "sessions_today": [],
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


async def test_today_sums_the_hours_of_every_closed_session_today(
    client, db, login_headers
) -> None:
    now = datetime.now(UTC)
    if jakarta_date(now - timedelta(minutes=10)) != jakarta_date(now):
        pytest.skip("needs ten minutes of today behind us")
    for start, end in [(10, 7), (6, 3)]:
        await add_attendance(
            db,
            "fresh@movon.test",
            checked_in_at=now - timedelta(minutes=start),
            checked_out_at=now - timedelta(minutes=end),
            agenda=[{}],
        )
    await add_attendance(
        db, "fresh@movon.test", checked_in_at=now - timedelta(minutes=2), agenda=[{}]
    )

    response = await client.get(
        "/api/v1/attendance/today", headers=await login_headers("fresh@movon.test")
    )

    assert response.json()["state"] == "checked_in"
    assert response.json()["closed_hours_today"] == 0.1


async def test_today_lists_every_session_today_in_order(client, db, login_headers) -> None:
    now = datetime.now(UTC).replace(microsecond=0)
    await add_attendance(
        db,
        "fresh@movon.test",
        checked_in_at=now - timedelta(minutes=10),
        checked_out_at=now - timedelta(minutes=7),
        agenda=[{}],
    )
    await add_attendance(
        db, "fresh@movon.test", checked_in_at=now - timedelta(minutes=2), agenda=[{}]
    )

    response = await client.get(
        "/api/v1/attendance/today", headers=await login_headers("fresh@movon.test")
    )

    spans = [
        [
            datetime.fromisoformat(item["checked_in_at"]),
            item["checked_out_at"] and datetime.fromisoformat(item["checked_out_at"]),
        ]
        for item in response.json()["sessions_today"]
    ]
    assert spans == [
        [now - timedelta(minutes=10), now - timedelta(minutes=7)],
        [now - timedelta(minutes=2), None],
    ]


async def test_check_out_reports_the_session_and_the_total_today(client, db, login_headers) -> None:
    now = datetime.now(UTC)
    await add_attendance(
        db,
        "fresh@movon.test",
        checked_in_at=now - timedelta(minutes=10),
        checked_out_at=now - timedelta(minutes=7),
        agenda=[{}],
    )
    await add_attendance(
        db, "fresh@movon.test", checked_in_at=now - timedelta(minutes=6), agenda=[{}]
    )

    response = await client.post(
        "/api/v1/attendance/check-out",
        headers=await login_headers("fresh@movon.test"),
        json={"summary": "Selesai"},
    )

    assert response.json()["effective_hours"] == 0.1
    assert response.json()["total_hours_today"] == 0.15


async def test_overnight_check_out_reports_the_full_session_in_the_total(
    client, db, login_headers, clock
) -> None:
    # Wednesday: a 17:00-18:00 WIB session, then a night shift from 20:00 WIB.
    for check_in, check_out in [(10, 11), (13, None)]:
        await add_attendance(
            db,
            "fresh@movon.test",
            checked_in_at=datetime(2026, 10, 21, check_in, tzinfo=UTC),
            checked_out_at=check_out and datetime(2026, 10, 21, check_out, tzinfo=UTC),
            agenda=[{}],
        )
    clock.move_to(datetime(2026, 10, 21, 19, tzinfo=UTC))  # 02:00 WIB Thursday

    response = await client.post(
        "/api/v1/attendance/check-out",
        headers=await login_headers("fresh@movon.test"),
        json={"summary": "Shift malam"},
    )

    # The night shift counts in full, past midnight, and the total adds Wednesday's hour.
    assert response.json()["effective_hours"] == 6.0
    assert response.json()["total_hours_today"] == 7.0
