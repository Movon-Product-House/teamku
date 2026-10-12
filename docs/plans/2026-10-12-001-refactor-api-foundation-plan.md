---
title: "refactor: Rebuild the API on a modular, Postgres-backed foundation"
type: plan
date: 2026-10-12
status: ready
origin:
  - docs/research/2026-10-12-001-fastapi-alembic-postgres-best-practices.md
  - docs/research/2026-10-12-002-api-architecture-options.md
  - docs/research/2026-10-12-003-api-dev-tooling.md
---

# refactor: Rebuild the API on a modular, Postgres-backed foundation

## Summary

Revamp arsitektur `apps/api` tanpa mengubah fitur, sejalan dengan revamp web (ADR 0001, PR #6). File `modules/api.py` yang berisi 2433 baris dipecah menjadi modul per domain. Persistence snapshot in-memory diganti dengan query langsung ke PostgreSQL 18 per request. Primary key menjadi UUIDv7 native, dan Alembic menjadi satu-satunya pemilik skema. Tooling (ruff, pyrefly, CI, satu perintah cek) dipasang sekaligus.

PR API ini `Closes #5`, karena semua endpoint mendapat skema respons di OpenAPI. Poin "auth cookie di semua endpoint" dan "lockout persisten" di #10 juga ikut terselesaikan.

Pekerjaan ini dikirim dalam **satu PR API** di branch `refactor/api-foundation`, ditambah **satu PR web pasangan** untuk ID yang di-hardcode. Data prod hanya berisi data demo, jadi DB baru di-seed ulang tanpa migrasi data.

## Problem Frame

Hasil audit 2026-10-12 (lihat origin):

- `modules/api.py` berisi semua domain, yaitu model, schema, aturan bisnis, dan ±60 route, dalam satu file. Klaim "modular monolith", Celery, Redis, dan S3 di `docs/architecture.md` tidak sesuai dengan kode.
- Persistence menyimpan `DemoStore` in-memory sebagai snapshot. Setiap request yang mengubah data menghapus lalu meng-insert ulang data **semua** tenant (`main.py:77-100`), dan kegagalannya hanya di-log.
- Primary key bentrok antar tenant (`office-default`, `section-n`) sehingga data tenant diam-diam tidak tersimpan (002 §0).
- Alert yang dibuat saat GET tidak pernah disimpan.
- `urlopen` yang blocking dipanggil di dalam handler `async def` (`api.py:1871,2307`).
- Rantai Alembic putus (`KeyError '0003_policy_assistant'`), skema menyimpang (`calendar_settings` dan kolom kalender tidak punya migrasi), dan Dockerfile tidak memasang Alembic. Artinya migrasi tidak pernah jalan di prod (001 §1, 003 §5).
- Tidak ada type checker, tidak ada CI untuk API, dan ruff hanya memakai rule default.

## Requirements

- R1. **Kontrak HTTP tetap.** Path `/api/v1`, method, status code, nama field, dan bentuk JSON setiap endpoint tidak berubah. Pengecualiannya:
  - nilai ID menjadi UUID;
  - field baru yang bersifat aditif (`is_primary` pada lokasi);
  - perilaku yang memang bug, seperti data hilang dan alert yang tidak tersimpan;
  - autentikasi menerima cookie `teamku_session` **atau** header `X-Demo-User` di **semua** endpoint. Sekarang sebagian besar endpoint hanya membaca header (#10);
  - alert presensi dan expire slot reverify dibuat oleh job terjadwal (tiap 5 menit), bukan lagi saat `GET /notifications` atau `GET /attendance/today`. Alert jadi tepat waktu meski tidak ada yang membuka aplikasi. Endpoint GET menjadi murni membaca.
- R2. Fitur demo tetap ada: akun demo, kata sandi `Demo123!`, data seed, header `X-Demo-User`, dan cookie `teamku_session`.
- R3. PostgreSQL 18 menjadi satu-satunya penyimpanan untuk prod, demo, dan tes. Mode tanpa DB dihapus.
- R4. Setiap request memakai satu transaksi. Commit terjadi sebelum response dikirim. Kalau ada error, semua perubahan di-rollback dan tidak ada data setengah tersimpan. Satu pengecualian: `POST /invites` memanggil `await db.commit()` sendiri di handler, lalu mengirim email, karena response membutuhkan `email_status`. Kalau email gagal, undangan tetap tersimpan dan statusnya dilaporkan di response, sama seperti sekarang.
- R5. Isolasi tenant ditegakkan otomatis untuk setiap query ORM. Jalur lintas tenant (login, token undangan, token reset, sesi, OAuth callback) harus eksplisit dan dites.
- R6. Primary key menggunakan `uuid` dengan default `uuidv7()`. Keunikan bisnis selalu menyertakan `tenant_id`.
- R7. Skema hanya dikelola Alembic. Tidak ada `create_all` atau `_add_missing_columns` saat runtime. CI membuktikan `upgrade head`, `alembic check`, dan bahwa hanya ada satu head.
- R8. **Full async.** Semua handler dan dependency ditulis `async def`, memakai `AsyncSession` (SQLAlchemy 2 + psycopg 3 async), `httpx.AsyncClient`, dan `resend.Emails.send_async`. Tidak boleh ada I/O blocking di dalam `async def`. Kerja CPU (argon2) dijalankan lewat `anyio.to_thread.run_sync`.
- R9. Struktur modul per domain dengan batas yang ditegakkan import-linter, dan setiap file maksimal 600 baris.
- R10. `scripts/check.sh` (ruff check, ruff format --check, pyrefly, lint-imports, pytest) hijau secara lokal dan di CI.
- R11. Seluruh perilaku yang sekarang dicakup tes tetap lolos. Kode setup tes boleh ditulis ulang, tapi assertion HTTP tidak boleh dilemahkan.

## Key Technical Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Gaya arsitektur | Modular monolith per domain dengan layer tipis di dalam setiap modul (router → service → `Session`). Adapter hanya untuk integrasi eksternal. | Fowler ("domain oriented modules which are internally layered"), Simon Brown (package by component), dan ADR 0001 di web. Hexagonal penuh atau gaya cosmicpython terlalu berat untuk 2 engineer (002 §1). |
| Repository/UoW | Tidak ada. `Session` SQLAlchemy sudah merupakan unit of work. | Dokumentasi SQLAlchemy, dan cosmicpython sendiri mengakuinya (002 §2). |
| Sync vs async | **Full async**, diputuskan user 2026-10-12. `async def` di semua handler dan dependency, `create_async_engine` dengan driver `postgresql+psycopg` (psycopg 3 async), `async_sessionmaker`, dan `httpx.AsyncClient` untuk HTTP keluar. `asyncpg` dihapus. | Referensi tim `Kludex/fastapi-tips` #2 ("always prefer to use async functions") dan `zhanymkanov/fastapi-best-practices` ("async-first", "Prefer `async` dependencies") sama-sama async-first. Semua handler sekarang memang sudah `async def`. Beban kerja kita I/O-bound (DB, Google, Resend, dan nanti streaming AI). Skill resmi FastAPI membolehkan async kalau semua yang dipanggil di dalamnya async-compatible (`SKILL.md` "Async vs Sync"). Driver psycopg 3 dipilih karena satu URL bisa dipakai async (app) maupun sync (Alembic). |
| Panggilan sync yang tersisa | **Resend:** pakai API async native, `resend[async]` dengan `resend.Emails.send_async`, dan atur `resend.default_async_http_client = HTTPXClient(timeout=10)`. **argon2** (`hash_password`/`verify_password`) dipanggil lewat `anyio.to_thread.run_sync`. Tiga `urlopen` (token Google, Calendar API, short link Maps) diganti `httpx.AsyncClient`. | Resend 2.47 menyediakan `send_async` (`resend/emails/_emails.py:644`) dan auto-detect httpx (`resend/__init__.py:233-238`). argon2-cffi tidak punya API async (dicek sampai CHANGELOG 25.1.0), karena hashing adalah kerja CPU, jadi di-offload ke thread. Rule ruff `ASYNC` (bagian dari default ruff sejak 0.16) mendeteksi panggilan blocking di dalam `async def`. |
| Relasi ORM | `lazy="raise"` di semua `relationship()`. Data relasi dimuat eksplisit dengan `selectinload`/`joinedload`. | Lazy load implisit tidak didukung di `AsyncSession` (berujung `MissingGreenlet`). Dengan `lazy="raise"`, kesalahan langsung muncul saat tes, bukan diam-diam di prod. |
| Pool | `pool_size=10, max_overflow=10, pool_pre_ping=True` | Default SQLAlchemy 5+10 terlalu sempit untuk request bersamaan yang masing-masing memegang session. Angka ini titik awal dan perlu diukur. |
| Session per request | Dependency `async` dengan `yield` dan `Depends(scope="function")` yang commit setelah handler selesai, rollback kalau ada exception, lalu close. `expire_on_commit=False`, yang wajib untuk async karena atribut yang expired tidak bisa di-refresh secara implisit. | Commit terjadi sebelum response dikirim (FastAPI ≥0.121, repo memakai 0.141.1) (002 §2). |
| Isolasi tenant | `tenant_id` disimpan di `session.info`. Listener `do_orm_execute` dipasang di kelas `Session` sync yang dibungkus `AsyncSession` (`sync_session_class`) dan menambahkan `with_loader_criteria(TenantScoped, …, include_aliases=True)` untuk SELECT, UPDATE, dan DELETE. `before_flush` mengisi `tenant_id` saat INSERT. **Fail closed**: kalau tenant belum di-bind, query raise, kecuali query diberi `execution_options(cross_tenant=True)`. | Event ORM berjalan di `Session` sync di balik `AsyncSession`. Tenant disimpan secara eksplisit per session, bukan lewat state global atau ContextVar. Celah INSERT, bulk update, dan raw SQL ditutup secara eksplisit (001 Rek. 4, 002 §3). |
| Raw SQL | Dilarang di modul domain. `text()` dan `Connection.execute` hanya boleh di `core/`. | Filter tenant hanya berlaku untuk ORM (002, belum terverifikasi). |
| RLS | Ditunda ke tiket terpisah. | Defense-in-depth. Desain session sudah menyisakan tempat untuk `set_config` di `after_begin` (002 §3). |
| ID | `uuid` PK dengan `server_default=text("uuidv7()")`. ID tetap dibuat oleh server, bukan oleh Python. | Native di PG18 (dokumentasi PG 18 §9.14) dan berurutan berdasarkan waktu sehingga ramah index. Menyelesaikan bentrok `office-default` dan `section-n`. |
| Versi Postgres | **PostgreSQL 18** (18.6 stabil) di compose, CI, dan prod. | Keputusan user 2026-10-12. PG19 masih beta. |
| Data prod | DB PG18 baru di-seed ulang. Tidak ada `stamp` dan tidak ada migrasi data. | Prod hanya berisi data demo (keputusan user). Prosedur baseline+stamp di riset 001 §3.6 jadi tidak diperlukan. |
| Migrasi | Hapus `0001`–`0004`. Buat satu baseline hasil `alembic revision --autogenerate` dari model baru, lalu di-review. `file_template` diberi prefix tanggal dengan revision ID acak bawaan. | Chain lama rusak dan tidak pernah jalan. DB baru bisa dimulai dari nol (001 §3.6). |
| `naming_convention` | Suffix gaya Postgres: `pk: %(table_name)s_pkey`, `uq: %(table_name)s_%(column_0_N_name)s_key`, `fk: %(table_name)s_%(column_0_N_name)s_fkey`, `ck: %(table_name)s_%(constraint_name)s_check`, `ix: %(table_name)s_%(column_0_N_name)s_idx` | DB baru, jadi tidak perlu meniru nama lama. Pola ini sama dengan default Postgres dan contoh di skill Supabase (001 §3.4, §4). |
| Penamaan tabel | Tabel plural snake_case, PK `id`, FK `<entity>_id`, waktu `<verb>_at` bertipe `timestamptz`, tanggal `_date`, teks tanpa panjang. Nama tabel lama dipertahankan, kecuali yang disebut di Schema Changes. | Sesuai konsensus PG wiki, Supabase, dan sqlstyle (001 §4). |
| Response schema | **Semua endpoint JSON** punya skema respons. Defaultnya return type annotation (`-> EmployeeOut`), dan `response_model=` hanya dipakai kalau handler me-return objek yang berbeda. Schema keluaran memakai `from_attributes=True`. Endpoint yang men-set cookie (`signup`, `login`, `accept-invite`, `reset-password`) tidak lagi me-return `JSONResponse`, tapi menerima parameter `response: Response`, men-set cookie di sana, lalu me-return model biasa, supaya skemanya ikut muncul di OpenAPI. Satu-satunya pengecualian adalah `GET /settings/calendar/google/callback`, yang memang mengembalikan redirect 302. | Mengikuti skill resmi FastAPI. Efeknya sama dengan `response_model`: field sensitif tersaring secara deklaratif dan OpenAPI terisi (001 Rek. 5). |
| ORM vs SQLModel | SQLAlchemy 2 (`Mapped[]`) dengan Pydantic terpisah, didokumentasikan di `AGENTS.md`. | Skill FastAPI menyarankan SQLModel, tapi kita tetap di SQLAlchemy 2 supaya agent tidak "membetulkannya" (001 Rek. 11). |
| Dependency cooldown | `[tool.uv] exclude-newer = "7 days"` di `apps/api/pyproject.toml`. Setiap `uv lock` hanya memilih file yang sudah diupload ke PyPI minimal 7 hari, **termasuk dependency transitive**. Pengecualian darurat, misalnya untuk security fix, memakai `exclude-newer-package = { <paket> = false }` sementara dan dicatat di PR. | Mitigasi serangan supply chain: versi berbahaya biasanya ketahuan dan ditarik dalam hitungan jam sampai hari. Angka 7 hari adalah penilaian tim, bukan angka resmi. Didukung native oleh uv (docs settings `exclude-newer`: durasi relatif `"7 days"`/`"P7D"`, dibandingkan dengan upload time per artefak). uv lokal versi 0.12.23. Apakah `uv.lock` merekam durasi relatif atau tanggal absolut diverifikasi di U1. |
| Versi target | Dicek dari PyPI 2026-10-12, versi terbaru yang berumur ≥7 hari:<br>**Runtime:** fastapi 0.142.2, uvicorn 0.54.0, pydantic 2.13.5, pydantic-settings 2.15.0, argon2-cffi 25.1.0, sqlalchemy 2.0.54, psycopg 3.3.6, alembic 1.20.0, resend 2.49.1, httpx 0.28.1. Transitive: starlette 1.7.0, anyio 4.15.1.<br>**Dev:** pytest 9.1.1, ruff 0.16.10, pyrefly 1.3.2, import-linter 2.15.<br>**Pin:** batas bawah = versi target. Batas atas mengikuti aturan versi dari maintainer masing-masing paket:
- versi 0.x, yang minor-nya boleh breaking, dibatasi di level minor: `fastapi<0.143`, `uvicorn<0.55`, `httpx<0.29`, `ruff<0.17`;
- pyrefly dibatasi minor (`<1.4`), karena minor bisa mengubah hasil pengecekan;
- `sqlalchemy[asyncio]<2.1`, karena 2.1 baru dan belum diriset;
- paket semver ≥1.0 dibatasi major: `pydantic<3`, `pydantic-settings<3`, `psycopg<4`, `alembic<2`, `resend<3`, `pytest<10`, `import-linter<3`;
- argon2-cffi (CalVer) dan starlette (mengikuti FastAPI) tidak diberi batas atas.

Versi persisnya dikunci `uv.lock`, dan kesegarannya dijaga cooldown. Batas atas hanya mencegah `uv lock --upgrade` diam-diam naik ke versi yang menurut maintainer-nya boleh breaking. `asyncpg` dihapus. | **Batas atas:** halaman resmi FastAPI "About FastAPI versions" menulis "any version below `1.0.0` could potentially add breaking changes… Breaking changes and new features are added in 'MINOR' versions", dengan contoh `fastapi>=0.112.0,<0.113.0`. Halaman yang sama menyebut Starlette tidak perlu di-pin dan Pydantic cukup `<3.0.0`. **SQLAlchemy tetap 2.0.x:** 2.1.0 rilis 2026-09-24 dan langsung diikuti empat patch dalam dua minggu (2.1.1–2.1.4), tanda masih stabilisasi. Perubahan 2.0→2.1 juga belum diriset, jadi upgrade ke 2.1 di PR terpisah. **Ruff 0.16.10, bukan 0.17:** 0.17.0 baru berumur 2 hari. Satu-satunya beda rule default adalah 7 rule DTZ yang dikeluarkan di 0.17, dan kita menambahkan DTZ lewat `extend-select`, jadi rule yang aktif sama. Versi minor ruff mengubah default, makanya di-pin `<0.17`. **pydantic 2.13.5:** 2.14.1 baru rilis kemarin. **pytest 9:** 8.x punya CVE (003 §8). |
| Efek samping | **Email** memakai `BackgroundTasks` bawaan FastAPI: `background_tasks.add_task(send_email, …)`. Task berjalan setelah response dikirim, sedangkan `get_db` dengan `scope="function"` sudah commit **sebelum** response, jadi email hanya terkirim untuk data yang sudah ter-commit. Kalau handler atau commit gagal, response error menggantikan response asli dan task-nya tidak ikut berjalan. Ini **diverifikasi dengan satu tes di U2**. Tidak ada antrean buatan sendiri. Job CLI mengirim email langsung (`await`) setelah commit. **Email undangan** dikirim setelah commit eksplisit di handler (`await db.commit()`) dan ditunggu, karena response membutuhkan `email_status` (pengecualian R4). **Google Calendar** tetap inline (`await` httpx) di request approve, karena web membaca `calendar_sync_status === "failed"` dari response (`decision-dialog.tsx:46`). | Tidak ada email yang terkirim untuk data yang di-rollback. Kontrak response tetap. httpx async tidak memblokir event loop. |
| Job terjadwal | Satu entrypoint CLI `python -m movon_hr.jobs <name>` di image yang sama, dijadwalkan lewat **Dokploy Schedule** (`scheduleType: application`, dijalankan dengan `docker exec` di container API). Ada dua job: **`attendance-alerts`** (`*/5 * * * *`), yang mengevaluasi alert dan meng-expire slot reverify untuk semua tenant, dan **`cleanup`** (`0 3 * * *` WIB), yang menghapus sesi kedaluwarsa, `password_resets` yang kedaluwarsa atau sudah dipakai, `login_attempts` di luar jendela lockout, serta `oauth_states` yang kedaluwarsa. Keduanya idempoten (`INSERT … ON CONFLICT DO NOTHING` pada `alert_receipts (tenant_id, employee_id, kind, local_date)`). GET murni membaca. | Pola standar: 12-Factor XII "Admin processes" (kode admin di codebase dan env yang sama), Django `clearsessions` "as a daily cron job", dan Kubernetes CronJob ("the Jobs that you define should be *idempotent*"). Dokploy mencatat log per run (docs "Schedule Jobs"). Ditolak: loop di lifespan, karena ikut terduplikasi per worker/replika, mati saat deploy, dan gagal diam-diam. Ditolak juga Celery/Redis dan task queue lain, karena hanya ada dua job periodik berfrekuensi rendah tanpa kebutuhan retry atau antrean. Inventaris kebutuhan waktu: alert dan reverify (5 menit) serta cleanup (harian). Undangan kedaluwarsa, token Google, payroll, dan masa berlaku kebijakan cukup dihitung saat dibaca. |
| State proses | `_login_attempts` dan `_google_oauth_states` dipindah ke tabel DB. | Supaya aman untuk lebih dari satu worker/instance. Juga menyelesaikan lockout in-memory dari gap analysis. |
| Tes | PostgreSQL 18 sungguhan. Skema dibuat dengan `alembic upgrade head` sekali per sesi tes. Setiap tes berjalan di dalam transaksi yang di-rollback (`join_transaction_mode="create_savepoint"`), dan seed demo dijalankan di dalam transaksi tersebut. | SQLite berbeda dalam perilaku JSONB, timezone, dan constraint (002 §5). Rollback per tes membuat tes tetap cepat dan terisolasi. |
| Jaring pengaman kontrak | **Characterization test**: bentuk response (key dan tipe) setiap endpoint direkam dari kode lama, lalu dibandingkan dengan kode baru. | Ini bukti mekanis untuk R1. Tes yang ada sekarang hanya memeriksa sebagian field. |
| Type checker | pyrefly (stabil 1.x, preset `default`) dan jadi gerbang CI. | 003 §3. ty masih beta. |
| Batas modul | import-linter (2.15, `seddonym/import-linter`) dipakai **sekarang**, dengan **dua kontrak minimal**: `forbidden` (`movon_hr.core` tidak boleh mengimpor `movon_hr.modules`) dan `acyclic_siblings` (tidak ada siklus antar modul di `movon_hr.modules`). Kontrak `layers` dengan urutan domain **ditunda** sampai struktur domain stabil setelah fitur revamp masuk. | Banyak kode ditulis agent, yang cenderung mengimpor apa saja. Dua kontrak ini menjaga hal yang fatal (siklus import dan `core` tercemar logika domain) tanpa mengunci urutan domain yang masih mungkin berubah. Ruff `I`/`TID` tidak bisa melakukan ini karena mengecek per file, tanpa graph dan tanpa import tidak langsung. |
| Git hooks | **Ditunda** (keputusan user 2026-10-12). `scripts/check.sh` sebelum push dan CI sudah menjaga ruff, pyrefly, import-linter, dan pytest. | Isi hook hanya ruff check dan format, yang sudah tertangkap oleh `check.sh` dan CI. Kalau nanti ditambahkan, konfigurasinya sudah siap di riset 003 §4 dan §9: root `prek.toml` + `apps/api/prek.toml` dengan `uv run ruff`. |
| Image | Dockerfile single-stage: `uv sync --locked --no-dev` dari `uv.lock`, lalu menyalin `alembic/` dan `alembic.ini`. Command-nya prestart (`alembic upgrade head` lalu seed kalau DB kosong) sebelum `uvicorn`. | Dependency tidak lagi didaftar di dua tempat. Pola prestart mengikuti template resmi (001 Rek. 8–9). |

## Target Structure

```
apps/api/
  alembic/                      # env.py membaca Base.metadata; versions/ = 1 baseline
  scripts/check.sh
  src/movon_hr/
    main.py                     # app, CORS, include_router per modul, health
    seed.py                     # demo seed; `python -m movon_hr.seed --if-empty`
    jobs.py                     # `python -m movon_hr.jobs attendance-alerts|cleanup`
    core/
      settings.py
      db.py                     # async engine, async_sessionmaker, Base + naming_convention,
                                # get_db (async yield, scope=function)
      tenancy.py                # Tenant model, TenantScoped mixin, listener filter + before_flush
      auth.py                   # CurrentUser dependency (cookie | X-Demo-User), require_role()
      security.py  mailer.py  ai_provider.py  policy_assistant.py  policy_retrieval.py
      time.py                   # JAKARTA, jakarta_date, working_days (logika murni)
    modules/
      audit/          models  schemas  service  router      # audit(), GET /audit-logs
      notifications/  models  schemas  service  router      # notify(), list, read-all
      settings/       models  schemas  service  router      # work locations + office policy,
                      maps.py  google_calendar.py           # calendar settings + Google OAuth
      employees/      models  schemas  service  router      # visible_employees, CRUD
      auth/           models  schemas  service  router      # sessions, invites, resets, login lockout
      leave/          models  schemas  service  router      # leave-requests, approvals, calendar sync
      attendance/     models  schemas  service  router      # today, check-in/out, reverify,
                      rules.py  alerts.py                   # geofence (murni), alert evaluation
      payroll/        models  schemas  service  router  rules.py
      policies/       models  schemas  service  router      # policies + policy assistant
      dashboard/      schemas  service  router              # read-only aggregation
```

**Arah dependency yang diharapkan** (panduan saat menulis kode, **tidak** ditegakkan sebagai kontrak `layers`, lihat Key Technical Decisions):

```
dashboard
attendance | payroll | policies | auth
leave
employees
settings
audit | notifications
core
```

Antar modul hanya boleh mengimpor `modules.<x>.service`, `.schemas`, atau `.models`, dan tidak boleh mengimpor `router`. Aturan ini ditegakkan lewat review, dan bisa dinaikkan jadi kontrak `protected` kalau sering dilanggar. Yang ditegakkan import-linter hanya dua hal: `core` tidak boleh mengimpor `modules`, dan tidak boleh ada siklus antar modul.

`GET /employees/{id}/location-history` didaftarkan oleh router `attendance` karena datanya milik attendance, meskipun path-nya di bawah `/employees`.

## Schema Changes

Semua tabel tenant memakai `TenantScoped`, yaitu `tenant_id uuid NOT NULL` dengan FK ke `tenants.id`, ditambah index. Semua PK bertipe `uuid DEFAULT uuidv7()`, kecuali yang disebut lain di bawah. Semua waktu bertipe `timestamptz`.

| Tabel | Perubahan dari skema sekarang |
|---|---|
| `tenants` | `id uuid`. `slug` unik global (tetap). |
| `employees` | `UNIQUE (lower(email))` **global**. Email tetap unik lintas perusahaan, sesuai perilaku sekarang. `work_location_id` FK ke `work_locations`, nullable. |
| `work_locations` (**ganti nama** dari `office_locations`, ditambah isi dari `office_settings`) | Satu baris per lokasi dengan semua kolom kebijakan (reverify, alert, `max_open_hours`). `is_primary bool` dengan unique parsial `(tenant_id) WHERE is_primary`. Tabel `office_settings` dihapus. Lihat catatan 1. |
| `calendar_settings` | PK `tenant_id`, satu baris per tenant. Token OAuth tetap di sini. |
| `oauth_states` (**baru**) | `state` PK, `tenant_id`, `employee_id`, `expires_at`. Menggantikan `_google_oauth_states`. |
| `login_attempts` (**baru**) | `id`, `email`, `attempted_at`, dengan index `(email, attempted_at)`. Tanpa tenant, karena login terjadi sebelum tenant diketahui. Menggantikan `_login_attempts`. |
| `sessions` | `token text` PK, berupa token acak (bukan uuid). `employee_id` FK. |
| `invitations`, `password_resets` | `token text` PK. FK ke `employees`/`work_locations`. |
| `attendance` | `employee_id` FK. Unique parsial `(tenant_id, employee_id) WHERE checked_out_at IS NULL`, sehingga hanya boleh ada satu sesi terbuka (409 sama seperti sekarang, tapi aman terhadap race). `agenda jsonb`. |
| `idempotency_keys` (**ganti nama** dari `idempotency`) | PK `(tenant_id, key)`, `attendance_id` FK. |
| `location_events`, `leave_requests`, `notifications`, `payroll_runs` | `employee_id`/`user_id` FK. Tabel `payroll_runs` mendapat `UNIQUE (tenant_id, period)`. |
| `alert_receipts` | PK `(tenant_id, employee_id, kind, local_date)`, tanpa kolom `id` surrogate. Key string gabungan yang lama dihapus. |
| `audit_logs` | `at` berubah dari `varchar` menjadi `timestamptz`. Lihat catatan 2. |
| `policies`, `policy_sections` | `policy_sections.policy_id` FK `ON DELETE CASCADE`. `id` section menjadi uuid. Lihat catatan 3. |
| `policy_answer_audit` | `cited_sections jsonb` (tetap). |

Catatan:

1. **Lokasi utama.** Sekarang `store.office` adalah lokasi `office-default` sekaligus pemegang kebijakan reverify dan alert. Lokasi tambahan memakai nilai default (reverify mati). Perilaku ini dipertahankan apa adanya, karena gap analysis #6 menandainya sebagai tiket terpisah: kebijakan dibaca dari lokasi milik karyawan, dan lokasi tambahan dibuat dengan nilai default. Respons lokasi mendapat field `is_primary`.
2. `GET /audit-logs` sekarang mengembalikan `at` sebagai string ISO dengan format `+00:00`. Setelah revamp, format serialisasinya ditentukan Pydantic. Characterization test akan menunjukkan kalau formatnya berubah, misalnya menjadi `Z`, dan formatnya disamakan lewat serializer kalau perlu.
3. `PolicySectionInput.id` (opsional, dikirim klien) sekarang dipakai apa adanya. Web tidak pernah mengirimnya (`settings/policies/page.tsx`). Setelah revamp, aturannya: kalau `id` sama dengan section yang sudah ada, ID itu dipertahankan; selain itu dibuat uuid baru.

## Implementation Units

Setiap unit menjadi satu commit, kecuali disebut lain. Pesan commit memakai Conventional Commits dalam bahasa Inggris, dengan scope `api` dan nomor unit di akhir subjek, misalnya `test(api): snapshot response shapes of the old API (U0)` atau `refactor(api): move employees into its own module (U7)`. **Gerbang hijau:**

- U0–U3: `scripts/check.sh` hijau penuh.
- U4–U11 (masa transisi, saat `api.py` + `DemoStore` hidup berdampingan dengan modul baru di DB): ruff, pyrefly, dan tes unit modul baru harus hijau. Tes HTTP untuk domain yang sudah dipindah boleh merah sampai domain yang dibutuhkannya ikut pindah, misalnya `employees` butuh login dari `auth`. Tidak ada strategi koeksistensi router lama dan baru.
- U12 dan seterusnya: `scripts/check.sh` hijau penuh, termasuk seluruh tes lama (R11) dan characterization test. **Ini gerbang merge.**

### U0. Characterization snapshot (di kode lama)

- Menambahkan `tests/contract/` berisi skrip yang menjalankan alur seed demo di **kode lama** dan menyimpan bentuk response setiap endpoint ke `tests/contract/shapes.json`. Yang disimpan adalah key secara rekursif dan tipe JSON, sedangkan nilai ID dan waktu diabaikan. Cakupannya mengikuti peran: HR, manager, dan employee, hanya untuk respons sukses. Respons error selalu berbentuk `{"detail": str}`, dan status code-nya sudah dicakup tes yang ada.
- Menambahkan `test_contract_shapes.py` yang membandingkan bentuk response kode baru dengan `shapes.json`. Perbedaan yang diizinkan hanya yang tercantum di daftar (`is_primary`).
- **Verifikasi:** tes lolos di kode lama, karena snapshot dan kode masih sama.
- `shapes.json` adalah artefak beku, yang tidak di-generate ulang setelah U0. Skrip perekamnya ikut dihapus di U12 bersama kode lama. `test_contract_shapes.py` ditulis ulang di U4 ke harness async + DB, dengan `shapes.json` yang sama.

### U1. Tooling

- `pyproject.toml`:
  - `[tool.uv] exclude-newer = "7 days"`;
  - dependency mengikuti baris "Versi target" di Key Technical Decisions: batas bawah dan atas persis seperti di baris itu, dengan `httpx` pindah dari grup dev dan `resend[async]`;
  - jalankan `uv lock --upgrade`, lalu cek bahwa versi di `uv.lock` sama dengan tabel target dan tidak ada yang berumur kurang dari 7 hari. Catat juga bagaimana uv merekam `exclude-newer` di lockfile;
  - `asyncpg` **belum** dihapus, karena `core/persistence.py` lama masih memakainya. Penghapusannya di U12;
  - grup dev: pytest 9.1, ruff 0.16.10, pyrefly 1.3, import-linter 2.15;
  - konfigurasi ruff (`extend-select = FAST, DTZ, S, C90, PLR0911/0912/0915`, ignore `S101/S105/S106` untuk tes, `known-third-party = ["alembic"]`);
  - `[tool.pyrefly]` dengan `project-includes=["src"]` dan `preset="default"`;
  - `[tool.importlinter]` (dikosongkan dulu, diisi di U12).
- `.python-version` diisi `3.12`.
- `scripts/check.sh`.
- `tests/test_file_lengths.py`, dengan batas 600 baris.
- `.github/workflows/api.yml`, **satu job** dengan service PG18: `uv sync --locked` lalu `scripts/check.sh`. Langkah alembic baru ditambahkan di U3, karena chain lama masih rusak sampai baseline dibuat.
- Di commit ini ruff dan pyrefly belum dijadikan gerbang untuk `modules/api.py` (lewat `extend-exclude` sementara), karena file itu akan dihapus di U12.

### U2. Fondasi DB dan tenancy

- `core/db.py`:
  - `create_async_engine` dari `settings.database_url`, yang sekarang wajib, dengan default `postgresql+psycopg://movon:movon@localhost:5432/movon`;
  - `async_sessionmaker(expire_on_commit=False, sync_session_class=TenantSession)`;
  - `Base` dengan `naming_convention`;
  - `get_db()` berupa async yield dengan commit/rollback;
  - satu tes: `BackgroundTasks` **tidak** berjalan kalau handler raise atau commit gagal, dan berjalan setelah commit kalau sukses.
- `core/tenancy.py`:
  - model `Tenant`, mixin `TenantScoped`;
  - `TenantSession`, subclass `Session` sync, dengan listener `do_orm_execute` (SELECT/UPDATE/DELETE, fail closed, bisa di-bypass dengan `cross_tenant=True`) dan `before_flush` yang mengisi `tenant_id`;
  - semua `relationship()` memakai `lazy="raise"`.
- `core/security.py`: tambah `hash_password_async` dan `verify_password_async`, yang membungkus argon2 dengan `anyio.to_thread.run_sync(..., limiter=_HASH_LIMITER)`. `_HASH_LIMITER` adalah `anyio.CapacityLimiter(4)`. Algoritma tetap Argon2id dengan default `argon2-cffi` (m=64 MiB, t=3, p=4), yang di atas minimum OWASP (19 MiB, t=2, p=1). Tidak pindah ke `pwdlib`, karena pwdlib hanya membungkus `argon2-cffi`.
- `core/mailer.py`: `send_email` menjadi `async`, memakai `resend.Emails.send_async` dengan `HTTPXClient(timeout=10)`. Transport `console` tetap tanpa I/O. `dispatch_email` dihapus, dan pemanggilnya memakai `BackgroundTasks`.
- HTTP keluar (Google, Maps) memakai `async with httpx.AsyncClient(timeout=…)` per panggilan, dengan timeout sama seperti sekarang (15 detik untuk Google, 8 detik untuk Maps). Tidak ada client bersama, karena panggilannya jarang.
- `core/auth.py`:
  - `CurrentUser` membaca token dari header `X-Demo-User` atau cookie, lalu mencari sesi secara lintas tenant;
  - sesi kedaluwarsa dihapus dan menghasilkan 401 dengan pesan yang sama seperti sekarang;
  - `session.info["tenant_id"]` di-bind setelah sesi ditemukan;
  - `require_role(*roles)`.
- `core/time.py`: `JAKARTA`, `jakarta_date`, `working_days`.
- Tes unit untuk isolasi tenant:
  - dua tenant, SELECT, UPDATE, dan DELETE tidak saling terlihat;
  - SELECT tanpa tenant raise;
  - INSERT otomatis mendapat `tenant_id`.

### U3. Model dan baseline migrasi

- `models.py` di setiap modul sesuai bagian Schema Changes, dengan `Base` bersama.
- `alembic/env.py` diarahkan ke `Base.metadata` dengan `compare_server_default=True`. `alembic.ini` memakai `file_template` berprefix tanggal.
- Hapus `versions/0001–0004`. Jalankan `alembic revision --autogenerate -m "baseline"` lalu review. Bagian yang ditulis atau diperiksa manual: `uuidv7()`, unique parsial, `lower(email)`, dan constraint dengan nama yang tepat.
- `docker-compose.yml`:
  - image `postgres:18-alpine`;
  - volume di-mount ke `/var/lib/postgresql`, bukan `/var/lib/postgresql/data`. Sudah diverifikasi di `docker-library/postgres` `18/alpine3.24/Dockerfile:202-205`: "in 18+, PGDATA has changed… and the VOLUME has moved from /var/lib/postgresql/data to /var/lib/postgresql", dengan `PGDATA=/var/lib/postgresql/18/docker`;
  - service `redis` dihapus, beserta `depends_on: redis` di service `api`;
  - URL diganti ke `postgresql+psycopg://…`;
  - **`command: uvicorn …` di service `api` dihapus.** Override ini menimpa `CMD` Dockerfile, sehingga prestart (migrasi + seed) tidak akan jalan di compose;
  - service `web`: `NEXT_PUBLIC_API_URL` dihapus karena sudah tidak dibaca kode web (yang dipakai `MOVON_API_ORIGIN` di `next.config.ts`). Diganti `build.args.MOVON_API_ORIGIN: http://api:8000`. Ini bug yang sudah ada sejak sebelum revamp: tanpa arg ini, rewrite `/api/*` dibakukan ke `127.0.0.1:8000`, yaitu container web itu sendiri, jadi web di compose tidak bisa menjangkau API;
  - catatan untuk developer di README: volume lama `postgres_data` berisi data PG16, jadi jalankan `docker compose down -v` sekali sebelum memakai PG18.
- `.env.example`:
  - `MOVON_DATABASE_URL` diganti ke `postgresql+psycopg://…`;
  - `MOVON_CORS_ORIGINS` diganti ke format JSON (`["http://localhost:3000"]`). Nilai plain string yang sekarang membuat `Settings()` gagal dengan `SettingsError` (sudah diuji).
- `.github/workflows/api.yml` ditambah langkah sebelum `scripts/check.sh`: `alembic upgrade head`, `alembic check`, dan `alembic heads` (harus tepat satu). Migrasi bersifat forward-only, jadi tidak ada tes downgrade bolak-balik.
- **Verifikasi:** `alembic upgrade head` lalu `alembic check` di PG18 lokal.

### U4. Seed demo dan harness tes

- `seed.py` berisi port dari `reset_demo_store()` dengan data yang sama persis (19 karyawan, 7 sesi presensi hari ini, 1 cuti, 2 notifikasi, lokasi utama "Jakarta HQ", `e-018` remote). ID memakai `uuidv7()`. `--if-empty` hanya melakukan seed kalau tabel `tenants` kosong.
- `seed.py` berupa async: `python -m movon_hr.seed` memanggil `asyncio.run`.
- `tests/conftest.py`, async penuh dengan plugin pytest bawaan `anyio`:
  - `alembic upgrade head` dijalankan sekali per sesi terhadap `MOVON_TEST_DATABASE_URL`;
  - fixture `AsyncConnection` dengan transaksi luar per tes, dan override `get_db` memakai `AsyncSession(bind=conn, join_transaction_mode="create_savepoint")`;
  - klien tes memakai `httpx.AsyncClient(transport=ASGITransport(app))`, menggantikan `TestClient`. `TestClient` menjalankan event loop di thread lain, padahal koneksi DB tes terikat ke loop tes (Kludex tips #5, zhanymkanov "Set tests client async from day 0");
  - semua fungsi tes menjadi `async def` dengan `await client.get(...)`. Assertion-nya tetap sama;
  - seed demo dijalankan di dalam transaksi tersebut;
  - helper `employee_id(email)` dan `login_headers(email)`;
  - mail tetap dipaksa ke `console`.
- `test_contract_shapes.py` dipindah ke harness ini (lihat U0).
- Tes lama yang memanipulasi `store` diubah supaya memakai helper fixture (misalnya `set_office_policy(db, …)` dan `add_attendance(db, …)`). **Assertion HTTP tidak diubah.**

### U5. `audit` dan `notifications`

- Service `audit(db, action, actor, target)` dan `notify(db, user_id, title, detail, target)`.
- Router `GET /audit-logs` (urut terbaru dulu, sama seperti sekarang), `GET /notifications`, dan `POST /notifications/read-all`. Semuanya ada di modul `notifications`, dan `GET /notifications` murni membaca. Evaluasi alert pindah ke job (U10), sehingga `notifications` tidak bergantung pada `attendance`.

### U6. `settings`

- Work locations dan kebijakan kantor:
  - `GET/POST /settings/locations`, dengan dedup nama dan koordinat yang sama seperti sekarang;
  - `GET/PUT /settings/office` (`validate_office_policy`);
  - `POST /settings/office/from-maps-url` (`maps.py`, short link di-resolve lewat `httpx` dengan `follow_redirects=True`).
- Kalender: `GET/PUT /settings/calendar` dan Google OAuth start, callback, serta calendars (`google_calendar.py` memakai `httpx`, state disimpan di `oauth_states`, dan callback berjalan lintas tenant).
- Respons lokasi ditambah field `is_primary`.

### U7. `employees`

- `visible_employees`, `public_employee` dalam bentuk schema `EmployeeOut` (field sensitif tidak ikut; `salary` disembunyikan untuk manager; `work_mode` dan `work_location` diturunkan).
- `GET /employees`, `GET /employees/{id}`, `POST /employees` (`temporary_password` sekali tampil), dan `PATCH /employees/{id}` (aturan suspend, cabut sesi, validasi lokasi).

### U8. `auth`

- `signup` (tenant baru, lokasi utama "Kantor Pusat", HR admin), `login` (lockout lewat `login_attempts`, verifikasi hash dengan timing yang sama, rehash), `logout`, `invites` (create menunggu email setelah commit, preview, dan accept lintas tenant), `forgot-password` (email lewat `BackgroundTasks`), `reset-password`, `change-password`, dan `GET /me`.
- Hash dan verifikasi password memakai varian async dari `core/security.py`, yaitu argon2 di thread.
- Cookie dan pesan error sama persis dengan sekarang.

### U9. `leave`

- `GET/POST /leave-requests`, `POST /leave-requests/{id}/cancel`, `GET /approvals`, dan `POST /approvals/{id}`.
- Sinkronisasi dan penghapusan event Google Calendar tetap inline, lewat `await` httpx. Email cuti dikirim lewat `BackgroundTasks`.
- `has_approved_leave` dan `leave_balance` diekspos lewat service.

### U10. `attendance`

- `rules.py` berisi logika murni: haversine, radius yang diizinkan, dan slot reverify.
- `alerts.py` berisi `evaluate_tenant(session, now)` yang idempoten, dengan aturan yang sama seperti `evaluate_attendance_alerts()` sekarang.
- `movon_hr/jobs.py` berisi:
  - `attendance-alerts`: loop per tenant dengan session sendiri, dan tenant di-bind per iterasi;
  - `cleanup`: hapus sesi kedaluwarsa, `password_resets` yang kedaluwarsa atau sudah dipakai, `login_attempts` di luar jendela lockout, dan `oauth_states` yang kedaluwarsa;
  - exit code bukan nol kalau gagal, supaya status run di Dokploy merah.
- Endpoint `GET /attendance/today`, `POST check-in` (idempotency key dengan `ON CONFLICT`, sesi terbuka dilindungi unique parsial), `check-out`, `reverify`, dan `GET /employees/{id}/location-history`.
- `GET /attendance/today` murni membaca. Slot reverify yang sudah lewat masa toleransi (`due_at + 15 menit`) dianggap terlewat saat dibaca, tanpa ditulis, sehingga isi `pending_reverification` sama seperti sekarang. Penulisan anomali `missed_reverify` dilakukan oleh job, dan oleh `check-out` seperti sekarang.
- Tes alert (`test_attendance_alerts.py`) memanggil `evaluate_tenant` langsung lalu `GET /notifications`. Assertion-nya tetap sama.

### U11. `payroll`, `policies`, `dashboard`

- Payroll:
  - `rules.py` berisi perhitungan Decimal, termasuk potongan 2% yang di-hardcode. Perilaku ini dipertahankan dan ada di daftar tiket bug terpisah;
  - endpoint runs, finalize, publish (notifikasi tetap ke semua karyawan seperti sekarang; bug ini juga sudah ada di daftar tiket terpisah), dan payslips.
- Policies: CRUD, publish, archive, dan policy assistant (audit jawaban).
- Dashboard: agregasi read-only.

### U12. Penutup

- Hapus `modules/api.py`, `core/persistence.py`, `DemoStore`, `StoreFacade`, `TenantScopeMiddleware`, dan middleware `persist_after_mutation`. Hapus juga dependency `asyncpg` dan konversi URL `+asyncpg` di `core/settings.py`, beserta `test_postgres_sync_url.py`.
- Isi dua kontrak import-linter (`forbidden` core→modules dan `acyclic_siblings` untuk `movon_hr.modules`). Hapus `extend-exclude` sementara.
- **Hapus** script dev di root repo: `scripts/run-api.sh`, `start-services.sh`, `ensure-db.sh`, dan `stop-services.sh`. Keputusan user 2026-10-12.
  - `ensure-db.sh` mengunci Postgres 16 Homebrew (khusus macOS) dan URL `+asyncpg`;
  - `start-services.sh` dan `stop-services.sh` tumpang tindih dengan `docker compose`;
  - keempatnya tidak dirujuk di README maupun `AGENTS.md`.

  Bagian "Local start" di README diganti dengan dua alur:
  - full stack: `docker compose -f infra/compose/docker-compose.yml up --build`;
  - dev API dengan hot reload: `docker compose … up -d postgres`, lalu dari `apps/api` jalankan `uv run alembic upgrade head && uv run python -m movon_hr.seed --if-empty && uv run uvicorn movon_hr.main:app --reload`.
- Ganti Dockerfile ke single-stage berbasis `uv`, mengikuti panduan uv "Using uv in Docker": binary uv di-pin (`COPY --from=ghcr.io/astral-sh/uv:<versi>`), layer dependency dipisah (`uv sync --locked --no-dev --no-install-project`), cache mount, `UV_COMPILE_BYTECODE=1`, `.venv/bin` dimasukkan ke `PATH` (tanpa `uv run` saat start), dan `USER nobody`. Prestart: `alembic upgrade head && python -m movon_hr.seed --if-empty && uvicorn …`.
- Dokumentasi:
  - **ADR 0002** (arsitektur backend);
  - update `docs/architecture.md` (hapus Celery, Redis, dan S3);
  - `docs/runbook.md`;
  - README (bagian persistence, cara menjalankan termasuk menjalankan job secara manual di lokal, dan klaim "vertical slices");
  - `apps/api/README.md` (konvensi, cara menambah modul). Konvensi bahasanya: kode, komentar, konfigurasi (termasuk nama kontrak import-linter), dan pesan commit ditulis dalam bahasa Inggris; teks untuk pengguna (pesan error API) dalam bahasa Indonesia; dokumen tim di `docs/` dalam bahasa Indonesia;
  - `AGENTS.md`: `scripts/check.sh` sebelum push; API full async (`async def`, `AsyncSession`, library sync lewat `to_thread`); SQLAlchemy 2, bukan SQLModel.
- Agent skill:
  - skill FastAPI resmi lewat `uvx library-skills --claude`, yang meng-commit symlink di `.claude/skills/fastapi`, mengikuti template resmi;
  - daftarkan `postgres-best-practices@supabase-agent-skills` di `extraKnownMarketplaces` dan `enabledPlugins` pada `.claude/settings.json`, dengan pola yang sama seperti plugin tim yang sudah ada (mattpocock-skills, ponytail).

### U13. Deploy (setelah merge, bersama PR web)

1. Buat service Postgres 18 baru di Dokploy dan verifikasi path volume-nya.
2. Ubah `MOVON_DATABASE_URL` ke `postgresql+psycopg://…` yang menunjuk ke DB baru.
3. Deploy API. Prestart akan menjalankan migrasi lalu seed demo.
4. Deploy web dari PR pasangan.
5. Smoke test: login dengan 3 akun demo, check-in, ajukan dan setujui cuti, jalankan payroll, ask-teamku, lalu restart container dan pastikan data tetap ada.
6. Hapus service `teamku-db-uzhmsj` (PG16) setelah smoke test lolos. Data di dalamnya hanya data demo.
7. Pasang jadwal backup untuk DB baru. Memory mencatat prod belum punya backup terjadwal.
8. Buat dua Dokploy Schedule untuk application API (`i_RLgal2WRmLaxzhuRjEh`), dengan timezone `Asia/Jakarta` dan shell `sh`:
   - `attendance-alerts`: `*/5 * * * *`, perintah `python -m movon_hr.jobs attendance-alerts`;
   - `cleanup`: `0 3 * * *`, perintah `python -m movon_hr.jobs cleanup`.

   Lalu cek log run pertama keduanya. Langkah ini mengubah prod, jadi dilakukan setelah konfirmasi user.

## Paired Web PR

Branch `refactor/web-location-ids`, di-merge bersamaan dengan PR API:

- `settings/page.tsx:747,803`: `location.id === "office-default"` diganti `location.is_primary`.
- `people/page.tsx:34` dan `people/[id]/page.tsx:238`: default `"office-default"` diganti ID lokasi dengan `is_primary`, atau string kosong kalau tidak ada.
- `people/page.tsx:265`: `employee.id !== "e-hr"` diganti `employee.id !== currentUser.id`, karena maksud aslinya adalah HR tidak bisa menindak dirinya sendiri.
- Type lokasi di `features/settings/types.ts` ditambah `is_primary: boolean`.

## Scope Boundaries

**Di luar scope.** Semua item ini sudah tercatat di bagian "BE · Perlu dibuat/diperbaiki" pada issue revamp v2, dan dikerjakan di modul baru setelah PR ini di-merge:

- Fitur baru revamp:
  - perjalanan dinas (#23, #24, Q1 di #8);
  - rekan pengganti cuti (#14, #18, Q2);
  - daftar, kirim ulang, dan pembatalan undangan (#23);
  - lifecycle 5 status dan arsip karyawan (#23, #24);
  - profil perusahaan, email HR, dan kelola HR Admin (#21, #27);
  - jenis cuti Sakit/Izin (#14, Q4);
  - update agenda (#13, Q5);
  - upload selfie (#12);
  - PDF slip gaji (#16, Q7);
  - tandai satu notifikasi dibaca (#17).
- Bug perilaku yang sengaja dipertahankan, karena revamp ini tidak mengubah fitur:
  - validasi prioritas check-in minimal 3 karakter (#12);
  - lokasi check-out wajib (#13);
  - validasi `work_location_id` saat create/invite (#23);
  - notifikasi payroll ke karyawan yang sudah keluar (#25);
  - urutan status kebijakan (#26);
  - `revision_requested` (#14, #18, Q3);
  - reverify dan alert per lokasi (#27);
  - jam terlambat 09:00, hak cuti 12 hari, dan email `hr@company.local` yang di-hardcode (#19, #14, #15);
  - potongan 2% yang di-hardcode (#25).
- `target` notifikasi masih berisi path v1 (#17). Pemetaan ke rute v2 dilakukan di FE. Menyimpan jenis+ID sebagai pengganti URL baru dipertimbangkan kalau rute berubah lagi.
- Penghapusan `X-Demo-User` (bersamaan dengan `demo-session.ts` di web).
- RLS, outbox/retry email otomatis, task queue, dan generate type web dari OpenAPI.
- pytest-cov, pytest-randomly, `uv audit` di CI, dan ty.
- Git hooks (prek) untuk API maupun web. Konfigurasinya siap di riset 003 §9.

## Risks & Dependencies

| Risiko | Mitigasi |
|---|---|
| Ada perubahan kontrak response yang tidak tertangkap | U0 characterization test untuk setiap endpoint dan peran. Ditambah smoke test web lokal terhadap API baru sebelum merge. |
| Format datetime berubah (`+00:00` vs `Z`, mikrodetik) | Characterization test mencatat format string untuk field waktu. Kalau berbeda, disamakan lewat serializer. |
| Filter tenant bocor lewat jalur yang tidak tercakup | Fail closed. Raw SQL dilarang di modul. Suite isolasi tenant (U2) ditambah tes per endpoint baca dengan dua tenant. |
| `with_loader_criteria` untuk bulk UPDATE/DELETE belum teruji (001) | Dicakup tes unit U2. Kalau tidak bekerja, bulk update/delete dilarang di modul dan diganti operasi per objek. |
| Path volume image PG18 berubah | Sudah diverifikasi: mount ke `/var/lib/postgresql` (lihat U3). Di Dokploy (U13), cek mount service PG18 baru mengarah ke path itu. Kalau salah, data tersimpan di layer container dan hilang saat redeploy. |
| Konflik dengan pekerjaan BE paralel: issue #9–#27 menulis "BE bisa dikerjakan sekarang", dan PR ini menulis ulang `api.py` | **Freeze BE di `apps/api`** sampai PR ini di-merge. Pekerjaan FE tetap jalan. Per 2026-10-12 tidak ada branch remote yang menyentuh `apps/api`. Sebelum merge, cek ulang dengan `git log main..` pada path `apps/api`. |
| Remote `origin` di checkout lokal masih menunjuk fork `fadhilsuh/teamku` | Push dan PR ke `Movon-Product-House/teamku`, karena itu repo yang di-deploy Dokploy. |
| PR besar sulit di-review | Satu commit per unit, dan urutan unit mengikuti lapisan dependency. Gerbang hijau berlaku per fase (lihat Implementation Units). Reviewer bisa membaca per commit. |
| Tes jadi lambat karena seed per tes | Hash password demo dihitung sekali. Seed dijalankan di dalam savepoint. Diukur setelah U4; batasnya kurang dari 2× waktu suite sekarang (14,6 detik). |
| Pool koneksi habis saat banyak request bersamaan | 10+10 dengan `pool_pre_ping`. Diukur di smoke test. `max_connections` PG default 100 (belum diverifikasi). |
| Spam login menjalankan banyak hash argon2 bersamaan (masing-masing 64 MiB), sehingga container kehabisan memori | `CapacityLimiter(4)` untuk hashing, ditambah lockout login yang sudah ada (5 gagal per 15 menit). Puncak memori ≈ 256 MiB. |
| Event Google Calendar dibuat (inline, sebelum commit) untuk approval cuti yang kemudian gagal commit, sehingga event-nya yatim | Diterima. Perilakunya sama seperti sekarang dan jarang terjadi. Kalau sampai terjadi, event dihapus manual dari kalender. Perbaikannya (outbox) di luar scope. |
| Lazy load tidak sengaja di `AsyncSession` (`MissingGreenlet`) | `lazy="raise"` di semua relasi, sehingga gagal keras di tes. Data relasi dimuat eksplisit dengan `selectinload`. |
| Panggilan blocking menyelinap ke `async def` | Rule ruff `ASYNC` di CI. Pada review, setiap library baru dicek dulu apakah punya API async. Kalau tidak ada, panggilannya dibungkus `to_thread`. Aturan ini dicatat di `AGENTS.md`. |
| Agent menulis endpoint `def` karena default skill FastAPI | `AGENTS.md` dan ADR 0002 mencatat: "API full async; semua handler/dependency `async def`; library sync lewat `anyio.to_thread.run_sync`". |

## Open Questions

Tidak ada. Semua keputusan sudah dikonfirmasi user pada 2026-10-12:

- `office_locations` dan `office_settings` digabung menjadi `work_locations` dengan `is_primary`. Penggabungannya wajib, karena lokasi utama tersimpan dua kali dan dihubungkan oleh ID literal. Namanya mengikuti kosakata API (`work_location_id`, `WorkLocationInput`).
- `idempotency` diganti `idempotency_keys`, mengikuti konvensi nama tabel jamak.
- import-linter versi minimal (`forbidden` dan `acyclic_siblings`), dengan `layers` ditunda.
- Job terjadwal lewat Dokploy Schedule, dan GET murni membaca.

Diverifikasi saat implementasi, tidak memblokir: `with_loader_criteria` untuk bulk UPDATE/DELETE (tes U2), apakah raw SQL tidak ikut terfilter (diasumsikan tidak, makanya raw SQL dilarang), dan `max_connections` PG (smoke test U13).

## Sources & Research

- `docs/research/2026-10-12-001-fastapi-alembic-postgres-best-practices.md`: skill FastAPI (async vs sync), Kludex tips dan zhanymkanov (async-first), pool, Alembic, `naming_convention`, penamaan PG, skill yang dipasang.
- `docs/research/2026-10-12-002-api-architecture-options.md`: gaya arsitektur, Session sebagai UoW, tenancy, ID, tes di Postgres, alert lazy, import-linter.
- `docs/research/2026-10-12-003-api-dev-tooling.md`: ruff 0.17, pyrefly, prek, CI, `check.sh`, tes panjang file, angka terukur.
- Dokumentasi PostgreSQL 18 §9.14 (`uuidv7()`); halaman versioning PostgreSQL (18.6 stabil, 19 beta 4), diakses 2026-10-12.
- Kode: `apps/api` @ `adc580a`; penggunaan ID di web (`apps/web/src/app/app/settings/page.tsx`, `people/page.tsx`, `people/[id]/page.tsx`); `calendar_sync_status` di `features/leave/components/decision-dialog.tsx:46`.
