import uuid
from datetime import datetime

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from movon_hr.core.db import Base, one_of
from movon_hr.core.identity import Role
from movon_hr.core.tenancy import TenantScoped


class Invitation(TenantScoped, Base):
    """A pending employee; lives here (not in auth) because email uniqueness checks it."""

    __tablename__ = "invitations"

    token: Mapped[str] = mapped_column(primary_key=True)
    email: Mapped[str]
    name: Mapped[str]
    role: Mapped[Role]
    department: Mapped[str]
    title: Mapped[str]
    salary: Mapped[int]
    invited_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("employees.id"))
    expires_at: Mapped[datetime]
    accepted_at: Mapped[datetime | None]
    is_remote: Mapped[bool] = mapped_column(default=False, server_default="false")
    work_location_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("work_locations.id"))

    __table_args__ = (one_of("role", Role),)
