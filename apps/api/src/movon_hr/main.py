import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from movon_hr.core.settings import settings
from movon_hr.modules.attendance.router import router as attendance_router
from movon_hr.modules.audit.router import router as audit_router
from movon_hr.modules.auth.router import router as auth_router
from movon_hr.modules.dashboard.router import router as dashboard_router
from movon_hr.modules.employees.router import router as employees_router
from movon_hr.modules.leave.router import router as leave_router
from movon_hr.modules.notifications.router import router as notifications_router
from movon_hr.modules.payroll.router import router as payroll_router
from movon_hr.modules.policies.router import router as policies_router
from movon_hr.modules.settings.router import router as settings_router

# Without this, app INFO logs (mail results) never reach the container log.
logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="Teamku API",
    version="0.1.0",
    # Off in production; the committed openapi.json is dumped from app.openapi() directly.
    openapi_url=None if settings.environment == "production" else "/api/v1/openapi.json",
    # Operation ids are the handler names, so the generated web client reads like the API.
    generate_unique_id_function=lambda route: route.name,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "PUT"],
    allow_headers=["Content-Type", "Idempotency-Key"],
)


class FieldErrorOut(BaseModel):
    loc: list[str | int]
    msg: str
    type: str


class ErrorOut(BaseModel):
    """Every 4xx body: an HTTPException message, or the field errors of a request 422."""

    detail: str | list[FieldErrorOut]


# "4XX" replaces FastAPI's own 422 entry, so ErrorOut covers validation errors too.
for router in (
    attendance_router,
    audit_router,
    auth_router,
    dashboard_router,
    employees_router,
    leave_router,
    notifications_router,
    payroll_router,
    policies_router,
    settings_router,
):
    app.include_router(router, prefix="/api/v1", responses={"4XX": {"model": ErrorOut}})


@app.get("/health/live", include_in_schema=False)
async def live() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready", include_in_schema=False)
async def ready() -> dict[str, str]:
    return {"status": "ready"}
