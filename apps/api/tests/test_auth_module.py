"""U8: auth module (login lockout table, cross-tenant invite/reset tokens, reset email)."""

from datetime import UTC, datetime, timedelta

import pytest
from helpers import count
from sqlalchemy import select

from movon_hr.core.identity import Employee
from movon_hr.core.mailer import last_email_to
from movon_hr.modules.auth import service as auth_service
from movon_hr.modules.auth.models import LoginAttempt, PasswordReset
from movon_hr.modules.auth.service import LOGIN_ATTEMPT_WINDOW, LOGIN_MAX_ATTEMPTS
from movon_hr.modules.employees.models import Invitation
from movon_hr.seed import DEMO_PASSWORD

pytestmark = pytest.mark.anyio

EMPLOYEE = "employee@movon.test"


@pytest.fixture
def login(client):
    async def post(email: str, password: str = DEMO_PASSWORD):
        return await client.post("/api/v1/auth/login", json={"email": email, "password": password})

    return post


async def test_failed_logins_are_stored_and_lock_the_email(db, login) -> None:
    for _ in range(LOGIN_MAX_ATTEMPTS - 1):
        assert (await login(EMPLOYEE, "wrong-pass-9")).status_code == 401
    # The 401 rolls the request back, but the failures survive in login_attempts.
    stored = await db.scalars(select(LoginAttempt.email))
    assert list(stored) == [EMPLOYEE] * (LOGIN_MAX_ATTEMPTS - 1)

    assert (await login(EMPLOYEE)).status_code == 200  # success clears the counter
    assert await count(db, LoginAttempt) == 0

    for _ in range(LOGIN_MAX_ATTEMPTS):
        assert (await login(EMPLOYEE, "wrong-pass-9")).status_code == 401
    locked = await login(EMPLOYEE)
    assert locked.status_code == 429
    assert locked.json()["detail"] == (
        "Terlalu banyak percobaan masuk. Coba lagi dalam beberapa menit."
    )
    # Unknown emails are counted too, without revealing that they do not exist.
    assert (await login("ghost@unknown.test")).status_code == 401
    assert await count(db, LoginAttempt) == LOGIN_MAX_ATTEMPTS + 1


async def test_short_wrong_password_is_a_401_and_counts(db, login) -> None:
    assert (await login(EMPLOYEE, "abc")).status_code == 401
    assert (await login("ghost@unknown.test", "x")).status_code == 401
    assert await count(db, LoginAttempt) == 2


async def test_failures_outside_the_window_do_not_lock(db, login) -> None:
    old = datetime.now(UTC) - LOGIN_ATTEMPT_WINDOW - timedelta(seconds=1)
    db.add_all(LoginAttempt(email=EMPLOYEE, attempted_at=old) for _ in range(LOGIN_MAX_ATTEMPTS))
    await db.commit()
    assert (await login(EMPLOYEE)).status_code == 200


async def test_invite_is_accepted_into_the_inviting_tenant(client, db) -> None:
    signup = await client.post(
        "/api/v1/auth/signup",
        json={
            "company_name": "PT Lain",
            "admin_name": "Admin Lain",
            "email": "hr@lain.test",
            "password": "Company123",
        },
    )
    assert signup.status_code == 200
    other_tenant = signup.json()["tenant"]["id"]
    assert other_tenant != str(db.info["tenant_id"])

    invited = await client.post(
        "/api/v1/invites",
        headers={"X-Demo-User": signup.json()["access_token"]},
        json={"name": "Tari", "email": "tari@lain.test", "department": "Ops", "role": "employee"},
    )
    assert invited.status_code == 200
    token = invited.json()["invite_url"].split("token=")[1]

    accepted = await client.post(
        "/api/v1/auth/accept-invite", json={"token": token, "password": "Tari12345"}
    )
    assert accepted.status_code == 200
    assert accepted.json()["tenant"]["id"] == other_tenant
    created = await db.scalar(
        select(Employee)
        .where(Employee.email == "tari@lain.test")
        .execution_options(cross_tenant=True)
    )
    assert created is not None
    assert str(created.tenant_id) == other_tenant
    # Signup gave the new company its own primary location; the invitee falls back to it.
    assert accepted.json()["user"]["work_location"]["name"] == "Kantor Pusat"

    used = await client.get(f"/api/v1/invites/{token}")
    assert used.status_code == 410
    assert used.json()["detail"] == auth_service.INVITE_USED
    again = await client.post(
        "/api/v1/auth/accept-invite", json={"token": token, "password": "Tari12345"}
    )
    assert again.status_code == 410


async def test_invite_preview_names_the_inviter_and_tells_expired_from_used(
    client, db, login
) -> None:
    hr = (await login("hr@movon.test")).json()
    invited = await client.post(
        "/api/v1/invites",
        headers={"X-Demo-User": hr["access_token"]},
        json={"name": "Tari", "email": "tari@movon.test", "department": "Ops", "role": "employee"},
    )
    token = invited.json()["invite_url"].split("token=")[1]

    preview = await client.get(f"/api/v1/invites/{token}")
    assert preview.status_code == 200
    assert preview.json()["invited_by"] == hr["user"]["name"]
    assert preview.json()["expires_at"] == invited.json()["expires_at"]

    invitation = await db.get(Invitation, token)
    assert invitation is not None
    invitation.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    await db.commit()
    expired = await client.get(f"/api/v1/invites/{token}")
    assert expired.status_code == 410
    assert expired.json()["detail"] == auth_service.INVITE_EXPIRED


async def test_reset_token_works_once(client) -> None:
    await client.post("/api/v1/auth/forgot-password", json={"email": EMPLOYEE})
    message = last_email_to(EMPLOYEE)
    assert message is not None
    token = next(part for part in message.body.split() if "token=" in part).split("token=")[1]

    preview = await client.post("/api/v1/auth/reset-password/preview", json={"token": token})
    assert preview.status_code == 200
    assert preview.json() == {"email": EMPLOYEE}

    first = await client.post(
        "/api/v1/auth/reset-password", json={"token": token, "password": "BaruSekali1"}
    )
    assert first.status_code == 200
    second = await client.post(
        "/api/v1/auth/reset-password", json={"token": token, "password": "BaruLagi12"}
    )
    assert second.status_code == 410
    gone = await client.post("/api/v1/auth/reset-password/preview", json={"token": token})
    assert gone.status_code == 410
    missing = await client.post(
        "/api/v1/auth/reset-password/preview", json={"token": "not-a-token"}
    )
    assert missing.status_code == 404
    unknown = await client.post(
        "/api/v1/auth/reset-password", json={"token": "not-a-token", "password": "BaruLagi12"}
    )
    assert unknown.status_code == 404


async def test_forgot_password_sends_nothing_when_the_request_fails(
    client, db, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def broken_audit(*args: object) -> None:
        raise RuntimeError("audit down")

    monkeypatch.setattr(auth_service, "audit", broken_audit)
    with pytest.raises(RuntimeError):
        await client.post("/api/v1/auth/forgot-password", json={"email": EMPLOYEE})
    assert last_email_to(EMPLOYEE) is None
    assert await count(db, PasswordReset) == 0
