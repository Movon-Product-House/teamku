from datetime import UTC, datetime

import pytest
from helpers import add_leave, location_events, set_employee

from movon_hr.modules.settings.models import WorkLocation
from movon_hr.seed import OFFICE_LATITUDE, OFFICE_LONGITUDE, OFFICE_RADIUS_METERS

pytestmark = pytest.mark.anyio


async def test_hr_can_add_location_and_assign_employee_to_its_geofence(
    client, login_headers, employee_id
) -> None:
    hr = await login_headers("hr@movon.test")
    created = await client.post(
        "/api/v1/settings/locations",
        headers=hr,
        json={
            "name": "Bandung Site",
            "latitude": -6.9175,
            "longitude": 107.6191,
            "radius_meters": 250,
        },
    )
    assert created.status_code == 200
    location_id = created.json()["id"]
    assigned = await client.patch(
        f"/api/v1/employees/{await employee_id('fresh@movon.test')}",
        headers=hr,
        json={"work_location_id": location_id},
    )
    assert assigned.status_code == 200
    assert assigned.json()["work_location"]["name"] == "Bandung Site"

    checked_in = await client.post(
        "/api/v1/attendance/check-in",
        headers=await login_headers("fresh@movon.test") | {"Idempotency-Key": "bandung"},
        json={
            "latitude": -6.9175,
            "longitude": 107.6191,
            "accuracy_meters": 10,
            "selfie_captured": True,
            "location_share_approved": True,
            "agenda": [{"title": "Site visit"}],
        },
    )
    assert checked_in.status_code == 200
    assert checked_in.json()["distance_meters"] == 0


async def test_duplicate_location_is_rejected_and_hidden_from_list(
    client, db, login_headers
) -> None:
    hr = await login_headers("hr@movon.test")
    duplicate = await client.post(
        "/api/v1/settings/locations",
        headers=hr,
        json={
            "name": "jakarta hq",
            "latitude": -6.2,
            "longitude": 106.8166,
            "radius_meters": 300,
        },
    )
    assert duplicate.status_code == 409

    # A legacy duplicate row of the primary location must not show up twice.
    db.add(
        WorkLocation(
            name="Jakarta HQ",
            latitude=OFFICE_LATITUDE,
            longitude=OFFICE_LONGITUDE,
            radius_meters=OFFICE_RADIUS_METERS,
        )
    )
    await db.commit()
    locations = (await client.get("/api/v1/settings/locations", headers=hr)).json()["items"]
    assert [item["name"] for item in locations] == ["Jakarta HQ"]


async def test_field_employee_checkout_records_location_and_dashboard_summarizes_today(
    client, db, login_headers
) -> None:
    await set_employee(db, "fresh@movon.test", is_remote=True)
    employee = await login_headers("fresh@movon.test")
    await client.post(
        "/api/v1/attendance/check-in",
        headers=employee | {"Idempotency-Key": "field"},
        json={
            "latitude": -6.9,
            "longitude": 107.6,
            "accuracy_meters": 12,
            "selfie_captured": True,
            "location_share_approved": True,
            "agenda": [{"title": "Visit customer"}],
        },
    )
    checked_out = await client.post(
        "/api/v1/attendance/check-out",
        headers=employee,
        json={
            "summary": "Customer visit complete",
            "latitude": -6.91,
            "longitude": 107.61,
            "accuracy_meters": 15,
        },
    )
    assert checked_out.status_code == 200
    events = await location_events(db, "fresh@movon.test")
    assert [event.kind for event in events] == ["check_in", "check_out"]
    assert events[-1].lat == -6.91

    today = datetime.now(UTC).astimezone().date()
    await add_leave(db, "dian@movon.test", today, today, "Cuti", status="approved")
    dashboard = (
        await client.get("/api/v1/dashboard", headers=await login_headers("hr@movon.test"))
    ).json()
    assert {
        "headcount",
        "present",
        "absent",
        "on_leave",
        "late",
        "attendance_rate",
    } <= dashboard.keys()
    assert dashboard["on_leave"] == 1
