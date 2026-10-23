"""U6: settings module (work locations, office policy, maps parsing, Google OAuth)."""

from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from fastapi import HTTPException
from sqlalchemy import select

from movon_hr.core.settings import settings
from movon_hr.modules.settings import google_calendar, maps, service
from movon_hr.modules.settings.models import CalendarSettings, OAuthState

FRESH = {"populate_existing": True}


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("-6.200000, 106.816600", (-6.2, 106.8166)),
        ("https://www.google.com/maps/place/X/data=!3d-6.1754!4d106.8272", (-6.1754, 106.8272)),
        (
            "https://www.google.com/maps/place/Monas/@-6.175392,106.827153,17z",
            (-6.175392, 106.827153),
        ),
        ("https://www.google.com/maps?q=-6.2%2C106.8166", (-6.2, 106.8166)),
        ("maps.google.com/?ll=1.5,2.5&z=3", (1.5, 2.5)),
        ("lokasi kantor 1.25, 3.5 dekat stasiun", (1.25, 3.5)),
        ("91, 10", None),
        ("   ", None),
        ("https://www.google.com/maps/place/Monas", None),
    ],
)
def test_parse_location(text: str, expected: tuple[float, float] | None) -> None:
    assert maps.parse_location(text) == expected


def test_short_link_detection() -> None:
    assert maps.is_short_link("maps.app.goo.gl/abc")
    assert maps.is_short_link("https://goo.gl/maps/abc")
    assert not maps.is_short_link("https://www.google.com/maps?q=1,2")


POLICY = {
    "reverify_count_per_day": 1,
    "reverify_window_start_minutes": 60,
    "reverify_window_end_minutes": 420,
    "clock_in_reminder_time": "09:15",
    "clock_out_reminder_time": "18:15",
    "max_open_hours": 10,
    "work_start_time": "09:00",
}


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"reverify_count_per_day": 4}, "Jumlah re-verifikasi per hari harus 1, 2, atau 3"),
        (
            {"reverify_window_end_minutes": 1_441},
            "Jendela re-verifikasi harus antara 0 dan 1440 menit",
        ),
        ({"reverify_window_end_minutes": 60}, "Jendela akhir harus lebih besar dari jendela mulai"),
        ({"clock_out_reminder_time": "24:00"}, "Format jam pengingat harus HH:MM"),
        ({"max_open_hours": 25}, "Batas sesi terbuka harus antara 1 dan 24 jam"),
        ({"work_start_time": "9:00"}, "Format jam mulai kerja harus HH:MM"),
    ],
)
def test_office_policy_validation(overrides: dict, message: str) -> None:
    service.validate_office_policy(POLICY)
    with pytest.raises(HTTPException) as raised:
        service.validate_office_policy(POLICY | overrides)
    assert (raised.value.status_code, raised.value.detail) == (422, message)


@pytest.mark.anyio
async def test_additional_location_gets_default_policy_and_is_listed_after_primary(
    client, login_headers
) -> None:
    hr = await login_headers("hr@movon.test")
    created = await client.post(
        "/api/v1/settings/locations",
        headers=hr,
        json={"name": "Bandung Site", "latitude": -6.9175, "longitude": 107.6191},
    )
    assert created.status_code == 200
    assert created.json()["is_primary"] is False
    assert created.json()["reverify_enabled"] is False
    assert created.json()["radius_meters"] == 300

    items = (await client.get("/api/v1/settings/locations", headers=hr)).json()["items"]
    assert [(item["name"], item["is_primary"]) for item in items] == [
        ("Jakarta HQ", True),
        ("Bandung Site", False),
    ]


@pytest.mark.anyio
async def test_unreachable_short_link_is_422(client, login_headers, monkeypatch) -> None:
    async def fail(url: str) -> str:
        raise httpx.ConnectError("offline")

    monkeypatch.setattr(maps, "resolve_short_link", fail)
    response = await client.post(
        "/api/v1/settings/office/from-maps-url",
        headers=await login_headers("hr@movon.test"),
        json={"url": "maps.app.goo.gl/abc"},
    )
    assert response.status_code == 422
    assert response.json()["detail"].startswith("Tautan singkat Google Maps tidak dapat dibuka")


@pytest.fixture
def google_configured(monkeypatch: pytest.MonkeyPatch) -> list[dict]:
    monkeypatch.setattr(settings, "google_client_id", "client-id")
    monkeypatch.setattr(settings, "google_client_secret", "client-secret")
    exchanges: list[dict] = []

    async def fake_token_request(values: dict[str, str]) -> dict:
        exchanges.append(values)
        return {"access_token": "access-1", "refresh_token": "refresh-1", "expires_in": 3600}

    monkeypatch.setattr(google_calendar, "token_request", fake_token_request)
    return exchanges


@pytest.mark.anyio
async def test_google_oauth_state_round_trip(client, db, login_headers, google_configured) -> None:
    started = await client.get(
        "/api/v1/settings/calendar/google/start", headers=await login_headers("hr@movon.test")
    )
    assert started.status_code == 200
    state = parse_qs(urlparse(started.json()["authorization_url"]).query)["state"][0]
    assert await db.scalar(select(OAuthState).where(OAuthState.state == state)) is not None

    # Google redirects the browser here: no session, the tenant comes from the state row.
    callback = await client.get(
        "/api/v1/settings/calendar/google/callback", params={"code": "auth-code", "state": state}
    )
    assert callback.status_code == 302
    assert callback.headers["location"].endswith("/app/settings?calendar=connected")
    assert google_configured[0]["code"] == "auth-code"
    calendar = await db.scalar(select(CalendarSettings).execution_options(**FRESH))
    assert calendar is not None
    assert (calendar.provider, calendar.connected) == ("google", True)
    assert (calendar.access_token, calendar.refresh_token) == ("access-1", "refresh-1")
    assert await db.scalar(select(OAuthState).where(OAuthState.state == state)) is None

    replay = await client.get(
        "/api/v1/settings/calendar/google/callback", params={"code": "auth-code", "state": state}
    )
    assert replay.status_code == 400


@pytest.mark.anyio
async def test_google_oauth_expired_state_is_rejected(
    client, db, login_headers, google_configured
) -> None:
    hr = await login_headers("hr@movon.test")
    await client.get("/api/v1/settings/calendar/google/start", headers=hr)
    pending = await db.scalar(select(OAuthState))
    assert pending is not None
    pending.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    await db.commit()

    callback = await client.get(
        "/api/v1/settings/calendar/google/callback",
        params={"code": "auth-code", "state": pending.state},
    )
    assert callback.status_code == 400
    assert callback.text == "Google Calendar connection expired or is not configured."
    assert google_configured == []
