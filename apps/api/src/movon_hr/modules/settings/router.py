from typing import Annotated

from fastapi import APIRouter, Depends, Response

from movon_hr.core.auth import CurrentUser, require_role
from movon_hr.core.db import DB
from movon_hr.core.identity import Employee
from movon_hr.modules.settings import service
from movon_hr.modules.settings.schemas import (
    AuthorizationUrlOut,
    CalendarOut,
    CalendarSettingsIn,
    GoogleCalendarListOut,
    LocationListOut,
    LocationOut,
    MapsCoordinatesOut,
    MapsUrlIn,
    OfficeSettingsIn,
    WorkLocationIn,
)

router = APIRouter(prefix="/settings", tags=["settings"])
HrAdmin = Annotated[Employee, Depends(require_role("hr_admin"))]


@router.get("/locations")
async def list_locations(db: DB, _: CurrentUser) -> LocationListOut:
    return LocationListOut.model_validate({"items": await service.list_locations(db)})


@router.post("/locations")
async def create_location(db: DB, user: HrAdmin, payload: WorkLocationIn) -> LocationOut:
    return LocationOut.model_validate(await service.create_location(db, user, payload))


@router.get("/office")
async def get_office(db: DB, _: CurrentUser) -> LocationOut:
    return LocationOut.model_validate(await service.primary_location(db))


@router.put("/office")
async def update_office(db: DB, user: HrAdmin, payload: OfficeSettingsIn) -> LocationOut:
    return LocationOut.model_validate(await service.update_office(db, user, payload))


@router.post("/office/from-maps-url")
async def office_from_maps_url(db: DB, user: HrAdmin, payload: MapsUrlIn) -> MapsCoordinatesOut:
    return await service.coordinates_from_maps(db, user, payload.url)


@router.get("/calendar")
async def get_calendar(db: DB, _: CurrentUser) -> CalendarOut:
    return CalendarOut.model_validate(await service.get_calendar(db))


@router.put("/calendar")
async def update_calendar(db: DB, user: HrAdmin, payload: CalendarSettingsIn) -> CalendarOut:
    return CalendarOut.model_validate(await service.update_calendar(db, user, payload))


@router.get("/calendar/google/start")
async def start_google_calendar(db: DB, user: HrAdmin) -> AuthorizationUrlOut:
    return AuthorizationUrlOut(authorization_url=await service.start_google(db, user))


@router.get("/calendar/google/callback", include_in_schema=False)
async def google_calendar_callback(
    db: DB, code: str | None = None, state: str | None = None, error: str | None = None
) -> Response:
    """The only non-JSON route: Google redirects the browser here."""
    return await service.finish_google(db, code, state, error)


@router.get("/calendar/google/calendars")
async def google_calendars(db: DB, _: HrAdmin) -> GoogleCalendarListOut:
    return GoogleCalendarListOut(items=await service.list_google_calendars(db))
