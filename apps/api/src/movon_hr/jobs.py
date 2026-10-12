"""Scheduled jobs: ``python -m movon_hr.jobs attendance-alerts|cleanup``.

Run by Dokploy Schedule in the API container (attendance-alerts every 5 minutes,
cleanup daily). Both are idempotent; a failure exits non-zero so the run shows red.
"""

import argparse
import asyncio
import logging
from datetime import UTC, datetime

from sqlalchemy import delete, or_, select

from movon_hr.core import db as core_db
from movon_hr.core.identity import AuthSession, Tenant
from movon_hr.core.mailer import send_email
from movon_hr.modules.attendance.alerts import evaluate_tenant
from movon_hr.modules.auth.models import LoginAttempt, PasswordReset
from movon_hr.modules.auth.service import LOGIN_ATTEMPT_WINDOW
from movon_hr.modules.settings.models import OAuthState

logger = logging.getLogger("movon_hr.jobs")
CROSS_TENANT = {"cross_tenant": True}


async def attendance_alerts(now: datetime) -> bool:
    """One session per tenant; emails go out after that tenant's commit. False if any failed."""
    async with core_db.SessionLocal() as session:
        tenant_ids = list(
            await session.scalars(select(Tenant.id).execution_options(**CROSS_TENANT))
        )
    ok = True
    for tenant_id in tenant_ids:
        try:
            async with core_db.SessionLocal() as session:
                session.info["tenant_id"] = tenant_id
                emails = await evaluate_tenant(session, now)
                await session.commit()
        except Exception:
            # One broken tenant must not starve the others.
            logger.exception("attendance-alerts failed for tenant %s", tenant_id)
            ok = False
            continue
        for email in emails:
            await send_email(email.to, email.subject, email.body, kind="attendance_alert")
        logger.info("attendance-alerts tenant=%s emails=%d", tenant_id, len(emails))
    return ok


async def cleanup(now: datetime) -> bool:
    """Delete expired sessions, spent password resets, old login attempts, stale OAuth states."""
    statements = {
        "sessions": delete(AuthSession).where(AuthSession.expires_at <= now),
        "password_resets": delete(PasswordReset).where(
            or_(PasswordReset.expires_at <= now, PasswordReset.used_at.is_not(None))
        ),
        "login_attempts": delete(LoginAttempt).where(
            LoginAttempt.attempted_at < now - LOGIN_ATTEMPT_WINDOW
        ),
        "oauth_states": delete(OAuthState).where(OAuthState.expires_at <= now),
    }
    async with core_db.SessionLocal() as session:
        for table, statement in statements.items():
            result = await session.execute(statement.execution_options(**CROSS_TENANT))
            logger.info("cleanup %s deleted=%d", table, getattr(result, "rowcount", 0))
        await session.commit()
    return True


JOBS = {"attendance-alerts": attendance_alerts, "cleanup": cleanup}


async def _run(name: str) -> bool:
    try:
        return await JOBS[name](datetime.now(UTC))
    finally:
        await core_db.engine.dispose()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="Run a Teamku scheduled job.")
    parser.add_argument("job", choices=sorted(JOBS))
    name = parser.parse_args().job
    try:
        ok = asyncio.run(_run(name))
    except Exception:
        logger.exception("%s failed", name)
        ok = False
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
