import re

import pytest
from sqlalchemy import CheckConstraint, text
from sqlalchemy.ext.asyncio import AsyncConnection

from movon_hr.core.db import Base

pytestmark = pytest.mark.anyio

QUOTED = re.compile(r"'([^']*)'")


async def test_migrated_checks_match_the_models(conn: AsyncConnection) -> None:
    # Autogenerate and `alembic check` ignore CHECK changes, so a new Literal value without
    # a hand-written revision would only surface as a failed insert in prod.
    models = {
        constraint.name: set(QUOTED.findall(str(constraint.sqltext)))
        for table in Base.metadata.tables.values()
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }
    rows = await conn.execute(
        text(
            "SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint"
            " WHERE contype = 'c' AND connamespace = 'public'::regnamespace"
        )
    )
    migrated = {name: set(QUOTED.findall(definition)) for name, definition in rows}
    assert migrated == models
