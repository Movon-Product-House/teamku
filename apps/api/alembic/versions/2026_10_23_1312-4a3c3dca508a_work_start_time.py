"""work_locations.work_start_time: late threshold from settings (#19)

Revision ID: 4a3c3dca508a
Revises: 4b81585c695d
Create Date: 2026-10-23 13:12:53.549825
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "4a3c3dca508a"
down_revision: str | Sequence[str] | None = "4b81585c695d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "work_locations",
        sa.Column("work_start_time", sa.Text(), server_default="09:00", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("work_locations", "work_start_time")
