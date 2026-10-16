import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from movon_hr.core.db import Base
from movon_hr.core.identity import UUIDV7
from movon_hr.core.tenancy import TenantScoped


class Notification(TenantScoped, Base):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=UUIDV7)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("employees.id"))
    title: Mapped[str]
    detail: Mapped[str]
    target: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    read: Mapped[bool] = mapped_column(default=False, server_default="false")
