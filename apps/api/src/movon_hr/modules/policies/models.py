import uuid
from datetime import date, datetime
from typing import Literal

from sqlalchemy import ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from movon_hr.core.db import Base, one_of
from movon_hr.core.identity import UUIDV7
from movon_hr.core.tenancy import TenantScoped

type PolicyLanguage = Literal["id", "en"]
type PolicyState = Literal["draft", "published", "archived"]


class Policy(TenantScoped, Base):
    __tablename__ = "policies"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=UUIDV7)
    title: Mapped[str]
    category: Mapped[str]
    language: Mapped[PolicyLanguage]
    effective_date: Mapped[date]
    expiry_date: Mapped[date | None]
    state: Mapped[PolicyState] = mapped_column(default="draft")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now())
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("employees.id"))
    updated_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("employees.id"))

    sections: Mapped[list["PolicySection"]] = relationship(
        lazy="raise",
        order_by="PolicySection.position",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (one_of("language", PolicyLanguage), one_of("state", PolicyState))


class PolicySection(TenantScoped, Base):
    __tablename__ = "policy_sections"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=UUIDV7)
    policy_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("policies.id", ondelete="CASCADE"), index=True
    )
    heading: Mapped[str]
    body: Mapped[str]
    position: Mapped[int]


class PolicyAnswerAudit(TenantScoped, Base):
    __tablename__ = "policy_answer_audit"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=UUIDV7)
    actor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("employees.id"))
    question: Mapped[str]
    cited_sections: Mapped[list[dict]] = mapped_column(JSONB)
    provider: Mapped[str]
    outcome: Mapped[str]
    suggested_action: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
