"""settings

Revision ID: 80a366acc130
Revises: c36da4a4630f
Create Date: 2026-10-12 14:36:01.800733
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "80a366acc130"
down_revision: str | Sequence[str] | None = "c36da4a4630f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "work_locations",
        sa.Column("id", sa.Uuid(), server_default=sa.text("uuidv7()"), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("radius_meters", sa.Float(), nullable=False),
        sa.Column("is_primary", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("reverify_enabled", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("reverify_count_per_day", sa.Integer(), server_default="1", nullable=False),
        sa.Column(
            "reverify_window_start_minutes", sa.Integer(), server_default="60", nullable=False
        ),
        sa.Column(
            "reverify_window_end_minutes", sa.Integer(), server_default="420", nullable=False
        ),
        sa.Column("alerts_enabled", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("clock_in_reminder_time", sa.Text(), server_default="09:15", nullable=False),
        sa.Column("clock_out_reminder_time", sa.Text(), server_default="18:15", nullable=False),
        sa.Column("max_open_hours", sa.Integer(), server_default="10", nullable=False),
        sa.Column("alert_managers", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], name=op.f("work_locations_tenant_id_fkey")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("work_locations_pkey")),
    )
    op.create_index(
        op.f("work_locations_tenant_id_idx"), "work_locations", ["tenant_id"], unique=False
    )
    op.create_index(
        "work_locations_tenant_id_key",
        "work_locations",
        ["tenant_id"],
        unique=True,
        postgresql_where=sa.text("is_primary"),
    )
    op.create_foreign_key(
        op.f("employees_work_location_id_fkey"),
        "employees",
        "work_locations",
        ["work_location_id"],
        ["id"],
    )
    op.create_table(
        "calendar_settings",
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.Text(), server_default="", nullable=False),
        sa.Column("connected", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("team_calendar_id", sa.Text(), server_default="", nullable=False),
        sa.Column("calendar_name", sa.Text(), server_default="", nullable=False),
        sa.Column("scope", sa.Text(), server_default="company", nullable=False),
        sa.Column("division", sa.Text(), server_default="", nullable=False),
        sa.Column("delivery_mode", sa.Text(), server_default="shared_and_email", nullable=False),
        sa.Column("refresh_token", sa.Text(), nullable=True),
        sa.Column("access_token", sa.Text(), nullable=True),
        sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], name=op.f("calendar_settings_tenant_id_fkey")
        ),
        sa.PrimaryKeyConstraint("tenant_id", name=op.f("calendar_settings_pkey")),
    )
    op.create_table(
        "oauth_states",
        sa.Column("state", sa.Text(), nullable=False),
        sa.Column("employee_id", sa.Uuid(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["employee_id"], ["employees.id"], name=op.f("oauth_states_employee_id_fkey")
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], name=op.f("oauth_states_tenant_id_fkey")
        ),
        sa.PrimaryKeyConstraint("state", name=op.f("oauth_states_pkey")),
    )
    op.create_index(op.f("oauth_states_tenant_id_idx"), "oauth_states", ["tenant_id"], unique=False)


def downgrade() -> None:
    op.drop_table("oauth_states")
    op.drop_table("calendar_settings")
    op.drop_constraint(op.f("employees_work_location_id_fkey"), "employees", type_="foreignkey")
    op.drop_table("work_locations")
