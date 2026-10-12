"""identity

Revision ID: c36da4a4630f
Revises:
Create Date: 2026-10-12 14:36:01.331532
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c36da4a4630f"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("id", sa.Uuid(), server_default=sa.text("uuidv7()"), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("slug", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("tenants_pkey")),
        sa.UniqueConstraint("slug", name=op.f("tenants_slug_key")),
    )
    # employees.work_location_id gets its FK in the settings revision.
    op.create_table(
        "employees",
        sa.Column("id", sa.Uuid(), server_default=sa.text("uuidv7()"), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("department", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("salary", sa.Integer(), nullable=False),
        sa.Column("password_hash", sa.Text(), server_default="", nullable=False),
        sa.Column("is_remote", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("work_location_id", sa.Uuid(), nullable=True),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], name=op.f("employees_tenant_id_fkey")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("employees_pkey")),
    )
    op.create_index(
        "employees_lower_email_key", "employees", [sa.text("lower(email)")], unique=True
    )
    op.create_index(op.f("employees_tenant_id_idx"), "employees", ["tenant_id"], unique=False)
    op.create_table(
        "sessions",
        sa.Column("token", sa.Text(), nullable=False),
        sa.Column("employee_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["employee_id"], ["employees.id"], name=op.f("sessions_employee_id_fkey")
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], name=op.f("sessions_tenant_id_fkey")
        ),
        sa.PrimaryKeyConstraint("token", name=op.f("sessions_pkey")),
    )
    op.create_index(op.f("sessions_tenant_id_idx"), "sessions", ["tenant_id"], unique=False)


def downgrade() -> None:
    op.drop_table("sessions")
    op.drop_table("employees")
    op.drop_table("tenants")
