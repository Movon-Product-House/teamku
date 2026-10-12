from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

# Import every model module so Base.metadata holds all tables.
import movon_hr.core.identity
import movon_hr.modules.attendance.models
import movon_hr.modules.audit.models
import movon_hr.modules.auth.models
import movon_hr.modules.leave.models
import movon_hr.modules.notifications.models
import movon_hr.modules.payroll.models
import movon_hr.modules.policies.models
import movon_hr.modules.settings.models  # noqa: F401
from movon_hr.core.db import Base
from movon_hr.core.settings import settings

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata
COMPARE = {"compare_type": True, "compare_server_default": True}


def run_migrations_offline() -> None:
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        **COMPARE,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    # The psycopg (v3) URL works for a sync engine too.
    connectable = create_engine(settings.database_url, poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, **COMPARE)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
