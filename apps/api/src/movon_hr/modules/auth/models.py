import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index, func
from sqlalchemy.orm import Mapped, mapped_column

from movon_hr.core.db import Base
from movon_hr.core.identity import UUIDV7
from movon_hr.core.tenancy import TenantScoped


class Invitation(TenantScoped, Base):
    __tablename__ = "invitations"

    token: Mapped[str] = mapped_column(primary_key=True)
    email: Mapped[str]
    name: Mapped[str]
    role: Mapped[str]
    department: Mapped[str]
    title: Mapped[str]
    salary: Mapped[int]
    invited_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("employees.id"))
    expires_at: Mapped[datetime]
    accepted_at: Mapped[datetime | None]
    is_remote: Mapped[bool] = mapped_column(default=False, server_default="false")
    work_location_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("work_locations.id"))


class PasswordReset(TenantScoped, Base):
    __tablename__ = "password_resets"

    token: Mapped[str] = mapped_column(primary_key=True)
    employee_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("employees.id"))
    expires_at: Mapped[datetime]
    used_at: Mapped[datetime | None]


class LoginAttempt(Base):
    """A failed login; not tenant-scoped because login happens before the tenant is known."""

    __tablename__ = "login_attempts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=UUIDV7)
    email: Mapped[str]
    attempted_at: Mapped[datetime] = mapped_column(server_default=func.now())

    __table_args__ = (Index("login_attempts_email_attempted_at_idx", "email", "attempted_at"),)
