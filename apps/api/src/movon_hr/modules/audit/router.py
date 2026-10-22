from typing import Annotated

from fastapi import APIRouter, Depends

from movon_hr.core.auth import require_role
from movon_hr.core.db import DB
from movon_hr.core.identity import Employee
from movon_hr.modules.audit import service
from movon_hr.modules.audit.schemas import AuditLogList

router = APIRouter(tags=["audit"])


@router.get("/audit-logs")
async def audit_logs(
    db: DB, _: Annotated[Employee, Depends(require_role("hr_admin"))]
) -> AuditLogList:
    return AuditLogList.model_validate({"items": await service.list_audit_logs(db)})
