import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from movon_hr.modules.policies.models import Language, PolicyState


class PolicySectionIn(BaseModel):
    # Kept only when it is the id of an existing section of the same policy.
    id: str | None = Field(default=None, max_length=80)
    heading: str = Field(min_length=1, max_length=160)
    body: str = Field(min_length=1, max_length=10_000)


class PolicyIn(BaseModel):
    title: str = Field(min_length=2, max_length=160)
    category: str = Field(default="general", min_length=2, max_length=80)
    language: Language = "id"
    effective_date: date
    expiry_date: date | None = None
    sections: list[PolicySectionIn] = Field(min_length=1, max_length=50)


class PolicyQuestionIn(BaseModel):
    question: str = Field(min_length=3, max_length=800)


class PolicySectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    heading: str
    body: str
    position: int


class PolicyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    category: str
    language: Language
    effective_date: date
    expiry_date: date | None
    state: PolicyState
    sections: list[PolicySectionOut]
    created_at: datetime
    updated_at: datetime
    created_by: uuid.UUID
    updated_by: uuid.UUID


class PolicyListOut(BaseModel):
    items: list[PolicyOut]


class CitationOut(BaseModel):
    policy_id: uuid.UUID
    policy_title: str
    section_id: uuid.UUID
    section_heading: str
    effective_date: date
    excerpt: str
    score: int


# The assistant (core/policy_assistant.py) maps provider output onto these closed sets.
class PersonalFactOut(BaseModel):
    type: Literal["leave_balance"]
    label: str
    value: int


class SuggestedActionOut(BaseModel):
    type: Literal["contact_hr", "open_leave_request"]
    href: str


class AnswerOut(BaseModel):
    answer: str
    confidence: Literal["supported", "partially_supported", "insufficient_evidence"]
    citations: list[CitationOut]
    personal_facts: list[PersonalFactOut]
    suggested_action: SuggestedActionOut
