import re
from datetime import UTC, datetime, timedelta
from secrets import token_urlsafe
from typing import Any

import httpx
from fastapi import HTTPException, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from movon_hr.core.identity import Employee
from movon_hr.core.settings import settings
from movon_hr.modules.audit.service import audit
from movon_hr.modules.settings import google_calendar, maps
from movon_hr.modules.settings.models import CalendarSettings, OAuthState, WorkLocation
from movon_hr.modules.settings.schemas import (
    HHMM,
    CalendarSettingsInput,
    GoogleCalendarOut,
    MapsCoordinates,
    OfficeSettingsInput,
    WorkLocationInput,
)

OAUTH_STATE_TTL = timedelta(minutes=10)
POLICY_FIELDS = (
    "name",
    "latitude",
    "longitude",
    "radius_meters",
    "reverify_enabled",
    "reverify_count_per_day",
    "reverify_window_start_minutes",
    "reverify_window_end_minutes",
    "alerts_enabled",
    "clock_in_reminder_time",
    "clock_out_reminder_time",
    "max_open_hours",
    "alert_managers",
)


# --- Work locations and the office policy (held by the primary location) ---


async def list_locations(db: AsyncSession) -> list[WorkLocation]:
    """Primary first, then creation order; same name + coordinates are listed once."""
    found = await db.scalars(
        select(WorkLocation).order_by(WorkLocation.is_primary.desc(), WorkLocation.id)
    )
    unique: dict[tuple[str, float, float], WorkLocation] = {}
    for item in found:
        key = (item.name.strip().casefold(), round(item.latitude, 6), round(item.longitude, 6))
        unique.setdefault(key, item)
    return list(unique.values())


async def create_location(
    db: AsyncSession, user: Employee, payload: WorkLocationInput
) -> WorkLocation:
    name = payload.name.strip().casefold()
    for item in await db.scalars(select(WorkLocation).order_by(WorkLocation.id)):
        same_place = (
            abs(item.latitude - payload.latitude) < 0.000001
            and abs(item.longitude - payload.longitude) < 0.000001
        )
        if item.name.strip().casefold() == name or same_place:
            raise HTTPException(409, f"Lokasi {item.name} sudah terdaftar")
    # Additional locations get the default policy (reverify off), see plan note 1.
    location = WorkLocation(**payload.model_dump())
    db.add(location)
    await db.flush()
    await audit(db, "settings.location_created", user, str(location.id))
    return location


async def primary_location(db: AsyncSession) -> WorkLocation:
    return (await db.scalars(select(WorkLocation).where(WorkLocation.is_primary))).one()


def validate_office_policy(data: dict[str, Any]) -> None:
    """Checks on the merged policy (the input model only sees the fields that were sent)."""
    if data["reverify_count_per_day"] not in {1, 2, 3}:
        raise HTTPException(422, "Jumlah re-verifikasi per hari harus 1, 2, atau 3")
    start = data["reverify_window_start_minutes"]
    end = data["reverify_window_end_minutes"]
    if not 0 <= start <= 1_440 or not 0 <= end <= 1_440:
        raise HTTPException(422, "Jendela re-verifikasi harus antara 0 dan 1440 menit")
    if end <= start:
        raise HTTPException(422, "Jendela akhir harus lebih besar dari jendela mulai")
    for key in ("clock_in_reminder_time", "clock_out_reminder_time"):
        if not re.fullmatch(HHMM, str(data[key])):
            raise HTTPException(422, "Format jam pengingat harus HH:MM")
    if not 1 <= data["max_open_hours"] <= 24:
        raise HTTPException(422, "Batas sesi terbuka harus antara 1 dan 24 jam")


async def update_office(
    db: AsyncSession, user: Employee, payload: OfficeSettingsInput
) -> WorkLocation:
    office = await primary_location(db)
    merged = {field: getattr(office, field) for field in POLICY_FIELDS}
    # An explicit null keeps the current value (the columns are NOT NULL).
    merged.update(payload.model_dump(exclude_unset=True, exclude_none=True))
    validate_office_policy(merged)
    for field, value in merged.items():
        setattr(office, field, value)
    await audit(db, "settings.office_updated", user, office.name)
    return office


async def coordinates_from_maps(db: AsyncSession, user: Employee, url: str) -> MapsCoordinates:
    source = url.strip()
    resolved = source
    if maps.is_short_link(source):
        try:
            resolved = await maps.resolve_short_link(maps.with_scheme(source))
        except (httpx.HTTPError, httpx.InvalidURL, ValueError) as error:
            raise HTTPException(
                422,
                "Tautan singkat Google Maps tidak dapat dibuka. Salin URL lengkap dari bilah "
                "alamat setelah membuka tautan.",
            ) from error
    coords = maps.parse_location(resolved) or maps.parse_location(source)
    if not coords:
        raise HTTPException(
            422,
            "Koordinat tidak ditemukan. Tempel tautan Google Maps (Share) atau teks seperti "
            "-6.2, 106.8166.",
        )
    latitude, longitude = coords
    await audit(db, "settings.office_maps_parsed", user, f"{latitude},{longitude}")
    return MapsCoordinates(
        latitude=latitude,
        longitude=longitude,
        resolved_url=resolved,
        maps_url=f"https://www.google.com/maps?q={latitude},{longitude}",
    )


# --- Calendar settings and Google OAuth ---


async def get_calendar(db: AsyncSession) -> CalendarSettings:
    """Every tenant has one row (seed, signup)."""
    return (await db.scalars(select(CalendarSettings))).one()


async def update_calendar(
    db: AsyncSession, user: Employee, payload: CalendarSettingsInput
) -> CalendarSettings:
    calendar = await get_calendar(db)
    # OAuth tokens are kept.
    calendar.provider = payload.provider
    calendar.connected = payload.connected
    calendar.team_calendar_id = payload.team_calendar_id.strip()
    calendar.calendar_name = payload.calendar_name.strip() or "Kalender perusahaan"
    calendar.scope = payload.scope
    calendar.division = payload.division.strip()
    calendar.delivery_mode = payload.delivery_mode
    await audit(db, "settings.calendar_updated", user, calendar.team_calendar_id)
    return calendar


async def start_google(db: AsyncSession, user: Employee) -> str:
    if not settings.google_client_id:
        raise HTTPException(503, "Google Calendar belum dikonfigurasi oleh administrator sistem")
    state = token_urlsafe(32)
    db.add(
        OAuthState(state=state, employee_id=user.id, expires_at=datetime.now(UTC) + OAUTH_STATE_TTL)
    )
    return google_calendar.authorization_url(state)


async def finish_google(
    db: AsyncSession, code: str | None, state: str | None, error: str | None
) -> Response:
    """OAuth callback: no session, so the tenant comes from the state row (cross-tenant)."""
    if error or not code or not state:
        return Response("Google Calendar connection was cancelled.", status_code=400)
    pending = await db.scalar(
        select(OAuthState).where(OAuthState.state == state).execution_options(cross_tenant=True)
    )
    if pending is not None:
        await db.delete(pending)  # single use, also when the exchange below fails
    if (
        pending is None
        or pending.expires_at <= datetime.now(UTC)
        or not settings.google_client_id
        or not settings.google_client_secret
    ):
        return Response("Google Calendar connection expired or is not configured.", status_code=400)
    db.info["tenant_id"] = pending.tenant_id
    try:
        tokens = await google_calendar.token_request(
            {
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": google_calendar.redirect_uri(),
                "grant_type": "authorization_code",
            }
        )
    except (httpx.HTTPError, ValueError):  # network, non-2xx, or a body that is not JSON
        return Response("Google Calendar token exchange failed.", status_code=502)
    if not tokens.get("access_token"):
        return Response("Google Calendar did not return an access token.", status_code=502)
    calendar = await get_calendar(db)
    calendar.provider = "google"
    calendar.connected = True
    calendar.refresh_token = tokens.get("refresh_token") or calendar.refresh_token
    google_calendar.store_tokens(calendar, tokens)
    return Response(
        status_code=302,
        headers={
            "Location": f"{settings.app_base_url.rstrip('/')}/app/settings?calendar=connected"
        },
    )


async def list_google_calendars(db: AsyncSession) -> list[GoogleCalendarOut]:
    calendar = await get_calendar(db)
    if not calendar.access_token:
        raise HTTPException(409, "Hubungkan akun Google terlebih dahulu")
    try:
        data = await google_calendar.calendar_request(
            calendar,
            "GET",
            "https://www.googleapis.com/calendar/v3/users/me/calendarList?minAccessRole=writer",
        )
    except Exception as error:
        raise HTTPException(502, "Daftar kalender Google tidak dapat diambil") from error
    return [
        GoogleCalendarOut(
            id=item["id"],
            name=item.get("summary") or item["id"],
            primary=item.get("primary", False),
        )
        for item in data.get("items", [])
    ]
