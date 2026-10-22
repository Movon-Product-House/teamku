import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, field_serializer


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    at: datetime
    action: str
    actor: uuid.UUID
    target: str

    @field_serializer("at")
    def _at(self, value: datetime) -> str:
        # The old API stored datetime.isoformat() strings: "+00:00", not Pydantic's "Z".
        return value.astimezone(UTC).isoformat(timespec="microseconds")


class AuditLogListOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: list[AuditLogOut]
