from typing import Annotated

from fastapi import APIRouter, Depends, Header

from movon_hr.core.auth import CurrentUser, require_role
from movon_hr.core.db import DB
from movon_hr.core.identity import Employee
from movon_hr.modules.attendance import service
from movon_hr.modules.attendance.schemas import (
    CheckIn,
    CheckInOut,
    CheckOut,
    CheckOutOut,
    IdempotentOut,
    LocationEventOut,
    LocationHistory,
    ReverifyInput,
    SkippedEventOut,
    SkippedOut,
    TodayOut,
    WeekOut,
)

router = APIRouter()
HrOrManager = Annotated[Employee, Depends(require_role("manager", "hr_admin"))]


@router.get("/attendance/today")
async def attendance_today(db: DB, user: CurrentUser) -> TodayOut:
    return await service.today(db, user)


@router.get("/attendance/week")
async def attendance_week(db: DB, user: CurrentUser) -> WeekOut:
    return await service.week(db, user)


@router.post("/attendance/check-in")
async def check_in(
    db: DB, user: CurrentUser, payload: CheckIn, idempotency_key: Annotated[str, Header()]
) -> CheckInOut | IdempotentOut:
    return await service.check_in(db, user, payload, idempotency_key)


@router.post("/attendance/check-out")
async def check_out(db: DB, user: CurrentUser, payload: CheckOut) -> CheckOutOut:
    return await service.check_out(db, user, payload)


@router.post("/attendance/reverify")
async def reverify(
    db: DB, user: CurrentUser, payload: ReverifyInput
) -> SkippedEventOut | LocationEventOut | SkippedOut:
    return await service.reverify(db, user, payload)


# Registered here because the data belongs to attendance (plan Target Structure).
@router.get("/employees/{employee_id}/location-history")
async def location_history(db: DB, user: HrOrManager, employee_id: str) -> LocationHistory:
    return await service.location_history(db, user, employee_id)
