import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import Select, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from movon_hr.core.identity import AuthSession, Employee
from movon_hr.core.security import (
    generate_temporary_password,
    hash_password_async,
    password_policy_error,
)
from movon_hr.modules.audit.service import audit
from movon_hr.modules.employees.models import Invitation
from movon_hr.modules.employees.schemas import (
    CreatedEmployeeOut,
    EmployeeColumns,
    EmployeeCreateIn,
    EmployeeOut,
    EmployeeUpdateIn,
    NewEmployeeOut,
)
from movon_hr.modules.notifications.service import notify
from movon_hr.modules.settings import service as settings_service
from movon_hr.modules.settings.models import WorkLocation
from movon_hr.modules.settings.schemas import LocationOut

NOT_FOUND = "Karyawan tidak ditemukan"


def parse_id(value: str | None) -> uuid.UUID | None:
    """Ids arrive as plain strings so a malformed one answers like an unknown one."""
    try:
        return uuid.UUID(value) if value else None
    except ValueError:
        return None


def visible_query(user: Employee) -> Select[tuple[Employee]]:
    """HR sees everyone, a manager their department, anyone else only themselves."""
    query = select(Employee)
    if user.role == "hr_admin":
        return query
    if user.role == "manager":
        return query.where(Employee.department == user.department)
    return query.where(Employee.id == user.id)


async def visible_employees(db: AsyncSession, user: Employee) -> Sequence[Employee]:
    return (await db.scalars(visible_query(user).order_by(Employee.id))).all()


async def visible_or_404(db: AsyncSession, user: Employee, employee_id: str) -> Employee:
    parsed = parse_id(employee_id)
    employee = await db.scalar(visible_query(user).where(Employee.id == parsed)) if parsed else None
    if employee is None:
        raise HTTPException(404, NOT_FOUND)
    return employee


def employee_out(
    employee: Employee,
    locations: dict[uuid.UUID, WorkLocation],
    primary: WorkLocation,
    *,
    hide_salary: bool = False,
) -> EmployeeOut:
    """The old public_employee(): a missing or unknown location falls back to the primary."""
    data = EmployeeColumns.model_validate(employee).model_dump()
    if hide_salary:
        data["salary"] = None
    location = None
    if not employee.is_remote:
        location = locations.get(employee.work_location_id or primary.id, primary)
    return EmployeeOut(
        **data,
        work_mode="field" if employee.is_remote else "office",
        work_location=LocationOut.model_validate(location) if location else None,
    )


async def to_out(
    db: AsyncSession, employees: Sequence[Employee], *, hide_salary: bool = False
) -> list[EmployeeOut]:
    locations = await settings_service.locations_by_id(db)
    primary = await settings_service.primary_location(db)
    return [employee_out(item, locations, primary, hide_salary=hide_salary) for item in employees]


async def email_taken(db: AsyncSession, email: str) -> bool:
    """Work email is unique across companies, including pending invitations."""
    needle = email.strip().lower()
    employee = await db.scalar(
        select(Employee.id)
        .where(func.lower(Employee.email) == needle)
        .execution_options(cross_tenant=True)
    )
    if employee is not None:
        return True
    invitation = await db.scalar(
        select(Invitation.token)
        .where(
            func.lower(Invitation.email) == needle,
            Invitation.accepted_at.is_(None),
            Invitation.expires_at > datetime.now(UTC),
        )
        .execution_options(cross_tenant=True)
    )
    return invitation is not None


async def revoke_sessions(
    db: AsyncSession, employee_id: uuid.UUID, *, keep_token: str | None = None
) -> None:
    """Invalidate every session of an employee, optionally keeping one."""
    query = delete(AuthSession).where(AuthSession.employee_id == employee_id)
    if keep_token is not None:
        query = query.where(AuthSession.token != keep_token)
    await db.execute(query)


async def create_employee(
    db: AsyncSession, user: Employee, payload: EmployeeCreateIn
) -> CreatedEmployeeOut | NewEmployeeOut:
    if await email_taken(db, payload.email):
        raise HTTPException(409, "Email kerja sudah digunakan")
    temporary_password: str | None = None
    password = payload.password
    if password is None:
        password = temporary_password = generate_temporary_password()
    else:
        policy_error = password_policy_error(password)
        if policy_error:
            raise HTTPException(422, policy_error)
    locations = await settings_service.locations_by_id(db)
    # Not validated on create (bug kept, see the plan); an id the FK cannot hold is dropped.
    location_id = parse_id(payload.work_location_id)
    employee = Employee(
        **payload.model_dump(exclude={"password", "work_location_id"}),
        work_location_id=location_id if location_id in locations else None,
        password_hash=await hash_password_async(password),
    )
    db.add(employee)
    await db.flush()
    await audit(db, "employee.created", user, str(employee.id))
    await notify(db, employee.id, "Akun Anda siap", "Profil dibuat oleh HR.", "/app/overview")
    out = employee_out(employee, locations, await settings_service.primary_location(db))
    if temporary_password is None:
        return CreatedEmployeeOut(**out.model_dump())
    # Returned once so HR can share it; never stored in plain text.
    return NewEmployeeOut(**out.model_dump(), temporary_password=temporary_password)


async def update_employee(
    db: AsyncSession, user: Employee, employee_id: str, payload: EmployeeUpdateIn
) -> EmployeeOut:
    parsed = parse_id(employee_id)
    employee = await db.scalar(select(Employee).where(Employee.id == parsed)) if parsed else None
    if employee is None:
        raise HTTPException(404, NOT_FOUND)
    if payload.status is not None:
        if employee.id == user.id and payload.status != "active":
            raise HTTPException(409, "Anda tidak dapat menonaktifkan akun sendiri")
        employee.status = payload.status
        # Deactivated accounts must lose any active sessions immediately.
        if payload.status != "active":
            await revoke_sessions(db, employee.id)
        await audit(db, "employee.status_changed", user, str(employee.id))
    if payload.is_remote is not None:
        employee.is_remote = payload.is_remote
        await audit(db, "employee.remote_changed", user, str(employee.id))
    locations = await settings_service.locations_by_id(db)
    if payload.work_location_id is not None:
        location_id = parse_id(payload.work_location_id)
        if location_id is None or location_id not in locations:
            raise HTTPException(422, "Lokasi kerja tidak ditemukan")
        employee.work_location_id = location_id
        employee.is_remote = False
        await audit(db, "employee.location_changed", user, str(employee.id))
    return employee_out(employee, locations, await settings_service.primary_location(db))
