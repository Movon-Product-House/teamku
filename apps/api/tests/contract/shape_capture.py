"""Shared by the shape recorder and the contract test (U0; reused by U4).

`capture(client)` replays the demo flow over HTTP and returns
``{"<METHOD> <route> | <role>[ | <label>]": shape}`` for every success response.
A shape keeps JSON keys and types but drops values, except that datetime strings
keep their layout (digits masked, offset literal) so "+00:00" vs "Z" or
dropped microseconds show up as a diff.
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import httpx

from movon_hr.core.mailer import last_email_to
from movon_hr.core.settings import settings

SHAPES_PATH = Path(__file__).with_name("shapes.json")
API = "/api/v1"
PASSWORD = "Demo123!"
USERS = {
    "hr": "hr@movon.test",
    "manager": "manager@movon.test",
    "employee": "employee@movon.test",
    "remote": "dian@movon.test",  # seeded as remote; recorded under role "employee"
}
ROLE_OF = {"hr": "hr", "manager": "manager", "employee": "employee", "remote": "employee"}
# Routes with no reachable JSON success response in a self-contained run.
EXCLUDED = {
    "GET /api/v1/settings/calendar/google/callback": (
        "302 redirect (not JSON) after a live Google token exchange"
    ),
    "GET /api/v1/settings/calendar/google/calendars": (
        "needs a connected Google account and a live Calendar API call"
    ),
}
# Fields the new API may add (plan R1); ignored when comparing.
ALLOWED_ADDITIONS = frozenset({"is_primary"})

_DATETIME = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(Z|[+-]\d{2}:\d{2})?")
_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


def shape_of(value: Any) -> Any:
    """JSON value -> shape: type name, {key: shape}, or sorted list of element shapes."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int | float):
        return "number"
    if isinstance(value, str):
        match = _DATETIME.fullmatch(value)
        if match:
            offset = match.group(1) or ""
            return "datetime:" + re.sub(r"\d", "9", value[: len(value) - len(offset)]) + offset
        return "date" if _DATE.fullmatch(value) else "string"
    if isinstance(value, dict):
        return {key: shape_of(item) for key, item in sorted(value.items())}
    # Lists keep each distinct element shape once, sorted, so order never matters.
    variants = {json.dumps(shape_of(item), sort_keys=True) for item in value}
    return [json.loads(item) for item in sorted(variants)]


def without_keys(shape: Any, keys: frozenset[str]) -> Any:
    if isinstance(shape, dict):
        return {k: without_keys(v, keys) for k, v in shape.items() if k not in keys}
    if isinstance(shape, list):
        variants = {json.dumps(without_keys(item, keys), sort_keys=True) for item in shape}
        return [json.loads(item) for item in sorted(variants)]
    return shape


def api_routes(app: Any) -> set[str]:
    paths = app.openapi()["paths"]
    return {
        f"{method.upper()} {path}"
        for path, ops in paths.items()
        if path.startswith(API)
        for method in ops
    }


def uncovered_routes(app: Any, shapes: dict[str, Any]) -> list[str]:
    covered = {key.split(" | ")[0] for key in shapes}
    return sorted(api_routes(app) - covered - set(EXCLUDED))


class _Recorder:
    def __init__(self, client: httpx.AsyncClient) -> None:
        self.client = client
        self.tokens: dict[str, str] = {}
        self.shapes: dict[str, Any] = {}

    async def call(
        self,
        method: str,
        route: str,
        who: str,
        label: str = "",
        *,
        json: Any = None,
        headers: dict[str, str] | None = None,
        **params: str,
    ) -> Any:
        path = API + route.format(**params)
        sent = {"X-Demo-User": self.tokens[who]} if who in self.tokens else {}
        response = await self.client.request(
            method, path, json=json, headers=sent | (headers or {})
        )
        assert response.status_code == 200, f"{method} {path} as {who}: {response.text}"
        key = f"{method} {API}{route} | {ROLE_OF.get(who, who)}" + (f" | {label}" if label else "")
        assert key not in self.shapes, f"duplicate capture key {key!r}; add a label"
        body = response.json()
        self.shapes[key] = shape_of(body)
        return body

    async def login(self, who: str) -> None:
        body = await self.call(
            "POST",
            "/auth/login",
            who,
            "remote" if who == "remote" else "",
            json={"email": USERS[who], "password": PASSWORD},
        )
        self.tokens[who] = body["access_token"]


def _today() -> date:
    return datetime.now(ZoneInfo("Asia/Jakarta")).date()


def _next_monday(start: date) -> date:
    return start + timedelta(days=(7 - start.weekday()) % 7 or 7)


async def capture(client: httpx.AsyncClient) -> dict[str, Any]:
    """Run the flow against freshly seeded demo data; returns shapes keyed by call."""
    saved = settings.mail_provider, settings.google_client_id
    settings.mail_provider = "console"
    settings.google_client_id = settings.google_client_id or "contract-client-id"
    try:
        recorder = _Recorder(client)
        await _flow(recorder)
        return recorder.shapes
    finally:
        settings.mail_provider, settings.google_client_id = saved


async def _flow(r: _Recorder) -> None:
    call = r.call
    for who in USERS:
        await r.login(who)

    # Read-only views for every role, on untouched seed data.
    for who in ("hr", "manager", "employee"):
        await call("GET", "/me", who)
        await call("GET", "/dashboard", who, "seed")
        await call("GET", "/attendance/today", who, "seed")
        await call("GET", "/leave-requests", who, "seed")
        await call("GET", "/notifications", who, "seed")
        await call("GET", "/settings/locations", who, "seed")
        await call("GET", "/settings/office", who, "seed")
        await call("GET", "/settings/calendar", who, "seed")
    for who in ("hr", "manager"):
        await call("GET", "/approvals", who, "seed")
    await call("GET", "/employees", "manager")
    listed = await call("GET", "/employees", "hr")
    employees = {item["email"]: item["id"] for item in listed["items"]}
    employee_id = employees[USERS["employee"]]
    for who in ("hr", "manager", "employee"):
        await call("GET", "/employees/{employee_id}", who, employee_id=employee_id)
    seeded_member = employees["ayu@movon.test"]  # has a seeded check-in event
    for who in ("hr", "manager"):
        await call(
            "GET",
            "/employees/{employee_id}/location-history",
            who,
            "seed",
            employee_id=seeded_member,
        )

    # Settings (HR).
    office = await call("GET", "/settings/office", "hr", "before_update")
    await call(
        "PUT",
        "/settings/office",
        "hr",
        json={
            "name": office["name"],
            "latitude": office["latitude"],
            "longitude": office["longitude"],
            "radius_meters": office["radius_meters"],
            "reverify_enabled": True,
            "reverify_count_per_day": 1,
            "reverify_window_start_minutes": 0,
            "reverify_window_end_minutes": 60,
        },
    )
    location = await call(
        "POST",
        "/settings/locations",
        "hr",
        json={
            "name": "Bandung Branch",
            "latitude": -6.9175,
            "longitude": 107.6191,
            "radius_meters": 250,
        },
    )
    await call("GET", "/settings/locations", "hr", "with_branch")
    await call(
        "POST",
        "/settings/office/from-maps-url",
        "hr",
        json={"url": "https://www.google.com/maps?q=-6.2,106.8166"},
    )
    await call(
        "PUT",
        "/settings/calendar",
        "hr",
        json={
            "provider": "google",
            "team_calendar_id": "team@movon.test",
            "calendar_name": "Kalender tim",
        },
    )
    await call("GET", "/settings/calendar/google/start", "hr")

    # Employees (HR).
    await call(
        "POST",
        "/employees",
        "hr",
        "temporary_password",
        json={
            "name": "Dimas Wijaya",
            "email": "dimas.contract@movon.test",
            "department": "Product",
            "role": "employee",
            "salary": 9_500_000,
        },
    )
    created = await call(
        "POST",
        "/employees",
        "hr",
        "with_password",
        json={
            "name": "Eka Saputra",
            "email": "eka.contract@movon.test",
            "department": "Engineering",
            "role": "employee",
            "salary": 8_000_000,
            "password": "Contract123",
            "work_location_id": location["id"],
        },
    )
    await call(
        "PATCH",
        "/employees/{employee_id}",
        "hr",
        "location",
        employee_id=created["id"],
        json={"work_location_id": location["id"]},
    )
    await call(
        "PATCH",
        "/employees/{employee_id}",
        "hr",
        "remote",
        employee_id=created["id"],
        json={"is_remote": True},
    )
    await call(
        "PATCH",
        "/employees/{employee_id}",
        "hr",
        "suspend",
        employee_id=created["id"],
        json={"status": "suspended"},
    )

    # Attendance: office worker with an immediately due reverify slot.
    check_in = {
        "latitude": office["latitude"],
        "longitude": office["longitude"],
        "accuracy_meters": 10,
        "selfie_captured": True,
        "location_share_approved": True,
        "agenda": [{"title": "Contract flow", "status": "planned"}],
    }
    key = {"Idempotency-Key": "contract-check-in"}
    await call("POST", "/attendance/check-in", "employee", json=check_in, headers=key)
    await call("POST", "/attendance/check-in", "employee", "idempotent", json=check_in, headers=key)
    await call("GET", "/attendance/today", "employee", "reverify_pending")
    await call(
        "POST",
        "/attendance/reverify",
        "employee",
        "office",
        json={
            "latitude": office["latitude"],
            "longitude": office["longitude"],
            "accuracy_meters": 10,
            "selfie_captured": True,
        },
    )
    await call("GET", "/attendance/today", "employee", "checked_in")
    await call("GET", "/dashboard", "manager", "employee_checked_in")
    await call(
        "POST",
        "/attendance/check-out",
        "employee",
        json={
            "summary": "Contract flow done",
            "latitude": office["latitude"],
            "longitude": office["longitude"],
            "accuracy_meters": 10,
        },
    )
    await call("GET", "/attendance/today", "employee", "completed")
    for who in ("hr", "manager"):
        await call(
            "GET",
            "/employees/{employee_id}/location-history",
            who,
            "after_shift",
            employee_id=employee_id,
        )
    # Remote worker: no geofence, nothing to reverify.
    await call(
        "POST",
        "/attendance/check-in",
        "remote",
        "remote",
        json=check_in | {"latitude": -7.25, "longitude": 112.75},
        headers={"Idempotency-Key": "contract-remote"},
    )
    await call(
        "POST",
        "/attendance/reverify",
        "remote",
        "remote",
        json={
            "latitude": -7.25,
            "longitude": 112.75,
            "accuracy_meters": 10,
            "selfie_captured": True,
        },
    )

    # Leave: submit, decide, cancel.
    monday = _next_monday(_today() + timedelta(days=30))
    employee_leave = await call(
        "POST",
        "/leave-requests",
        "employee",
        json={
            "start": str(monday),
            "end": str(monday + timedelta(days=1)),
            "reason": "Acara keluarga",
        },
    )
    manager_leave = await call(
        "POST",
        "/leave-requests",
        "manager",
        json={
            "start": str(monday),
            "end": str(monday),
            "reason": "Urusan pribadi",
        },
    )
    cancel_leave = await call(
        "POST",
        "/leave-requests",
        "employee",
        "to_cancel",
        json={
            "start": str(monday + timedelta(days=7)),
            "end": str(monday + timedelta(days=7)),
            "reason": "Mungkin batal",
        },
    )
    for who in ("hr", "manager"):
        await call("GET", "/approvals", who, "pending")
    await call(
        "POST",
        "/approvals/{request_id}",
        "manager",
        "approved",
        request_id=employee_leave["id"],
        json={"decision": "approved", "comment": "Oke"},
    )
    await call(
        "POST",
        "/approvals/{request_id}",
        "hr",
        "rejected",
        request_id=manager_leave["id"],
        json={"decision": "rejected", "comment": "Maaf"},
    )
    await call(
        "POST", "/leave-requests/{request_id}/cancel", "employee", request_id=cancel_leave["id"]
    )
    for who in ("manager", "employee"):
        await call("GET", "/leave-requests", who, "after_decisions")

    # Payroll (HR runs it; everyone reads payslips).
    await call("GET", "/payroll/runs", "hr", "empty")
    run = await call("POST", "/payroll/runs", "hr", json={"month": "2026-10"})
    await call("POST", "/payroll/runs", "hr", "existing", json={"month": "2026-10"})
    await call("POST", "/payroll/runs/{run_id}/finalize", "hr", run_id=run["id"])
    await call("POST", "/payroll/runs/{run_id}/publish", "hr", run_id=run["id"])
    await call("GET", "/payroll/runs", "hr", "published")
    for who in ("hr", "manager", "employee"):
        await call("GET", "/payroll/payslips", who)

    # Policies (HR) and the assistant (everyone).
    policy_body = {
        "title": "Sick Leave Policy",
        "category": "leave",
        "language": "en",
        "effective_date": str(_today() - timedelta(days=1)),
        "sections": [
            {
                "heading": "Medical certificate",
                "body": "A doctor letter is required after two sick days.",
            }
        ],
    }
    await call("GET", "/policies", "hr", "empty")
    await call(
        "POST",
        "/policy-assistant/questions",
        "employee",
        "insufficient_evidence",
        json={"question": "Do I need a doctor letter for sick leave?"},
    )
    policy = await call("POST", "/policies", "hr", json=policy_body)
    await call(
        "PUT",
        "/policies/{policy_id}",
        "hr",
        policy_id=policy["id"],
        json=policy_body | {"expiry_date": str(_today() + timedelta(days=365))},
    )
    await call("POST", "/policies/{policy_id}/publish", "hr", policy_id=policy["id"])
    for who in ("hr", "manager", "employee"):
        await call(
            "POST",
            "/policy-assistant/questions",
            who,
            "supported",
            json={"question": "Do I need a doctor letter for sick leave?"},
        )
    await call("POST", "/policies/{policy_id}/archive", "hr", policy_id=policy["id"])
    await call("GET", "/policies", "hr", "with_policy")

    # Activity read-back after the flow, then mark read.
    for who in ("hr", "manager", "employee"):
        await call("GET", "/notifications", who, "after_flow")
        await call("POST", "/notifications/read-all", who)
        await call("GET", "/dashboard", who, "after_flow")
    await call("GET", "/audit-logs", "hr")

    # Public auth flows.
    await call(
        "POST",
        "/auth/signup",
        "anon",
        json={
            "company_name": "Kontrak Dua",
            "admin_name": "Admin Dua",
            "email": "admin@kontrak-dua.test",
            "password": "Company123",
        },
    )
    invite = await call(
        "POST",
        "/invites",
        "hr",
        json={
            "name": "Wulan Sari",
            "email": "wulan.contract@movon.test",
            "department": "Finance",
            "role": "employee",
        },
    )
    invite_token = invite["invite_url"].split("token=")[1]
    await call("GET", "/invites/{token}", "anon", token=invite_token)
    await call(
        "POST",
        "/auth/accept-invite",
        "anon",
        json={"token": invite_token, "password": "Wulan12345"},
    )
    await call("POST", "/auth/forgot-password", "anon", json={"email": "andi@movon.test"})
    message = last_email_to("andi@movon.test")
    assert message is not None, "forgot-password sent no email"
    reset_token = next(part for part in message.body.split() if "token=" in part)
    await call(
        "POST",
        "/auth/reset-password/preview",
        "anon",
        json={"token": reset_token.split("token=")[1]},
    )
    await call(
        "POST",
        "/auth/reset-password",
        "anon",
        json={"token": reset_token.split("token=")[1], "password": "BaruSekali1"},
    )
    await call(
        "POST",
        "/auth/change-password",
        "employee",
        json={"current_password": PASSWORD, "new_password": "Ganti12345"},
    )
    await call("POST", "/auth/logout", "employee")
