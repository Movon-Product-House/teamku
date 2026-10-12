"""auth

Revision ID: 1169768db875
Revises: 18474c2c63aa
Create Date: 2026-10-12 14:36:02.701958
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "1169768db875"
down_revision: str | Sequence[str] | None = "18474c2c63aa"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "invitations",
        sa.Column("token", sa.Text(), nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("department", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("salary", sa.Integer(), nullable=False),
        sa.Column("invited_by", sa.Uuid(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_remote", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("work_location_id", sa.Uuid(), nullable=True),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["invited_by"], ["employees.id"], name=op.f("invitations_invited_by_fkey")
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], name=op.f("invitations_tenant_id_fkey")
        ),
        sa.ForeignKeyConstraint(
            ["work_location_id"],
            ["work_locations.id"],
            name=op.f("invitations_work_location_id_fkey"),
        ),
        sa.PrimaryKeyConstraint("token", name=op.f("invitations_pkey")),
    )
    op.create_index(op.f("invitations_tenant_id_idx"), "invitations", ["tenant_id"], unique=False)
    op.create_table(
        "password_resets",
        sa.Column("token", sa.Text(), nullable=False),
        sa.Column("employee_id", sa.Uuid(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["employee_id"], ["employees.id"], name=op.f("password_resets_employee_id_fkey")
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], name=op.f("password_resets_tenant_id_fkey")
        ),
        sa.PrimaryKeyConstraint("token", name=op.f("password_resets_pkey")),
    )
    op.create_index(
        op.f("password_resets_tenant_id_idx"), "password_resets", ["tenant_id"], unique=False
    )
    op.create_table(
        "login_attempts",
        sa.Column("id", sa.Uuid(), server_default=sa.text("uuidv7()"), nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column(
            "attempted_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("login_attempts_pkey")),
    )
    op.create_index(
        "login_attempts_email_attempted_at_idx",
        "login_attempts",
        ["email", "attempted_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table("login_attempts")
    op.drop_table("password_resets")
    op.drop_table("invitations")
