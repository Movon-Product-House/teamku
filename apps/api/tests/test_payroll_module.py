"""U11: payroll rules, duplicate period and publish notifications."""

import pytest
from helpers import count, set_employee
from sqlalchemy import func, select

from movon_hr.core.identity import Employee
from movon_hr.modules.audit.models import AuditLog
from movon_hr.modules.notifications.models import Notification
from movon_hr.modules.payroll.models import PayrollRun
from movon_hr.modules.payroll.rules import payroll_item

HR = "hr@movon.test"


def test_payroll_item_deducts_two_percent_rounded_half_up() -> None:
    assert payroll_item("e", "Sinta", 8_000_000) == {
        "employee_id": "e",
        "employee": "Sinta",
        "gross_rupiah": 8_000_000,
        "deductions_rupiah": 160_000,
        "net_rupiah": 7_840_000,
    }
    # 0.5 rupiah rounds up (Decimal ROUND_HALF_UP, not banker's rounding).
    assert payroll_item("e", "x", 25)["deductions_rupiah"] == 1
    assert payroll_item("e", "x", 125)["deductions_rupiah"] == 3


@pytest.mark.anyio
async def test_duplicate_period_returns_the_existing_run(client, db, login_headers) -> None:
    hr = await login_headers(HR)
    first = await client.post("/api/v1/payroll/runs", headers=hr, json={"month": "2026-10"})
    again = await client.post("/api/v1/payroll/runs", headers=hr, json={"month": "2026-10"})
    assert (first.status_code, again.status_code) == (200, 200)
    assert again.json() == first.json()
    assert await count(db, PayrollRun) == 1
    calculated = select(func.count()).where(AuditLog.action == "payroll.calculated")
    assert await db.scalar(calculated) == 1
    body = first.json()
    assert body["total_net_rupiah"] == body["total_gross_rupiah"] - body["total_deductions_rupiah"]


@pytest.mark.anyio
async def test_publish_notifies_every_employee_including_suspended(
    client, db, login_headers
) -> None:
    await set_employee(db, "andi@movon.test", status="suspended")
    hr = await login_headers(HR)
    run = (await client.post("/api/v1/payroll/runs", headers=hr, json={"month": "2026-11"})).json()
    assert "Andi Gunawan" not in {item["employee"] for item in run["items"]}
    await client.post(f"/api/v1/payroll/runs/{run['id']}/finalize", headers=hr)
    published = await client.post(f"/api/v1/payroll/runs/{run['id']}/publish", headers=hr)
    assert published.status_code == 200

    notified = await db.scalars(
        select(Notification.user_id).where(Notification.title == "Slip gaji tersedia")
    )
    assert sorted(notified) == sorted(await db.scalars(select(Employee.id)))
    unknown = await client.post("/api/v1/payroll/runs/not-a-uuid/finalize", headers=hr)
    assert unknown.status_code == 404
