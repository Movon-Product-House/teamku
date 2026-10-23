import uuid
from datetime import UTC, date, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import ColumnElement, and_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from movon_hr.core.identity import Employee
from movon_hr.core.time import jakarta_date
from movon_hr.modules.attendance import rules
from movon_hr.modules.attendance.models import Attendance, IdempotencyKey, LocationEvent
from movon_hr.modules.attendance.schemas import (
    CheckInIn,
    CheckInOut,
    CheckOutIn,
    CheckOutOut,
    IdempotentOut,
    LocationEventOut,
    LocationHistoryOut,
    PendingOut,
    ReverifyIn,
    SessionOut,
    SessionSpanOut,
    SkippedEventOut,
    SkippedOut,
    TodayOut,
    VerifiedEventOut,
    WeekDayOut,
    WeekOut,
)
from movon_hr.modules.audit.service import audit
from movon_hr.modules.employees import service as employees_service
from movon_hr.modules.leave.models import LeaveRequest
from movon_hr.modules.settings import service as settings_service
from movon_hr.modules.settings.models import WorkLocation

OPEN_SESSION = "Anda masih memiliki sesi kehadiran yang terbuka"
NO_OPEN_SESSION = "Tidak ada sesi kehadiran terbuka"
SELFIE_REQUIRED = "Selfie kamera langsung wajib untuk kebijakan ini"


def open_slot() -> ColumnElement[bool]:
    """A reverify slot nobody answered yet and not marked missed."""
    return and_(
        LocationEvent.kind == "reverify",
        LocationEvent.lat.is_(None),
        LocationEvent.anomaly.is_distinct_from("missed_reverify"),
    )


async def office_for(db: AsyncSession, employee: Employee) -> WorkLocation:
    """The employee's work location; none or unknown falls back to the primary."""
    if employee.work_location_id is not None:
        found = await db.scalar(
            select(WorkLocation).where(WorkLocation.id == employee.work_location_id)
        )
        if found is not None:
            return found
    return await settings_service.primary_location(db)


async def sessions_on(db: AsyncSession, employee_id: uuid.UUID, day: date) -> list[Attendance]:
    start, end = rules.jakarta_day_bounds(day)
    found = await db.scalars(
        select(Attendance)
        .where(
            Attendance.employee_id == employee_id,
            Attendance.checked_in_at >= start,
            Attendance.checked_in_at < end,
        )
        .order_by(Attendance.checked_in_at)
    )
    return list(found)


async def open_session(db: AsyncSession, employee_id: uuid.UUID) -> Attendance | None:
    return await db.scalar(
        select(Attendance).where(
            Attendance.employee_id == employee_id, Attendance.checked_out_at.is_(None)
        )
    )


async def pending_slot(
    db: AsyncSession, attendance_id: uuid.UUID, now: datetime
) -> LocationEvent | None:
    """Earliest due slot still inside its grace period; past it, it counts as missed.

    Read-only: the job (and check-out) write the missed_reverify anomaly.
    """
    return await db.scalar(
        select(LocationEvent)
        .where(
            LocationEvent.attendance_id == attendance_id,
            open_slot(),
            LocationEvent.due_at <= now,
            LocationEvent.due_at > now - rules.REVERIFY_GRACE,
        )
        .order_by(LocationEvent.due_at)
        .limit(1)
    )


def worked_hours(session: Attendance, now: datetime) -> float:
    """Up to check-out (or now), but never past the end of the check-in day."""
    until = min(
        session.checked_out_at or now,
        rules.jakarta_day_bounds(jakarta_date(session.checked_in_at))[1],
    )
    return (until - session.checked_in_at).total_seconds() / 3600


async def today(db: AsyncSession, user: Employee) -> TodayOut:
    """Pure read."""
    sessions = await sessions_on(db, user.id, jakarta_date())
    if not sessions:
        return TodayOut(
            state="not_checked_in",
            session=None,
            pending_reverification=None,
            is_remote=user.is_remote,
            closed_hours_today=0,
            sessions_today=[],
        )
    latest = sessions[-1]
    now = datetime.now(UTC)
    pending = None
    if latest.checked_out_at is None:
        pending = await pending_slot(db, latest.id, now)
    closed = sum(worked_hours(item, now) for item in sessions if item.checked_out_at)
    return TodayOut(
        state="completed" if latest.checked_out_at else "checked_in",
        session=SessionOut(
            id=latest.id,
            checked_in_at=latest.checked_in_at,
            checked_out_at=latest.checked_out_at,
            anomaly=latest.anomaly,
            agenda_count=len(latest.agenda),
            agenda=latest.agenda,
            summary=latest.summary,
        ),
        pending_reverification=PendingOut.model_validate(pending) if pending else None,
        is_remote=user.is_remote,
        closed_hours_today=round(closed, 2),
        sessions_today=[SessionSpanOut.model_validate(item) for item in sessions],
    )


async def week(db: AsyncSession, user: Employee) -> WeekOut:
    """Monday to Friday of the current Jakarta week.

    Hours per day follow ``worked_hours``. A day is late when its first check-in is late.
    """
    today = jakarta_date()
    days = [today - timedelta(days=today.weekday() - offset) for offset in range(5)]
    start, _ = rules.jakarta_day_bounds(days[0])
    _, end = rules.jakarta_day_bounds(days[-1])
    sessions = await db.scalars(
        select(Attendance)
        .where(
            Attendance.employee_id == user.id,
            Attendance.checked_in_at >= start,
            Attendance.checked_in_at < end,
        )
        .order_by(Attendance.checked_in_at)
    )
    leaves = (
        await db.execute(
            select(LeaveRequest.start_date, LeaveRequest.end_date).where(
                LeaveRequest.employee_id == user.id,
                LeaveRequest.status == "approved",
                LeaveRequest.start_date <= days[-1],
                LeaveRequest.end_date >= days[0],
            )
        )
    ).all()
    office = await settings_service.primary_location(db)
    work_start = rules.parse_hhmm(office.work_start_time)
    now = datetime.now(UTC)
    hours = dict.fromkeys(days, 0.0)
    late: dict[date, bool] = {}
    for item in sessions:
        day = jakarta_date(item.checked_in_at)
        hours[day] += worked_hours(item, now)
        late.setdefault(day, rules.is_late(item.checked_in_at, work_start))
    return WeekOut(
        target_hours=rules.TARGET_HOURS_PER_DAY,
        days=[
            WeekDayOut(
                date=day,
                hours=round(hours[day], 2),
                late=late.get(day, False),
                on_leave=any(first <= day <= last for first, last in leaves),
            )
            for day in days
        ],
    )


def schedule_reverify_slots(db: AsyncSession, record: Attendance, office: WorkLocation) -> None:
    for offset in rules.reverify_offsets_minutes(
        office.reverify_count_per_day,
        office.reverify_window_start_minutes,
        office.reverify_window_end_minutes,
    ):
        due_at = record.checked_in_at + timedelta(minutes=offset)
        db.add(
            LocationEvent(
                employee_id=record.employee_id,
                attendance_id=record.id,
                kind="reverify",
                at=due_at,
                due_at=due_at,
            )
        )


async def check_in(
    db: AsyncSession, user: Employee, payload: CheckInIn, idempotency_key: str
) -> CheckInOut | IdempotentOut:
    replay = await db.scalar(
        select(IdempotencyKey.attendance_id).where(IdempotencyKey.key == idempotency_key)
    )
    if replay is not None:
        return IdempotentOut(id=replay, idempotent=True)
    if await open_session(db, user.id) is not None:
        raise HTTPException(409, OPEN_SESSION)
    if not payload.selfie_captured:
        raise HTTPException(422, SELFIE_REQUIRED)
    if not payload.location_share_approved:
        raise HTTPException(422, "Persetujuan berbagi lokasi diperlukan untuk check-in")
    office = await office_for(db, user)
    distance = rules.haversine_meters(
        payload.latitude, payload.longitude, office.latitude, office.longitude
    )
    allowed_radius = rules.allowed_check_in_radius_meters(
        office.radius_meters, payload.accuracy_meters
    )
    if not user.is_remote and distance > allowed_radius:
        raise HTTPException(
            403,
            (
                f"Check-in ditolak. Anda berada sekitar {round(distance)} m dari kantor. "
                f"Presensi hanya diizinkan dalam radius {round(office.radius_meters)} m "
                f"dari {office.name}."
            ),
        )
    anomaly = "low_accuracy" if payload.accuracy_meters > rules.LOW_ACCURACY_METERS else None
    record = Attendance(
        employee_id=user.id,
        checked_in_at=datetime.now(UTC),
        latitude=payload.latitude,
        longitude=payload.longitude,
        accuracy_meters=payload.accuracy_meters,
        agenda=[item.model_dump() for item in payload.agenda],
        anomaly=anomaly,
    )
    db.add(record)
    try:
        await db.flush()
    except IntegrityError as error:
        # A concurrent check-in won the one-open-session index.
        raise HTTPException(409, OPEN_SESSION) from error
    # A concurrent request with the same key already stored it: keep theirs.
    await db.execute(
        insert(IdempotencyKey)
        .values(tenant_id=user.tenant_id, key=idempotency_key, attendance_id=record.id)
        .on_conflict_do_nothing()
    )
    db.add(
        LocationEvent(
            employee_id=user.id,
            attendance_id=record.id,
            kind="check_in",
            at=record.checked_in_at,
            lat=payload.latitude,
            lng=payload.longitude,
            accuracy=payload.accuracy_meters,
            distance_meters=round(distance),
            inside_geofence=distance <= allowed_radius,
            anomaly=anomaly,
        )
    )
    if office.reverify_enabled and not user.is_remote:
        schedule_reverify_slots(db, record, office)
    await audit(db, "attendance.check_in", user, str(record.id))
    return CheckInOut(
        id=record.id,
        checked_in_at=record.checked_in_at,
        distance_meters=round(distance),
        allowed_radius_meters=round(allowed_radius),
        anomaly=anomaly,
        agenda_count=len(payload.agenda),
    )


async def check_out(db: AsyncSession, user: Employee, payload: CheckOutIn) -> CheckOutOut:
    record = await open_session(db, user.id)
    if record is None:
        raise HTTPException(409, NO_OPEN_SESSION)
    now = datetime.now(UTC)
    # Every slot still open is missed once the shift ends.
    await db.execute(
        update(LocationEvent)
        .where(LocationEvent.attendance_id == record.id, open_slot())
        .values(anomaly="missed_reverify", at=now)
    )
    record.checked_out_at = now
    record.summary = payload.summary
    distance = None
    inside = None
    if payload.latitude is not None and payload.longitude is not None:
        office = await office_for(db, user)
        distance = rules.haversine_meters(
            payload.latitude, payload.longitude, office.latitude, office.longitude
        )
        inside = user.is_remote or distance <= rules.allowed_check_in_radius_meters(
            office.radius_meters, payload.accuracy_meters or 0
        )
    db.add(
        LocationEvent(
            employee_id=user.id,
            attendance_id=record.id,
            kind="check_out",
            at=now,
            lat=payload.latitude,
            lng=payload.longitude,
            accuracy=payload.accuracy_meters,
            distance_meters=round(distance) if distance is not None else None,
            inside_geofence=inside,
        )
    )
    await audit(db, "attendance.check_out", user, str(record.id))
    # The total is the check-in day: its other sessions (capped at midnight, as on Beranda)
    # plus this one in full, so a night shift never shows a session above its total.
    session_hours = (now - record.checked_in_at).total_seconds() / 3600
    day = await sessions_on(db, user.id, jakarta_date(record.checked_in_at))
    others = sum(worked_hours(item, now) for item in day if item.id != record.id)
    return CheckOutOut(
        id=record.id,
        checked_out_at=now,
        effective_hours=round(session_hours, 2),
        total_hours_today=round(others + session_hours, 2),
    )


async def reverify(
    db: AsyncSession, user: Employee, payload: ReverifyIn
) -> VerifiedEventOut | SkippedEventOut | SkippedOut:
    record = next(
        (
            item
            for item in await sessions_on(db, user.id, jakarta_date())
            if not item.checked_out_at
        ),
        None,
    )
    if record is None:
        raise HTTPException(409, NO_OPEN_SESSION)
    now = datetime.now(UTC)
    pending = await pending_slot(db, record.id, now)
    office = await office_for(db, user)
    distance = rules.haversine_meters(
        payload.latitude, payload.longitude, office.latitude, office.longitude
    )
    allowed_radius = rules.allowed_check_in_radius_meters(
        office.radius_meters, payload.accuracy_meters
    )
    if pending is None:
        if user.is_remote:
            return SkippedOut(skipped=True, pending_reverification=None)
        if not payload.selfie_captured:
            raise HTTPException(422, SELFIE_REQUIRED)
        raise HTTPException(409, "Tidak ada re-verifikasi yang menunggu")
    if not user.is_remote and not payload.selfie_captured:
        raise HTTPException(422, SELFIE_REQUIRED)
    inside = user.is_remote or distance <= allowed_radius
    pending.lat = payload.latitude
    pending.lng = payload.longitude
    pending.accuracy = payload.accuracy_meters
    pending.at = now
    pending.distance_meters = round(distance)
    pending.inside_geofence = inside
    pending.anomaly = None if inside else "outside_geofence"
    await audit(db, "attendance.reverify", user, str(pending.id))
    event = LocationEventOut.model_validate(pending).model_dump(exclude={"maps_url"})
    if user.is_remote:
        return SkippedEventOut(**event, skipped=True)
    return VerifiedEventOut(**event)


async def location_history(
    db: AsyncSession, user: Employee, employee_id: str
) -> LocationHistoryOut:
    employee = await employees_service.visible_or_404(db, user, employee_id)
    found = await db.scalars(
        select(LocationEvent)
        .where(LocationEvent.employee_id == employee.id)
        .order_by(LocationEvent.at, LocationEvent.id)
    )
    return LocationHistoryOut(
        employee_id=employee.id, items=[LocationEventOut.model_validate(item) for item in found]
    )
