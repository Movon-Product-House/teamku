"""Request authentication: session token (X-Demo-User header or cookie) -> employee."""

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy import select

from movon_hr.core.db import DB
from movon_hr.core.identity import AuthSession, Employee
from movon_hr.core.settings import settings

INVALID_SESSION = "Sesi tidak valid"
EXPIRED_SESSION = "Sesi telah berakhir. Silakan masuk kembali."


async def current_user(
    request: Request,
    db: DB,
    x_demo_user: Annotated[str | None, Header()] = None,
) -> Employee:
    """Resolve the employee behind the session token and bind their tenant to ``db``."""
    token = x_demo_user or request.cookies.get(settings.session_cookie_name)
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, INVALID_SESSION)
    # The token is the only thing that identifies the tenant, so this lookup is cross-tenant.
    row = (
        await db.execute(
            select(AuthSession, Employee)
            .join(Employee, Employee.id == AuthSession.employee_id)
            .where(AuthSession.token == token)
            .execution_options(cross_tenant=True)
        )
    ).first()
    if row is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, INVALID_SESSION)
    auth_session, employee = row
    if auth_session.expires_at <= datetime.now(UTC):
        await db.delete(auth_session)
        await db.commit()  # get_db rolls back on the 401 below
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, EXPIRED_SESSION)
    if employee.status != "active":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, INVALID_SESSION)
    db.info["tenant_id"] = employee.tenant_id
    return employee


CurrentUser = Annotated[Employee, Depends(current_user)]


def require_role(*roles: str) -> Callable[[Employee], Awaitable[Employee]]:
    """Dependency: the current user, or 403 unless their role is one of ``roles``."""

    async def check(user: CurrentUser) -> Employee:
        if user.role not in roles:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN, "Anda tidak memiliki izin untuk aksi ini"
            )
        return user

    return check
