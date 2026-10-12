"""Tenant isolation for every ORM query.

The bound tenant lives in ``session.info["tenant_id"]``. ``TenantSession`` adds a
``tenant_id`` filter to every ORM SELECT/UPDATE/DELETE and fills ``tenant_id`` on
INSERT. It fails closed: without a bound tenant a query raises, unless it opts out
with ``execution_options(cross_tenant=True)`` (login, invite/reset tokens, sessions,
OAuth callback, jobs). Raw SQL (``text()``, ``Connection.execute``) is NOT filtered.
"""

from __future__ import annotations

import uuid
from contextvars import ContextVar

from sqlalchemy import ForeignKey, event
from sqlalchemy.orm import (
    Mapped,
    ORMExecuteState,
    Session,
    UOWTransaction,
    mapped_column,
    with_loader_criteria,
)


class TenantNotBoundError(RuntimeError):
    """An ORM statement touched tenant data without a bound tenant."""


class TenantScoped:
    """Mixin for tenant-owned tables: ``tenant_id uuid NOT NULL`` FK + index."""

    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), index=True)


class TenantSession(Session):
    """Sync session behind ``AsyncSession``; ORM events run here."""


@event.listens_for(TenantSession, "do_orm_execute")
def _filter_by_tenant(state: ORMExecuteState) -> None:
    if not (state.is_select or state.is_update or state.is_delete):
        return
    # Column/relationship loads inherit the criteria of the statement that loaded the parent.
    if state.is_column_load or state.is_relationship_load:
        return
    if state.execution_options.get("cross_tenant"):
        return
    tenant_id = state.session.info.get("tenant_id")
    if tenant_id is None:
        raise TenantNotBoundError("No tenant bound; use execution_options(cross_tenant=True)")
    # tenant_id must stay a plain closure variable: the lambda runs once per class and
    # closure values are tracked as bound parameters.
    state.statement = state.statement.options(
        with_loader_criteria(
            TenantScoped, lambda cls: cls.tenant_id == tenant_id, include_aliases=True
        )
    )


@event.listens_for(TenantSession, "before_flush")
def _fill_tenant_id(session: Session, _flush: UOWTransaction, _instances: object) -> None:
    for obj in session.new:
        if isinstance(obj, TenantScoped) and obj.tenant_id is None:
            tenant_id = session.info.get("tenant_id")
            if tenant_id is None:
                raise TenantNotBoundError(f"No tenant bound for new {type(obj).__name__}")
            obj.tenant_id = tenant_id


# --- Legacy in-memory tenant registry, used by modules/api.py; deleted in U12. ---

DEMO_TENANT_ID = "pt-movon-solusi-kreatif"
DEMO_TENANT_NAME = "PT Movon Solusi Kreatif"
DEMO_TENANT_SLUG = "pt-movon-solusi-kreatif"

_active_tenant_id: ContextVar[str] = ContextVar("active_tenant_id", default=DEMO_TENANT_ID)
_stores: dict = {}


def bind_tenant(tenant_id: str) -> None:
    _active_tenant_id.set(tenant_id)


def current_tenant_id() -> str:
    return _active_tenant_id.get()


def get_store(tenant_id: str | None = None):
    from movon_hr.modules.api import DemoStore

    tid = tenant_id or current_tenant_id()
    store = _stores.get(tid)
    if store is None:
        store = DemoStore(tenant_id=tid)
        _stores[tid] = store
    return store


def put_store(store) -> None:
    _stores[store.tenant_id] = store


def iter_stores():
    return list(_stores.values())


def clear_registry() -> None:
    _stores.clear()
    bind_tenant(DEMO_TENANT_ID)


class StoreFacade:
    """Attribute proxy so existing ``store.employees`` code stays tenant-scoped."""

    def _raw(self):
        return get_store()

    def __getattr__(self, name):
        return getattr(self._raw(), name)

    def __setattr__(self, name, value):
        setattr(self._raw(), name, value)


store = StoreFacade()
