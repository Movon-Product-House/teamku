"""Identity models core/auth.py needs: tenants, employees and login sessions."""

import uuid
from datetime import datetime
from typing import Literal

from sqlalchemy import ForeignKey, Index, func, text
from sqlalchemy.orm import Mapped, mapped_column

from movon_hr.core.db import Base, one_of
from movon_hr.core.tenancy import TenantScoped

UUIDV7 = text("uuidv7()")

Role = Literal["employee", "manager", "hr_admin"]
EmployeeStatus = Literal["active", "suspended", "terminated"]


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=UUIDV7)
    name: Mapped[str]
    slug: Mapped[str] = mapped_column(unique=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class Employee(TenantScoped, Base):
    __tablename__ = "employees"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=UUIDV7)
    name: Mapped[str]
    email: Mapped[str]
    role: Mapped[Role]
    department: Mapped[str]
    title: Mapped[str] = mapped_column(default="Staff")
    status: Mapped[EmployeeStatus] = mapped_column(default="active")
    salary: Mapped[int] = mapped_column(default=8_000_000)
    password_hash: Mapped[str] = mapped_column(default="", server_default="")
    is_remote: Mapped[bool] = mapped_column(default=False, server_default="false")
    # work_locations is defined in modules/settings/models.py (core must not import modules).
    work_location_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("work_locations.id"))

    __table_args__ = (one_of("role", Role), one_of("status", EmployeeStatus))


# Work email stays unique across companies, like today.
Index("employees_lower_email_key", func.lower(Employee.email), unique=True)


class AuthSession(TenantScoped, Base):
    """A login session; the token is random text, not a uuid."""

    __tablename__ = "sessions"

    token: Mapped[str] = mapped_column(primary_key=True)
    employee_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("employees.id"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    expires_at: Mapped[datetime]
