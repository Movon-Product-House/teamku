import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index, text
from sqlalchemy.orm import Mapped, mapped_column

from movon_hr.core.db import Base
from movon_hr.core.identity import UUIDV7
from movon_hr.core.tenancy import TenantScoped


class WorkLocation(TenantScoped, Base):
    """A work location; the primary one also carries the office policy (reverify, alerts)."""

    __tablename__ = "work_locations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=UUIDV7)
    name: Mapped[str]
    latitude: Mapped[float]
    longitude: Mapped[float]
    radius_meters: Mapped[float]
    is_primary: Mapped[bool] = mapped_column(default=False, server_default="false")
    reverify_enabled: Mapped[bool] = mapped_column(default=False, server_default="false")
    reverify_count_per_day: Mapped[int] = mapped_column(default=1, server_default="1")
    reverify_window_start_minutes: Mapped[int] = mapped_column(default=60, server_default="60")
    reverify_window_end_minutes: Mapped[int] = mapped_column(default=420, server_default="420")
    alerts_enabled: Mapped[bool] = mapped_column(default=False, server_default="false")
    clock_in_reminder_time: Mapped[str] = mapped_column(default="09:15", server_default="09:15")
    clock_out_reminder_time: Mapped[str] = mapped_column(default="18:15", server_default="18:15")
    max_open_hours: Mapped[int] = mapped_column(default=10, server_default="10")
    alert_managers: Mapped[bool] = mapped_column(default=False, server_default="false")

    __table_args__ = (
        # At most one primary location per tenant.
        Index(
            "work_locations_tenant_id_key",
            "tenant_id",
            unique=True,
            postgresql_where=text("is_primary"),
        ),
    )


class CalendarSettings(TenantScoped, Base):
    """One row per tenant; Google OAuth tokens live here."""

    __tablename__ = "calendar_settings"

    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), primary_key=True)
    provider: Mapped[str] = mapped_column(default="", server_default="")
    connected: Mapped[bool] = mapped_column(default=False, server_default="false")
    team_calendar_id: Mapped[str] = mapped_column(default="", server_default="")
    calendar_name: Mapped[str] = mapped_column(default="", server_default="")
    scope: Mapped[str] = mapped_column(default="company", server_default="company")
    division: Mapped[str] = mapped_column(default="", server_default="")
    delivery_mode: Mapped[str] = mapped_column(
        default="shared_and_email", server_default="shared_and_email"
    )
    refresh_token: Mapped[str | None]
    access_token: Mapped[str | None]
    token_expires_at: Mapped[datetime | None]


class OAuthState(TenantScoped, Base):
    """Pending Google OAuth flow; looked up cross-tenant by the callback."""

    __tablename__ = "oauth_states"

    state: Mapped[str] = mapped_column(primary_key=True)
    employee_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("employees.id"))
    expires_at: Mapped[datetime]
