"""U5: notifications and audit-logs served from Postgres."""

import pytest
from helpers import employee

from movon_hr.modules.audit.service import audit
from movon_hr.modules.notifications.service import notify

pytestmark = pytest.mark.anyio


async def test_notifications_newest_first_and_read_all_is_per_user(
    client, db, login_headers
) -> None:
    manager = await employee(db, "manager@movon.test")
    await notify(db, manager.id, "Baru", "detail", "/app/approvals")
    await db.commit()
    headers = await login_headers("manager@movon.test")

    listed = (await client.get("/api/v1/notifications", headers=headers)).json()
    assert [item["title"] for item in listed["items"]] == ["Baru", "Permohonan cuti baru"]
    assert listed["unread"] == 2
    assert listed["items"][0]["created_at"].endswith("Z")

    assert (await client.post("/api/v1/notifications/read-all", headers=headers)).json() == {
        "ok": True
    }
    assert (await client.get("/api/v1/notifications", headers=headers)).json()["unread"] == 0
    hr = (
        await client.get("/api/v1/notifications", headers=await login_headers("hr@movon.test"))
    ).json()
    assert hr["unread"] == 1


async def test_audit_logs_hr_only_newest_first_with_utc_offset(client, db, login_headers) -> None:
    hr = await employee(db, "hr@movon.test")
    await audit(db, "first", hr, "a")
    await audit(db, "second", hr, "b")
    await db.commit()

    denied = await client.get(
        "/api/v1/audit-logs", headers=await login_headers("employee@movon.test")
    )
    assert denied.status_code == 403

    items = (
        await client.get("/api/v1/audit-logs", headers=await login_headers("hr@movon.test"))
    ).json()["items"]
    assert [item["action"] for item in items] == ["second", "first"]
    assert items[0]["at"].endswith("+00:00")
    assert items[0]["actor"] == str(hr.id)
