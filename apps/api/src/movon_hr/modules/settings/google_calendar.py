"""Google OAuth and Calendar API over httpx; tokens live on ``CalendarSettings``."""

from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlencode

import httpx

from movon_hr.core.settings import settings
from movon_hr.modules.settings.models import CalendarSettings

SCOPE = "https://www.googleapis.com/auth/calendar"
TIMEOUT = 15


def redirect_uri() -> str:
    return (
        settings.google_redirect_uri
        or f"{settings.app_base_url.rstrip('/')}/api/v1/settings/calendar/google/callback"
    )


def authorization_url(state: str) -> str:
    query = urlencode(
        {
            "client_id": settings.google_client_id,
            "redirect_uri": redirect_uri(),
            "response_type": "code",
            "scope": SCOPE,
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        }
    )
    return f"https://accounts.google.com/o/oauth2/v2/auth?{query}"


async def token_request(values: dict[str, str]) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.post("https://oauth2.googleapis.com/token", data=values)
        response.raise_for_status()
        return response.json()


def store_tokens(calendar: CalendarSettings, tokens: dict[str, Any]) -> None:
    calendar.access_token = tokens["access_token"]
    calendar.token_expires_at = datetime.now(UTC) + timedelta(
        seconds=int(tokens.get("expires_in", 3600))
    )


async def access_token(calendar: CalendarSettings) -> str:
    """The stored access token, refreshed when it expires within a minute."""
    expires_at = calendar.token_expires_at
    if (
        calendar.access_token
        and expires_at
        and datetime.now(UTC) < expires_at - timedelta(minutes=1)
    ):
        return calendar.access_token
    if (
        not calendar.refresh_token
        or not settings.google_client_id
        or not settings.google_client_secret
    ):
        raise ValueError("Google Calendar is not connected")
    tokens = await token_request(
        {
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "refresh_token": calendar.refresh_token,
            "grant_type": "refresh_token",
        }
    )
    store_tokens(calendar, tokens)
    return tokens["access_token"]


async def calendar_request(
    calendar: CalendarSettings, method: str, url: str, body: dict[str, Any] | None = None
) -> dict[str, Any]:
    token = await access_token(calendar)
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.request(
            method, url, json=body, headers={"Authorization": f"Bearer {token}"}
        )
        response.raise_for_status()
        return response.json() if response.content else {}
