"""Async engine, session factory, declarative ``Base`` and the per-request session."""

from collections.abc import AsyncIterator
from datetime import datetime
from typing import Annotated, ClassVar

from fastapi import Depends
from sqlalchemy import DateTime, MetaData, Text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from movon_hr.core.settings import settings
from movon_hr.core.tenancy import TenantSession

NAMING_CONVENTION = {
    "pk": "%(table_name)s_pkey",
    "uq": "%(table_name)s_%(column_0_N_name)s_key",
    "fk": "%(table_name)s_%(column_0_N_name)s_fkey",
    "ck": "%(table_name)s_%(constraint_name)s_check",
    "ix": "%(table_name)s_%(column_0_N_name)s_idx",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)
    # Text without length, every timestamp is timestamptz.
    type_annotation_map: ClassVar = {str: Text, datetime: DateTime(timezone=True)}


engine = create_async_engine(
    settings.database_url, pool_size=10, max_overflow=10, pool_pre_ping=True
)
# expire_on_commit=False: expired attributes cannot be lazily refreshed under asyncio.
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, sync_session_class=TenantSession)


async def get_db() -> AsyncIterator[AsyncSession]:
    """One transaction per request: commit after the handler, rollback on any error.

    Use through ``DB`` (``scope="function"``) so the commit happens before the
    response is sent; background tasks then only see committed data.
    """
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except BaseException:
            await session.rollback()
            raise


DB = Annotated[AsyncSession, Depends(get_db, scope="function")]
