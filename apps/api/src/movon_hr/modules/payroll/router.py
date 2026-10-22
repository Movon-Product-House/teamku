from typing import Annotated

from fastapi import APIRouter, Depends

from movon_hr.core.auth import CurrentUser, require_role
from movon_hr.core.db import DB
from movon_hr.core.identity import Employee
from movon_hr.modules.payroll import service
from movon_hr.modules.payroll.schemas import (
    PayrollInput,
    PayrollRunList,
    PayrollRunOut,
    PayslipList,
)

router = APIRouter(prefix="/payroll", tags=["payroll"])
HrAdmin = Annotated[Employee, Depends(require_role("hr_admin"))]


@router.get("/runs")
async def list_runs(db: DB, _: HrAdmin) -> PayrollRunList:
    return PayrollRunList.model_validate({"items": await service.list_runs(db)})


@router.post("/runs")
async def create_run(db: DB, user: HrAdmin, payload: PayrollInput) -> PayrollRunOut:
    return PayrollRunOut.model_validate(await service.create_run(db, user, payload.month))


@router.post("/runs/{run_id}/finalize")
async def finalize(db: DB, user: HrAdmin, run_id: str) -> PayrollRunOut:
    return PayrollRunOut.model_validate(await service.finalize(db, user, run_id))


@router.post("/runs/{run_id}/publish")
async def publish(db: DB, user: HrAdmin, run_id: str) -> PayrollRunOut:
    return PayrollRunOut.model_validate(await service.publish(db, user, run_id))


@router.get("/payslips")
async def payslips(db: DB, user: CurrentUser) -> PayslipList:
    return PayslipList(items=await service.payslips(db, user))
