from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends

from movon_hr.core.auth import CurrentUser, require_role
from movon_hr.core.db import DB
from movon_hr.core.identity import Employee
from movon_hr.modules.leave import service
from movon_hr.modules.leave.schemas import (
    ApprovalIn,
    ApprovalListOut,
    LeaveDaysOut,
    LeaveIn,
    LeaveListOut,
    LeaveOut,
)

router = APIRouter(tags=["leave"])
Approver = Annotated[Employee, Depends(require_role("manager", "hr_admin"))]


@router.get("/leave-requests")
async def list_leave_requests(db: DB, user: CurrentUser) -> LeaveListOut:
    items = [LeaveDaysOut.model_validate(item) for item in await service.own_requests(db, user)]
    return LeaveListOut(items=items, balance=await service.leave_balance(db, user.id))


@router.post("/leave-requests")
async def submit_leave(
    db: DB, user: CurrentUser, payload: LeaveIn, background_tasks: BackgroundTasks
) -> LeaveDaysOut:
    return LeaveDaysOut.model_validate(await service.submit(db, user, payload, background_tasks))


@router.post("/leave-requests/{request_id}/cancel")
async def cancel_leave(
    db: DB, user: CurrentUser, request_id: str, background_tasks: BackgroundTasks
) -> LeaveOut:
    return LeaveOut.model_validate(await service.cancel(db, user, request_id, background_tasks))


@router.get("/approvals")
async def approvals(db: DB, user: Approver) -> ApprovalListOut:
    return await service.approvals(db, user)


@router.post("/approvals/{request_id}")
async def decide(
    db: DB,
    user: Approver,
    request_id: str,
    payload: ApprovalIn,
    background_tasks: BackgroundTasks,
) -> LeaveOut:
    request = await service.decide(db, user, request_id, payload, background_tasks)
    return LeaveOut.model_validate(request)
