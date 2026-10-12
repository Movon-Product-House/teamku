from datetime import datetime

import pytest
from helpers import count, office
from sqlalchemy import select

from movon_hr.core.identity import Employee, Tenant
from movon_hr.core.security import verify_password
from movon_hr.core.time import JAKARTA
from movon_hr.modules.attendance.models import Attendance, LocationEvent
from movon_hr.modules.leave.models import LeaveRequest
from movon_hr.modules.notifications.models import Notification
from movon_hr.modules.settings.models import CalendarSettings, WorkLocation
from movon_hr.seed import DEMO_PASSWORD, run

pytestmark = pytest.mark.anyio


async def test_seed_creates_the_old_demo_store(db) -> None:
    employees = (await db.scalars(select(Employee))).all()
    assert len(employees) == 19
    assert [e.role for e in employees].count("manager") == 2
    assert [e.email for e in employees if e.role == "hr_admin"] == ["hr@movon.test"]
    assert [e.email for e in employees if e.is_remote] == ["dian@movon.test"]
    assert verify_password(DEMO_PASSWORD, employees[0].password_hash)

    hq = await office(db)
    assert (hq.name, hq.latitude, hq.longitude, hq.radius_meters) == (
        "Jakarta HQ",
        -6.2,
        106.8166,
        300,
    )
    assert {e.work_location_id for e in employees} == {hq.id}
    assert await count(db, WorkLocation) == 1
    assert await count(db, CalendarSettings) == 1

    sessions = (await db.scalars(select(Attendance))).all()
    assert len(sessions) == 7
    assert {s.checked_in_at.astimezone(JAKARTA).date() for s in sessions} == {
        datetime.now(JAKARTA).date()
    }
    assert [s.anomaly for s in sessions].count("low_accuracy") == 1
    assert await count(db, LocationEvent) == 7
    assert await count(db, LeaveRequest) == 1
    assert await count(db, Notification) == 2


async def test_if_empty_skips_a_seeded_database(db) -> None:
    assert await run(if_empty=True) is False
    assert await count(db, Tenant) == 1
