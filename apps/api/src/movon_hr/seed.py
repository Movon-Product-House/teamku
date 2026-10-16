"""Demo company seed: the demo tenant, its 19 employees and today's sample activity.

``python -m movon_hr.seed [--if-empty]``; ``--if-empty`` seeds only when there are no tenants.
"""

import argparse
import asyncio
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from movon_hr.core import db as core_db
from movon_hr.core.identity import Employee, Tenant
from movon_hr.core.security import hash_password_async
from movon_hr.core.time import JAKARTA
from movon_hr.modules.attendance.models import Attendance, LocationEvent
from movon_hr.modules.leave.models import LeaveRequest
from movon_hr.modules.notifications.models import Notification
from movon_hr.modules.settings.models import CalendarSettings, WorkLocation

DEMO_TENANT_NAME = "PT Movon Solusi Kreatif"
DEMO_TENANT_SLUG = "pt-movon-solusi-kreatif"
DEMO_PASSWORD = "Demo123!"  # noqa: S105 - public demo password (plan R2)
OFFICE_LATITUDE = -6.2
OFFICE_LONGITUDE = 106.8166
OFFICE_RADIUS_METERS = 300

# (name, email, role, department, title, salary), in the old seed order.
# fmt: off
PEOPLE = [
    ("Nadia Putri", "hr@movon.test", "hr_admin", "Human Resources", "HR Lead", 12_000_000),
    ("Raka Pratama", "manager@movon.test", "manager", "Engineering", "Engineering Manager", 15_000_000),
    ("Sinta Lestari", "employee@movon.test", "employee", "Engineering", "Frontend Engineer", 8_000_000),
    ("Rani Prasetyo", "fresh@movon.test", "employee", "Engineering", "QA Tester", 8_000_000),
    ("Andi Gunawan", "andi@movon.test", "employee", "Product", "Product Designer", 9_000_000),
    ("Rizky Pranata", "rizky@movon.test", "employee", "Sales", "Sales Lead", 11_000_000),
    ("Budi Santoso", "budi@movon.test", "employee", "Operations", "Logistics Staff", 7_000_000),
    ("Dewi Lestari", "dewi@movon.test", "employee", "Creative", "Marketing Executive", 8_500_000),
    ("Fajar Nugroho", "fajar@movon.test", "manager", "Product", "Product Manager", 14_000_000),
    ("Ayu Maharani", "ayu@movon.test", "employee", "Engineering", "QA Engineer", 8_500_000),
    ("Gilang Ramadhan", "gilang@movon.test", "employee", "Engineering", "Backend Engineer", 10_000_000),
    ("Maya Sari", "maya@movon.test", "employee", "Human Resources", "People Ops", 8_500_000),
    ("Kevin Wijaya", "kevin@movon.test", "employee", "Creative", "Copywriter", 7_500_000),
    ("Lina Hartati", "lina@movon.test", "employee", "Finance", "Finance Staff", 9_000_000),
    ("Yoga Saputra", "yoga@movon.test", "employee", "Operations", "Project Officer", 8_000_000),
    ("Nabila Azzahra", "nabila@movon.test", "employee", "Sales", "Account Executive", 8_000_000),
    ("Reza Maulana", "reza@movon.test", "employee", "Product", "Product Analyst", 8_500_000),
    ("Citra Amelia", "citra@movon.test", "employee", "Management", "Executive Assistant", 9_000_000),
    ("Dian Permata", "dian@movon.test", "employee", "Engineering", "Engineering Intern", 4_500_000),
]
# fmt: on
REMOTE = "dian@movon.test"
# Checked in today from 08:50 Jakarta, four minutes apart.
CHECKED_IN = [
    "manager@movon.test",
    "andi@movon.test",
    "rizky@movon.test",
    "budi@movon.test",
    "dewi@movon.test",
    "ayu@movon.test",
    "gilang@movon.test",
]

_password_hash: str | None = None


async def demo_password_hash() -> str:
    """Argon2 is slow on purpose: hash the shared demo password once per process."""
    global _password_hash
    if _password_hash is None:
        _password_hash = await hash_password_async(DEMO_PASSWORD)
    return _password_hash


async def seed_demo(session: AsyncSession) -> Tenant:
    """Insert the demo company and bind its tenant to ``session``; the caller commits."""
    tenant = Tenant(name=DEMO_TENANT_NAME, slug=DEMO_TENANT_SLUG)
    session.add(tenant)
    await session.flush()
    session.info["tenant_id"] = tenant.id

    office = WorkLocation(
        name="Jakarta HQ",
        latitude=OFFICE_LATITUDE,
        longitude=OFFICE_LONGITUDE,
        radius_meters=OFFICE_RADIUS_METERS,
        is_primary=True,
    )
    session.add_all([office, CalendarSettings()])
    await session.flush()

    password_hash = await demo_password_hash()
    employees = {
        email: Employee(
            name=name,
            email=email,
            role=role,
            department=department,
            title=title,
            status="active",
            salary=salary,
            password_hash=password_hash,
            is_remote=email == REMOTE,
            work_location_id=office.id,
        )
        for name, email, role, department, title, salary in PEOPLE
    }
    session.add_all(employees.values())
    await session.flush()

    jakarta_now = datetime.now(JAKARTA)
    sessions = [
        Attendance(
            employee_id=employees[email].id,
            checked_in_at=(
                jakarta_now.replace(hour=8, minute=50, second=0, microsecond=0)
                + timedelta(minutes=index * 4)
            ).astimezone(UTC),
            latitude=OFFICE_LATITUDE,
            longitude=OFFICE_LONGITUDE,
            accuracy_meters=18,
            agenda=[{"title": "Prioritas utama", "status": "done" if index < 4 else "planned"}],
            anomaly="low_accuracy" if index == 5 else None,
        )
        for index, email in enumerate(CHECKED_IN)
    ]
    session.add_all(sessions)
    await session.flush()
    session.add_all(
        LocationEvent(
            employee_id=item.employee_id,
            attendance_id=item.id,
            kind="check_in",
            at=item.checked_in_at,
            lat=OFFICE_LATITUDE,
            lng=OFFICE_LONGITUDE,
            accuracy=18,
            distance_meters=0,
            inside_geofence=True,
            anomaly=item.anomaly,
        )
        for item in sessions
    )

    today = datetime.now(JAKARTA).date()
    session.add(
        LeaveRequest(
            employee_id=employees["ayu@movon.test"].id,
            start_date=today + timedelta(days=7),
            end_date=today + timedelta(days=8),
            reason="Acara keluarga",
        )
    )
    session.add_all(
        [
            Notification(
                user_id=employees["manager@movon.test"].id,
                title="Permohonan cuti baru",
                detail="Ayu Maharani menunggu persetujuan Anda.",
                target="/app/approvals",
            ),
            Notification(
                user_id=employees["hr@movon.test"].id,
                title="Data demo siap",
                detail="Dashboard operasional sudah diperbarui.",
                target="/app/overview",
            ),
        ]
    )
    await session.flush()
    return tenant


async def run(*, if_empty: bool) -> bool:
    """Seed in its own transaction; returns False when skipped by ``if_empty``."""
    async with core_db.SessionLocal() as session:
        if if_empty:
            existing = await session.scalar(
                select(Tenant.id).limit(1).execution_options(cross_tenant=True)
            )
            if existing is not None:
                return False
        await seed_demo(session)
        await session.commit()
    return True


async def _main(*, if_empty: bool) -> bool:
    try:
        return await run(if_empty=if_empty)
    finally:
        await core_db.engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed the Teamku demo company.")
    parser.add_argument("--if-empty", action="store_true", help="skip when any tenant exists")
    args = parser.parse_args()
    seeded = asyncio.run(_main(if_empty=args.if_empty))
    print("Demo data seeded." if seeded else "Tenants exist; demo seed skipped.")


if __name__ == "__main__":
    main()
