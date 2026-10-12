"""Functional Teamku vertical slices backed by a deterministic demo repository."""

from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass, field
from datetime import UTC, date, datetime, time, timedelta
from decimal import ROUND_HALF_UP, Decimal
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
