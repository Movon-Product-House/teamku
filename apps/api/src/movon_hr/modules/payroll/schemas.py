import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field


class PayrollInput(BaseModel):
    month: str = Field(pattern=r"^\d{4}-\d{2}$")


class PayrollItem(BaseModel):
    employee_id: str
    employee: str
    gross_rupiah: int
    deductions_rupiah: int
    net_rupiah: int


class PayrollRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    period: str
    status: str
    items: list[PayrollItem]
    created_at: datetime
    finalized_at: datetime | None
    published_at: datetime | None
    calculation_version: str = "manual-components-v1"
    disclaimer: str = "PPh 21 dan BPJS harus dikonfigurasi atau disesuaikan manual."

    @computed_field
    @property
    def total_gross_rupiah(self) -> int:
        return sum(item.gross_rupiah for item in self.items)

    @computed_field
    @property
    def total_deductions_rupiah(self) -> int:
        return sum(item.deductions_rupiah for item in self.items)

    @computed_field
    @property
    def total_net_rupiah(self) -> int:
        return sum(item.net_rupiah for item in self.items)


class PayrollRunList(BaseModel):
    items: list[PayrollRunOut]


class PayslipOut(PayrollItem):
    id: uuid.UUID
    period: str
    published_at: datetime | None


class PayslipList(BaseModel):
    items: list[PayslipOut]
