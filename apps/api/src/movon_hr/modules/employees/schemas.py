import uuid

from pydantic import BaseModel, ConfigDict, Field

from movon_hr.modules.settings.schemas import LocationOut


class EmployeeInput(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: str = Field(min_length=5, max_length=150)
    department: str = Field(min_length=2, max_length=100)
    role: str = Field(pattern="^(employee|manager|hr_admin)$")
    title: str = Field(default="Staff", min_length=2, max_length=100)
    salary: int = Field(ge=0, le=10_000_000_000)
    # Optional initial password; when omitted a temporary one is generated.
    password: str | None = Field(default=None, min_length=8, max_length=128)
    is_remote: bool = False
    # Plain str, not UUID: the web sends "" for "no location" and ids are not validated here.
    work_location_id: str | None = None


class EmployeeUpdate(BaseModel):
    status: str | None = Field(default=None, pattern="^(active|suspended|terminated)$")
    is_remote: bool | None = None
    # Plain str, so an unknown or malformed id gets the old 422 message.
    work_location_id: str | None = None


class EmployeeColumns(BaseModel):
    """The employee columns that are safe to send; password_hash and tenant_id never are."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    email: str
    role: str
    department: str
    title: str
    status: str
    salary: int | None  # None when the viewer is a manager
    is_remote: bool
    work_location_id: uuid.UUID | None


class EmployeeOut(EmployeeColumns):
    work_mode: str
    work_location: LocationOut | None  # None for remote (field) employees


class NewEmployeeOut(EmployeeOut):
    """Returned once by POST /employees when HR did not set a password."""

    temporary_password: str


class EmployeeList(BaseModel):
    items: list[EmployeeOut]
    total: int
