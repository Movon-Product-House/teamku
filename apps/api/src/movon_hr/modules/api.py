"""Functional Teamku vertical slices backed by a deterministic demo repository."""

from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass, field
from datetime import UTC, date, datetime, time, timedelta
from decimal import ROUND_HALF_UP, Decimal
from math import asin, cos, radians, sin, sqrt
from random import uniform
from uuid import uuid4

from fastapi import APIRouter, Header, HTTPException, Request, status
from pydantic import BaseModel, Field

from movon_hr.core import mailer
from movon_hr.core.mailer import MailKind, reset_outbox, send_email
from movon_hr.core.policy_assistant import answer_question
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
from movon_hr.core.time import JAKARTA, jakarta_date, working_days

router = APIRouter()
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

# Fields that must never be serialized to API clients.
SENSITIVE_EMPLOYEE_FIELDS = frozenset({"password_hash", "tenant_id"})


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


def actor(
    session_token: str | None,
    request: Request | None = None,
) -> Employee:
    token = session_token or (
        request.cookies.get(settings.session_cookie_name) if request is not None else None
    )
    if not token:
        raise HTTPException(401, "Sesi tidak valid")
    now = datetime.now(UTC)
    for tenant_store in iter_stores():
        session = tenant_store.sessions.get(token)
        if not session:
            continue
        if session.expires_at <= now:
            tenant_store.sessions.pop(session.token, None)
            raise HTTPException(401, "Sesi telah berakhir. Silakan masuk kembali.")
        employee = tenant_store.employees.get(session.employee_id)
        if not employee or employee.status != "active":
            raise HTTPException(401, "Sesi tidak valid")
        bind_tenant(tenant_store.tenant_id)
        if not employee.tenant_id:
            employee.tenant_id = tenant_store.tenant_id
        return employee
    raise HTTPException(401, "Sesi tidak valid")


def bind_from_token(token: str | None) -> None:
    """Bind the request to the tenant that owns ``token``, else the demo tenant."""
    if token:
        for tenant_store in iter_stores():
            if token in tenant_store.sessions:
                bind_tenant(tenant_store.tenant_id)
                return
    bind_tenant(DEMO_TENANT_ID)


def app_url(path: str) -> str:
    return f"{settings.app_base_url.rstrip('/')}{path}"


def require(user: Employee, *roles: str) -> None:
    if user.role not in roles:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Anda tidak memiliki izin untuk aksi ini")


def public_employee(employee: Employee, *, hide_salary: bool = False) -> dict:
    """Serialize an employee for API responses, never exposing secret fields."""
    data = {
        key: value
        for key, value in asdict(employee).items()
        if key not in SENSITIVE_EMPLOYEE_FIELDS
    }
    if hide_salary:
        data["salary"] = None
    location = current_office(employee) if not employee.is_remote else None
    data["work_mode"] = "field" if employee.is_remote else "office"
    data["work_location"] = office_payload(location) if location else None
    return data


def audit(action: str, user: Employee, target: str) -> None:
    store.audit.append(
        {
            "id": str(uuid4()),
            "at": datetime.now(UTC).isoformat(),
            "action": action,
            "actor": user.id,
            "target": target,
        }
    )


def notify(user_id: str, title: str, detail: str, target: str) -> None:
    item = Notification(str(uuid4()), user_id, title, detail, target)
    store.notifications[item.id] = item


DEFAULT_OFFICE_LATITUDE = -6.2
DEFAULT_OFFICE_LONGITUDE = 106.8166
DEFAULT_OFFICE_RADIUS_METERS = 300
# Keep aliases used by tests and seed data.
OFFICE_LATITUDE = DEFAULT_OFFICE_LATITUDE
OFFICE_LONGITUDE = DEFAULT_OFFICE_LONGITUDE
OFFICE_RADIUS_METERS = DEFAULT_OFFICE_RADIUS_METERS
# GPS uncertainty may expand the allowed radius slightly, but never enough to check in from home.
MAX_ACCURACY_CREDIT_METERS = 50
LOW_ACCURACY_METERS = 100


def haversine_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6_371_000
    d_lat, d_lon = radians(lat2 - lat1), radians(lon2 - lon1)
    value = (
        sin(d_lat / 2) ** 2
        + cos(radians(lat1)) * cos(radians(lat2)) * sin(d_lon / 2) ** 2
    )
    return 2 * radius * asin(sqrt(value))


def current_office(employee: Employee | None = None) -> OfficeLocation:
    if employee and employee.work_location_id:
        return store.office_locations.get(employee.work_location_id, store.office)
    return store.office


def office_payload(office: OfficeLocation | None = None) -> dict:
    item = office or current_office()
    return {
        "id": item.id,
        "name": item.name,
        "latitude": item.latitude,
        "longitude": item.longitude,
        "radius_meters": item.radius_meters,
        "reverify_enabled": item.reverify_enabled,
        "reverify_count_per_day": item.reverify_count_per_day,
        "reverify_window_start_minutes": item.reverify_window_start_minutes,
        "reverify_window_end_minutes": item.reverify_window_end_minutes,
        "alerts_enabled": item.alerts_enabled,
        "clock_in_reminder_time": item.clock_in_reminder_time,
        "clock_out_reminder_time": item.clock_out_reminder_time,
        "max_open_hours": item.max_open_hours,
        "alert_managers": item.alert_managers,
    }


def office_distance_meters(latitude: float, longitude: float, employee: Employee | None = None) -> float:
    office = current_office(employee)
    return haversine_meters(latitude, longitude, office.latitude, office.longitude)


def allowed_check_in_radius_meters(accuracy_meters: float, employee: Employee | None = None) -> float:
    return current_office(employee).radius_meters + min(max(accuracy_meters, 0), MAX_ACCURACY_CREDIT_METERS)


REVERIFY_GRACE_MINUTES = 15
ALERT_COPY = {
    "missed_clock_in": ("Belum clock-in", "Anda belum check-in hari ini."),
    "missed_clock_out": ("Sesi masih terbuka", "Sesi kehadiran Anda masih terbuka. Lakukan check-out."),
    "limit_reverify": (
        "Re-verifikasi terlewat",
        "Ada permintaan re-verifikasi lokasi yang belum diselesaikan.",
    ),
    "limit_geofence": (
        "Lokasi di luar area kantor",
        "Re-verifikasi lokasi tercatat di luar radius kantor.",
    ),
}


def parse_hhmm(value: str) -> time:
    hour, minute = value.split(":")
    return time(int(hour), int(minute))


def employee_sessions_on(employee_id: str, day: date) -> list[Attendance]:
    return [
        item
        for item in store.attendance.values()
        if item.employee_id == employee_id and jakarta_date(item.checked_in_at) == day
    ]


def has_approved_leave(employee_id: str, day: date) -> bool:
    return any(
        item.employee_id == employee_id
        and item.status == "approved"
        and item.start <= day <= item.end
        for item in store.requests.values()
    )


def location_events_for(attendance_id: str) -> list[LocationEvent]:
    return [item for item in store.location_events.values() if item.attendance_id == attendance_id]


def is_reverify_slot_open(event: LocationEvent) -> bool:
    return event.kind == "reverify" and event.lat is None and event.anomaly != "missed_reverify"


def record_location_event(**kwargs: object) -> LocationEvent:
    event = LocationEvent(id=str(uuid4()), **kwargs)  # type: ignore[arg-type]
    store.location_events[event.id] = event
    return event


def schedule_reverify_slots(record: Attendance, policy: OfficeLocation) -> None:
    count = policy.reverify_count_per_day
    start = policy.reverify_window_start_minutes
    span = max(policy.reverify_window_end_minutes - start, 1)
    for index in range(count):
        if index == 0:
            offset = start
        else:
            low = start + span * index / count
            high = start + span * (index + 1) / count
            offset = uniform(low, high)
        due_at = record.checked_in_at + timedelta(minutes=offset)
        record_location_event(
            employee_id=record.employee_id,
            attendance_id=record.id,
            kind="reverify",
            at=due_at,
            due_at=due_at,
        )


def expire_missed_reverify_slots(record: Attendance | None = None) -> None:
    now = datetime.now(UTC)
    items = location_events_for(record.id) if record else list(store.location_events.values())
    for event in items:
        if not is_reverify_slot_open(event) or event.due_at is None:
            continue
        if now >= event.due_at + timedelta(minutes=REVERIFY_GRACE_MINUTES):
            event.anomaly = "missed_reverify"
            event.at = now


def pending_reverify_for(record: Attendance) -> LocationEvent | None:
    expire_missed_reverify_slots(record)
    now = datetime.now(UTC)
    open_slots = [
        event
        for event in location_events_for(record.id)
        if is_reverify_slot_open(event) and event.due_at and event.due_at <= now
    ]
    if not open_slots:
        return None
    return min(open_slots, key=lambda item: item.due_at or item.at)


def pending_payload(event: LocationEvent | None) -> dict | None:
    if not event:
        return None
    return {"id": event.id, "due_at": event.due_at, "kind": event.kind}


def location_event_payload(event: LocationEvent) -> dict:
    maps_url = (
        f"https://www.google.com/maps?q={event.lat},{event.lng}"
        if event.lat is not None and event.lng is not None
        else None
    )
    return {
        "id": event.id,
        "employee_id": event.employee_id,
        "attendance_id": event.attendance_id,
        "kind": event.kind,
        "at": event.at,
        "lat": event.lat,
        "lng": event.lng,
        "accuracy": event.accuracy,
        "distance_meters": event.distance_meters,
        "inside_geofence": event.inside_geofence,
        "anomaly": event.anomaly,
        "due_at": event.due_at,
        "maps_url": maps_url,
    }


def visible_or_404(user: Employee, employee_id: str) -> Employee:
    employee = store.employees.get(employee_id)
    if not employee or employee.id not in {item.id for item in visible_employees(user)}:
        raise HTTPException(404, "Karyawan tidak ditemukan")
    return employee


def alert_receipt_key(kind: str, employee_id: str, day: date) -> str:
    return f"{kind}:{employee_id}:{day.isoformat()}"


def emit_attendance_alert(kind: str, employee: Employee, policy: OfficeLocation) -> None:
    today = jakarta_date()
    key = alert_receipt_key(kind, employee.id, today)
    if key in store.alert_receipts:
        return
    title, detail = ALERT_COPY[kind]
    store.alert_receipts[key] = AlertReceipt(key, employee.id, kind, today)
    notify(employee.id, title, detail, "/app/attendance/today")
    if kind in {"missed_clock_in", "missed_clock_out"}:
        dispatch_email(
            employee.email,
            f"{title} — Teamku",
            (
                f"Halo {employee.name},\n\n{detail}\n"
                f"Buka presensi: {app_url('/app/attendance/today')}\n"
            ),
            kind="attendance_alert",
        )
    if not policy.alert_managers:
        return
    for recipient in store.employees.values():
        if recipient.id == employee.id or recipient.status != "active":
            continue
        same_manager = recipient.role == "manager" and recipient.department == employee.department
        if recipient.role == "hr_admin" or same_manager:
            notify(recipient.id, title, f"{employee.name}: {detail}", "/app/attendance/today")


def evaluate_attendance_alerts() -> None:
    policy = current_office()
    if not policy.alerts_enabled:
        return
    now = datetime.now(JAKARTA)
    today = now.date()
    reminder_in = datetime.combine(today, parse_hhmm(policy.clock_in_reminder_time), JAKARTA)
    reminder_out = datetime.combine(today, parse_hhmm(policy.clock_out_reminder_time), JAKARTA)

    for employee in store.employees.values():
        if employee.status != "active":
            continue
        sessions = employee_sessions_on(employee.id, today)
        open_session = next((item for item in sessions if not item.checked_out_at), None)
        if open_session:
            expire_missed_reverify_slots(open_session)

        if now >= reminder_in and not sessions and not has_approved_leave(employee.id, today):
            emit_attendance_alert("missed_clock_in", employee, policy)

        if open_session:
            hours_open = (datetime.now(UTC) - open_session.checked_in_at).total_seconds() / 3600
            if now >= reminder_out or hours_open >= policy.max_open_hours:
                emit_attendance_alert("missed_clock_out", employee, policy)

        if employee.is_remote:
            continue
        events = [
            item
            for item in store.location_events.values()
            if item.employee_id == employee.id and jakarta_date(item.at) == today
        ]
        if any(item.anomaly == "missed_reverify" for item in events):
            emit_attendance_alert("limit_reverify", employee, policy)
        if any(item.anomaly == "outside_geofence" for item in events):
            emit_attendance_alert("limit_geofence", employee, policy)


def visible_employees(user: Employee) -> list[Employee]:
    if user.role == "hr_admin":
        return list(store.employees.values())
    if user.role == "manager":
        return [item for item in store.employees.values() if item.department == user.department]
    return [user]


def calculate_payroll_items() -> list[dict]:
    rows = []
    for employee in store.employees.values():
        if employee.status != "active":
            continue
        gross = Decimal(employee.salary)
        deduction = (gross * Decimal("0.02")).quantize(Decimal(1), rounding=ROUND_HALF_UP)
        rows.append(
            {
                "employee_id": employee.id,
                "employee": employee.name,
                "gross_rupiah": int(gross),
                "deductions_rupiah": int(deduction),
                "net_rupiah": int(gross - deduction),
            }
        )
    return rows


def payroll_payload(run: PayrollRun) -> dict:
    return asdict(run) | {
        "total_gross_rupiah": sum(item["gross_rupiah"] for item in run.items),
        "total_deductions_rupiah": sum(item["deductions_rupiah"] for item in run.items),
        "total_net_rupiah": sum(item["net_rupiah"] for item in run.items),
        "calculation_version": "manual-components-v1",
        "disclaimer": "PPh 21 dan BPJS harus dikonfigurasi atau disesuaikan manual.",
    }


def leave_balance(employee_id: str) -> dict:
    approved_days = sum(
        working_days(item.start, item.end)
        for item in store.requests.values()
        if item.employee_id == employee_id and item.status == "approved"
    )
    return {"annual_days": 12, "used_days": approved_days, "remaining_days": max(12 - approved_days, 0)}


def policy_payload(policy: PolicyDocument) -> dict:
    return {
        "id": policy.id, "title": policy.title, "category": policy.category, "language": policy.language,
        "effective_date": policy.effective_date, "expiry_date": policy.expiry_date, "state": policy.state,
        "sections": [asdict(item) for item in sorted(policy.sections, key=lambda item: item.position)],
        "created_at": policy.created_at, "updated_at": policy.updated_at,
        "created_by": policy.created_by, "updated_by": policy.updated_by,
    }


def validate_policy(title: str, sections: list[PolicySection]) -> None:
    if not title.strip() or not any(item.heading.strip() and item.body.strip() for item in sections):
        raise HTTPException(422, "Kebijakan memerlukan judul dan setidaknya satu bagian yang terisi")


class CheckIn(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    accuracy_meters: float = Field(ge=0, le=10_000)
    selfie_captured: bool
    location_share_approved: bool
    agenda: list[dict] = Field(min_length=1, max_length=5)


class CheckOut(BaseModel):
    summary: str = Field(min_length=4, max_length=1000)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    accuracy_meters: float | None = Field(default=None, ge=0, le=10_000)


class ReverifyInput(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    accuracy_meters: float = Field(ge=0, le=10_000)
    selfie_captured: bool


class PayrollInput(BaseModel):
    month: str = Field(pattern=r"^\d{4}-\d{2}$")


class PolicySectionInput(BaseModel):
    id: str | None = Field(default=None, max_length=80)
    heading: str = Field(min_length=1, max_length=160)
    body: str = Field(min_length=1, max_length=10_000)


class PolicyInput(BaseModel):
    title: str = Field(min_length=2, max_length=160)
    category: str = Field(default="general", min_length=2, max_length=80)
    language: str = Field(default="id", pattern="^(id|en)$")
    effective_date: date
    expiry_date: date | None = None
    sections: list[PolicySectionInput] = Field(min_length=1, max_length=50)


class PolicyQuestion(BaseModel):
    question: str = Field(min_length=3, max_length=800)


@router.get("/dashboard")
async def dashboard(x_demo_user: str | None = Header(default=None)) -> dict:
    user = actor(x_demo_user)
    employees = [item for item in visible_employees(user) if item.status == "active"]
    employee_ids = {employee.id for employee in employees}
    today = datetime.now(JAKARTA).date()
    sessions = [
        item
        for item in store.attendance.values()
        if item.employee_id in employee_ids
        and item.checked_in_at.astimezone(JAKARTA).date() == today
    ]
    agenda_items = [agenda for session in sessions for agenda in session.agenda]
    pending = [
        item
        for item in store.requests.values()
        if item.status == "pending" and item.employee_id in employee_ids
    ]
    present_ids = {item.employee_id for item in sessions}
    leave_today_ids = {
        item.employee_id for item in store.requests.values()
        if item.status == "approved" and item.start <= today <= item.end and item.employee_id in employee_ids
    }
    absent_ids = employee_ids - present_ids - leave_today_ids
    late_ids = {
        item.employee_id for item in sessions
        if item.checked_in_at.astimezone(JAKARTA).time() >= time(9, 0)
    }
    return {
        "current_user": public_employee(user),
        "headcount": len(employees),
        "present": len(present_ids),
        "absent": len(absent_ids),
        "on_leave": len(leave_today_ids),
        "late": len(late_ids),
        "attendance_rate": round(len(present_ids) / len(employees) * 100) if employees else 0,
        "pending_approvals": len(pending) if user.role in {"manager", "hr_admin"} else 0,
        "agenda_total": len(agenda_items),
        "agenda_completed": sum(1 for item in agenda_items if item.get("status") == "done"),
        "attendance": [
            {
                "employee": store.employees[item.employee_id].name,
                "department": store.employees[item.employee_id].department,
                "checked_in_at": item.checked_in_at,
                "checked_out_at": item.checked_out_at,
                "anomaly": item.anomaly,
            }
            for item in sorted(sessions, key=lambda entry: entry.checked_in_at, reverse=True)
        ],
    }


@router.get("/employees/{employee_id}/location-history")
async def employee_location_history(
    employee_id: str, x_demo_user: str | None = Header(default=None)
) -> dict:
    user = actor(x_demo_user)
    require(user, "manager", "hr_admin")
    employee = visible_or_404(user, employee_id)
    events = [
        item for item in store.location_events.values() if item.employee_id == employee.id
    ]
    events.sort(key=lambda item: item.at)
    return {
        "employee_id": employee.id,
        "items": [location_event_payload(item) for item in events],
    }


def _policy_sections(payload: PolicyInput) -> list[PolicySection]:
    return [
        PolicySection(item.id or f"section-{index + 1}", item.heading.strip(), item.body.strip(), index)
        for index, item in enumerate(payload.sections)
    ]


@router.get("/policies")
async def list_policies(x_demo_user: str | None = Header(default=None)) -> dict:
    user = actor(x_demo_user)
    require(user, "hr_admin")
    return {"items": [policy_payload(item) for item in sorted(store.policies.values(), key=lambda p: p.updated_at, reverse=True)]}


@router.post("/policies")
async def create_policy(payload: PolicyInput, x_demo_user: str | None = Header(default=None)) -> dict:
    user = actor(x_demo_user)
    require(user, "hr_admin")
    if payload.expiry_date and payload.expiry_date < payload.effective_date:
        raise HTTPException(422, "Tanggal berakhir harus setelah tanggal berlaku")
    sections = _policy_sections(payload)
    validate_policy(payload.title, sections)
    item = PolicyDocument(
        id=f"policy-{uuid4().hex[:12]}", title=payload.title.strip(), category=payload.category.strip(),
        language=payload.language, effective_date=payload.effective_date, expiry_date=payload.expiry_date,
        sections=sections, created_by=user.id, updated_by=user.id,
    )
    store.policies[item.id] = item
    audit("policy.created", user, item.id)
    return policy_payload(item)


@router.put("/policies/{policy_id}")
async def update_policy(policy_id: str, payload: PolicyInput, x_demo_user: str | None = Header(default=None)) -> dict:
    user = actor(x_demo_user)
    require(user, "hr_admin")
    item = store.policies.get(policy_id)
    if not item:
        raise HTTPException(404, "Kebijakan tidak ditemukan")
    if payload.expiry_date and payload.expiry_date < payload.effective_date:
        raise HTTPException(422, "Tanggal berakhir harus setelah tanggal berlaku")
    sections = _policy_sections(payload)
    validate_policy(payload.title, sections)
    item.title, item.category, item.language = payload.title.strip(), payload.category.strip(), payload.language
    item.effective_date, item.expiry_date, item.sections = payload.effective_date, payload.expiry_date, sections
    item.updated_at, item.updated_by = datetime.now(UTC), user.id
    audit("policy.updated", user, item.id)
    return policy_payload(item)


@router.post("/policies/{policy_id}/publish")
async def publish_policy(policy_id: str, x_demo_user: str | None = Header(default=None)) -> dict:
    user = actor(x_demo_user)
    require(user, "hr_admin")
    item = store.policies.get(policy_id)
    if not item:
        raise HTTPException(404, "Kebijakan tidak ditemukan")
    validate_policy(item.title, item.sections)
    item.state, item.updated_at, item.updated_by = "published", datetime.now(UTC), user.id
    audit("policy.published", user, item.id)
    return policy_payload(item)


@router.post("/policies/{policy_id}/archive")
async def archive_policy(policy_id: str, x_demo_user: str | None = Header(default=None)) -> dict:
    user = actor(x_demo_user)
    require(user, "hr_admin")
    item = store.policies.get(policy_id)
    if not item:
        raise HTTPException(404, "Kebijakan tidak ditemukan")
    item.state, item.updated_at, item.updated_by = "archived", datetime.now(UTC), user.id
    audit("policy.archived", user, item.id)
    return policy_payload(item)


@router.post("/policy-assistant/questions")
async def policy_question(payload: PolicyQuestion, x_demo_user: str | None = Header(default=None)) -> dict:
    user = actor(x_demo_user)
    facts = [{"type": "leave_balance", "label": "Sisa cuti tahunan", "value": leave_balance(user.id)["remaining_days"]}]
    response, outcome = answer_question(
        policies=list(store.policies.values()), question=payload.question.strip(), today=jakarta_date(), facts=facts
    )
    receipt = PolicyAnswerAudit(
        id=str(uuid4()), actor_id=user.id, question=payload.question.strip()[:800],
        cited_sections=[{"policy_id": item["policy_id"], "section_id": item["section_id"]} for item in response["citations"]],
        provider="fake-policy-provider-v1", outcome=outcome, suggested_action=response["suggested_action"]["type"],
    )
    store.policy_answer_audit[receipt.id] = receipt
    audit("policy_assistant.answered", user, receipt.id)
    return response


@router.get("/attendance/today")
async def attendance_today(x_demo_user: str | None = Header(default=None)) -> dict:
    user = actor(x_demo_user)
    evaluate_attendance_alerts()
    today = jakarta_date()
    sessions = employee_sessions_on(user.id, today)
    if not sessions:
        return {
            "state": "not_checked_in",
            "session": None,
            "pending_reverification": None,
            "is_remote": user.is_remote,
        }
    latest = max(sessions, key=lambda item: item.checked_in_at)
    state = "completed" if latest.checked_out_at else "checked_in"
    pending = None if latest.checked_out_at else pending_reverify_for(latest)
    return {
        "state": state,
        "session": {
            "id": latest.id,
            "checked_in_at": latest.checked_in_at,
            "checked_out_at": latest.checked_out_at,
            "anomaly": latest.anomaly,
            "agenda_count": len(latest.agenda),
            "summary": latest.summary,
        },
        "pending_reverification": pending_payload(pending),
        "is_remote": user.is_remote,
    }


@router.post("/attendance/check-in")
async def check_in(
    payload: CheckIn,
    idempotency_key: str = Header(...),
    x_demo_user: str | None = Header(default=None),
) -> dict:
    user = actor(x_demo_user)
    if idempotency_key in store.idempotency:
        return {"id": store.idempotency[idempotency_key], "idempotent": True}
    if any(
        item.employee_id == user.id
        and not item.checked_out_at
        for item in store.attendance.values()
    ):
        raise HTTPException(409, "Anda masih memiliki sesi kehadiran yang terbuka")
    if not payload.selfie_captured:
        raise HTTPException(422, "Selfie kamera langsung wajib untuk kebijakan ini")
    if not payload.location_share_approved:
        raise HTTPException(422, "Persetujuan berbagi lokasi diperlukan untuk check-in")
    distance = office_distance_meters(payload.latitude, payload.longitude, user)
    allowed_radius = allowed_check_in_radius_meters(payload.accuracy_meters, user)
    office = current_office(user)
    if not user.is_remote and distance > allowed_radius:
        raise HTTPException(
            403,
            (
                f"Check-in ditolak. Anda berada sekitar {round(distance)} m dari kantor. "
                f"Presensi hanya diizinkan dalam radius {round(office.radius_meters)} m dari {office.name}."
            ),
        )
    anomaly = "low_accuracy" if payload.accuracy_meters > LOW_ACCURACY_METERS else None
    record = Attendance(
        str(uuid4()),
        user.id,
        datetime.now(UTC),
        payload.latitude,
        payload.longitude,
        payload.accuracy_meters,
        payload.agenda,
        anomaly,
    )
    store.attendance[record.id] = record
    store.idempotency[idempotency_key] = record.id
    record_location_event(
        employee_id=user.id,
        attendance_id=record.id,
        kind="check_in",
        at=record.checked_in_at,
        lat=payload.latitude,
        lng=payload.longitude,
        accuracy=payload.accuracy_meters,
        distance_meters=round(distance),
        inside_geofence=distance <= allowed_radius,
        anomaly=anomaly,
    )
    if office.reverify_enabled and not user.is_remote:
        schedule_reverify_slots(record, office)
    audit("attendance.check_in", user, record.id)
    return {
        "id": record.id,
        "checked_in_at": record.checked_in_at,
        "distance_meters": round(distance),
        "allowed_radius_meters": round(allowed_radius),
        "anomaly": anomaly,
        "agenda_count": len(payload.agenda),
    }


@router.post("/attendance/check-out")
async def check_out(
    payload: CheckOut, x_demo_user: str | None = Header(default=None)
) -> dict:
    user = actor(x_demo_user)
    record = next(
        (
            item
            for item in store.attendance.values()
            if item.employee_id == user.id and not item.checked_out_at
        ),
        None,
    )
    if not record:
        raise HTTPException(409, "Tidak ada sesi kehadiran terbuka")
    expire_missed_reverify_slots(record)
    for event in location_events_for(record.id):
        if is_reverify_slot_open(event):
            event.anomaly = "missed_reverify"
            event.at = datetime.now(UTC)
    record.checked_out_at = datetime.now(UTC)
    record.summary = payload.summary
    checkout_distance = None
    checkout_inside = None
    if payload.latitude is not None and payload.longitude is not None:
        checkout_distance = office_distance_meters(payload.latitude, payload.longitude, user)
        checkout_inside = user.is_remote or checkout_distance <= allowed_check_in_radius_meters(payload.accuracy_meters or 0, user)
    record_location_event(
        employee_id=user.id,
        attendance_id=record.id,
        kind="check_out",
        at=record.checked_out_at,
        lat=payload.latitude,
        lng=payload.longitude,
        accuracy=payload.accuracy_meters,
        distance_meters=round(checkout_distance) if checkout_distance is not None else None,
        inside_geofence=checkout_inside,
    )
    audit("attendance.check_out", user, record.id)
    return {
        "id": record.id,
        "checked_out_at": record.checked_out_at,
        "effective_hours": round(
            (record.checked_out_at - record.checked_in_at).total_seconds() / 3600, 2
        ),
    }


@router.post("/attendance/reverify")
async def reverify(
    payload: ReverifyInput, x_demo_user: str | None = Header(default=None)
) -> dict:
    user = actor(x_demo_user)
    today = jakarta_date()
    record = next(
        (item for item in employee_sessions_on(user.id, today) if not item.checked_out_at),
        None,
    )
    if not record:
        raise HTTPException(409, "Tidak ada sesi kehadiran terbuka")
    pending = pending_reverify_for(record)
    distance = office_distance_meters(payload.latitude, payload.longitude, user)
    allowed_radius = allowed_check_in_radius_meters(payload.accuracy_meters, user)
    now = datetime.now(UTC)

    if user.is_remote:
        if pending:
            pending.lat = payload.latitude
            pending.lng = payload.longitude
            pending.accuracy = payload.accuracy_meters
            pending.at = now
            pending.distance_meters = round(distance)
            pending.inside_geofence = True
            pending.anomaly = None
            audit("attendance.reverify", user, pending.id)
            return location_event_payload(pending) | {"skipped": True}
        return {"skipped": True, "pending_reverification": None}

    if not payload.selfie_captured:
        raise HTTPException(422, "Selfie kamera langsung wajib untuk kebijakan ini")
    if not pending:
        raise HTTPException(409, "Tidak ada re-verifikasi yang menunggu")

    inside = distance <= allowed_radius
    pending.lat = payload.latitude
    pending.lng = payload.longitude
    pending.accuracy = payload.accuracy_meters
    pending.at = now
    pending.distance_meters = round(distance)
    pending.inside_geofence = inside
    pending.anomaly = None if inside else "outside_geofence"
    audit("attendance.reverify", user, pending.id)
    return location_event_payload(pending)


@router.get("/payroll/runs")
async def list_payroll(x_demo_user: str | None = Header(default=None)) -> dict:
    user = actor(x_demo_user)
    require(user, "hr_admin")
    items = [
        payroll_payload(item)
        for item in sorted(
            store.payroll_runs.values(), key=lambda entry: entry.created_at, reverse=True
        )
    ]
    return {"items": items}


@router.post("/payroll/runs")
async def payroll(
    payload: PayrollInput, x_demo_user: str | None = Header(default=None)
) -> dict:
    user = actor(x_demo_user)
    require(user, "hr_admin")
    existing = next(
        (item for item in store.payroll_runs.values() if item.period == payload.month), None
    )
    if existing:
        return payroll_payload(existing)
    run = PayrollRun(
        str(uuid4()), payload.month, "draft", calculate_payroll_items(), datetime.now(UTC)
    )
    store.payroll_runs[run.id] = run
    audit("payroll.calculated", user, run.id)
    return payroll_payload(run)


@router.post("/payroll/runs/{run_id}/finalize")
async def finalize_payroll(
    run_id: str, x_demo_user: str | None = Header(default=None)
) -> dict:
    user = actor(x_demo_user)
    require(user, "hr_admin")
    run = store.payroll_runs.get(run_id)
    if not run:
        raise HTTPException(404, "Payroll run tidak ditemukan")
    if run.status != "draft":
        raise HTTPException(409, "Hanya draft payroll yang dapat difinalisasi")
    run.status = "finalized"
    run.finalized_at = datetime.now(UTC)
    audit("payroll.finalized", user, run.id)
    return payroll_payload(run)


@router.post("/payroll/runs/{run_id}/publish")
async def publish_payroll(
    run_id: str, x_demo_user: str | None = Header(default=None)
) -> dict:
    user = actor(x_demo_user)
    require(user, "hr_admin")
    run = store.payroll_runs.get(run_id)
    if not run:
        raise HTTPException(404, "Payroll run tidak ditemukan")
    if run.status != "finalized":
        raise HTTPException(409, "Finalisasi payroll sebelum dipublikasikan")
    run.status = "published"
    run.published_at = datetime.now(UTC)
    audit("payroll.published", user, run.id)
    for employee in store.employees.values():
        notify(
            employee.id,
            "Slip gaji tersedia",
            f"Payroll periode {run.period} telah dipublikasikan.",
            "/app/payroll/payslips",
        )
    return payroll_payload(run)


@router.get("/payroll/payslips")
async def payslips(x_demo_user: str | None = Header(default=None)) -> dict:
    user = actor(x_demo_user)
    items = []
    for run in store.payroll_runs.values():
        if run.status != "published":
            continue
        employee_row = next(
            (row for row in run.items if row["employee_id"] == user.id),
            None,
        )
        if employee_row:
            items.append(
                {
                    "id": run.id,
                    "period": run.period,
                    "published_at": run.published_at,
                    **employee_row,
                }
            )
    items.sort(key=lambda item: item["period"], reverse=True)
    return {"items": items}
