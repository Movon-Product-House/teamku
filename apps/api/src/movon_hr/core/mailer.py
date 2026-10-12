"""Transactional email adapter.

``MOVON_MAIL_PROVIDER=console`` (default) writes to the process logger and an
in-memory outbox so tests and local onboarding can read invite/reset links
without a mail server. ``resend`` sends through the Resend API.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal

import resend
from resend.http_client_httpx import HTTPXClient

from movon_hr.core.settings import settings

logger = logging.getLogger("movon_hr.mailer")

# The SDK default is 30s; stay under the web client's 15s fetch timeout.
resend.default_async_http_client = HTTPXClient(timeout=10)

# Demo seed data uses these (e.g. @movon.test). Sending there only bounces,
# and a high bounce rate gets the Resend account paused.
RESERVED_SUFFIXES = (".test", ".example", ".invalid", ".localhost")

MailKind = Literal["generic", "invite", "password_reset", "leave", "attendance_alert"]


@dataclass
class EmailMessage:
    to: str
    subject: str
    body: str
    sent_at: datetime = field(default_factory=lambda: datetime.now(UTC))


outbox: list[EmailMessage] = []


def reset_outbox() -> None:
    outbox.clear()


async def send_email(to: str, subject: str, body: str, *, kind: MailKind = "generic") -> bool:
    """Send one plain-text email; True if sent. Never raises: callers must not fail on mail.

    Routes schedule it with ``BackgroundTasks`` so it runs only after the commit.
    """
    if settings.mail_provider == "resend":
        return await _send_resend(to, subject, body, kind)
    return _queue_console(to, subject, body, kind)


def _queue_console(to: str, subject: str, body: str, kind: MailKind) -> bool:
    outbox.append(EmailMessage(to=to, subject=subject, body=body))
    if settings.environment == "development":
        logger.info("Email queued to=%s subject=%s\n%s", to, subject, body)
    else:
        # Bodies carry invite/reset tokens; keep them out of shared logs.
        logger.info("Email queued kind=%s", kind)
    return True


async def _send_resend(to: str, subject: str, body: str, kind: MailKind) -> bool:
    if to.strip().lower().endswith(RESERVED_SUFFIXES):
        logger.info("Email skipped kind=%s reason=reserved_domain", kind)
        return False
    try:
        api_key, sender = settings.resend_api_key, settings.mail_from
        if api_key is None or sender is None:
            raise RuntimeError("Resend is not configured")
        resend.api_key = api_key.get_secret_value()
        sent = await resend.Emails.send_async(
            {
                "from": sender,
                "to": [to],
                "subject": subject,
                "text": body,
                "tags": [{"name": "kind", "value": kind}],
            }
        )
    except Exception as exc:  # noqa: BLE001 - mail must never fail the caller
        error = getattr(exc, "error_type", None) or type(exc).__name__
        code = getattr(exc, "code", None)
        logger.warning("Email failed kind=%s error=%s code=%s", kind, error, code)
        return False
    logger.info("Email sent kind=%s id=%s", kind, sent.get("id"))
    return True


def last_email_to(address: str) -> EmailMessage | None:
    email = address.strip().lower()
    for message in reversed(outbox):
        if message.to.lower() == email:
            return message
    return None
