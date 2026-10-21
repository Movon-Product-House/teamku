"""Test harness: real PostgreSQL, one rolled-back transaction per test (plan U4).

Every session the code under test opens (``get_db``, jobs, seed) joins the test's
connection through a SAVEPOINT, so its commits never reach the database.
"""

import os
import secrets
from collections.abc import AsyncIterator, Awaitable, Callable, Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest
import time_machine
from alembic import command
from alembic.config import Config
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from movon_hr.core import db as core_db
from movon_hr.core.identity import AuthSession, Employee
from movon_hr.core.mailer import reset_outbox
from movon_hr.core.settings import settings
from movon_hr.core.tenancy import TenantSession
from movon_hr.main import app
from movon_hr.seed import seed_demo

# Every test starts at this moment: Wednesday 10:00 WIB, after the seed's 08:50-09:14
# check-ins and far from midnight, so UTC and Jakarta agree on "today".
# Always pass UTC to the clock: time-machine also sets the process time zone from the
# destination's tzinfo, and prod/CI run in UTC (a Jakarta TZ would hide local-time bugs).
# Postgres now() (server defaults) still reads the real clock, so keep this in the past.
TEST_NOW = datetime(2026, 10, 21, 3, 0, tzinfo=UTC)

TEST_DATABASE_URL = os.environ.get(
    "MOVON_TEST_DATABASE_URL", "postgresql+psycopg://movon:movon@localhost:5432/movon_test"
)
# NullPool: each test runs on its own event loop, pooled connections must not outlive it.
engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
def clock(time_machine: time_machine.TimeMachineFixture) -> time_machine.TimeMachineFixture:
    """Simulated clock; a test that needs another moment calls ``clock.move_to(...)``."""
    time_machine.move_to(TEST_NOW, tick=True)
    return time_machine


@pytest.fixture(autouse=True)
def console_mail(monkeypatch: pytest.MonkeyPatch) -> None:
    # A developer .env with MOVON_MAIL_PROVIDER=resend must never make tests send real email.
    monkeypatch.setattr(settings, "mail_provider", "console")
    reset_outbox()


@pytest.fixture(scope="session")
def migrated() -> Iterator[None]:
    """``alembic upgrade head`` once per run."""
    config = Config()  # no ini file: env.py then skips fileConfig, which would mute loggers
    config.set_main_option("script_location", str(Path(__file__).parents[1] / "alembic"))
    saved = settings.database_url
    settings.database_url = TEST_DATABASE_URL  # env.py reads it
    try:
        command.upgrade(config, "head")
    finally:
        settings.database_url = saved
    yield


@pytest.fixture
async def conn(migrated: None) -> AsyncIterator[AsyncConnection]:
    async with engine.connect() as connection:
        transaction = await connection.begin()
        try:
            yield connection
        finally:
            await transaction.rollback()


@pytest.fixture
def sessions(
    conn: AsyncConnection, monkeypatch: pytest.MonkeyPatch
) -> async_sessionmaker[AsyncSession]:
    """Session factory on the test connection; also replaces the app's ``SessionLocal``."""
    factory = async_sessionmaker(
        bind=conn,
        join_transaction_mode="create_savepoint",
        sync_session_class=TenantSession,
        expire_on_commit=False,
    )
    monkeypatch.setattr(core_db, "SessionLocal", factory)
    return factory


@pytest.fixture
async def db(sessions: async_sessionmaker[AsyncSession]) -> AsyncIterator[AsyncSession]:
    """A session with the demo company seeded and its tenant bound."""
    async with sessions() as session:
        await seed_demo(session)
        await session.commit()
        yield session


@pytest.fixture
async def client(db: AsyncSession) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as http:
        yield http


@pytest.fixture
def employee_id(db: AsyncSession) -> Callable[[str], Awaitable[str]]:
    """``await employee_id(email)`` -> the demo employee's id as the API returns it."""

    async def lookup(email: str) -> str:
        found = await db.execute(select(Employee.id).where(Employee.email == email))
        return str(found.scalar_one())

    return lookup


@pytest.fixture
def login_headers(db: AsyncSession) -> Callable[[str], Awaitable[dict[str, str]]]:
    """``await login_headers(email)`` -> auth headers for a fresh session (no password check)."""

    async def login(email: str) -> dict[str, str]:
        found = await db.execute(select(Employee.id).where(Employee.email == email))
        token = secrets.token_urlsafe(32)
        db.add(
            AuthSession(
                token=token,
                employee_id=found.scalar_one(),
                expires_at=datetime.now(UTC) + timedelta(hours=12),
            )
        )
        await db.commit()
        return {"X-Demo-User": token}

    return login
