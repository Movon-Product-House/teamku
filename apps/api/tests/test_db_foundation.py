"""U2: per-request transaction, background tasks, tenant isolation and CurrentUser on real PG."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated

import httpx
import pytest
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession, async_sessionmaker
from sqlalchemy.orm import Mapped, aliased, mapped_column

from movon_hr.core.auth import CurrentUser, require_role
from movon_hr.core.db import DB, Base
from movon_hr.core.identity import AuthSession, Employee, Tenant
from movon_hr.core.tenancy import TenantNotBoundError, TenantScoped

pytestmark = pytest.mark.anyio


class Widget(TenantScoped, Base):
    """Test-only tenant-scoped table, created inside each test's transaction."""

    __tablename__ = "test_widgets"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=func.uuidv7())
    name: Mapped[str]


@pytest.fixture(autouse=True)
async def widgets_table(conn: AsyncConnection) -> None:
    # `sessions` (conftest) joins this connection and is what get_db hands out here.
    await conn.run_sync(Widget.__table__.create)


def client(app: FastAPI) -> httpx.AsyncClient:
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    return httpx.AsyncClient(transport=transport, base_url="http://test")


async def make_tenant(db: AsyncSession, slug: str) -> uuid.UUID:
    tenant = Tenant(name=slug.upper(), slug=slug)
    db.add(tenant)
    await db.flush()
    return tenant.id


# --- get_db + BackgroundTasks ----------------------------------------------------


async def test_background_tasks_run_only_after_commit(sessions: async_sessionmaker) -> None:
    seen: list[tuple[str, int]] = []

    async def record(slug: str) -> None:
        # A fresh session only sees committed rows.
        async with sessions() as other:
            count = await other.scalar(
                select(func.count())
                .select_from(Tenant)
                .where(Tenant.slug == slug)
                .execution_options(cross_tenant=True)
            )
            seen.append((slug, count or 0))

    app = FastAPI()

    @app.post("/ok")
    async def ok(db: DB, tasks: BackgroundTasks) -> dict:
        db.add(Tenant(name="Ok", slug="ok"))
        tasks.add_task(record, "ok")
        return {}

    @app.post("/handler-fails")
    async def handler_fails(db: DB, tasks: BackgroundTasks) -> dict:
        db.add(Tenant(name="Bad", slug="bad"))
        tasks.add_task(record, "bad")
        raise HTTPException(400, "nope")

    @app.post("/crash")
    async def crash(db: DB, tasks: BackgroundTasks) -> dict:
        db.add(Tenant(name="Crash", slug="crash"))
        tasks.add_task(record, "crash")
        raise RuntimeError("boom")

    @app.post("/commit-fails")
    async def commit_fails(db: DB, tasks: BackgroundTasks) -> dict:
        db.add(Tenant(name="Dup", slug="ok"))  # violates the unique slug only at commit
        tasks.add_task(record, "dup")
        return {}

    async with client(app) as http:
        assert (await http.post("/ok")).status_code == 200
        assert seen == [("ok", 1)]
        assert (await http.post("/handler-fails")).status_code == 400
        assert (await http.post("/crash")).status_code == 500
        assert (await http.post("/commit-fails")).status_code == 500
    assert seen == [("ok", 1)]
    async with sessions() as db:
        slugs = (await db.scalars(select(Tenant.slug).execution_options(cross_tenant=True))).all()
    assert slugs == ["ok"]


# --- tenant isolation ------------------------------------------------------------


@pytest.fixture
async def two_tenants(sessions: async_sessionmaker) -> tuple[uuid.UUID, uuid.UUID]:
    async with sessions() as db:
        a, b = await make_tenant(db, "a"), await make_tenant(db, "b")
        for tenant_id, names in ((a, ["a1", "a2"]), (b, ["b1"])):
            db.info["tenant_id"] = tenant_id
            db.add_all(Widget(name=name) for name in names)
            await db.flush()
        await db.commit()
    return a, b


async def names(db: AsyncSession) -> list[str]:
    return sorted((await db.scalars(select(Widget.name))).all())


async def test_insert_fills_tenant_id(
    sessions: async_sessionmaker, two_tenants: tuple[uuid.UUID, uuid.UUID]
) -> None:
    a, b = two_tenants
    async with sessions() as db:
        rows = (
            await db.execute(
                select(Widget.name, Widget.tenant_id).execution_options(cross_tenant=True)
            )
        ).all()
    assert sorted(rows) == [("a1", a), ("a2", a), ("b1", b)]


async def test_insert_without_tenant_raises(sessions: async_sessionmaker) -> None:
    async with sessions() as db:
        db.add(Widget(name="orphan"))
        with pytest.raises(TenantNotBoundError):
            await db.flush()


async def test_select_is_scoped_to_bound_tenant(
    sessions: async_sessionmaker, two_tenants: tuple[uuid.UUID, uuid.UUID]
) -> None:
    a, b = two_tenants
    async with sessions() as db:
        db.info["tenant_id"] = a
        assert await names(db) == ["a1", "a2"]
        other = aliased(Widget)
        joined = await db.execute(
            select(Widget.name, other.name).join(other, other.id == Widget.id)
        )
        assert sorted(joined.all()) == [("a1", "a1"), ("a2", "a2")]
        b_widget = await db.scalar(
            select(Widget.id).where(Widget.name == "b1").execution_options(cross_tenant=True)
        )
        assert await db.get(Widget, b_widget) is None
        db.info["tenant_id"] = b
        assert await names(db) == ["b1"]


async def test_select_without_tenant_raises_unless_cross_tenant(
    sessions: async_sessionmaker, two_tenants: tuple[uuid.UUID, uuid.UUID]
) -> None:
    async with sessions() as db:
        with pytest.raises(TenantNotBoundError):
            await names(db)
        everything = await db.scalars(select(Widget.name).execution_options(cross_tenant=True))
        assert sorted(everything.all()) == ["a1", "a2", "b1"]


async def test_bulk_update_and_delete_are_scoped(
    sessions: async_sessionmaker, two_tenants: tuple[uuid.UUID, uuid.UUID]
) -> None:
    a, b = two_tenants
    async with sessions() as db:
        db.info["tenant_id"] = a
        result = await db.execute(update(Widget).values(name=Widget.name + "!"))
        assert result.rowcount == 2
        result = await db.execute(delete(Widget).where(Widget.name.in_(["a1!", "b1"])))
        assert result.rowcount == 1
        del db.info["tenant_id"]
        with pytest.raises(TenantNotBoundError):
            await db.execute(delete(Widget))
        db.info["tenant_id"] = b
        assert await names(db) == ["b1"]
        db.info["tenant_id"] = a
        assert await names(db) == ["a2!"]


async def test_unit_of_work_update_and_delete_stay_in_tenant(
    sessions: async_sessionmaker, two_tenants: tuple[uuid.UUID, uuid.UUID]
) -> None:
    a, b = two_tenants
    async with sessions() as db:
        db.info["tenant_id"] = a
        widgets = (await db.scalars(select(Widget).order_by(Widget.name))).all()
        widgets[0].name = "renamed"
        await db.delete(widgets[1])
        await db.commit()
    async with sessions() as db:
        db.info["tenant_id"] = a
        assert await names(db) == ["renamed"]
        db.info["tenant_id"] = b
        assert await names(db) == ["b1"]


# --- CurrentUser ---------------------------------------------------------------


@pytest.fixture
async def tokens(sessions: async_sessionmaker) -> dict[str, str]:
    now = datetime.now(UTC)
    async with sessions() as db:
        tenant_id = await make_tenant(db, "acme")
        db.info["tenant_id"] = tenant_id
        people = {
            role: Employee(name=role, email=f"{role}@acme.test", role=role, department="Ops")
            for role in ("hr_admin", "employee")
        }
        people["suspended"] = Employee(
            name="s", email="s@acme.test", role="employee", department="Ops", status="suspended"
        )
        db.add_all(people.values())
        await db.flush()
        db.add_all(
            AuthSession(
                token=f"t-{key}", employee_id=person.id, expires_at=now + timedelta(hours=1)
            )
            for key, person in people.items()
        )
        db.add(AuthSession(token="t-expired", employee_id=people["employee"].id, expires_at=now))
        await db.commit()
    return {key: f"t-{key}" for key in [*people, "expired"]}


def auth_app() -> FastAPI:
    app = FastAPI()

    @app.get("/me")
    async def me(user: CurrentUser, db: DB) -> dict:
        widgets = await db.scalars(select(Widget.name))  # tenant is bound: no raise
        return {"role": user.role, "tenant_bound": "tenant_id" in db.info, "w": widgets.all()}

    @app.get("/hr-only")
    async def hr_only(user: Annotated[Employee, Depends(require_role("hr_admin"))]) -> dict:
        return {"role": user.role}

    return app


async def test_current_user_from_header_or_cookie(
    sessions: async_sessionmaker, tokens: dict[str, str]
) -> None:
    async with client(auth_app()) as http:
        by_header = await http.get("/me", headers={"X-Demo-User": tokens["employee"]})
        assert by_header.json() == {"role": "employee", "tenant_bound": True, "w": []}
        http.cookies.set("teamku_session", tokens["hr_admin"])
        assert (await http.get("/me")).json()["role"] == "hr_admin"


async def test_current_user_rejects_bad_sessions(
    sessions: async_sessionmaker, tokens: dict[str, str]
) -> None:
    async with client(auth_app()) as http:
        for headers in ({}, {"X-Demo-User": "nope"}, {"X-Demo-User": tokens["suspended"]}):
            response = await http.get("/me", headers=headers)
            assert response.status_code == 401
            assert response.json() == {"detail": "Sesi tidak valid"}
        expired = await http.get("/me", headers={"X-Demo-User": tokens["expired"]})
        assert expired.status_code == 401
        assert expired.json() == {"detail": "Sesi telah berakhir. Silakan masuk kembali."}
    async with sessions() as db:
        found = await db.get(
            AuthSession, tokens["expired"], execution_options={"cross_tenant": True}
        )
        assert found is None


async def test_require_role(sessions: async_sessionmaker, tokens: dict[str, str]) -> None:
    async with client(auth_app()) as http:
        allowed = await http.get("/hr-only", headers={"X-Demo-User": tokens["hr_admin"]})
        assert allowed.json() == {"role": "hr_admin"}
        denied = await http.get("/hr-only", headers={"X-Demo-User": tokens["employee"]})
        assert denied.status_code == 403
        assert denied.json() == {"detail": "Anda tidak memiliki izin untuk aksi ini"}
