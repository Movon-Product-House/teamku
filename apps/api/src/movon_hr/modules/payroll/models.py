import uuid
from datetime import datetime
from typing import Literal

from sqlalchemy import UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from movon_hr.core.db import Base, one_of
from movon_hr.core.identity import UUIDV7
from movon_hr.core.tenancy import TenantScoped

PayrollStatus = Literal["draft", "finalized", "published"]


class PayrollRun(TenantScoped, Base):
    __tablename__ = "payroll_runs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=UUIDV7)
    period: Mapped[str]
    status: Mapped[PayrollStatus]
    items: Mapped[list[dict]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    finalized_at: Mapped[datetime | None]
    published_at: Mapped[datetime | None]

    __table_args__ = (UniqueConstraint("tenant_id", "period"), one_of("status", PayrollStatus))
