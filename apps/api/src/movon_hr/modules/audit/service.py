from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from movon_hr.core.identity import Employee
from movon_hr.modules.audit.models import AuditLog


async def audit(db: AsyncSession, action: str, actor: Employee, target: str) -> None:
    db.add(AuditLog(action=action, actor=actor.id, target=target))


async def list_audit_logs(db: AsyncSession) -> Sequence[AuditLog]:
    """Newest first; ``at`` is the transaction time, so the uuidv7 id breaks ties."""
    found = await db.scalars(select(AuditLog).order_by(AuditLog.at.desc(), AuditLog.id.desc()))
    return found.all()
