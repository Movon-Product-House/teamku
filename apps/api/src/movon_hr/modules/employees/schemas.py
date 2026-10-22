import uuid
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from movon_hr.core.identity import EmployeeRole, EmployeeStatus
from movon_hr.modules.settings.schemas import LocationOut


class EmployeeCreateIn(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: str = Field(min_length=5, max_length=150)
    department: str = Field(min_length=2, max_length=100)
    role: EmployeeRole
    title: str = Field(default="Staff", min_length=2, max_length=100)
    salary: int = Field(ge=0, le=10_000_000_000)
    # Optional initial password; when omitted a temporary one is generated.
    password: str | None = Field(default=None, min_length=8, max_length=128)
    is_remote: bool = False
    # Plain str, not UUID: the web sends "" for "no location" and ids are not validated here.
    work_location_id: str | None = None


class EmployeeUpdateIn(BaseModel):
    status: EmployeeStatus | None = None
    is_remote: bool | None = None
    # Plain str, so an unknown or malformed id gets the old 422 message.
    work_location_id: str | None = None


class EmployeeColumns(BaseModel):
    """The employee columns that are safe to send; password_hash and tenant_id never are."""

    model_config = ConfigDict(
        from_attributes=True, json_schema_serialization_defaults_required=True
    )

    id: uuid.UUID
    name: str
    email: str
    role: EmployeeRole
    department: str
    title: str
    status: EmployeeStatus
    salary: int | None  # None when the viewer is a manager
    is_remote: bool
    work_location_id: uuid.UUID | None


class EmployeeOut(EmployeeColumns):
    work_mode: Literal["office", "field"]
    work_location: LocationOut | None  # None for remote (field) employees


class CreatedEmployeeOut(EmployeeOut):
    """Returned by POST /employees when HR set the password."""

    result: Literal["password_set"] = "password_set"


class NewEmployeeOut(EmployeeOut):
    """Returned once by POST /employees when HR did not set a password."""

    result: Literal["temporary_password"] = "temporary_password"
    temporary_password: str


CreateEmployeeResult = Annotated[CreatedEmployeeOut | NewEmployeeOut, Field(discriminator="result")]


class EmployeeListOut(BaseModel):
    items: list[EmployeeOut]
    total: int
