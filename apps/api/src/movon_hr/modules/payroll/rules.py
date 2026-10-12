"""Pure payroll calculation in Decimal, rounded to whole rupiah."""

from decimal import ROUND_HALF_UP, Decimal

# Hardcoded flat deduction, kept as is (bug #25, see the plan's scope boundaries).
DEDUCTION_RATE = Decimal("0.02")


def payroll_item(employee_id: str, name: str, salary: int) -> dict:
    gross = Decimal(salary)
    deduction = (gross * DEDUCTION_RATE).quantize(Decimal(1), rounding=ROUND_HALF_UP)
    return {
        "employee_id": employee_id,
        "employee": name,
        "gross_rupiah": int(gross),
        "deductions_rupiah": int(deduction),
        "net_rupiah": int(gross - deduction),
    }
