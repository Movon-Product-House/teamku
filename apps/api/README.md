# Teamku API

FastAPI (full async) + SQLAlchemy 2 + psycopg 3 + PostgreSQL 18 + Alembic, dikelola dengan uv.
Keputusan arsitekturnya ada di [`docs/adr/0002-backend-api-architecture.md`](../../docs/adr/0002-backend-api-architecture.md); operasional prod di [`docs/runbook.md`](../../docs/runbook.md).

**Aturan kode** (batas modul, async, transaksi, tenancy, kontrak HTTP dan penamaan, tes, cara menambah modul) ada di [`AGENTS.md`](AGENTS.md), file yang juga dibaca agent AI (Claude Code memuatnya lewat `CLAUDE.md` saat bekerja di `apps/api`).

## Perintah

Semua dijalankan dari `apps/api`. Postgres lokal: `docker compose -f ../../infra/compose/docker-compose.yml up -d postgres`.

| Perintah | Fungsi |
|---|---|
| `uv sync` | Pasang dependency + paket `movon_hr` (editable) ke `.venv` |
| `uv run alembic upgrade head` | Migrasi DB di `MOVON_DATABASE_URL` (default `localhost:5432/movon`) |
| `uv run python -m movon_hr.seed --if-empty` | Seed perusahaan demo kalau DB belum punya tenant |
| `uv run uvicorn movon_hr.main:app --reload` | Dev server, docs di `http://localhost:8000/docs` |
| `uv run python -m movon_hr.jobs attendance-alerts` | Job alert presensi (di prod tiap 5 menit) |
| `uv run python -m movon_hr.jobs cleanup` | Job pembersihan harian |
| `uv run alembic revision --autogenerate -m "<domain>_<perubahan>"` | Revisi migrasi baru dari model |
| `uv run python -m movon_hr.openapi` | Tulis ulang `openapi.json` (kontrak sumber client web). Wajib setelah mengubah route atau schema; `tests/test_openapi.py` gagal kalau basi |
| `scripts/check.sh` | Gerbang yang sama dengan CI: ruff check, ruff format --check, pyrefly, lint-imports, pytest |

Jalankan `scripts/check.sh` sebelum push. Tes butuh database kosong terpisah: sekali saja jalankan `docker compose -f ../../infra/compose/docker-compose.yml exec postgres createdb -U movon movon_test`, atau arahkan `MOVON_TEST_DATABASE_URL` ke DB lain (default `postgresql+psycopg://movon:movon@localhost:5432/movon_test`; `tests/conftest.py` menjalankan `alembic upgrade head` ke sana sekali per sesi). CI (`.github/workflows/api.yml`) menjalankan `check.sh` ditambah `alembic upgrade head`, `alembic check`, dan cek satu head.

## Struktur

```
alembic/versions/       # Revisi berantai per domain. Satu-satunya pemilik skema
openapi.json            # Kontrak API (dump dari app.openapi()), sumber client web
src/movon_hr/
  main.py               # App, CORS, include_router setiap modul, health
  openapi.py            # Dump openapi.json (python -m movon_hr.openapi)
  seed.py               # Seed demo (python -m movon_hr.seed)
  jobs.py               # Job terjadwal (python -m movon_hr.jobs)
  core/                 # Generik, tanpa logika domain: settings, db, tenancy, identity
                        # (Tenant, Employee, AuthSession), auth, security, mailer, time, AI
  modules/<domain>/
    router.py           #   Route HTTP
    schemas.py          #   Pydantic in/out
    service.py          #   Aturan bisnis + query ORM
    models.py           #   Model SQLAlchemy (Mapped[]) + enum Literal
    rules.py, …         #   Logika murni tanpa I/O (opsional)
tests/                  # pytest di PostgreSQL sungguhan
```
