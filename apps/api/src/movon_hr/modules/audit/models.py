import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from movon_hr.core.db import Base
from movon_hr.core.identity import UUIDV7
from movon_hr.core.tenancy import TenantScoped


class AuditLog(TenantScoped, Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=UUIDV7)
    at: Mapped[datetime] = mapped_column(server_default=func.now())
    action: Mapped[str]
    actor: Mapped[uuid.UUID] = mapped_column(ForeignKey("employees.id"))
    target: Mapped[str]
