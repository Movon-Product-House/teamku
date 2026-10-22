import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from movon_hr.core.identity import Role
from movon_hr.modules.employees.schemas import EmployeeOut


class LoginIn(BaseModel):
    email: str
    # No min_length: a short wrong password must be a 401 that counts toward the lockout.
    password: str = Field(max_length=128)


class SignupIn(BaseModel):
    company_name: str = Field(min_length=2, max_length=120)
    slug: str | None = Field(default=None, min_length=3, max_length=40)
    admin_name: str = Field(min_length=2, max_length=100)
    email: str = Field(min_length=5, max_length=150)
    password: str = Field(min_length=8, max_length=128)


class InviteIn(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: str = Field(min_length=5, max_length=150)
    department: str = Field(min_length=2, max_length=100)
    role: Role
    title: str = Field(default="Staff", min_length=2, max_length=100)
    salary: int = Field(default=8_000_000, ge=0, le=10_000_000_000)
    is_remote: bool = False
    # Plain str, not UUID: not validated on invite (bug kept, see the plan).
    work_location_id: str | None = None


class AcceptInviteIn(BaseModel):
    token: str = Field(min_length=8, max_length=200)
    password: str = Field(min_length=8, max_length=128)
    name: str | None = Field(default=None, min_length=2, max_length=100)


class ForgotPasswordIn(BaseModel):
    email: str = Field(min_length=5, max_length=150)


class ResetPasswordIn(BaseModel):
    token: str = Field(min_length=8, max_length=200)
    password: str = Field(min_length=8, max_length=128)


class ResetPreviewIn(BaseModel):
    # No min_length: a cut-off link must 404 (dead link), not 422.
    token: str = Field(max_length=200)


class ChangePasswordIn(BaseModel):
    # Only checked against the hash, not the policy: a short current password is just wrong.
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class TenantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str


class MeOut(BaseModel):
    user: EmployeeOut
    tenant: TenantOut


class InviteOut(BaseModel):
    email: str
    expires_at: datetime
    invite_url: str
    email_status: Literal["sent", "failed"]


class InvitePreviewOut(BaseModel):
    email: str
    name: str
    company: str
    role: Role
    department: str
    title: str
    invited_by: str | None
    expires_at: datetime


class ResetPreviewOut(BaseModel):
    email: str
