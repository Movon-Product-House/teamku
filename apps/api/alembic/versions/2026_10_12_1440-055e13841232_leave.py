"""leave

Revision ID: 055e13841232
Revises: 1169768db875
Create Date: 2026-10-12 14:36:03.174676
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "055e13841232"
down_revision: str | Sequence[str] | None = "1169768db875"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "leave_requests",
        sa.Column("id", sa.Uuid(), server_default=sa.text("uuidv7()"), nullable=False),
        sa.Column("employee_id", sa.Uuid(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("request_type", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("approver_comment", sa.Text(), nullable=True),
        sa.Column(
            "calendar_sync_status", sa.Text(), server_default="not_applicable", nullable=False
        ),
        sa.Column("employee_calendar_event_id", sa.Text(), nullable=True),
        sa.Column("team_calendar_event_id", sa.Text(), nullable=True),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["employee_id"], ["employees.id"], name=op.f("leave_requests_employee_id_fkey")
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], name=op.f("leave_requests_tenant_id_fkey")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("leave_requests_pkey")),
    )
    op.create_index(
        op.f("leave_requests_tenant_id_idx"), "leave_requests", ["tenant_id"], unique=False
    )


def downgrade() -> None:
    op.drop_table("leave_requests")
