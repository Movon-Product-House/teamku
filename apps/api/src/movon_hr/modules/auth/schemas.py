import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from movon_hr.modules.employees.schemas import EmployeeOut


class Login(BaseModel):
    email: str
    password: str = Field(min_length=8, max_length=128)


class Signup(BaseModel):
    company_name: str = Field(min_length=2, max_length=120)
    slug: str | None = Field(default=None, min_length=3, max_length=40)
    admin_name: str = Field(min_length=2, max_length=100)
    email: str = Field(min_length=5, max_length=150)
    password: str = Field(min_length=8, max_length=128)


class InviteInput(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: str = Field(min_length=5, max_length=150)
    department: str = Field(min_length=2, max_length=100)
    role: str = Field(pattern="^(employee|manager|hr_admin)$")
    title: str = Field(default="Staff", min_length=2, max_length=100)
    salary: int = Field(default=8_000_000, ge=0, le=10_000_000_000)
    is_remote: bool = False
    # Plain str, not UUID: not validated on invite (bug kept, see the plan).
    work_location_id: str | None = None


class AcceptInvite(BaseModel):
    token: str = Field(min_length=8, max_length=200)
    password: str = Field(min_length=8, max_length=128)
    name: str | None = Field(default=None, min_length=2, max_length=100)


class ForgotPassword(BaseModel):
    email: str = Field(min_length=5, max_length=150)


class ResetPassword(BaseModel):
    token: str = Field(min_length=8, max_length=200)
    password: str = Field(min_length=8, max_length=128)


class ChangePassword(BaseModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class TenantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str


class MeOut(BaseModel):
    user: EmployeeOut
    tenant: TenantOut


class AuthOut(MeOut):
    access_token: str


class InviteOut(BaseModel):
    email: str
    expires_at: datetime
    invite_url: str
    email_status: str  # "sent" | "failed"


class InvitePreview(BaseModel):
    email: str
    name: str
    company: str
    role: str
    department: str
    title: str
