"""attendance

Revision ID: 4fd60e633204
Revises: 055e13841232
Create Date: 2026-10-12 14:36:03.611386
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "4fd60e633204"
down_revision: str | Sequence[str] | None = "055e13841232"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "attendance",
        sa.Column("id", sa.Uuid(), server_default=sa.text("uuidv7()"), nullable=False),
        sa.Column("employee_id", sa.Uuid(), nullable=False),
        sa.Column("checked_in_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("accuracy_meters", sa.Float(), nullable=False),
        sa.Column("agenda", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("anomaly", sa.Text(), nullable=True),
        sa.Column("checked_out_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["employee_id"], ["employees.id"], name=op.f("attendance_employee_id_fkey")
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], name=op.f("attendance_tenant_id_fkey")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("attendance_pkey")),
    )
    op.create_index(
        "attendance_tenant_id_employee_id_key",
        "attendance",
        ["tenant_id", "employee_id"],
        unique=True,
        postgresql_where=sa.text("checked_out_at IS NULL"),
    )
    op.create_index(op.f("attendance_tenant_id_idx"), "attendance", ["tenant_id"], unique=False)
    op.create_table(
        "idempotency_keys",
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("key", sa.Text(), nullable=False),
        sa.Column("attendance_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["attendance_id"], ["attendance.id"], name=op.f("idempotency_keys_attendance_id_fkey")
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], name=op.f("idempotency_keys_tenant_id_fkey")
        ),
        sa.PrimaryKeyConstraint("tenant_id", "key", name=op.f("idempotency_keys_pkey")),
    )
    op.create_table(
        "location_events",
        sa.Column("id", sa.Uuid(), server_default=sa.text("uuidv7()"), nullable=False),
        sa.Column("employee_id", sa.Uuid(), nullable=False),
        sa.Column("attendance_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lat", sa.Float(), nullable=True),
        sa.Column("lng", sa.Float(), nullable=True),
        sa.Column("accuracy", sa.Float(), nullable=True),
        sa.Column("distance_meters", sa.Float(), nullable=True),
        sa.Column("inside_geofence", sa.Boolean(), nullable=True),
        sa.Column("anomaly", sa.Text(), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["attendance_id"], ["attendance.id"], name=op.f("location_events_attendance_id_fkey")
        ),
        sa.ForeignKeyConstraint(
            ["employee_id"], ["employees.id"], name=op.f("location_events_employee_id_fkey")
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], name=op.f("location_events_tenant_id_fkey")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("location_events_pkey")),
    )
    op.create_index(
        op.f("location_events_tenant_id_idx"), "location_events", ["tenant_id"], unique=False
    )
    op.create_table(
        "alert_receipts",
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("employee_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("local_date", sa.Date(), nullable=False),
        sa.ForeignKeyConstraint(
            ["employee_id"], ["employees.id"], name=op.f("alert_receipts_employee_id_fkey")
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], name=op.f("alert_receipts_tenant_id_fkey")
        ),
        sa.PrimaryKeyConstraint(
            "tenant_id", "employee_id", "kind", "local_date", name=op.f("alert_receipts_pkey")
        ),
    )


def downgrade() -> None:
    op.drop_table("alert_receipts")
    op.drop_table("location_events")
    op.drop_table("idempotency_keys")
    op.drop_table("attendance")
