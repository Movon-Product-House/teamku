"""Legacy in-memory demo store, still read by core/persistence.py; deleted in U12.

Serves no routes: every endpoint lives in its domain module.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta

from movon_hr.core import mailer
from movon_hr.core.mailer import MailKind, reset_outbox, send_email
from movon_hr.core.security import hash_password
from movon_hr.core.settings import settings
from movon_hr.core.tenancy import (
    DEMO_TENANT_ID,
    DEMO_TENANT_NAME,
    DEMO_TENANT_SLUG,
    bind_tenant,
    clear_registry,
    iter_stores,
    put_store,
    store,
)
from movon_hr.core.time import JAKARTA

_mail_tasks: set[asyncio.Task] = set()


def dispatch_email(to: str, subject: str, body: str, *, kind: MailKind = "generic") -> None:
    """Legacy fire-and-forget send for the old sync helpers; deleted in U12."""
    if settings.mail_provider != "resend":
        mailer._queue_console(to, subject, body, kind)  # no I/O: inline, like before
        return
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        asyncio.run(send_email(to, subject, body, kind=kind))
        return
    task = loop.create_task(send_email(to, subject, body, kind=kind))
    _mail_tasks.add(task)
    task.add_done_callback(_mail_tasks.discard)


@dataclass
class Employee:
    id: str
    name: str
    email: str
    role: str
    department: str
    title: str = "Staff"
    status: str = "active"
    salary: int = 8_000_000
    password_hash: str = ""
    tenant_id: str = ""
    is_remote: bool = False
    work_location_id: str | None = "office-default"


@dataclass
class Session:
    token: str
    employee_id: str
    created_at: datetime
    expires_at: datetime
    tenant_id: str = ""


@dataclass
class Invitation:
    token: str
    tenant_id: str
    email: str
    name: str
    role: str
    department: str
    title: str
    salary: int
    invited_by: str
    expires_at: datetime
    accepted_at: datetime | None = None
    is_remote: bool = False
    work_location_id: str | None = None


@dataclass
class PasswordReset:
    token: str
    tenant_id: str
    employee_id: str
    expires_at: datetime
    used_at: datetime | None = None


@dataclass
class Attendance:
    id: str
    employee_id: str
    checked_in_at: datetime
    latitude: float
    longitude: float
    accuracy_meters: float
    agenda: list[dict]
    anomaly: str | None = None
    checked_out_at: datetime | None = None
    summary: str | None = None


@dataclass
class LeaveRequest:
    id: str
    employee_id: str
    start: date
    end: date
    reason: str
    request_type: str = "time_off"
    status: str = "pending"
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    approver_comment: str | None = None
    calendar_sync_status: str = "not_applicable"
    employee_calendar_event_id: str | None = None
    team_calendar_event_id: str | None = None


@dataclass
class PayrollRun:
    id: str
    period: str
    status: str
    items: list[dict]
    created_at: datetime
    finalized_at: datetime | None = None
    published_at: datetime | None = None


@dataclass
class Notification:
    id: str
    user_id: str
    title: str
    detail: str
    target: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    read: bool = False


@dataclass
class LocationEvent:
    id: str
    employee_id: str
    attendance_id: str
    kind: str
    at: datetime
    lat: float | None = None
    lng: float | None = None
    accuracy: float | None = None
    distance_meters: float | None = None
    inside_geofence: bool | None = None
    anomaly: str | None = None
    due_at: datetime | None = None


@dataclass
class AlertReceipt:
    id: str
    employee_id: str
    kind: str
    local_date: date


@dataclass
class PolicySection:
    id: str
    heading: str
    body: str
    position: int


@dataclass
class PolicyDocument:
    id: str
    title: str
    category: str
    language: str
    effective_date: date
    expiry_date: date | None
    state: str = "draft"
    sections: list[PolicySection] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    created_by: str = ""
    updated_by: str = ""


@dataclass
class PolicyAnswerAudit:
    id: str
    actor_id: str
    question: str
    cited_sections: list[dict]
    provider: str
    outcome: str
    suggested_action: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class OfficeLocation:
    id: str = "office-default"
    name: str = "Jakarta HQ"
    latitude: float = -6.2
    longitude: float = 106.8166
    radius_meters: float = 300
    reverify_enabled: bool = False
    reverify_count_per_day: int = 1
    reverify_window_start_minutes: int = 60
    reverify_window_end_minutes: int = 420
    alerts_enabled: bool = False
    clock_in_reminder_time: str = "09:15"
    clock_out_reminder_time: str = "18:15"
    max_open_hours: int = 10
    alert_managers: bool = False


@dataclass
class CalendarSettings:
    provider: str = ""
    connected: bool = False
    team_calendar_id: str = ""
    calendar_name: str = ""
    scope: str = "company"
    division: str = ""
    delivery_mode: str = "shared_and_email"
    refresh_token: str | None = None
    access_token: str | None = None
    token_expires_at: datetime | None = None


@dataclass
class DemoStore:
    tenant_id: str = DEMO_TENANT_ID
    tenant_name: str = DEMO_TENANT_NAME
    tenant_slug: str = DEMO_TENANT_SLUG
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    employees: dict[str, Employee] = field(default_factory=dict)
    attendance: dict[str, Attendance] = field(default_factory=dict)
    requests: dict[str, LeaveRequest] = field(default_factory=dict)
    payroll_runs: dict[str, PayrollRun] = field(default_factory=dict)
    notifications: dict[str, Notification] = field(default_factory=dict)
    sessions: dict[str, Session] = field(default_factory=dict)
    idempotency: dict[str, str] = field(default_factory=dict)
    audit: list[dict] = field(default_factory=list)
    office: OfficeLocation = field(default_factory=OfficeLocation)
    office_locations: dict[str, OfficeLocation] = field(default_factory=dict)
    calendar: CalendarSettings = field(default_factory=CalendarSettings)
    invitations: dict[str, Invitation] = field(default_factory=dict)
    password_resets: dict[str, PasswordReset] = field(default_factory=dict)
    location_events: dict[str, LocationEvent] = field(default_factory=dict)
    alert_receipts: dict[str, AlertReceipt] = field(default_factory=dict)
    policies: dict[str, PolicyDocument] = field(default_factory=dict)
    policy_answer_audit: dict[str, PolicyAnswerAudit] = field(default_factory=dict)

# Every demo account signs in with this password. Hashed once at import time so
# seeding stays fast even though tests reset the store frequently.
DEMO_PASSWORD = "Demo123!"
DEMO_PASSWORD_HASH = hash_password(DEMO_PASSWORD)


def reset_demo_store() -> None:
    """Restore the demo tenant and drop any other in-memory companies."""
    clear_registry()
    reset_outbox()
    demo = DemoStore(
        tenant_id=DEMO_TENANT_ID,
        tenant_name=DEMO_TENANT_NAME,
        tenant_slug=DEMO_TENANT_SLUG,
    )
    put_store(demo)
    bind_tenant(DEMO_TENANT_ID)
    people = [
        ("e-hr", "Nadia Putri", "hr@movon.test", "hr_admin", "Human Resources", "HR Lead", 12_000_000),
        ("e-manager", "Raka Pratama", "manager@movon.test", "manager", "Engineering", "Engineering Manager", 15_000_000),
        ("e-employee", "Sinta Lestari", "employee@movon.test", "employee", "Engineering", "Frontend Engineer", 8_000_000),
        ("e-fresh", "Rani Prasetyo", "fresh@movon.test", "employee", "Engineering", "QA Tester", 8_000_000),
        ("e-004", "Andi Gunawan", "andi@movon.test", "employee", "Product", "Product Designer", 9_000_000),
        ("e-005", "Rizky Pranata", "rizky@movon.test", "employee", "Sales", "Sales Lead", 11_000_000),
        ("e-006", "Budi Santoso", "budi@movon.test", "employee", "Operations", "Logistics Staff", 7_000_000),
        ("e-007", "Dewi Lestari", "dewi@movon.test", "employee", "Creative", "Marketing Executive", 8_500_000),
        ("e-008", "Fajar Nugroho", "fajar@movon.test", "manager", "Product", "Product Manager", 14_000_000),
        ("e-009", "Ayu Maharani", "ayu@movon.test", "employee", "Engineering", "QA Engineer", 8_500_000),
        ("e-010", "Gilang Ramadhan", "gilang@movon.test", "employee", "Engineering", "Backend Engineer", 10_000_000),
        ("e-011", "Maya Sari", "maya@movon.test", "employee", "Human Resources", "People Ops", 8_500_000),
        ("e-012", "Kevin Wijaya", "kevin@movon.test", "employee", "Creative", "Copywriter", 7_500_000),
        ("e-013", "Lina Hartati", "lina@movon.test", "employee", "Finance", "Finance Staff", 9_000_000),
        ("e-014", "Yoga Saputra", "yoga@movon.test", "employee", "Operations", "Project Officer", 8_000_000),
        ("e-015", "Nabila Azzahra", "nabila@movon.test", "employee", "Sales", "Account Executive", 8_000_000),
        ("e-016", "Reza Maulana", "reza@movon.test", "employee", "Product", "Product Analyst", 8_500_000),
        ("e-017", "Citra Amelia", "citra@movon.test", "employee", "Management", "Executive Assistant", 9_000_000),
        ("e-018", "Dian Permata", "dian@movon.test", "employee", "Engineering", "Engineering Intern", 4_500_000),
    ]
    store.employees = {
        employee_id: Employee(
            employee_id, name, email, role, department, title, "active", salary,
            DEMO_PASSWORD_HASH,
            DEMO_TENANT_ID,
        )
        for employee_id, name, email, role, department, title, salary in people
    }
    jakarta_now = datetime.now(JAKARTA)
    store.attendance = {}
    store.location_events = {}
    for index, employee_id in enumerate(
        ["e-manager", "e-004", "e-005", "e-006", "e-007", "e-009", "e-010"]
    ):
        checked_in = (
            jakarta_now.replace(hour=8, minute=50, second=0, microsecond=0)
            + timedelta(minutes=index * 4)
        ).astimezone(UTC)
        item = Attendance(
            f"attendance-seed-{index}",
            employee_id,
            checked_in,
            -6.2,
            106.8166,
            18,
            [{"title": "Prioritas utama", "status": "done" if index < 4 else "planned"}],
            "low_accuracy" if index == 5 else None,
        )
        store.attendance[item.id] = item
        event = LocationEvent(
            id=f"loc-seed-{index}",
            employee_id=employee_id,
            attendance_id=item.id,
            kind="check_in",
            at=checked_in,
            lat=-6.2,
            lng=106.8166,
            accuracy=18,
            distance_meters=0,
            inside_geofence=True,
            anomaly=item.anomaly,
        )
        store.location_events[event.id] = event
    store.employees["e-018"].is_remote = True
    demo_today = datetime.now(JAKARTA).date()
    request = LeaveRequest(
        "request-seed-1",
        "e-009",
        demo_today + timedelta(days=7),
        demo_today + timedelta(days=8),
        "Acara keluarga",
    )
    store.requests = {request.id: request}
    store.payroll_runs = {}
    store.notifications = {
        "notification-manager": Notification(
            "notification-manager",
            "e-manager",
            "Permohonan cuti baru",
            "Ayu Maharani menunggu persetujuan Anda.",
            "/app/approvals",
        ),
        "notification-hr": Notification(
            "notification-hr",
            "e-hr",
            "Data demo siap",
            "Dashboard operasional sudah diperbarui.",
            "/app/overview",
        ),
    }
    store.idempotency = {}
    store.sessions = {}
    store.audit = []
    store.office = OfficeLocation()
    store.office_locations = {store.office.id: store.office}
    store.invitations = {}
    store.password_resets = {}
    store.alert_receipts = {}
    store.policies = {}
    store.policy_answer_audit = {}


reset_demo_store()


def bind_from_token(token: str | None) -> None:
    """Bind the request to the tenant that owns ``token``, else the demo tenant."""
    if token:
        for tenant_store in iter_stores():
            if token in tenant_store.sessions:
                bind_tenant(tenant_store.tenant_id)
                return
    bind_tenant(DEMO_TENANT_ID)
