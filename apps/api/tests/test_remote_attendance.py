import pytest
from helpers import set_employee
from sqlalchemy import select

from movon_hr.modules.auth.models import Invitation
from movon_hr.seed import OFFICE_LATITUDE, OFFICE_LONGITUDE

pytestmark = pytest.mark.anyio


def check_in_payload(**overrides: object) -> dict:
    payload = {
        "latitude": OFFICE_LATITUDE,
        "longitude": OFFICE_LONGITUDE,
        "accuracy_meters": 10,
        "selfie_captured": True,
        "location_share_approved": True,
        "agenda": [{"title": "Kerja remote"}],
    }
    payload.update(overrides)
    return payload


async def test_remote_employee_can_check_in_far_from_office(client, db, login_headers) -> None:
    await set_employee(db, "fresh@movon.test", is_remote=True)

    response = await client.post(
        "/api/v1/attendance/check-in",
        headers=await login_headers("fresh@movon.test") | {"Idempotency-Key": "remote-far"},
        json=check_in_payload(latitude=-6.3, longitude=106.8166),
    )

    assert response.status_code == 200
    assert response.json()["id"]


async def test_office_employee_far_from_office_is_still_rejected(client, login_headers) -> None:
    response = await client.post(
        "/api/v1/attendance/check-in",
        headers=await login_headers("fresh@movon.test") | {"Idempotency-Key": "office-far"},
        json=check_in_payload(latitude=-6.3, longitude=106.8166),
    )

    assert response.status_code == 403
    assert "ditolak" in response.json()["detail"].lower()


async def test_create_and_invite_remote_employee_persists_flag(client, db, login_headers) -> None:
    hr = await login_headers("hr@movon.test")
    created = await client.post(
        "/api/v1/employees",
        headers=hr,
        json={
            "name": "Remote Staff",
            "email": "remote.staff@movon.test",
            "department": "Engineering",
            "role": "employee",
            "salary": 8_000_000,
            "is_remote": True,
        },
    )
    assert created.status_code == 200
    assert created.json()["is_remote"] is True

    listed = (await client.get("/api/v1/employees", headers=hr)).json()["items"]
    remote = next(item for item in listed if item["email"] == "remote.staff@movon.test")
    assert remote["is_remote"] is True

    invited = await client.post(
        "/api/v1/invites",
        headers=hr,
        json={
            "name": "Remote Invite",
            "email": "remote.invite@movon.test",
            "department": "Engineering",
            "role": "employee",
            "salary": 8_000_000,
            "is_remote": True,
        },
    )
    assert invited.status_code == 200
    invitation = await db.scalar(
        select(Invitation).where(Invitation.email == "remote.invite@movon.test")
    )
    assert invitation is not None
    assert invitation.is_remote is True
