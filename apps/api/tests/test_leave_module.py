"""U9: leave module (approval scope, Google Calendar sync on approve/cancel, leave emails)."""

from datetime import date
from typing import Any

import httpx
import pytest
from helpers import add_leave, count
from sqlalchemy import update

from movon_hr.core.mailer import last_email_to
from movon_hr.modules.leave import service as leave_service
from movon_hr.modules.leave.models import LeaveRequest
from movon_hr.modules.settings import google_calendar
from movon_hr.modules.settings.models import CalendarSettings

pytestmark = pytest.mark.anyio

HR = "hr@movon.test"
MANAGER = "manager@movon.test"  # Engineering
EMPLOYEE = "employee@movon.test"  # Engineering
PRODUCT_EMPLOYEE = "andi@movon.test"
MONDAY = date(2030, 1, 7)
APPROVE = {"decision": "approved", "comment": "Disetujui"}


@pytest.fixture
async def google(db, monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str, Any]]:
    """Connect the team calendar and record Calendar API calls instead of sending them."""
    await db.execute(
        update(CalendarSettings).values(
            provider="google", connected=True, team_calendar_id="team@group.calendar.google.com"
        )
    )
    await db.commit()
    calls: list[tuple[str, str, Any]] = []

    async def fake_request(calendar, method: str, url: str, body: Any = None) -> dict:
        calls.append((method, url, body))
        return {"id": "evt-1"} if method == "POST" else {}

    monkeypatch.setattr(google_calendar, "calendar_request", fake_request)
    return calls


async def submit(client, headers, start: date = MONDAY, end: date = MONDAY) -> dict:
    response = await client.post(
        "/api/v1/leave-requests",
        headers=headers,
        json={"start": str(start), "end": str(end), "reason": "Acara keluarga"},
    )
    assert response.status_code == 200
    return response.json()


async def test_approval_syncs_the_team_calendar(client, login_headers, google) -> None:
    request = await submit(client, await login_headers(EMPLOYEE), MONDAY, date(2030, 1, 8))
    approved = await client.post(
        f"/api/v1/approvals/{request['id']}", headers=await login_headers(MANAGER), json=APPROVE
    )
    assert approved.status_code == 200
    body = approved.json()
    assert (body["status"], body["calendar_sync_status"]) == ("approved", "ok")
    assert body["team_calendar_event_id"] == "evt-1"
    method, url, event = google[0]
    assert method == "POST"
    assert url.endswith("/calendars/team%40group.calendar.google.com/events?sendUpdates=all")
    assert event["start"] == {"date": "2030-01-07"}
    assert event["end"] == {"date": "2030-01-09"}  # exclusive end
    assert event["attendees"] == [{"email": EMPLOYEE}]


async def test_calendar_failure_still_approves(
    client, db, login_headers, google, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def down(*args: object) -> dict:
        raise httpx.ConnectError("google down")

    monkeypatch.setattr(google_calendar, "calendar_request", down)
    request = await submit(client, await login_headers(EMPLOYEE))
    approved = await client.post(
        f"/api/v1/approvals/{request['id']}", headers=await login_headers(MANAGER), json=APPROVE
    )
    assert approved.status_code == 200
    assert (approved.json()["status"], approved.json()["calendar_sync_status"]) == (
        "approved",
        "failed",
    )
    listed = await client.get("/api/v1/leave-requests", headers=await login_headers(EMPLOYEE))
    assert listed.json()["items"][0]["calendar_sync_status"] == "failed"
    assert listed.json()["balance"]["used_days"] == 1


async def test_unconnected_calendar_is_skipped(client, login_headers) -> None:
    request = await submit(client, await login_headers(EMPLOYEE))
    approved = await client.post(
        f"/api/v1/approvals/{request['id']}", headers=await login_headers(MANAGER), json=APPROVE
    )
    assert approved.json()["calendar_sync_status"] == "skipped"


async def test_cancel_deletes_the_calendar_event(client, login_headers, google) -> None:
    staff = await login_headers(EMPLOYEE)
    request = await submit(client, staff)
    await client.post(
        f"/api/v1/approvals/{request['id']}", headers=await login_headers(MANAGER), json=APPROVE
    )
    cancelled = await client.post(f"/api/v1/leave-requests/{request['id']}/cancel", headers=staff)
    assert cancelled.status_code == 200
    assert (cancelled.json()["status"], cancelled.json()["calendar_sync_status"]) == (
        "cancelled",
        "removed",
    )
    method, url, _ = google[-1]
    assert method == "DELETE"
    assert url.endswith("/events/evt-1")
    again = await client.post(f"/api/v1/leave-requests/{request['id']}/cancel", headers=staff)
    assert again.status_code == 409


async def test_leave_emails_go_out_after_success_only(
    client, db, login_headers, monkeypatch: pytest.MonkeyPatch
) -> None:
    await submit(client, await login_headers(EMPLOYEE))
    for recipient in (MANAGER, HR):
        message = last_email_to(recipient)
        assert message is not None
        assert message.subject == "Permohonan cuti baru — Teamku"

    async def broken_audit(*args: object) -> None:
        raise RuntimeError("audit down")

    before = await count(db, LeaveRequest)
    monkeypatch.setattr(leave_service, "audit", broken_audit)
    with pytest.raises(RuntimeError):
        await client.post(
            "/api/v1/leave-requests",
            headers=await login_headers(PRODUCT_EMPLOYEE),
            json={"start": str(MONDAY), "end": str(MONDAY), "reason": "Acara keluarga"},
        )
    assert last_email_to("fajar@movon.test") is None  # Product manager
    assert await count(db, LeaveRequest) == before


async def test_manager_and_hr_approval_scope(client, db, login_headers) -> None:
    product = await add_leave(db, PRODUCT_EMPLOYEE, MONDAY, MONDAY, "Urusan", status="pending")
    own = await submit(client, await login_headers(MANAGER))
    manager = await login_headers(MANAGER)
    hr = await login_headers(HR)

    manager_list = (await client.get("/api/v1/approvals", headers=manager)).json()
    assert {item["department"] for item in manager_list["items"]} == {"Engineering"}
    hr_list = (await client.get("/api/v1/approvals", headers=hr)).json()
    assert str(product.id) in {item["id"] for item in hr_list["items"]}
    assert hr_list["pending"] == len(hr_list["items"])
    newest = hr_list["items"][0]
    assert (newest["id"], newest["employee_name"], newest["days"]) == (own["id"], "Raka Pratama", 1)

    outside = await client.post(f"/api/v1/approvals/{product.id}", headers=manager, json=APPROVE)
    assert outside.status_code == 403
    assert outside.json()["detail"] == "Permohonan berada di luar cakupan tim Anda"
    self_approval = await client.post(
        f"/api/v1/approvals/{own['id']}", headers=manager, json=APPROVE
    )
    assert self_approval.json()["detail"] == "Persetujuan diri sendiri tidak diperbolehkan"

    assert (
        await client.post(f"/api/v1/approvals/{product.id}", headers=hr, json=APPROVE)
    ).status_code == 200
    processed = await client.post(f"/api/v1/approvals/{product.id}", headers=hr, json=APPROVE)
    assert processed.status_code == 409
    missing = await client.post("/api/v1/approvals/not-an-id", headers=hr, json=APPROVE)
    assert missing.status_code == 404
