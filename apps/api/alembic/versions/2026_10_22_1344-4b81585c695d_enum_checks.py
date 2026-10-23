"""enum_checks

CHECK constraints for the text columns the API exposes as enums (#46). Values are
frozen here; the models build theirs from the Literal types with one_of().

Revision ID: 4b81585c695d
Revises: daa8ed3243d2
Create Date: 2026-10-22 13:44:48.219921
"""

from collections.abc import Sequence

from alembic import op

revision: str = "4b81585c695d"
down_revision: str | Sequence[str] | None = "daa8ed3243d2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ROLE = ("employee", "manager", "hr_admin")
ANOMALY = ("low_accuracy", "missed_reverify", "outside_geofence")

# (table, column, allowed values)
CHECKS = [
    ("employees", "role", ROLE),
    ("employees", "status", ("active", "suspended", "terminated")),
    ("invitations", "role", ROLE),
    ("leave_requests", "request_type", ("time_off",)),
    (
        "leave_requests",
        "status",
        ("pending", "cancelled", "approved", "rejected", "revision_requested"),
    ),
    (
        "leave_requests",
        "calendar_sync_status",
        ("not_applicable", "skipped", "ok", "failed", "removed"),
    ),
    ("attendance", "anomaly", ANOMALY),
    ("location_events", "kind", ("check_in", "check_out", "reverify")),
    ("location_events", "anomaly", ANOMALY),
    ("payroll_runs", "status", ("draft", "finalized", "published")),
    ("policies", "language", ("id", "en")),
    ("policies", "state", ("draft", "published", "archived")),
    ("calendar_settings", "provider", ("", "google", "microsoft")),
    ("calendar_settings", "scope", ("company", "division")),
    ("calendar_settings", "delivery_mode", ("shared", "shared_and_email")),
]


def upgrade() -> None:
    for table, column, values in CHECKS:
        allowed = ", ".join(f"'{value}'" for value in values)
        op.create_check_constraint(
            op.f(f"{table}_{column}_check"), table, f"{column} IN ({allowed})"
        )


def downgrade() -> None:
    for table, column, _ in reversed(CHECKS):
        op.drop_constraint(op.f(f"{table}_{column}_check"), table, type_="check")
