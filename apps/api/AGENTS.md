# Aturan kode API (`apps/api`)

FastAPI full async + SQLAlchemy 2 (`Mapped[]`) + Pydantic + PostgreSQL 18 + Alembic. Path di file ini relatif ke `apps/api`; `core/` dan `modules/` berarti `src/movon_hr/core/` dan `src/movon_hr/modules/`. Perintah dan setup DB: `apps/api/README.md`. Keputusan arsitektur dan alasannya: `docs/adr/0002-backend-api-architecture.md`. Gerbang sebelum push: `scripts/check.sh`.

## Batas modul

- Arah dependency, modul atas memakai modul di bawahnya:

  ```
  dashboard
  attendance | payroll | policies | auth
  leave
  employees
  settings
  audit | notifications
  core
  ```

  Dua modul yang saling butuh: pindahkan bagian bersamanya ke modul yang lebih bawah (contoh: `Invitation` tinggal di `employees` karena `auth` mengimpor `employees`).
- `core` generik, tanpa logika domain, dan tidak mengimpor `modules`. Import-linter (`[tool.importlinter]` di `pyproject.toml`) menegakkan larangan impor itu dan larangan siklus antar modul.
- Antar modul, impor hanya `modules.<x>.service`, `.schemas`, atau `.models` (dijaga review).
- Router tipis: cek peran, panggil service, return schema. Aturan bisnis dan query ORM di `service.py`; logika murni tanpa I/O di `rules.py` dengan tes unit. Contoh terkecil: `modules/audit/`.
- Maksimal 600 baris per file (`tests/test_file_lengths.py`).

## Async

- Setiap handler dan dependency `async def`, termasuk endpoint yang tidak menunggu apa pun. Ini mengalahkan skill FastAPI yang membolehkan `def`.
- DB lewat `db: DB` (`AsyncSession`, `core/db.py`). HTTP keluar lewat `async with httpx.AsyncClient(timeout=…)`. Email lewat `core.mailer.send_email`.
- Library sync dan kerja CPU berat dibungkus `anyio.to_thread.run_sync` (contoh: argon2 di `core/security.py`). Rule ruff `ASYNC` menangkap sebagian panggilan blocking, tidak semuanya.
- Relasi ORM `lazy="raise"`; muat eksplisit dengan `selectinload`/`joinedload`.
- Model tetap SQLAlchemy 2 dengan schema Pydantic terpisah, bukan SQLModel.

## Transaksi

- `get_db` memegang satu transaksi per request: commit sebelum response, rollback bila exception. Service membiarkan commit ke `get_db`.
- `commit()` di service hanya untuk pengecualian berikut, dan selalu dengan komentar alasannya: `POST /invites` (commit sebelum kirim email, ADR 0002) dan tulisan yang harus bertahan walau request error (percobaan login gagal, sesi kedaluwarsa yang dihapus sebelum 401).
- Efek samping setelah commit (email) lewat `BackgroundTasks`, supaya data yang di-rollback tidak memicu email.

## Tenancy

- Tabel milik tenant memakai mixin `TenantScoped` (`core/tenancy.py`): `tenant_id` terisi saat INSERT, dan setiap query ORM difilter ke tenant yang di-bind `CurrentUser`. Query tanpa tenant ter-bind raise (fail closed).
- Jalur lintas tenant (login, token undangan/reset, OAuth callback, job) menulis `.execution_options(cross_tenant=True)` secara eksplisit dan punya tes.
- Modul domain hanya memakai query ORM. Raw SQL (`text()`, `Connection.execute`) lolos dari filter tenant, jadi bila benar-benar perlu, letakkan di `core/`.
- Keunikan bisnis menyertakan `tenant_id`. Pengecualian: email karyawan unik global.

## Skema dan migrasi

- Skema berubah hanya lewat revisi Alembic di `alembic/versions/`.
- Kolom enum tetap `text` dengan CHECK dari `one_of(kolom, Alias)` (`core/db.py`). Autogenerate ikut membuat CHECK untuk tabel baru, tetapi tidak melihat perubahan CHECK di tabel yang sudah ada: setelah mengubah nilai sebuah `Literal`, tulis revisinya dengan tangan dan bekukan nilainya di revisi itu.

## Kontrak HTTP

Spec (`openapi.json`) adalah kontrak tempat client web di-generate. Setiap nama di bawah menjadi nama fungsi, hook, atau type di web, dalam satu namespace datar, jadi nama selalu membawa domainnya.

- Setiap endpoint JSON punya schema respons lewat return annotation (`-> EmployeeOut`); `response_model=` hanya bila handler me-return objek lain.
- Peran dicek lewat dependency `require_role(...)` dari `core/auth.py`.
- Schema: body request `XIn` (`LeaveIn`, `EmployeeUpdateIn`); respons dan semua bagiannya `XOut` (`LeaveOut`, `LeaveListOut`, `CitationOut`). `XOut` yang dibangun dari model ORM memakai `from_attributes=True`. Field respons yang punya default tetap `required` di spec (`json_schema_serialization_defaults_required=True`, dijaga `tests/test_openapi.py`).
- Enum: `type <Resource><Atribut> = Literal[...]` di `models.py` resource-nya (atau di `core/` bila dipakai lintas resource, mis. `EmployeeRole` di `core/identity.py`), tanpa sufiks (`EmployeeRole`, `LeaveDecision`, `PayrollRunStatus`).
- Nama fungsi handler = operationId, diturunkan dari method + path dengan nama resource lengkap (`payroll_run`, bukan `run`):

  | Endpoint | Nama | Contoh |
  |---|---|---|
  | `GET` koleksi | `list_<jamak>` | `list_approvals` |
  | `GET` satu item / singleton | `get_<tunggal>` | `get_me`, `get_dashboard` |
  | `POST` koleksi yang menyimpan resource baru | `create_<tunggal>` | `create_leave_request` |
  | `PUT`/`PATCH` | `update_<tunggal>` | `update_office` |
  | `POST` aksi lain (dengan atau tanpa segmen aksi di path) | `<aksi>_<resource>` | `publish_payroll_run`, `decide_approval`, `read_all_notifications`, `ask_policy_question` |
  | `POST /auth/…`, `POST /attendance/…` (modul bukan nama resource) | `<aksi>` | `login`, `check_in` |

  `tests/test_openapi.py` menjaga awalan: GET wajib `list_`/`get_`, PUT/PATCH wajib `update_`, `create_` hanya untuk POST. Nama aksi POST dijaga review.
- Union respons: field `result: Literal[...]` per varian dan `Field(discriminator="result")`.
- Setelah mengubah route atau schema: `uv run python -m movon_hr.openapi`, commit `openapi.json`, lalu `npm run api:gen` di `apps/web`.

## Bahasa

Kode, komentar, konfigurasi (termasuk nama kontrak import-linter), dan pesan commit dalam bahasa Inggris. Teks untuk pengguna (pesan error API) dalam bahasa Indonesia. Dokumen tim di `docs/` dalam bahasa Indonesia.

## Tes

- Tes `async def` dengan `@pytest.mark.anyio`, di PostgreSQL sungguhan. Setiap tes berjalan dalam satu transaksi yang di-rollback; session yang dibuka kode (`get_db`, job, seed) ikut lewat SAVEPOINT.
- Fixture utama di `tests/conftest.py`: `client`, `db` (demo ter-seed, tenant ter-bind), `login_headers(email)`, `employee_id(email)`, `clock`. Helper DB di `tests/helpers.py`. Email selalu lewat transport `console`.
- Jam simulasi: fixture autouse `clock` memulai setiap tes pada `TEST_NOW` (Rabu 10:00 WIB). Pindah waktu dengan `clock.move_to(...)` memakai datetime ber-tzinfo UTC: time-machine ikut memasang zona waktu proses dari tzinfo itu, dan prod serta CI berjalan di UTC.
- Kolom `server_default=func.now()` diisi jam asli Postgres, bukan `clock`, jadi bandingkan kolom itu hanya dengan sesamanya. Yang terdampak: lockout login (`LoginAttempt.attempted_at`, `raise_if_locked_out`), cleanup login attempt di `jobs.py`, urutan `list_policies` (`Policy.updated_at`). Contoh: `clock.move_to` melewati `LOGIN_ATTEMPT_WINDOW` tidak membuka lockout.

## Menambah modul

1. Buat `modules/<domain>/` berisi `__init__.py`, `models.py`, `schemas.py`, `service.py`, `router.py`. Tabel tenant: `Base` dari `core/db.py` + mixin `TenantScoped`, PK `uuid` dengan `server_default=text("uuidv7()")`.
2. Import `models.py` baru di `alembic/env.py`, supaya tabelnya masuk `Base.metadata` dan terlihat autogenerate.
3. `uv run alembic upgrade head`, lalu `uv run alembic revision --autogenerate -m "<domain>"`. Periksa hasilnya (`uuidv7()`, index parsial, nama constraint), lalu `uv run alembic upgrade head && uv run alembic check`.
4. `router = APIRouter(tags=["<domain>"])` tanpa `prefix`, path lengkap di setiap route (`@router.get("/payroll/runs")`): satu modul bisa melayani lebih dari satu akar path (`attendance` juga melayani `/employees/{id}/location-history`). Daftarkan router di `main.py`, yang memasang `/api/v1` dan respons `4XX`.
5. Tes di `tests/`, dump spec, lalu `scripts/check.sh`.

**Selesai bila:** `scripts/check.sh` hijau, `alembic check` bersih, dan `openapi.json` ter-commit.
