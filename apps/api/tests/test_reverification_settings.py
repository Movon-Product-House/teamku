import pytest
from helpers import office, set_office_policy

from movon_hr.seed import OFFICE_LATITUDE, OFFICE_LONGITUDE

pytestmark = pytest.mark.anyio


def office_payload(**overrides: object) -> dict:
    payload = {
        "name": "Jakarta HQ",
        "latitude": OFFICE_LATITUDE,
        "longitude": OFFICE_LONGITUDE,
        "radius_meters": 300,
        "reverify_enabled": True,
        "reverify_count_per_day": 2,
        "reverify_window_start_minutes": 0,
        "reverify_window_end_minutes": 120,
    }
    payload.update(overrides)
    return payload


async def test_hr_can_enable_reverify_policy_from_settings(client, login_headers) -> None:
    response = await client.put(
        "/api/v1/settings/office",
        headers=await login_headers("hr@movon.test"),
        json=office_payload(),
    )

    assert response.status_code == 200
    assert response.json()["reverify_enabled"] is True
    assert response.json()["reverify_count_per_day"] == 2
    fetched = await client.get(
        "/api/v1/settings/office", headers=await login_headers("hr@movon.test")
    )
    assert fetched.json()["reverify_count_per_day"] == 2


async def test_invalid_reverify_count_is_rejected(client, db, login_headers) -> None:
    response = await client.put(
        "/api/v1/settings/office",
        headers=await login_headers("hr@movon.test"),
        json=office_payload(reverify_count_per_day=4),
    )

    assert response.status_code == 422
    assert (await office(db)).reverify_enabled is False


async def test_manager_cannot_update_attendance_policy(client, db, login_headers) -> None:
    response = await client.put(
        "/api/v1/settings/office",
        headers=await login_headers("manager@movon.test"),
        json=office_payload(),
    )

    assert response.status_code == 403
    assert (await office(db)).reverify_enabled is False


async def test_disabled_policy_does_not_schedule_pending_reverify(
    client, db, login_headers
) -> None:
    await set_office_policy(db, reverify_enabled=False)

    checked_in = await client.post(
        "/api/v1/attendance/check-in",
        headers=await login_headers("fresh@movon.test") | {"Idempotency-Key": "policy-off"},
        json={
            "latitude": OFFICE_LATITUDE,
            "longitude": OFFICE_LONGITUDE,
            "accuracy_meters": 10,
            "selfie_captured": True,
            "location_share_approved": True,
            "agenda": [{"title": "Tanpa reverify"}],
        },
    )
    assert checked_in.status_code == 200

    today = await client.get(
        "/api/v1/attendance/today", headers=await login_headers("fresh@movon.test")
    )
    assert today.status_code == 200
    assert today.json()["pending_reverification"] is None
