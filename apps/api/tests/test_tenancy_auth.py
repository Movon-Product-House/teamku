import httpx
import pytest
from helpers import count, session_of

from movon_hr.core.identity import Tenant
from movon_hr.core.mailer import last_email_to, outbox
from movon_hr.core.settings import settings
from movon_hr.main import app
from movon_hr.seed import DEMO_PASSWORD

pytestmark = pytest.mark.anyio


@pytest.fixture
def signup(client):
    async def post(company: str, email: str, slug: str | None = None):
        payload = {
            "company_name": company,
            "admin_name": "Admin Satu",
            "email": email,
            "password": "Company123",
        }
        if slug:
            payload["slug"] = slug
        return await client.post("/api/v1/auth/signup", json=payload)

    return post


async def test_signup_creates_isolated_tenant_and_sets_cookie(client, db, signup) -> None:
    response = await signup("PT Merdeka Digital", "admin@merdeka.test", "merdeka")
    assert response.status_code == 200
    body = response.json()
    assert body["user"]["email"] == "admin@merdeka.test"
    assert body["user"]["role"] == "hr_admin"
    assert body["tenant"]["slug"] == "merdeka"
    assert settings.session_cookie_name in response.cookies
    me = await client.get("/api/v1/me", headers=session_of(response))
    assert me.json()["tenant"]["slug"] == "merdeka"
    assert await count(db, Tenant) == 2  # demo + new company


async def test_tenants_cannot_see_each_others_employees(client, signup) -> None:
    first = await signup("PT Satu", "hr@satu.test", "satu")
    assert first.status_code == 200
    created = await client.post(
        "/api/v1/employees",
        headers=session_of(first),
        json={
            "name": "Karyawan Satu",
            "email": "orang@satu.test",
            "department": "Engineering",
            "role": "employee",
            "salary": 8_000_000,
        },
    )
    assert created.status_code == 200
    listed = await client.get("/api/v1/employees", headers=session_of(first))
    satu_emails = {item["email"] for item in listed.json()["items"]}
    assert "orang@satu.test" in satu_emails
    assert "hr@movon.test" not in satu_emails

    second = await signup("PT Dua", "hr@dua.test", "dua")
    assert second.status_code == 200
    listed = await client.get("/api/v1/employees", headers=session_of(second))
    dua_emails = {item["email"] for item in listed.json()["items"]}
    assert dua_emails == {"hr@dua.test"}


async def test_cookie_login_works_without_demo_header(client, db) -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as fresh:
        login = await fresh.post(
            "/api/v1/auth/login",
            json={"email": "employee@movon.test", "password": DEMO_PASSWORD},
        )
        assert login.status_code == 200
        assert settings.session_cookie_name in login.cookies
        me = await fresh.get("/api/v1/me")
    assert me.status_code == 200
    assert me.json()["user"]["email"] == "employee@movon.test"
    assert me.json()["tenant"]["id"] == str(db.info["tenant_id"])


async def test_invite_and_accept_creates_employee_in_same_tenant(client, signup) -> None:
    created = await signup("PT Undang", "hr@undang.test", "undang")
    assert created.status_code == 200
    invited = await client.post(
        "/api/v1/invites",
        headers=session_of(created),
        json={
            "name": "Sinta Baru",
            "email": "sinta@undang.test",
            "department": "Product",
            "role": "employee",
            "title": "Designer",
            "salary": 9_000_000,
        },
    )
    assert invited.status_code == 200
    assert last_email_to("sinta@undang.test") is not None
    assert invited.json()["email_status"] == "sent"
    token = invited.json()["invite_url"].split("token=")[1]

    preview = await client.get(f"/api/v1/invites/{token}")
    assert preview.status_code == 200
    assert preview.json()["company"] == "PT Undang"

    accepted = await client.post(
        "/api/v1/auth/accept-invite",
        json={"token": token, "password": "Sinta1234"},
    )
    assert accepted.status_code == 200
    assert accepted.json()["user"]["email"] == "sinta@undang.test"
    assert accepted.json()["tenant"]["slug"] == "undang"


async def test_password_reset_rotates_credentials(client) -> None:
    forgot = await client.post(
        "/api/v1/auth/forgot-password", json={"email": "employee@movon.test"}
    )
    assert forgot.status_code == 200
    message = last_email_to("employee@movon.test")
    assert message is not None
    token = next(part for part in message.body.split() if "token=" in part).split("token=")[1]

    reset = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "password": "BaruSekali1"},
    )
    assert reset.status_code == 200
    assert (
        await client.post(
            "/api/v1/auth/login",
            json={"email": "employee@movon.test", "password": DEMO_PASSWORD},
        )
    ).status_code == 401
    assert (
        await client.post(
            "/api/v1/auth/login",
            json={"email": "employee@movon.test", "password": "BaruSekali1"},
        )
    ).status_code == 200


async def test_forgot_password_does_not_reveal_unknown_email(client) -> None:
    before = len(outbox)
    response = await client.post(
        "/api/v1/auth/forgot-password", json={"email": "ghost@unknown.test"}
    )
    assert response.status_code == 200
    assert len(outbox) == before
