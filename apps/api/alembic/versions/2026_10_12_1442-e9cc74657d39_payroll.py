"""payroll

Revision ID: e9cc74657d39
Revises: 4fd60e633204
Create Date: 2026-10-12 14:36:04.058509
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "e9cc74657d39"
down_revision: str | Sequence[str] | None = "4fd60e633204"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "payroll_runs",
        sa.Column("id", sa.Uuid(), server_default=sa.text("uuidv7()"), nullable=False),
        sa.Column("period", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("items", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], name=op.f("payroll_runs_tenant_id_fkey")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("payroll_runs_pkey")),
        sa.UniqueConstraint("tenant_id", "period", name=op.f("payroll_runs_tenant_id_period_key")),
    )
    op.create_index(op.f("payroll_runs_tenant_id_idx"), "payroll_runs", ["tenant_id"], unique=False)


def downgrade() -> None:
    op.drop_table("payroll_runs")
