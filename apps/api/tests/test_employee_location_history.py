from datetime import UTC, datetime, timedelta

import pytest
from helpers import add_attendance, add_location_event

from movon_hr.seed import OFFICE_LATITUDE, OFFICE_LONGITUDE

pytestmark = pytest.mark.anyio


async def test_manager_cannot_read_other_department_history(
    client, login_headers, employee_id
) -> None:
    response = await client.get(
        f"/api/v1/employees/{await employee_id('rizky@movon.test')}/location-history",
        headers=await login_headers("manager@movon.test"),
    )

    assert response.status_code == 404


async def test_hr_can_list_location_events_for_any_tenant_employee(
    client, login_headers, employee_id
) -> None:
    target = await employee_id("employee@movon.test")
    response = await client.get(
        f"/api/v1/employees/{target}/location-history",
        headers=await login_headers("hr@movon.test"),
    )

    assert response.status_code == 200
    assert response.json()["employee_id"] == target


async def test_employee_cannot_fetch_another_employee_location_history(
    client, login_headers, employee_id
) -> None:
    response = await client.get(
        f"/api/v1/employees/{await employee_id('andi@movon.test')}/location-history",
        headers=await login_headers("employee@movon.test"),
    )

    assert response.status_code == 403


async def test_detail_history_is_chronological_check_in_and_reverify(
    client, db, login_headers, employee_id
) -> None:
    earlier = datetime.now(UTC).replace(microsecond=0)
    # location_events.attendance_id is a FK now, so the events need a real session.
    session = await add_attendance(
        db,
        "employee@movon.test",
        checked_in_at=earlier - timedelta(hours=1),
        agenda=[{"title": "Riwayat lokasi"}],
    )
    await add_location_event(
        db,
        "employee@movon.test",
        session.id,
        kind="reverify",
        at=earlier,
        lat=OFFICE_LATITUDE,
        lng=OFFICE_LONGITUDE,
        accuracy=10,
        distance_meters=0,
        inside_geofence=True,
    )
    await add_location_event(
        db,
        "employee@movon.test",
        session.id,
        kind="check_in",
        at=earlier - timedelta(hours=1),
        lat=OFFICE_LATITUDE,
        lng=OFFICE_LONGITUDE,
        accuracy=12,
        distance_meters=0,
        inside_geofence=True,
    )
    target = await employee_id("employee@movon.test")

    response = await client.get(
        f"/api/v1/employees/{target}/location-history",
        headers=await login_headers("manager@movon.test"),
    )

    assert response.status_code == 200
    kinds = [item["kind"] for item in response.json()["items"]]
    assert kinds == ["check_in", "reverify"]
    assert response.json()["items"][0]["at"] <= response.json()["items"][-1]["at"]

    profile = await client.get(
        f"/api/v1/employees/{target}", headers=await login_headers("manager@movon.test")
    )
    assert profile.status_code == 200
    assert profile.json()["id"] == target
