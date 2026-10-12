# 0002 — Arsitektur API backend: modular monolith async di atas PostgreSQL 18

- Status: diterima
- Tanggal: 2026-10-12

## Konteks

`apps/api` berupa satu file `modules/api.py` (±2400 baris) yang memuat model, aturan bisnis, dan semua route. Datanya disimpan di `DemoStore` in-memory yang ditulis ulang utuh ke PostgreSQL setelah setiap request mutasi, sehingga kegagalan simpan hanya di-log dan primary key bisa bentrok antar tenant. Rantai Alembic putus, `docs/architecture.md` mengklaim Celery, Redis, dan S3 yang tidak ada, dan API belum punya type checker maupun CI. Detail audit dan riset ada di `docs/plans/2026-10-12-001-refactor-api-foundation-plan.md`.

## Keputusan

- **Modular monolith per domain**: `src/movon_hr/modules/<domain>/` berisi `router.py`, `schemas.py`, `service.py`, dan `models.py`. Hal lintas domain yang generik ada di `core/`. Batasnya ditegakkan import-linter dengan dua kontrak: `core` tidak boleh mengimpor `modules`, dan tidak boleh ada siklus import antar modul.
- **Tanpa repository/unit of work**. `AsyncSession` SQLAlchemy sudah menjadi unit of work. Service menerima session dan menulis query ORM langsung.
- **SQLAlchemy 2 (`Mapped[]`) dengan schema Pydantic terpisah**, bukan SQLModel, walaupun skill FastAPI menyarankan SQLModel.
- **Full async**: semua handler dan dependency `async def`, `AsyncSession` dengan driver psycopg 3, `httpx.AsyncClient` untuk HTTP keluar, `resend.Emails.send_async` untuk email. Library sync (argon2) dijalankan lewat `anyio.to_thread.run_sync`.
- **Satu transaksi per request**: dependency `get_db` commit sebelum response dikirim dan rollback kalau ada error. Email dikirim lewat `BackgroundTasks`, jadi hanya untuk data yang sudah ter-commit. `POST /invites` commit sendiri lalu menunggu email karena response butuh `email_status`. Percobaan login gagal dan sesi kedaluwarsa juga di-commit sebelum 401, supaya tidak ikut di-rollback.
- **PostgreSQL 18 satu-satunya penyimpanan** untuk prod, demo, dan tes. Primary key `uuid` dengan default `uuidv7()` dari server.
- **Isolasi tenant lewat listener session, fail closed**: `tenant_id` disimpan di `session.info`. Listener `do_orm_execute` menambahkan filter tenant ke setiap SELECT, UPDATE, dan DELETE ORM, dan `before_flush` mengisi `tenant_id` saat INSERT. Query tanpa tenant akan raise, kecuali diberi `execution_options(cross_tenant=True)` (login, token undangan dan reset, sesi, OAuth callback, job). Raw SQL tidak ikut terfilter, jadi dilarang di modul domain.
- **Alembic satu-satunya pemilik skema**, dengan delapan revisi berantai per domain (identity, settings, audit_notifications, auth, leave, attendance, payroll, policies). Tidak ada `create_all` saat runtime. CI menjalankan `upgrade head`, `alembic check`, dan memastikan hanya ada satu head.
- **Job terjadwal** lewat satu entrypoint `python -m movon_hr.jobs attendance-alerts|cleanup` di image yang sama, dijadwalkan dengan Dokploy Schedule. Keduanya idempoten. Endpoint GET murni membaca.
- **`Tenant`, `Employee`, dan `AuthSession` tinggal di `core/identity.py`**, bukan di `modules/employees` dan `modules/auth`, karena `core/auth.py` membutuhkannya dan `core` tidak boleh mengimpor `modules`.
- **Model `Invitation` ada di `modules/employees/models.py`**, bukan di `auth`. `employees` perlu mengecek undangan yang masih pending, sedangkan `auth` mengimpor `employees`. Kalau `Invitation` ada di `auth`, akan terjadi siklus `auth ↔ employees`.

## Alternatif yang ditolak

- **Hexagonal penuh atau gaya cosmicpython** (port, adapter, repository per agregat): terlalu berat untuk dua engineer. Adapter hanya dipakai untuk integrasi eksternal (Google, Resend, AI).
- **API sync (`def` + threadpool)**: beban kerja kita I/O-bound, dan semua handler lama memang sudah `async def`.
- **Celery/Redis atau loop di lifespan untuk job**: hanya ada dua job periodik berfrekuensi rendah. Loop di lifespan ikut terduplikasi per worker dan mati saat deploy.
- **Satu migrasi baseline** (rencana awal): diganti delapan revisi per domain atas keputusan user (2026-10-12).
- **Row Level Security sekarang**: ditunda ke tiket terpisah sebagai lapisan tambahan.

## Konsekuensi

- Setiap domain bisa dibaca dan diubah tanpa membuka file lain, dan `scripts/check.sh` (ruff, pyrefly, import-linter, pytest di PG18 sungguhan) menjadi gerbang yang sama di lokal dan di CI.
- Semua state ada di PostgreSQL, termasuk lockout login dan state OAuth, sehingga API tidak lagi terikat ke satu proses.
- Modul baru harus menambahkan model ke `alembic/env.py` dan membuat revisi Alembic sendiri. Caranya ada di `apps/api/README.md`.
- Library baru harus dicek dulu apakah punya API async. Kalau tidak, panggilannya dibungkus `anyio.to_thread.run_sync`. Rule ruff `ASYNC` menangkap sebagian kesalahan ini.
- Relasi ORM memakai `lazy="raise"`, sehingga data relasi harus dimuat eksplisit dengan `selectinload`/`joinedload`.
