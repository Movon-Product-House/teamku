import pytest
from helpers import office, set_office_policy

from movon_hr.seed import OFFICE_LATITUDE, OFFICE_LONGITUDE, OFFICE_RADIUS_METERS

pytestmark = pytest.mark.anyio


async def test_any_user_can_read_office_settings(client, login_headers) -> None:
    response = await client.get(
        "/api/v1/settings/office", headers=await login_headers("fresh@movon.test")
    )

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Jakarta HQ"
    assert body["latitude"] == OFFICE_LATITUDE
    assert body["longitude"] == OFFICE_LONGITUDE
    assert body["radius_meters"] == OFFICE_RADIUS_METERS
    assert body["reverify_enabled"] is False
    assert body["alerts_enabled"] is False


async def test_employee_cannot_update_office_settings(client, db, login_headers) -> None:
    response = await client.put(
        "/api/v1/settings/office",
        headers=await login_headers("fresh@movon.test"),
        json={
            "name": "Rumah",
            "latitude": -6.3,
            "longitude": 106.8,
            "radius_meters": 1000,
        },
    )

    assert response.status_code == 403
    assert (await office(db)).name == "Jakarta HQ"


async def test_hr_admin_can_update_office_settings(client, db, login_headers) -> None:
    response = await client.put(
        "/api/v1/settings/office",
        headers=await login_headers("hr@movon.test"),
        json={
            "name": "Bandung Hub",
            "latitude": -6.9175,
            "longitude": 107.6191,
            "radius_meters": 200,
        },
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Bandung Hub"
    updated = await office(db)
    assert updated.latitude == -6.9175
    assert updated.radius_meters == 200


async def test_check_in_uses_configured_office_location(client, db, login_headers) -> None:
    await set_office_policy(
        db, name="Bandung Hub", latitude=-6.9175, longitude=107.6191, radius_meters=200
    )

    rejected = await client.post(
        "/api/v1/attendance/check-in",
        headers=await login_headers("fresh@movon.test") | {"Idempotency-Key": "old-hq"},
        json={
            "latitude": OFFICE_LATITUDE,
            "longitude": OFFICE_LONGITUDE,
            "accuracy_meters": 10,
            "selfie_captured": True,
            "location_share_approved": True,
            "agenda": [{"title": "Masih di Jakarta"}],
        },
    )
    assert rejected.status_code == 403
    assert "bandung hub" in rejected.json()["detail"].lower()

    accepted = await client.post(
        "/api/v1/attendance/check-in",
        headers=await login_headers("fresh@movon.test") | {"Idempotency-Key": "new-hub"},
        json={
            "latitude": -6.9175,
            "longitude": 107.6191,
            "accuracy_meters": 10,
            "selfie_captured": True,
            "location_share_approved": True,
            "agenda": [{"title": "Kerja di Bandung"}],
        },
    )
    assert accepted.status_code == 200
    assert accepted.json()["distance_meters"] == 0


async def test_hr_admin_can_parse_google_maps_share_link(client, login_headers) -> None:
    response = await client.post(
        "/api/v1/settings/office/from-maps-url",
        headers=await login_headers("hr@movon.test"),
        json={"url": "https://www.google.com/maps/place/Monas/@-6.175392,106.827153,17z"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["latitude"] == -6.175392
    assert body["longitude"] == 106.827153
    assert "google.com/maps" in body["maps_url"]


async def test_hr_admin_can_parse_raw_coordinates(client, login_headers) -> None:
    response = await client.post(
        "/api/v1/settings/office/from-maps-url",
        headers=await login_headers("hr@movon.test"),
        json={"url": "-6.200000, 106.816600"},
    )

    assert response.status_code == 200
    assert response.json()["latitude"] == -6.2
    assert response.json()["longitude"] == 106.8166


async def test_employee_cannot_parse_maps_url(client, login_headers) -> None:
    response = await client.post(
        "/api/v1/settings/office/from-maps-url",
        headers=await login_headers("fresh@movon.test"),
        json={"url": "https://www.google.com/maps?q=-6.2,106.8166"},
    )

    assert response.status_code == 403
