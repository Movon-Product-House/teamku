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


async def test_read_one_marks_only_that_notification(client, db, login_headers) -> None:
    manager = await employee(db, "manager@movon.test")
    await notify(db, manager.id, "Baru", "detail", "/app/approvals")
    await db.commit()
    headers = await login_headers("manager@movon.test")
    newest = (await client.get("/api/v1/notifications", headers=headers)).json()["items"][0]

    marked = await client.post(f"/api/v1/notifications/{newest['id']}/read", headers=headers)
    assert marked.json() == {"ok": True}

    listed = (await client.get("/api/v1/notifications", headers=headers)).json()
    assert [item["read"] for item in listed["items"]] == [True, False]
    assert listed["unread"] == 1


async def test_read_one_of_someone_else_is_404_and_leaves_it_unread(
    client, db, login_headers
) -> None:
    manager = await employee(db, "manager@movon.test")
    await notify(db, manager.id, "Baru", "detail", "/app/approvals")
    await db.commit()
    headers = await login_headers("manager@movon.test")
    newest = (await client.get("/api/v1/notifications", headers=headers)).json()["items"][0]

    marked = await client.post(
        f"/api/v1/notifications/{newest['id']}/read",
        headers=await login_headers("hr@movon.test"),
    )
    assert marked.status_code == 404

    assert (await client.get("/api/v1/notifications", headers=headers)).json()["unread"] == 2


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
