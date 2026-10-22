# Teamku API

FastAPI (full async) + SQLAlchemy 2 + psycopg 3 + PostgreSQL 18 + Alembic, dikelola dengan uv.
Keputusan arsitekturnya ada di [`docs/adr/0002-backend-api-architecture.md`](../../docs/adr/0002-backend-api-architecture.md); operasional prod di [`docs/runbook.md`](../../docs/runbook.md).

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

Jalankan `scripts/check.sh` sebelum push. Tes butuh database kosong terpisah: sekali saja jalankan `docker compose -f ../../infra/compose/docker-compose.yml exec postgres createdb -U movon movon_test`, atau arahkan `MOVON_TEST_DATABASE_URL` ke DB lain. CI (`.github/workflows/api.yml`) menjalankan `check.sh` ditambah `alembic upgrade head`, `alembic check`, dan cek satu head.

Tes berjalan di jam simulasi (`time-machine`): fixture autouse `clock` di `tests/conftest.py` memulai setiap tes pada `TEST_NOW` (Rabu 10:00 WIB), jadi hasilnya tidak bergantung kapan CI jalan. Butuh momen lain: `clock.move_to(...)` dengan datetime ber-tzinfo UTC (time-machine ikut memasang zona waktu proses dari tzinfo itu; prod dan CI berjalan di UTC). Kolom `server_default=func.now()` tetap diisi jam asli Postgres, jadi jangan bandingkan kolom itu dengan jam aplikasi di tes. Yang terdampak saat ini: jendela lockout login (`LoginAttempt.attempted_at` di `raise_if_locked_out`, `modules/auth/service.py`), cleanup login attempt di `jobs.py`, dan urutan `list_policies` (`Policy.updated_at`). Contoh: `clock.move_to` melewati `LOGIN_ATTEMPT_WINDOW` tidak membuka lockout.

## Struktur

```
alembic/versions/       # Revisi berantai per domain. Satu-satunya pemilik skema
src/movon_hr/
  main.py               # App, CORS, include_router setiap modul, health
  seed.py               # Seed demo (python -m movon_hr.seed)
  jobs.py               # Job terjadwal (python -m movon_hr.jobs)
  core/                 # Generik, tanpa logika domain: settings, db, tenancy, identity
                        # (Tenant, Employee, AuthSession), auth, security, mailer, time, AI
  modules/<domain>/
    router.py           #   Route HTTP. Tipis: validasi peran, panggil service, return schema
    schemas.py          #   Pydantic in/out. Keluaran memakai from_attributes=True
    service.py          #   Aturan bisnis + query ORM. Menerima AsyncSession
    models.py           #   Model SQLAlchemy (Mapped[]) di atas core.db.Base
    rules.py, …         #   Logika murni tanpa I/O (opsional), diberi tes unit
tests/                  # pytest di PostgreSQL sungguhan
```

Contoh terkecil: `modules/audit/`.

## Aturan

### Batas modul
1. **`core` tidak boleh mengimpor `modules`**, dan **tidak boleh ada siklus import antar modul**. Keduanya ditegakkan import-linter (`[tool.importlinter]` di `pyproject.toml`).
2. Antar modul hanya boleh mengimpor `modules.<x>.service`, `.schemas`, atau `.models`. **Jangan mengimpor `router` modul lain.** Aturan ini dijaga lewat review.
3. Arah dependency yang diharapkan (modul atas boleh memakai modul di bawahnya, tidak sebaliknya):

   ```
   dashboard
   attendance | payroll | policies | auth
   leave
   employees
   settings
   audit | notifications
   core
   ```

   Kalau dua modul saling butuh, pindahkan bagian bersamanya ke modul yang lebih bawah (contoh: model `Invitation` ada di `employees` karena `auth` mengimpor `employees`).
4. Maksimal 600 baris per file (`tests/test_file_lengths.py`).

### Async
1. **Semua handler dan dependency `async def`.** Jangan menulis endpoint `def`, walaupun skill FastAPI membolehkannya.
2. DB lewat `AsyncSession` (`db: DB` dari `core.db`). HTTP keluar lewat `async with httpx.AsyncClient(timeout=…)`. Email lewat `core.mailer.send_email` (async).
3. Library tanpa API async atau kerja CPU berat dibungkus `anyio.to_thread.run_sync` (contoh: argon2 di `core/security.py`). Rule ruff `ASYNC` menangkap sebagian panggilan blocking.
4. Relasi ORM memakai `lazy="raise"`. Muat relasi secara eksplisit dengan `selectinload`/`joinedload`.
5. SQLAlchemy 2 + Pydantic terpisah, **bukan SQLModel**.

### Transaksi
1. `get_db` membuka satu transaksi per request, commit sebelum response, dan rollback kalau ada exception. Service tidak memanggil `commit()` sendiri, kecuali ada alasan yang dikomentari: `POST /invites` (commit sebelum kirim email, lihat ADR 0002) dan penulisan yang harus bertahan walau request berakhir error (percobaan login gagal, sesi kedaluwarsa yang dihapus sebelum 401).
2. Efek samping setelah commit (email) lewat `BackgroundTasks`, supaya tidak ada email untuk data yang di-rollback.

### Tenancy
1. Tabel milik tenant memakai mixin `TenantScoped` (`core/tenancy.py`). `tenant_id` terisi otomatis saat INSERT, dan semua SELECT/UPDATE/DELETE ORM otomatis difilter ke tenant yang di-bind `CurrentUser`.
2. Query tanpa tenant ter-bind akan raise (fail closed). Jalur yang memang lintas tenant (login, token undangan/reset, OAuth callback, job) menulis `.execution_options(cross_tenant=True)` secara eksplisit, dan harus punya tes.
3. **Raw SQL (`text()`, `Connection.execute`) dilarang di modul domain**, karena tidak ikut difilter tenant. Kalau benar-benar perlu, letakkan di `core/`.
4. Keunikan bisnis selalu menyertakan `tenant_id` (kecuali email karyawan, yang unik global).

### HTTP
1. Setiap endpoint JSON punya schema respons lewat return annotation (`-> EmployeeOut`). `response_model=` hanya kalau handler me-return objek lain.
2. Cek peran lewat dependency `require_role(...)` dari `core.auth`.
3. Nama schema mengikuti arah data: body request `XIn` (`LeaveIn`, `EmployeeUpdateIn`), respons dan semua bagiannya `XOut` (`LeaveOut`, `LeaveListOut`, `CitationOut`). Enum tidak bersufiks dan selalu `<Resource><Atribut>`: `type EmployeeRole = Literal[...]` di `models.py` (lihat `one_of` di `core/db.py`), bukan `Role`. Nama ini menjadi nama type di client web.
4. Nama fungsi handler = operationId = nama fungsi/hook di client web, jadi diturunkan dari method + path, dengan nama resource lengkap (`payroll_run`, bukan `run`):

   | Endpoint | Nama | Contoh |
   |---|---|---|
   | `GET` koleksi | `list_<jamak>` | `list_approvals` |
   | `GET` satu item / singleton | `get_<tunggal>` | `get_me`, `get_dashboard` |
   | `POST` koleksi yang menyimpan resource baru | `create_<tunggal>` | `create_leave_request` |
   | `PUT`/`PATCH` | `update_<tunggal>` | `update_office` |
   | `POST` aksi lain (dengan atau tanpa segmen aksi di path) | `<aksi>_<resource>` | `publish_payroll_run`, `decide_approval`, `read_all_notifications`, `ask_policy_question` |
   | `POST /auth/…`, `POST /attendance/…` (modul bukan nama resource) | `<aksi>` | `login`, `check_in` |

   `tests/test_openapi.py` menjaga awalan: GET wajib `list_`/`get_`, PUT/PATCH wajib `update_`, dan `create_` hanya untuk POST. Nama aksi POST dijaga review.
5. Union respons diberi field `result: Literal[...]` per varian dan `Field(discriminator="result")`.

### Bahasa
Kode, komentar, konfigurasi (termasuk nama kontrak import-linter), dan pesan commit dalam bahasa Inggris. Teks untuk pengguna (pesan error API) dalam bahasa Indonesia. Dokumen tim di `docs/` dalam bahasa Indonesia.

## Menambah modul

1. Buat `src/movon_hr/modules/<domain>/` dengan `__init__.py`, `models.py`, `schemas.py`, `service.py`, `router.py`. Tabel tenant memakai `Base` dari `core.db` dan mixin `TenantScoped`; PK `uuid` dengan `server_default=text("uuidv7()")`.
2. Import `models.py` baru di `alembic/env.py`, supaya tabelnya masuk `Base.metadata`.
3. `uv run alembic upgrade head`, lalu `uv run alembic revision --autogenerate -m "<domain>"`. Review hasilnya (`uuidv7()`, index parsial, nama constraint), lalu `uv run alembic upgrade head && uv run alembic check`.
4. `router = APIRouter(tags=["<domain>"])` tanpa `prefix`: tulis path lengkap di setiap route (`@router.get("/payroll/runs")`), karena satu modul bisa melayani lebih dari satu akar path. Tambahkan router ke daftar di `main.py`, yang memasang `/api/v1` dan respons `4XX`.
5. Tambah tes di `tests/`, `uv run python -m movon_hr.openapi`, lalu `scripts/check.sh`.

## Tes

- `tests/conftest.py` menjalankan `alembic upgrade head` sekali per sesi ke `MOVON_TEST_DATABASE_URL` (default `postgresql+psycopg://movon:movon@localhost:5432/movon_test`).
- Setiap tes berjalan di dalam satu transaksi yang di-rollback di akhir tes. Semua session yang dibuka kode (`get_db`, job, seed) ikut transaksi itu lewat SAVEPOINT, dan seed demo dijalankan di dalamnya.
- Fixture utama: `client` (`httpx.AsyncClient` di atas ASGI), `db` (session dengan demo ter-seed dan tenant ter-bind), `login_headers(email)`, `employee_id(email)`, `clock` (autouse, jam simulasi; lihat di atas). Helper DB ada di `tests/helpers.py`.
- Tes ditulis `async def` dengan `@pytest.mark.anyio`. Email selalu dipaksa ke transport `console`.
