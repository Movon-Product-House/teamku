"""policies

Revision ID: daa8ed3243d2
Revises: e9cc74657d39
Create Date: 2026-10-12 14:36:04.565291
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "daa8ed3243d2"
down_revision: str | Sequence[str] | None = "e9cc74657d39"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "policies",
        sa.Column("id", sa.Uuid(), server_default=sa.text("uuidv7()"), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("category", sa.Text(), nullable=False),
        sa.Column("language", sa.Text(), nullable=False),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column("expiry_date", sa.Date(), nullable=True),
        sa.Column("state", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("updated_by", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["created_by"], ["employees.id"], name=op.f("policies_created_by_fkey")
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], name=op.f("policies_tenant_id_fkey")
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"], ["employees.id"], name=op.f("policies_updated_by_fkey")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("policies_pkey")),
    )
    op.create_index(op.f("policies_tenant_id_idx"), "policies", ["tenant_id"], unique=False)
    op.create_table(
        "policy_sections",
        sa.Column("id", sa.Uuid(), server_default=sa.text("uuidv7()"), nullable=False),
        sa.Column("policy_id", sa.Uuid(), nullable=False),
        sa.Column("heading", sa.Text(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["policy_id"],
            ["policies.id"],
            name=op.f("policy_sections_policy_id_fkey"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], name=op.f("policy_sections_tenant_id_fkey")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("policy_sections_pkey")),
    )
    op.create_index(
        op.f("policy_sections_policy_id_idx"), "policy_sections", ["policy_id"], unique=False
    )
    op.create_index(
        op.f("policy_sections_tenant_id_idx"), "policy_sections", ["tenant_id"], unique=False
    )
    op.create_table(
        "policy_answer_audit",
        sa.Column("id", sa.Uuid(), server_default=sa.text("uuidv7()"), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("cited_sections", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("outcome", sa.Text(), nullable=False),
        sa.Column("suggested_action", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["actor_id"], ["employees.id"], name=op.f("policy_answer_audit_actor_id_fkey")
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], name=op.f("policy_answer_audit_tenant_id_fkey")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("policy_answer_audit_pkey")),
    )
    op.create_index(
        op.f("policy_answer_audit_tenant_id_idx"),
        "policy_answer_audit",
        ["tenant_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table("policy_answer_audit")
    op.drop_table("policy_sections")
    op.drop_table("policies")
