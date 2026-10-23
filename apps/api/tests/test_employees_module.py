"""U7: employees module (visibility, salary hiding, create, suspend, work location)."""

import pytest
from helpers import employee
from sqlalchemy import func, select

from movon_hr.core.identity import AuthSession, Employee

pytestmark = pytest.mark.anyio

HR = "hr@movon.test"
MANAGER = "manager@movon.test"
EMPLOYEE = "employee@movon.test"
REMOTE = "dian@movon.test"
NEW = {
    "name": "Nadia Putri",
    "email": "nadia@movon.test",
    "department": "Product",
    "role": "employee",
    "salary": 1,
}


async def test_visibility_and_salary_per_role(client, db, login_headers, employee_id) -> None:
    manager = await employee(db, MANAGER)
    hr_list = (await client.get("/api/v1/employees", headers=await login_headers(HR))).json()
    assert hr_list["total"] == await db.scalar(select(func.count()).select_from(Employee))
    assert all(item["salary"] is not None for item in hr_list["items"])

    listed = await client.get("/api/v1/employees", headers=await login_headers(MANAGER))
    items = listed.json()["items"]
    assert items and {item["department"] for item in items} == {manager.department}
    assert all(item["salary"] is None for item in items)

    staff = await login_headers(EMPLOYEE)
    assert (await client.get("/api/v1/employees", headers=staff)).status_code == 403
    own = await client.get(f"/api/v1/employees/{await employee_id(EMPLOYEE)}", headers=staff)
    assert own.status_code == 200
    assert own.json()["salary"] is not None
    other = await client.get(f"/api/v1/employees/{await employee_id(HR)}", headers=staff)
    assert other.status_code == 404
    malformed = await client.get("/api/v1/employees/e-unknown", headers=staff)
    assert malformed.status_code == 404


async def test_work_mode_and_location_are_derived(client, login_headers, employee_id) -> None:
    hr = await login_headers(HR)
    remote = (await client.get(f"/api/v1/employees/{await employee_id(REMOTE)}", headers=hr)).json()
    assert (remote["work_mode"], remote["work_location"]) == ("field", None)
    office = (await client.get(f"/api/v1/employees/{await employee_id(HR)}", headers=hr)).json()
    assert office["work_mode"] == "office"
    assert office["work_location"]["name"] == "Jakarta HQ"
    assert "password_hash" not in office
    assert "tenant_id" not in office


async def test_temporary_password_only_without_password(client, login_headers) -> None:
    hr = await login_headers(HR)
    generated = await client.post(
        "/api/v1/employees",
        headers=hr,
        json=NEW | {"work_location_id": "office-default"},
    )
    assert generated.status_code == 200
    assert generated.json()["result"] == "temporary_password"
    assert generated.json()["temporary_password"]
    # An unknown location id is not validated on create; the primary location is shown.
    assert generated.json()["work_location"]["name"] == "Jakarta HQ"

    chosen = await client.post(
        "/api/v1/employees",
        headers=hr,
        json=NEW | {"email": "nadia2@movon.test", "password": "Rahasia123", "work_location_id": ""},
    )
    assert chosen.status_code == 200
    assert chosen.json()["result"] == "password_set"
    assert "temporary_password" not in chosen.json()
    assert chosen.json()["work_location_id"] is None

    taken = await client.post("/api/v1/employees", headers=hr, json=NEW)
    assert (taken.status_code, taken.json()["detail"]) == (409, "Email kerja sudah digunakan")


async def test_suspend_revokes_sessions_but_not_for_self(
    client, db, login_headers, employee_id
) -> None:
    hr = await login_headers(HR)
    staff = await login_headers(EMPLOYEE)
    target = await employee_id(EMPLOYEE)
    response = await client.patch(
        f"/api/v1/employees/{target}", headers=hr, json={"status": "suspended"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "suspended"
    sessions = select(func.count()).select_from(AuthSession)
    assert await db.scalar(sessions.where(AuthSession.employee_id == target)) == 0
    assert (await client.get("/api/v1/notifications", headers=staff)).status_code == 401

    self_suspend = await client.patch(
        f"/api/v1/employees/{await employee_id(HR)}", headers=hr, json={"status": "terminated"}
    )
    assert self_suspend.status_code == 409


async def test_work_location_must_exist_on_update(client, login_headers, employee_id) -> None:
    hr = await login_headers(HR)
    url = f"/api/v1/employees/{await employee_id(REMOTE)}"
    for bad in ("", "office-default", "0192f6a0-0000-7000-8000-000000000000"):
        response = await client.patch(url, headers=hr, json={"work_location_id": bad})
        assert (response.status_code, response.json()["detail"]) == (
            422,
            "Lokasi kerja tidak ditemukan",
        )
    primary = (await client.get("/api/v1/settings/office", headers=hr)).json()["id"]
    moved = await client.patch(url, headers=hr, json={"work_location_id": primary})
    assert (moved.json()["is_remote"], moved.json()["work_mode"]) == (False, "office")
