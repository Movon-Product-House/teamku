from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select, update

from movon_hr.core.identity import AuthSession
from movon_hr.modules.auth.service import LOGIN_MAX_ATTEMPTS
from movon_hr.seed import DEMO_PASSWORD

pytestmark = pytest.mark.anyio


@pytest.fixture
def login(client):
    async def post(email: str, password: str = DEMO_PASSWORD):
        return await client.post("/api/v1/auth/login", json={"email": email, "password": password})

    return post


@pytest.fixture
def token_for(login):
    async def token(email: str) -> str:
        return (await login(email)).json()["access_token"]

    return token


async def test_password_is_verified_against_hash_and_never_leaked(client, login) -> None:
    wrong = await login("hr@movon.test", "totally-wrong-1")
    assert wrong.status_code == 401

    ok = await login("hr@movon.test")
    assert ok.status_code == 200
    assert "password_hash" not in ok.json()["user"]

    token = ok.json()["access_token"]
    headers = {"X-Demo-User": token}
    assert "password_hash" not in (await client.get("/api/v1/me", headers=headers)).json()["user"]

    listed = (await client.get("/api/v1/employees", headers=headers)).json()["items"]
    assert all("password_hash" not in item for item in listed)


async def test_login_is_rate_limited_after_repeated_failures(login) -> None:
    for _ in range(LOGIN_MAX_ATTEMPTS):
        assert (await login("hr@movon.test", "wrong-pass-9")).status_code == 401
    # Threshold reached: even a valid password is temporarily blocked.
    locked = await login("hr@movon.test")
    assert locked.status_code == 429


async def test_expired_session_is_rejected(client, db, token_for) -> None:
    token = await token_for("employee@movon.test")
    assert (await client.get("/api/v1/me", headers={"X-Demo-User": token})).status_code == 200

    await db.execute(
        update(AuthSession)
        .where(AuthSession.token == token)
        .values(expires_at=datetime.now(UTC) - timedelta(seconds=1))
    )
    await db.commit()
    assert (await client.get("/api/v1/me", headers={"X-Demo-User": token})).status_code == 401
    # Expired token is cleaned up on rejection.
    assert await db.scalar(select(AuthSession.token).where(AuthSession.token == token)) is None


async def test_change_password_revokes_other_sessions_and_rotates_credentials(
    client, login, token_for
) -> None:
    keep = await token_for("employee@movon.test")
    other = await token_for("employee@movon.test")

    changed = await client.post(
        "/api/v1/auth/change-password",
        headers={"X-Demo-User": keep},
        json={"current_password": DEMO_PASSWORD, "new_password": "BrandNew123"},
    )
    assert changed.status_code == 200

    # Current session survives; other sessions are revoked.
    assert (await client.get("/api/v1/me", headers={"X-Demo-User": keep})).status_code == 200
    assert (await client.get("/api/v1/me", headers={"X-Demo-User": other})).status_code == 401

    # Old credentials no longer work; new ones do.
    assert (await login("employee@movon.test", DEMO_PASSWORD)).status_code == 401
    assert (await login("employee@movon.test", "BrandNew123")).status_code == 200


async def test_change_password_enforces_policy_and_current_password(client, token_for) -> None:
    token = await token_for("employee@movon.test")

    wrong_current = await client.post(
        "/api/v1/auth/change-password",
        headers={"X-Demo-User": token},
        json={"current_password": "not-the-one", "new_password": "BrandNew123"},
    )
    assert wrong_current.status_code == 401

    weak = await client.post(
        "/api/v1/auth/change-password",
        headers={"X-Demo-User": token},
        json={"current_password": DEMO_PASSWORD, "new_password": "alllowercase"},
    )
    assert weak.status_code == 422


async def test_created_employee_gets_temporary_password_and_can_sign_in(
    client, login, token_for
) -> None:
    hr = {"X-Demo-User": await token_for("hr@movon.test")}
    created = await client.post(
        "/api/v1/employees",
        headers=hr,
        json={
            "name": "Bimo Aji",
            "email": "bimo.aji@movon.test",
            "department": "Product",
            "role": "employee",
            "salary": 9_000_000,
        },
    )
    assert created.status_code == 200
    body = created.json()
    assert "password_hash" not in body
    temporary_password = body["temporary_password"]

    assert (await login("bimo.aji@movon.test", temporary_password)).status_code == 200


async def test_creating_employee_with_weak_password_is_rejected(client, token_for) -> None:
    hr = {"X-Demo-User": await token_for("hr@movon.test")}
    response = await client.post(
        "/api/v1/employees",
        headers=hr,
        json={
            "name": "Weak Pass",
            "email": "weak.pass@movon.test",
            "department": "Product",
            "role": "employee",
            "salary": 9_000_000,
            "password": "nodigitshere",
        },
    )
    assert response.status_code == 422
