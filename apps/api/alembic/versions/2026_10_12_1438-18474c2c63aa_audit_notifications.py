"""audit_notifications

Revision ID: 18474c2c63aa
Revises: 80a366acc130
Create Date: 2026-10-12 14:36:02.250930
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "18474c2c63aa"
down_revision: str | Sequence[str] | None = "80a366acc130"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Uuid(), server_default=sa.text("uuidv7()"), nullable=False),
        sa.Column(
            "at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("actor", sa.Uuid(), nullable=False),
        sa.Column("target", sa.Text(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["actor"], ["employees.id"], name=op.f("audit_logs_actor_fkey")),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], name=op.f("audit_logs_tenant_id_fkey")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("audit_logs_pkey")),
    )
    op.create_index(op.f("audit_logs_tenant_id_idx"), "audit_logs", ["tenant_id"], unique=False)
    op.create_table(
        "notifications",
        sa.Column("id", sa.Uuid(), server_default=sa.text("uuidv7()"), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False),
        sa.Column("target", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("read", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], name=op.f("notifications_tenant_id_fkey")
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["employees.id"], name=op.f("notifications_user_id_fkey")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("notifications_pkey")),
    )
    op.create_index(
        op.f("notifications_tenant_id_idx"), "notifications", ["tenant_id"], unique=False
    )


def downgrade() -> None:
    op.drop_table("notifications")
    op.drop_table("audit_logs")
