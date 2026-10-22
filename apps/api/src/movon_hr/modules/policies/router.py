from typing import Annotated

from fastapi import APIRouter, Depends

from movon_hr.core.auth import CurrentUser, require_role
from movon_hr.core.db import DB
from movon_hr.core.identity import Employee
from movon_hr.modules.policies import service
from movon_hr.modules.policies.schemas import (
    AnswerOut,
    PolicyInput,
    PolicyList,
    PolicyOut,
    PolicyQuestion,
)

router = APIRouter(tags=["policies"])
HrAdmin = Annotated[Employee, Depends(require_role("hr_admin"))]


@router.get("/policies")
async def list_policies(db: DB, _: HrAdmin) -> PolicyList:
    return PolicyList.model_validate({"items": await service.list_policies(db)})


@router.post("/policies")
async def create_policy(db: DB, user: HrAdmin, payload: PolicyInput) -> PolicyOut:
    return PolicyOut.model_validate(await service.create_policy(db, user, payload))


@router.put("/policies/{policy_id}")
async def update_policy(db: DB, user: HrAdmin, policy_id: str, payload: PolicyInput) -> PolicyOut:
    return PolicyOut.model_validate(await service.update_policy(db, user, policy_id, payload))


@router.post("/policies/{policy_id}/publish")
async def publish_policy(db: DB, user: HrAdmin, policy_id: str) -> PolicyOut:
    return PolicyOut.model_validate(await service.set_state(db, user, policy_id, "published"))


@router.post("/policies/{policy_id}/archive")
async def archive_policy(db: DB, user: HrAdmin, policy_id: str) -> PolicyOut:
    return PolicyOut.model_validate(await service.set_state(db, user, policy_id, "archived"))


@router.post("/policy-assistant/questions")
async def ask(db: DB, user: CurrentUser, payload: PolicyQuestion) -> AnswerOut:
    return await service.ask(db, user, payload.question)
