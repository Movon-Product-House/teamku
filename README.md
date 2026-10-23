# Teamku

Teamku, powered by movon digital house, is a modular, API-first HRIS MVP for Indonesian teams. This repository contains independently deployable Next.js and FastAPI applications.

## Local start

Compose runs PostgreSQL 18. The old `postgres_data` volume holds PG16 data, so run `docker compose -f infra/compose/docker-compose.yml down -v` once before the first PG18 start.

**Full stack** (web, API, Postgres):

1. Copy `.env.example` to `.env`.
2. Run `docker compose -f infra/compose/docker-compose.yml up --build`. The API container migrates the database and seeds the demo company on first start.
3. Open `http://localhost:3000`; API documentation is at `http://localhost:8000/docs`.

**API with hot reload** (needs [uv](https://docs.astral.sh/uv/)):

```bash
docker compose -f infra/compose/docker-compose.yml up -d postgres
cd apps/api
uv sync
uv run alembic upgrade head && uv run python -m movon_hr.seed --if-empty && uv run uvicorn movon_hr.main:app --reload
```

The API defaults to `postgresql+psycopg://movon:movon@localhost:5432/movon`, which is the compose Postgres. Scheduled jobs do not run locally; run them by hand from `apps/api` when needed:

```bash
uv run python -m movon_hr.jobs attendance-alerts   # attendance alerts + expire missed reverify slots
uv run python -m movon_hr.jobs cleanup             # expired sessions, resets, login attempts, OAuth states
```

## Persistence

PostgreSQL 18 is the only store, for production, the demo, and the tests. Every request runs in one transaction, committed before the response is sent. Alembic owns the schema (`apps/api/alembic`); the API never creates tables on startup. The demo seed (`python -m movon_hr.seed --if-empty`) only runs when the database has no tenants, so data survives restarts. Compose keeps Postgres data in the `postgres_data` volume.

Demo credentials: `hr@movon.test` / `Demo123!`, `manager@movon.test` / `Demo123!`, and `employee@movon.test` / `Demo123!`. New companies can self-serve at `/signup`. Sessions are stored in an HttpOnly cookie (`teamku_session`); invite and password-reset emails go to the process log by default (`MOVON_MAIL_PROVIDER=console`). Set `MOVON_MAIL_PROVIDER=resend` with `MOVON_RESEND_API_KEY` and `MOVON_MAIL_FROM` to send them through Resend.

## Architecture and boundaries

The web app only renders UI and calls `/api/v1`; authorization, calculation, validation, audit events, and persistence belong to the Python API. The API is a modular monolith with one module per domain; see [docs/adr/0002-backend-api-architecture.md](docs/adr/0002-backend-api-architecture.md) and the module rules in [apps/api/AGENTS.md](apps/api/AGENTS.md).

Implemented demo features: authenticated role-aware dashboards; searchable employee directory with HR create/status actions; camera/location attendance with server-side Haversine validation, idempotency and agenda; leave request history, balance impact, cancellation and manager/HR decisions; in-app notifications; and a decimal-safe payroll calculation, finalization, locking and publishing flow.

Attendance is browser verification, not liveness or anti-spoofing. A selfie is captured from the live camera (never uploaded from a gallery), location accuracy is recorded, and out-of-range/low-confidence results are review signals.

## Quality commands

```bash
cd apps/api && scripts/check.sh   # ruff, pyrefly, import-linter, pytest (needs PostgreSQL, see apps/api/README.md)
cd apps/web && npm run check && npm run build
```

## Deployment

Repositori tetap monorepo; yang terpisah hanya target deploy-nya.

| Bagian | Target | Catatan |
|---|---|---|
| `apps/web` | Server Biznet (Dokploy) | `https://teamku.movoncreative.dev`, build dari `apps/web/Dockerfile` |
| `apps/api` | Server Biznet (Dokploy) | `https://api-teamku.movoncreative.dev` |

Project Vercel lama (`teamku-web`) di-pause dan build-nya dimatikan
(Ignored Build Step `exit 0`), jadi tidak ada deploy ganda. Untuk menyalakan
lagi: Resume project dan kembalikan Ignored Build Step ke Automatic.

`MOVON_APP_BASE_URL` di API harus `https://teamku.movoncreative.dev`, karena
tautan undangan dan reset password dibentuk dari nilai ini.

Browser hanya berbicara ke domain web. `apps/web/next.config.ts` mem-proxy
`/api/*` ke `${MOVON_API_ORIGIN}/api/v1/*`, sehingga cookie sesi tetap
first-party dan tidak ada CORS di jalur browser.

`MOVON_API_ORIGIN` dibutuhkan saat **build**, bukan runtime — Next membakukan
rewrite ke `routes-manifest.json`. Bila kosong, build tetap berhasil namun
mem-proxy ke `localhost`. `apps/web/scripts/require-api-origin.mjs` berjalan
sebagai `prebuild` dan menggagalkan build bila variabel kosong di Docker/CI.
Karena itu build harus lewat `npm run build`, bukan `next build`.

Semua state API (termasuk sesi, lockout login, dan state OAuth) ada di
PostgreSQL, jadi API tidak lagi terikat ke satu proses. Job terjadwal dan
operasional lainnya ada di [docs/runbook.md](docs/runbook.md).

Langkah deploy Dokploy, ID app, dan rollback ada di
[docs/plans/2026-10-22-001-deploy-web-to-dokploy-plan.md](docs/plans/2026-10-22-001-deploy-web-to-dokploy-plan.md).
Riwayat deploy Vercel sebelumnya:
[docs/plans/2026-09-12-001-migrate-web-to-vercel-plan.md](docs/plans/2026-09-12-001-migrate-web-to-vercel-plan.md).

## Operations

See [docs/architecture.md](docs/architecture.md), [docs/privacy-and-permissions.md](docs/privacy-and-permissions.md), and [docs/runbook.md](docs/runbook.md). In production configure PostgreSQL 18 with scheduled backups, HTTPS-only cookie settings, and the two scheduled jobs. The MVP intentionally leaves Indonesian tax/BPJS logic as transparent manual/configurable components rather than claiming compliance.
