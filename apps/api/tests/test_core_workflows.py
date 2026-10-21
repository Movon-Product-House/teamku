from datetime import datetime

import pytest
from helpers import session_cookie
from sqlalchemy import select

from movon_hr.core.time import JAKARTA
from movon_hr.modules.attendance.models import Attendance

pytestmark = pytest.mark.anyio
HR = "hr@movon.test"
MANAGER = "manager@movon.test"
EMPLOYEE = "employee@movon.test"
PRODUCT_MANAGER = "fajar@movon.test"


async def test_leave_request_approval_updates_dashboard_and_balance(client, login_headers) -> None:
    submitted = await client.post(
        "/api/v1/leave-requests",
        headers=await login_headers(EMPLOYEE),
        json={"start": "2026-10-12", "end": "2026-10-13", "reason": "Acara keluarga"},
    )
    assert submitted.status_code == 200
    request_id = submitted.json()["id"]

    manager_dashboard = await client.get("/api/v1/dashboard", headers=await login_headers(MANAGER))
    assert manager_dashboard.json()["pending_approvals"] >= 1

    approved = await client.post(
        f"/api/v1/approvals/{request_id}",
        headers=await login_headers(MANAGER),
        json={"decision": "approved", "comment": "Disetujui, selamat beristirahat"},
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"

    requests = (
        await client.get("/api/v1/leave-requests", headers=await login_headers(EMPLOYEE))
    ).json()
    assert requests["items"][0]["status"] == "approved"
    assert requests["balance"]["remaining_days"] == 10


async def test_hr_can_create_employee_and_dashboard_uses_the_new_record(
    client, login_headers
) -> None:
    hr = await login_headers(HR)
    before = (await client.get("/api/v1/dashboard", headers=hr)).json()["headcount"]
    created = await client.post(
        "/api/v1/employees",
        headers=hr,
        json={
            "name": "Dimas Wijaya",
            "email": "dimas.wijaya@movon.test",
            "department": "Product",
            "role": "employee",
            "salary": 9_500_000,
        },
    )
    assert created.status_code == 200

    after = (await client.get("/api/v1/dashboard", headers=hr)).json()["headcount"]
    assert after == before + 1


async def test_payroll_requires_valid_state_transitions_before_publish(
    client, login_headers
) -> None:
    hr = await login_headers(HR)
    created = await client.post("/api/v1/payroll/runs", headers=hr, json={"month": "2026-10"})
    assert created.status_code == 200
    run_id = created.json()["id"]

    too_early = await client.post(f"/api/v1/payroll/runs/{run_id}/publish", headers=hr)
    assert too_early.status_code == 409

    finalized = await client.post(f"/api/v1/payroll/runs/{run_id}/finalize", headers=hr)
    assert finalized.json()["status"] == "finalized"

    published = await client.post(f"/api/v1/payroll/runs/{run_id}/publish", headers=hr)
    assert published.json()["status"] == "published"

    employee_payslips = await client.get(
        "/api/v1/payroll/payslips", headers=await login_headers(EMPLOYEE)
    )
    assert employee_payslips.status_code == 200
    assert employee_payslips.json()["items"][0]["employee"] == "Sinta Lestari"


async def test_employee_cannot_run_payroll_or_approve_requests(client, login_headers) -> None:
    employee = await login_headers(EMPLOYEE)
    payroll = await client.post("/api/v1/payroll/runs", headers=employee, json={"month": "2026-10"})
    assert payroll.status_code == 403

    approval = await client.get("/api/v1/approvals", headers=employee)
    assert approval.status_code == 403


async def test_forged_and_missing_session_tokens_are_rejected_and_logout_revokes(
    client, login_headers
) -> None:
    assert (await client.get("/api/v1/me")).status_code == 401
    assert (await client.get("/api/v1/me", headers=session_cookie("e-hr"))).status_code == 401

    session_headers = await login_headers(EMPLOYEE)
    assert (await client.get("/api/v1/me", headers=session_headers)).status_code == 200
    assert (await client.post("/api/v1/auth/logout", headers=session_headers)).status_code == 200
    assert (await client.get("/api/v1/me", headers=session_headers)).status_code == 401


async def test_manager_cannot_approve_a_request_outside_their_department(
    client, login_headers
) -> None:
    submitted = await client.post(
        "/api/v1/leave-requests",
        headers=await login_headers(EMPLOYEE),
        json={"start": "2026-11-02", "end": "2026-11-02", "reason": "Urusan keluarga"},
    )
    request_id = submitted.json()["id"]

    denied = await client.post(
        f"/api/v1/approvals/{request_id}",
        headers=await login_headers(PRODUCT_MANAGER),
        json={"decision": "approved", "comment": "Mencoba lintas departemen"},
    )

    assert denied.status_code == 403
    manager_items = (
        await client.get("/api/v1/approvals", headers=await login_headers(MANAGER))
    ).json()
    request = next(item for item in manager_items["items"] if item["id"] == request_id)
    assert request["status"] == "pending"


async def test_suspended_employee_is_removed_from_all_dashboard_counts(
    client, login_headers, employee_id
) -> None:
    hr_headers = await login_headers(HR)
    before = (await client.get("/api/v1/dashboard", headers=hr_headers)).json()
    assert before["headcount"] == 19
    assert before["present"] == 7

    response = await client.patch(
        f"/api/v1/employees/{await employee_id(MANAGER)}",
        headers=hr_headers,
        json={"status": "suspended"},
    )
    assert response.status_code == 200

    after = (await client.get("/api/v1/dashboard", headers=hr_headers)).json()
    assert after["headcount"] == 18
    assert after["present"] == 6


async def test_seed_attendance_uses_the_current_jakarta_business_date(db) -> None:
    jakarta_dates = {
        checked_in_at.astimezone(JAKARTA).date()
        for checked_in_at in await db.scalars(select(Attendance.checked_in_at))
    }
    assert jakarta_dates == {datetime.now(JAKARTA).date()}
