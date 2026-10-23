from typing import Annotated

from fastapi import APIRouter, Depends

from movon_hr.core.auth import CurrentUser, require_role
from movon_hr.core.db import DB
from movon_hr.core.identity import Employee
from movon_hr.modules.employees import service
from movon_hr.modules.employees.schemas import (
    CreateEmployeeResult,
    EmployeeCreateIn,
    EmployeeListOut,
    EmployeeOut,
    EmployeeUpdateIn,
)

router = APIRouter(tags=["employees"])
HrAdmin = Annotated[Employee, Depends(require_role("hr_admin"))]
HrOrManager = Annotated[Employee, Depends(require_role("hr_admin", "manager"))]


@router.get("/employees")
async def list_employees(db: DB, user: HrOrManager) -> EmployeeListOut:
    employees = await service.visible_employees(db, user)
    items = await service.to_out(db, employees, hide_salary=user.role == "manager")
    return EmployeeListOut(items=items, total=len(items))


@router.get("/employees/{employee_id}")
async def get_employee(db: DB, user: CurrentUser, employee_id: str) -> EmployeeOut:
    employee = await service.visible_or_404(db, user, employee_id)
    return (await service.to_out(db, [employee], hide_salary=user.role == "manager"))[0]


@router.post("/employees")
async def create_employee(db: DB, user: HrAdmin, payload: EmployeeCreateIn) -> CreateEmployeeResult:
    return await service.create_employee(db, user, payload)


@router.patch("/employees/{employee_id}")
async def update_employee(
    db: DB, user: HrAdmin, employee_id: str, payload: EmployeeUpdateIn
) -> EmployeeOut:
    return await service.update_employee(db, user, employee_id, payload)
