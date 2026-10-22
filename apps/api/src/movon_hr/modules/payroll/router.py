from typing import Annotated

from fastapi import APIRouter, Depends

from movon_hr.core.auth import CurrentUser, require_role
from movon_hr.core.db import DB
from movon_hr.core.identity import Employee
from movon_hr.modules.payroll import service
from movon_hr.modules.payroll.schemas import (
    PayrollIn,
    PayrollRunListOut,
    PayrollRunOut,
    PayslipListOut,
)

router = APIRouter(tags=["payroll"])
HrAdmin = Annotated[Employee, Depends(require_role("hr_admin"))]


@router.get("/payroll/runs")
async def list_runs(db: DB, _: HrAdmin) -> PayrollRunListOut:
    return PayrollRunListOut.model_validate({"items": await service.list_runs(db)})


@router.post("/payroll/runs")
async def create_run(db: DB, user: HrAdmin, payload: PayrollIn) -> PayrollRunOut:
    return PayrollRunOut.model_validate(await service.create_run(db, user, payload.month))


@router.post("/payroll/runs/{run_id}/finalize")
async def finalize(db: DB, user: HrAdmin, run_id: str) -> PayrollRunOut:
    return PayrollRunOut.model_validate(await service.finalize(db, user, run_id))


@router.post("/payroll/runs/{run_id}/publish")
async def publish(db: DB, user: HrAdmin, run_id: str) -> PayrollRunOut:
    return PayrollRunOut.model_validate(await service.publish(db, user, run_id))


@router.get("/payroll/payslips")
async def payslips(db: DB, user: CurrentUser) -> PayslipListOut:
    return PayslipListOut(items=await service.payslips(db, user))
