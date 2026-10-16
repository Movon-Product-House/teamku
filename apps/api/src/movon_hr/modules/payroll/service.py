from collections.abc import Sequence
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from movon_hr.core.identity import Employee
from movon_hr.modules.audit.service import audit
from movon_hr.modules.employees.service import parse_id
from movon_hr.modules.notifications.service import notify
from movon_hr.modules.payroll import rules
from movon_hr.modules.payroll.models import PayrollRun
from movon_hr.modules.payroll.schemas import PayslipOut

NOT_FOUND = "Payroll run tidak ditemukan"


async def list_runs(db: AsyncSession) -> Sequence[PayrollRun]:
    """Newest first; ``created_at`` is the transaction time, so the uuidv7 id breaks ties."""
    found = await db.scalars(
        select(PayrollRun).order_by(PayrollRun.created_at.desc(), PayrollRun.id.desc())
    )
    return found.all()


async def create_run(db: AsyncSession, user: Employee, period: str) -> PayrollRun:
    """A period is calculated once; asking again returns the existing run (200, as before)."""
    by_period = select(PayrollRun).where(PayrollRun.period == period)
    existing = await db.scalar(by_period)
    if existing is not None:
        return existing
    employees = await db.scalars(
        select(Employee).where(Employee.status == "active").order_by(Employee.id)
    )
    items = [rules.payroll_item(str(item.id), item.name, item.salary) for item in employees]
    # UNIQUE (tenant_id, period): a concurrent request may have created it meanwhile.
    run = await db.scalar(
        insert(PayrollRun)
        .values(tenant_id=user.tenant_id, period=period, status="draft", items=items)
        .on_conflict_do_nothing(index_elements=["tenant_id", "period"])
        .returning(PayrollRun)
    )
    if run is None:
        return (await db.scalars(by_period)).one()
    await audit(db, "payroll.calculated", user, str(run.id))
    return run


async def run_or_404(db: AsyncSession, run_id: str) -> PayrollRun:
    parsed = parse_id(run_id)
    run = await db.scalar(select(PayrollRun).where(PayrollRun.id == parsed)) if parsed else None
    if run is None:
        raise HTTPException(404, NOT_FOUND)
    return run


async def finalize(db: AsyncSession, user: Employee, run_id: str) -> PayrollRun:
    run = await run_or_404(db, run_id)
    if run.status != "draft":
        raise HTTPException(409, "Hanya draft payroll yang dapat difinalisasi")
    run.status = "finalized"
    run.finalized_at = datetime.now(UTC)
    await audit(db, "payroll.finalized", user, str(run.id))
    return run


async def publish(db: AsyncSession, user: Employee, run_id: str) -> PayrollRun:
    run = await run_or_404(db, run_id)
    if run.status != "finalized":
        raise HTTPException(409, "Finalisasi payroll sebelum dipublikasikan")
    run.status = "published"
    run.published_at = datetime.now(UTC)
    await audit(db, "payroll.published", user, str(run.id))
    # Every employee, whatever their status (kept bug #25, see the plan's scope boundaries).
    for employee_id in await db.scalars(select(Employee.id).order_by(Employee.id)):
        await notify(
            db,
            employee_id,
            "Slip gaji tersedia",
            f"Payroll periode {run.period} telah dipublikasikan.",
            "/app/payroll/payslips",
        )
    return run


async def payslips(db: AsyncSession, user: Employee) -> list[PayslipOut]:
    """The caller's row of every published run, newest period first."""
    runs = await db.scalars(select(PayrollRun).where(PayrollRun.status == "published"))
    own = str(user.id)
    items = [
        PayslipOut(id=run.id, period=run.period, published_at=run.published_at, **row)
        for run in runs
        for row in run.items
        if row["employee_id"] == own
    ]
    items.sort(key=lambda item: item.period, reverse=True)
    return items
