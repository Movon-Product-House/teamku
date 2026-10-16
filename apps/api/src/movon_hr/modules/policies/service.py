import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from movon_hr.core.identity import Employee
from movon_hr.core.policy_assistant import answer_question
from movon_hr.core.time import jakarta_date
from movon_hr.modules.audit.service import audit
from movon_hr.modules.employees.service import parse_id
from movon_hr.modules.leave.service import leave_balance
from movon_hr.modules.policies.models import Policy, PolicyAnswerAudit, PolicySection
from movon_hr.modules.policies.schemas import AnswerOut, PolicyInput

NOT_FOUND = "Kebijakan tidak ditemukan"
INCOMPLETE = "Kebijakan memerlukan judul dan setidaknya satu bagian yang terisi"
PROVIDER = "fake-policy-provider-v1"
with_sections = selectinload(Policy.sections)


def validate_policy(title: str, sections: Sequence[PolicySection]) -> None:
    filled = any(item.heading.strip() and item.body.strip() for item in sections)
    if not title.strip() or not filled:
        raise HTTPException(422, INCOMPLETE)


def build_sections(
    payload: PolicyInput, existing: Sequence[PolicySection] = ()
) -> list[PolicySection]:
    """A client-sent id is kept only when it names an existing section; otherwise a new uuid."""
    by_id: dict[uuid.UUID, PolicySection] = {item.id: item for item in existing}
    sections = []
    for position, item in enumerate(payload.sections):
        parsed = parse_id(item.id)
        section = (by_id.pop(parsed, None) if parsed else None) or PolicySection()
        section.heading, section.body = item.heading.strip(), item.body.strip()
        section.position = position
        sections.append(section)
    return sections


def check_dates(payload: PolicyInput) -> None:
    if payload.expiry_date and payload.expiry_date < payload.effective_date:
        raise HTTPException(422, "Tanggal berakhir harus setelah tanggal berlaku")


async def list_policies(db: AsyncSession) -> Sequence[Policy]:
    found = await db.scalars(
        select(Policy).options(with_sections).order_by(Policy.updated_at.desc(), Policy.id.desc())
    )
    return found.all()


async def policy_or_404(db: AsyncSession, policy_id: str) -> Policy:
    parsed = parse_id(policy_id)
    policy = (
        await db.scalar(select(Policy).options(with_sections).where(Policy.id == parsed))
        if parsed
        else None
    )
    if policy is None:
        raise HTTPException(404, NOT_FOUND)
    return policy


async def create_policy(db: AsyncSession, user: Employee, payload: PolicyInput) -> Policy:
    check_dates(payload)
    sections = build_sections(payload)
    validate_policy(payload.title, sections)
    policy = Policy(
        title=payload.title.strip(),
        category=payload.category.strip(),
        language=payload.language,
        effective_date=payload.effective_date,
        expiry_date=payload.expiry_date,
        state="draft",
        sections=sections,
        created_by=user.id,
        updated_by=user.id,
    )
    db.add(policy)
    await db.flush()
    await audit(db, "policy.created", user, str(policy.id))
    return policy


async def update_policy(
    db: AsyncSession, user: Employee, policy_id: str, payload: PolicyInput
) -> Policy:
    policy = await policy_or_404(db, policy_id)
    check_dates(payload)
    sections = build_sections(payload, policy.sections)
    validate_policy(payload.title, sections)
    policy.title, policy.category = payload.title.strip(), payload.category.strip()
    policy.language = payload.language
    policy.effective_date, policy.expiry_date = payload.effective_date, payload.expiry_date
    policy.sections = sections  # sections left out are deleted (delete-orphan)
    policy.updated_at, policy.updated_by = datetime.now(UTC), user.id
    await db.flush()
    await audit(db, "policy.updated", user, str(policy.id))
    return policy


async def set_state(db: AsyncSession, user: Employee, policy_id: str, state: str) -> Policy:
    """Publish or archive; no transition rules, as before (kept, #26)."""
    policy = await policy_or_404(db, policy_id)
    if state == "published":
        validate_policy(policy.title, policy.sections)
    policy.state, policy.updated_at, policy.updated_by = state, datetime.now(UTC), user.id
    await audit(db, f"policy.{state}", user, str(policy.id))
    return policy


async def ask(db: AsyncSession, user: Employee, question: str) -> AnswerOut:
    balance = await leave_balance(db, user.id)
    facts = [
        {"type": "leave_balance", "label": "Sisa cuti tahunan", "value": balance.remaining_days}
    ]
    # Retrieval only uses published policies; creation order keeps ties as before.
    policies = await db.scalars(
        select(Policy)
        .options(with_sections)
        .where(Policy.state == "published")
        .order_by(Policy.created_at, Policy.id)
    )
    response, outcome = answer_question(
        policies=list(policies), question=question.strip(), today=jakarta_date(), facts=facts
    )
    receipt = PolicyAnswerAudit(
        actor_id=user.id,
        question=question.strip()[:800],
        cited_sections=[
            {"policy_id": str(item["policy_id"]), "section_id": str(item["section_id"])}
            for item in response["citations"]
        ],
        provider=PROVIDER,
        outcome=outcome,
        suggested_action=response["suggested_action"]["type"],
    )
    db.add(receipt)
    await db.flush()
    await audit(db, "policy_assistant.answered", user, str(receipt.id))
    return AnswerOut.model_validate(response)
