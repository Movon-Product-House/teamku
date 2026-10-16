# Best practice FastAPI + SQLAlchemy + Alembic + Postgres untuk revamp arsitektur API

Tanggal riset: 2026-10-12. Target: revamp arsitektur `apps/api` dalam satu PR tanpa perubahan fitur. Isinya: memecah `src/movon_hr/modules/api.py` (2433 baris) menjadi `modules/<domain>/{router,schemas,service,models}.py`, mengganti persistence snapshot in-memory dengan SQLAlchemy langsung (sync + handler `def`), tenant filter otomatis di level session, `response_model` di semua endpoint, dan Alembic sebagai satu-satunya sumber skema. Kode diaudit pada `main` @ `adc580a` (2026-10-10).

Sumber primer: kode repo ini; source dan docs resmi FastAPI (`github.com/fastapi/fastapi` @ `f5c6e9b`, docs `docs/en/docs/**`); wheel `fastapi` 0.141.1 yang terpasang di `apps/api/.venv`; `github.com/fastapi/full-stack-fastapi-template` @ `7257e60`; docs SQLAlchemy 2.0 (`docs.sqlalchemy.org/en/20`) dan repo `sqlalchemy/sqlalchemy` branch `rel_2_0` @ `9180a1d`; docs Alembic 1.20 (`alembic.sqlalchemy.org/en/latest`) dan source `sqlalchemy/alembic` @ `1bc21b8`; docs Pydantic (`docs.pydantic.dev/latest`); docs AnyIO; docs PostgreSQL 16; PostgreSQL wiki "Don't Do This" (revisi terakhir 2024-11-21); metadata PyPI (JSON API); repo GitHub komunitas dan skill yang dibaca langsung via `gh api` (bintang dan commit terakhir dicatat per repo). Tidak ada blog atau ringkasan pihak kedua yang dijadikan dasar klaim.

---

## Ringkasan (jawaban dulu)

- **Skill FastAPI resmi ada.** Sejak commit `4fce9ce` (2026-02-25, "Add FastAPI Agents Skill") FastAPI membundel skill Agent Skills di dalam package: `fastapi/.agents/skills/fastapi/SKILL.md` plus 6 file `references/`. File ini **sudah ada di `.venv` kita** (fastapi 0.141.1). Cara pasang resmi: `uvx library-skills` (alat dari tiangolo), lalu pilih target `.claude/skills` untuk Claude Code. Docs FastAPI membahasnya di bagian "AI Agent Skills" (`docs/en/docs/tutorial/index.md:115-131`). FastAPI **tidak** punya `llms.txt` (`https://fastapi.tiangolo.com/llms.txt` → 404). Repo `anthropics/skills` tidak punya skill FastAPI/Python/SQL.
- **Skill resmi FastAPI sejalan dengan rencana sync kita.** Kutipannya: "In case of doubt, or by default, use regular `def` functions." Ada dua titik yang berbeda dari rencana kita. (1) Skill lebih menyarankan **return type annotation** daripada `response_model`; `response_model` dipakai hanya kalau tipe yang di-return berbeda dari skema publik. (2) Skill menyarankan **SQLModel daripada SQLAlchemy**. Poin (2) tidak perlu diikuti (alasan di §2.6).
- **`zhanymkanov/fastapi-best-practices`** (18.2k★, commit terakhir 2026-05-03) memang menulis bahwa strukturnya "inspired by Netflix's Dispatch, with some minor modifications". Klaim ini benar: Dispatch memakai `src/dispatch/<domain>/{models,service,views}.py`. Tapi `Netflix/dispatch` **sudah di-archive** (read-only sejak 2025-09). Repo best-practices itu menyarankan **async** SQLAlchemy dan **nama tabel singular**; keduanya bertentangan dengan rencana dan skema kita.
- **`Kludex/fastapi-tips`** (3.6k★) memang ditulis Marcelo Trylesinski. Bio GitHub-nya: "Uvicorn & Starlette maintainer", bekerja di Pydantic. `encode/starlette` dan `encode/uvicorn` kini redirect ke `Kludex/starlette` dan `Kludex/uvicorn`. Tip #2 dan #9 mengingatkan bahwa fungsi `def` jalan di threadpool AnyIO yang **default-nya hanya 40 thread** (dikonfirmasi di docs AnyIO). Untuk rencana sync, angka ini harus diselaraskan dengan ukuran pool koneksi.
- **Alembic kita rusak dan kemungkinan besar tidak pernah jalan di prod.** `alembic history` lokal gagal dengan `KeyError: '0003_policy_assistant'`. `Dockerfile` tidak meng-install `alembic` dan tidak meng-copy folder `alembic/`. Skema prod dibuat oleh `metadata.create_all` + `_add_missing_columns` saat startup (`core/persistence.py:305-332`). `MetaData()` tidak punya `naming_convention`, dan tidak ada satu pun `ForeignKey`.
- **Prosedur yang disarankan:** buang `0001-0004`, buat **baseline** yang identik dengan skema prod (buktikan dengan `alembic stamp` + `alembic check` pada restore dump prod), lalu satu revision autogenerate untuk perubahan revamp. Perubahan PK komposit wajib ditulis tangan karena autogenerate tidak mendeteksi perubahan PRIMARY KEY. Di prod: `stamp` sekali, lalu `upgrade head` sebagai langkah pre-start.
- **`naming_convention`:** pakai pola **suffix gaya Postgres** (`%(table_name)s_pkey`, `_key`, `_fkey`, `_check`) dan **pertahankan** default SQLAlchemy `ix_%(column_0_label)s` untuk index. Dengan begitu nama constraint/index yang sudah dibuat `create_all` di prod tetap cocok dan tidak perlu di-rename.
- **Penamaan Postgres:** semua sumber sepakat soal lowercase `snake_case`, `timestamptz`, dan `text`/`varchar` tanpa panjang. Sumber **tidak sepakat** soal plural vs singular dan `id` vs `<table>_id`. Skill Supabase `supabase-postgres-best-practices` tidak beropini soal plural/singular. Yang ia tegaskan: lowercase identifiers, `timestamptz`, `text`, `bigint identity`, index di kolom FK, dan RLS untuk multi-tenant. Rekomendasi kita: pertahankan nama plural dan `id` yang sudah ada (revamp tanpa perubahan fitur).
- **Skill yang layak dipasang:** skill FastAPI resmi (via `library-skills`), `postgres-best-practices@supabase-agent-skills`, opsional `pydantic@pydantic-skills` dan `pyright-lsp` dari marketplace resmi Anthropic. Tidak ditemukan skill resmi untuk SQLAlchemy, Alembic, atau pytest.

---

## 1. Kondisi repo saat ini (dasar untuk bagian Alembic)

| Fakta | Bukti |
|---|---|
| Versi terkunci: fastapi 0.141.1, sqlalchemy 2.0.52, alembic 1.19.2 | `apps/api/uv.lock:393-394, 964-965, 10-11` |
| Rilis terbaru PyPI per 2026-10-12: fastapi 0.143.0, **sqlalchemy 2.1.4** (2026-10-07), alembic 1.20.0, pydantic 2.14.1, sqlmodel 0.0.48 | `pypi.org/pypi/<pkg>/json` |
| Pin `sqlalchemy[asyncio]>=2.0,<3`, jadi `uv lock --upgrade` berikutnya akan naik ke **2.1** | `apps/api/pyproject.toml:11` |
| `MetaData()` tanpa `naming_convention`; Core `Table(...)`, bukan ORM declarative | `core/persistence.py:52` |
| Engine async (`create_async_engine`) dengan asyncpg | `core/persistence.py:28, 298-302` |
| Startup: `create_all` + `_add_missing_columns` (ALTER TABLE ADD COLUMN untuk kolom yang belum ada) | `core/persistence.py:305-332`, `main.py:49` |
| `office_locations.id` dan `policy_sections.id` adalah PK tunggal global, padahal ID-nya `"office-default"` / `f"section-{index + 1}"` dan berulang di setiap tenant | `core/persistence.py:80-82, 277-279`; `modules/api.py:225, 1895` |
| Tidak ada `ForeignKey` maupun `UniqueConstraint` di `persistence.py` (selain `tenants.slug` di migrasi 0001) | `grep ForeignKey` → 0 hasil |
| Semua kolom waktu sudah `DateTime(timezone=True)` → `timestamptz` di PG | `core/persistence.py:60,96,102,...` |
| Nama tabel mayoritas plural (`tenants`, `employees`, `policies`, `invitations`); beberapa mass noun (`attendance`, `idempotency`, `policy_answer_audit`, `calendar_settings`) | `core/persistence.py:54-284` |
| Revision ID ditulis tangan: `"0001"`, `"0002"`, `"0003"`, `"0004_multi_work_locations"` | `alembic/versions/*.py` |
| **Chain rusak:** `0004.down_revision = "0003_policy_assistant"` padahal revision 0003 = `"0003"`. `uv run alembic history` → `KeyError: '0003_policy_assistant'` (dijalankan lokal, read-only) | `alembic/versions/0004_multi_work_locations.py:6-7` |
| `0004` tidak punya header docstring Revision/Revises dan memakai `index=True` di `op.create_table` (nama index implisit) | idem |
| `Dockerfile` hanya meng-install `fastapi uvicorn pydantic pydantic-settings argon2-cffi sqlalchemy[asyncio] asyncpg resend`. **Tidak ada `alembic` dan `psycopg`**, dan tidak meng-copy `alembic/`/`alembic.ini` | `apps/api/Dockerfile:3-4` |
| `alembic upgrade head` hanya dipanggil oleh `scripts/start-services.sh` (dev lokal) | `scripts/start-services.sh:25` |
| Belum ada `response_model` di endpoint mana pun; 49 decorator route di `api.py` | `grep response_model apps/api/src` → 0 |

**Inferensi (belum diverifikasi ke DB prod):** karena image prod tidak berisi Alembic, tabel `alembic_version` kemungkinan besar **tidak ada** di DB prod, dan skema prod = hasil `create_all` dari `metadata` versi terakhir + kolom tambahan dari `_add_missing_columns`. Cek dengan `SELECT to_regclass('public.alembic_version');` sebelum mengeksekusi §3.6.

---

## 2. Referensi best practice FastAPI

### 2.1 Skill resmi FastAPI (pertanyaan 1)

- **Lokasi:** `fastapi/.agents/skills/fastapi/SKILL.md` + `references/{dependencies,other-tools,path-operations,pydantic,responses,streaming}.md` di repo `fastapi/fastapi`. File ini ada **di dalam package Python**, jadi ikut ter-install. Terverifikasi di `apps/api/.venv/lib/python3.13/site-packages/fastapi/.agents/skills/fastapi/`.
- **Riwayat:** ditambahkan di `4fce9ce` (2026-02-25, PR #14982), direfaktor di `0af003a` (2026-06-25), terakhir diubah di `af889e4` (2026-10-08). Frontmatter: `name: fastapi`, description "FastAPI best practices and conventions…"; teks pembukanya "Official FastAPI skill to write code with best practices".
- **Docs resmi** (`docs/en/docs/tutorial/index.md:115-131`, https://fastapi.tiangolo.com/tutorial/#ai-agent-skills): "FastAPI includes an official skill for AI coding agents. It is bundled with the package…". Cara pasangnya `uvx library-skills`, dan "For Claude Code, select `.claude/skills` when asked where to install the skill."
- **`tiangolo/library-skills`** (810★, commit terakhir `114fa2c` 2026-10-08, PyPI `library-skills` 0.0.19) memindai dependency proyek, menemukan `.agents/skills` di package yang ter-install, lalu membuat **symlink relatif**. Dengan begitu skill ikut ter-update saat `fastapi` di-upgrade. README-nya mengklaim "Claude Code doesn't support the standard `.agents` directory" sehingga target `.claude/skills` harus dipilih (atau flag `--claude`). Klaim tentang Claude Code ini berasal dari README pihak ketiga dan tidak saya cek ke docs Claude Code. `full-stack-fastapi-template` sendiri memakai pola ini: `.claude/skills/fastapi` dan `.claude/skills/sqlmodel` berupa symlink.
- **Tidak ada `llms.txt`** untuk FastAPI (404, hanya fallback HTML). Docs FastAPI punya halaman internal `_llm-test.md`, tapi itu untuk pengujian terjemahan, bukan panduan agen. Untuk perbandingan: Pydantic punya `docs.pydantic.dev/latest/llms.txt` (200). SQLAlchemy dan Alembic tidak punya (404 / halaman not found).
- **Anthropic `anthropics/skills`** (180k★, `dbd4588` 2026-10-09) berisi: academy-guide, algorithmic-art, brand-guidelines, canvas-design, claude-api, discernment-nudge, doc-coauthoring, docx, frontend-design, internal-comms, mcp-builder, pdf, pptx, skill-creator, slack-gif-creator, theme-factory, web-artifacts-builder, webapp-testing, xlsx. **Tidak ada FastAPI/Python/SQL.**
- **Pydantic:** ada skill `pydantic` di `pydantic/pydantic` (`.agents/skills/pydantic/SKILL.md`, terakhir diubah `952c239` 2026-08-25), tetapi letaknya di root repo, **bukan** di dalam package. Folder `.agents` tidak ada di `site-packages/pydantic`. Skill yang sama didistribusikan lewat marketplace `pydantic/skills` (§5).

Isi skill FastAPI yang relevan untuk revamp (dikutip dari `SKILL.md` di wheel 0.141.1 / repo @ `af889e4`):

| Aturan skill | Dampak ke rencana |
|---|---|
| "Use `async` *path operations* only when fully certain that the logic called inside is compatible with async… In case of doubt, or by default, use regular `def` functions. They will be run in a threadpool… The same rules apply to dependencies." | **Mendukung** rencana sync + `def`. |
| "When possible, include a return type… Use `response_model` when the type you return is not the same as the public schema" (`references/responses.md`) | **Sedikit beda.** Rencana "`response_model` di setiap endpoint" bisa diganti return type `-> XxxRead`. Fungsinya sama (validate, filter, document, serialize), dan `response_model=` cukup dipakai kalau handler me-return objek ORM/dict (`-> Any`). |
| Pakai `Annotated[..., Depends(...)]` + alias tipe (`CurrentUserDep`, `DBDep`) | Adopsi: `SessionDep`, `TenantDep`, `ActorDep`. |
| Set `prefix`, `tags`, `dependencies` di `APIRouter(...)`, bukan di `include_router()` | Adopsi di `modules/<domain>/router.py`. |
| Dependency `yield` dengan `scope` default `"request"` (cleanup setelah response); `"function"` (cleanup sebelum response dikirim) | Relevan untuk session DB. Lihat §2.5 soal commit. |
| Jangan pakai `...` (Ellipsis) maupun `RootModel`; jangan pakai `ORJSONResponse`/`UJSONResponse` (deprecated) | Adopsi. |
| "SQLModel for working with SQL databases, prefer it over SQLAlchemy." (`references/other-tools.md`) | **Konflik.** Lihat §2.6. |
| Pakai uv, Ruff ("Consider enabling the FastAPI rules"), ty, HTTPX | Sudah memakai uv. Ruff opsional. |

### 2.2 Docs resmi FastAPI

| Halaman | Gunanya | Catatan vs rencana |
|---|---|---|
| Concurrency and async/await, https://fastapi.tiangolo.com/async/ (`docs/en/docs/async.md`) | TL;DR: library tanpa `await` → "declare your *path operation functions* as normally, with just `def`"; "(this is currently the case for most database libraries)"; "If you just don't know, use normal `def`." Fungsi `def` "is run in an external threadpool that is then awaited" (baris 418); berlaku juga untuk dependency (baris 426). | Mendukung sync. |
| Bigger Applications, https://fastapi.tiangolo.com/tutorial/bigger-applications/ | Contohnya **per tipe file** (`app/routers/items.py`, `app/dependencies.py`, `app/internal/admin.py`) dengan `APIRouter` + `include_router`. | Layout per-domain kita lebih mirip Dispatch/zhanymkanov. Mekanisme `APIRouter` sama, jadi tidak ada konflik teknis. |
| SQL (Relational) Databases, https://fastapi.tiangolo.com/tutorial/sql-databases/ | Memakai **SQLModel**. Dependency `get_session()` dengan `with Session(engine) as session: yield session`, alias `SessionDep`, **handler `def`** (`docs_src/sql_databases/tutorial001_an_py310.py`). `create_all` di startup hanya untuk tutorial; "For production you would probably use a migration script that runs before you start your app… you can use Alembic directly." | Pola session-per-request + `def` = rencana kita. `create_all` di startup memang tidak dimaksudkan untuk prod. |
| Response Model - Return Type, https://fastapi.tiangolo.com/tutorial/response-model/ | Return type vs `response_model`, dan aturan prioritas: kalau dua-duanya ada, `response_model` yang dipakai. | Lihat §2.1. |
| Testing, https://fastapi.tiangolo.com/tutorial/testing/ dan Testing Dependencies with Overrides, https://fastapi.tiangolo.com/advanced/testing-dependencies/ | `TestClient` dan `app.dependency_overrides`. | Untuk test, override `get_session` ke engine SQLite. |
| Dependencies with yield, https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-with-yield/ | Siklus hidup session. | |

### 2.3 `fastapi/full-stack-fastapi-template` (45.9k★, `7257e60` 2026-10-08, org resmi `fastapi`)

- Struktur **per tipe file**: `backend/app/{api/routes/*.py, api/deps.py, core/{config,db,security}.py, crud.py, models.py, alembic/}`.
- **SQLModel + sync**: `create_engine(..., pool_pre_ping=True)`; `get_db()` = `with Session(engine) as session: yield session`; handler `def read_items(session: SessionDep, current_user: CurrentUser, ...) -> Any` dengan `@router.get("/", response_model=ItemsPublic)`.
- **Alembic dengan ID autogenerate default** (`e2412789c190_initialize_models.py`, `1a31ce608336_...`, dst.).
- `create_all` sengaja dikomentari: "Tables should be created with Alembic migrations" (`backend/app/core/db.py`).
- `scripts/prestart.sh`: `alembic upgrade head` lalu `python app/initial_data.py` sebelum server start.
- Pelajaran untuk kita: pola **sync Session + `def` + `response_model` + `-> Any`** adalah pola resmi. Migrasi dijalankan sebagai langkah *prestart*, bukan dari dalam aplikasi.

### 2.4 `zhanymkanov/fastapi-best-practices` dan `Netflix/dispatch`

`zhanymkanov/fastapi-best-practices`: 18,167★, commit terakhir `5e00aa6` (2026-05-03), pushed 2026-08-27, tidak di-archive. README memuat "Opinionated list of best practices and conventions we use at our startups." dan pada bagian Project Structure: "The structure I found more scalable and evolvable is inspired by Netflix's [Dispatch](https://github.com/Netflix/dispatch), with some minor modifications." Repo ini juga punya `AGENTS.md` versi ringkas untuk agen.

**Verifikasi klaim Dispatch:** `Netflix/dispatch` (6,488★) **archived** (commit terakhir `dd2837e` 2025-09-03; README: "This repository will be archived and marked as read-only on September 1, 2025"). Strukturnya memang per domain: `src/dispatch/{incident,case,project,...}/` masing-masing berisi `models.py`, `service.py`, `views.py` (+`flows.py`, `enums.py`, dll.). Bedanya, zhanymkanov memakai `router.py` dan `schemas.py` terpisah, sedangkan Dispatch memakai `views.py` dan meletakkan Pydantic di `models.py`. Jadi klaim "inspired by… with minor modifications" **akurat**. Catatan lain tentang Dispatch (`src/dispatch/database/core.py`):
- memakai **sync** `sessionmaker`, dengan session diambil dari `request.state.db`;
- multi-tenancy-nya **schema-per-organization** (`schema_translate_map={None: f"dispatch_organization_{slug}"}`), bukan kolom `tenant_id`;
- `__tablename__` diturunkan dari nama class menjadi snake_case **singular**.

Yang berguna untuk kita: layout `src/<domain>/{router,schemas,models,service,dependencies,constants,exceptions}.py`; import lintas domain eksplisit (`from src.auth import service as auth_service`); `alembic.ini` `file_template = %%(year)d-%%(month).2d-%%(day).2d_%%(slug)s`; "Migrations must be static and reversible"; `naming_convention` gaya Postgres (§3.4).

**Konflik dengan rencana kita:**
1. **Async.** `AGENTS.md` repo itu menulis "SQLAlchemy 2.0 — Use the async API (`AsyncSession`, `async_sessionmaker`)", dan README punya bagian "Prefer `async` dependencies". Ini bertentangan dengan skill resmi FastAPI yang default-nya `def`. Keduanya sah. Pilihan sync kita didukung docs/skill resmi dan template resmi.
2. **Nama tabel singular** ("singular form (e.g. `post`, `post_like`)"). Skema kita plural.
3. Bagian "FastAPI response serialization" (model dibuat dua kali) **sudah usang** untuk FastAPI versi baru. Skill resmi menulis bahwa return type/response model "let Pydantic serialize the data on the Rust side". Mekanisme internal ini tidak saya ukur sendiri.

### 2.5 `Kludex/fastapi-tips`

3,627★, commit terakhir `a263df9` (2026-09-14). Penulis: Marcelo Trylesinski (`gh api users/Kludex`: bio "Software Engineer @ Pydantic… Uvicorn & Starlette maintainer… FastAPI Expert", company `@pydantic`). `encode/starlette` dan `encode/uvicorn` sekarang resolve ke `Kludex/starlette` dan `Kludex/uvicorn`; Kludex adalah kontributor #2 di keduanya (380 dan 400 commit). Klaim maintainer **terverifikasi**.

Tip yang relevan:
- **#2 "Be careful with non-async functions":** "There's a performance penalty when you use non-async functions… always prefer to use async functions… There are only 40 threads available in the thread pool." Angka 40 dikonfirmasi docs AnyIO (https://anyio.readthedocs.io/en/stable/threads.html: default limiter "40, meaning… a maximum of 40 threads"). Tip ini memberi cara menaikkannya via `anyio.to_thread.current_default_thread_limiter().total_tokens` di lifespan.
- **#9 "Your dependencies may be running on threads":** dependency `def` juga memakan slot thread.
- **#5:** `httpx.AsyncClient` daripada `TestClient`. **#10:** `pytest.mark.anyio`.

**Konflik:** Kludex pro-async; skill resmi FastAPI pro-`def` saat ragu. Untuk rencana sync, implikasi praktisnya adalah kapasitas. 40 thread berbanding pool SQLAlchemy default `pool_size=5`, `max_overflow=10` = 15 koneksi (https://docs.sqlalchemy.org/en/20/core/engines.html). Request ke-16 yang memegang session akan menunggu `pool_timeout`. Atur `pool_size`/`max_overflow` sesuai beban dan batas `max_connections` Postgres. Batas thread tidak perlu dinaikkan sebelum ada pengukuran.

### 2.6 SQLAlchemy 2.0 docs

- **Session per request** (https://docs.sqlalchemy.org/en/20/orm/session_basics.html, "When do I construct a Session…"): "create a Session at the start of a web request, call the Session.commit() method at the end of web requests that do POST, PUT, or DELETE, and then close the session at the end of web request. It's also usually a good idea to set Session.expire_on_commit to False…". Implementasinya: `sessionmaker(engine, expire_on_commit=False)` + dependency `yield`. Commit dilakukan eksplisit di service atau di dependency.
- **Global WHERE untuk multi-tenancy** (https://docs.sqlalchemy.org/en/20/orm/session_events.html#adding-global-where-on-criteria): pola resmi `@event.listens_for(Session, "do_orm_execute")` dengan guard `is_select and not is_column_load and not is_relationship_load`, lalu `statement.options(with_loader_criteria(Mixin, lambda cls: ..., include_aliases=True))`. Docs API `with_loader_criteria` (https://docs.sqlalchemy.org/en/20/orm/queryguide/api.html) menyebut "The primary purpose… is to use it in the SessionEvents.do_orm_execute() event handler to ensure that all occurrences of a particular entity are filtered in a certain way, such as filtering for access control roles". Kriteria ikut diterapkan ke subquery, join ON, dan lazy/eager relationship loads.
  - **Batasan penting (dari docs yang sama):**
    1. Lambda "is only invoked once per unique class. Custom functions should not be invoked within this lambda". Nilai tenant **harus** berupa variabel closure biasa. `track_closure_variables=True` (default) membuat variabel closure dilacak sebagai bagian cache key/bound parameter. Contoh resmi `examples/extending_query/temporal_range.py` (`rel_2_0` @ `9180a1d`) memakai pola ini dengan `range_lower/range_upper` dari closure.
    2. Hook hanya mencegat statement ORM yang lewat `Session.execute()`. **INSERT tidak difilter.** `tenant_id` pada objek baru harus di-set sendiri (mis. di service atau listener `before_flush`). Query Core/`text()` lewat `connection.execute` juga tidak tersentuh.
    3. Docs memakai guard `is_select`. Untuk ORM-enabled `update()`/`delete()` bulk, perlu menambah cabang `is_update`/`is_delete` di event yang sama. Docs `ORMExecuteState` menyediakan atribut itu; kombinasi ini tidak saya uji.
  - Simpan `tenant_id` di `session.info["tenant_id"]` saat dependency membuat session, lalu baca di listener. **Fail closed:** kalau `tenant_id` tidak ada di `info` untuk entity ber-mixin tenant, raise error, bukan diam-diam tanpa filter. Pola `session.info` ini inferensi saya; docs tidak memberi contoh tenant secara eksplisit.
- **SQLite in-memory untuk demo/test** (https://docs.sqlalchemy.org/en/20/dialects/sqlite.html, "Memory Database in Multiple Threads or Coroutines"): ":memory: database exists only within the scope of a single DBAPI connection… not suitable for use with multiple concurrent threads… unless… shared-cache". Rekomendasi docs: `create_engine("sqlite:///file::memory:?cache=shared&uri=true")` (QueuePool + `check_same_thread=False` otomatis); pakai nama unik per engine untuk isolasi (`file:db_a?mode=memory&cache=shared&uri=true`). `StaticPool` disebut "older approach… only appropriate when access to the engine is fully serialized, such as in single-threaded test suites", dengan peringatan bahwa ROLLBACK satu session ikut menggulung session lain. **Ini langsung relevan:** handler `def` kita berjalan paralel di threadpool, jadi mode demo harus memakai URI shared-cache, bukan `sqlite://` + `StaticPool`.
- **SQLModel vs SQLAlchemy (konflik dengan skill FastAPI).** Docs FastAPI dan skill resmi menyarankan SQLModel. Rencana kita memakai SQLAlchemy 2 langsung dengan `schemas.py` (Pydantic) terpisah dari `models.py` (ORM). Pemisahan ini diambil dari zhanymkanov/Dispatch. Alasan tetap memakai SQLAlchemy: kode kita sudah SQLAlchemy Core; fitur `do_orm_execute`/`with_loader_criteria` dan `naming_convention` berdokumentasi di SQLAlchemy; SQLModel masih `0.0.x` (0.0.48). Ini **pilihan, bukan pelanggaran**. Kalau skill FastAPI dipasang, tambahkan catatan di `AGENTS.md`/`apps/api/README` bahwa proyek ini memakai SQLAlchemy 2 + Pydantic terpisah, supaya agen tidak "memperbaiki" ke SQLModel.
- **Pydantic v2** (https://docs.pydantic.dev/latest/concepts/models/#arbitrary-class-instances): `model_config = ConfigDict(from_attributes=True)` / `model_validate(obj, from_attributes=True)` untuk membuat schema dari objek ORM. Contoh di docs memakai SQLAlchemy.
- **SQLAlchemy 2.1 sudah rilis** (2.1.4, 2026-10-07). Docs default `docs.sqlalchemy.org` kini 2.1. Pin `<3` kita akan menariknya. Saya tidak meriset perubahan 2.0→2.1; sarannya pin `>=2.0,<2.1` selama revamp, lalu upgrade di PR terpisah.

---

## 3. Alembic

### 3.1 Autogenerate vs tulis tangan

Docs (https://alembic.sqlalchemy.org/en/latest/autogenerate.html): autogenerate menghasilkan "candidate migrations"; "We review and modify these by hand as needed". Artinya alurnya **autogenerate lalu review manual**, bukan menulis dari nol dan bukan menerima mentah.

- **Terdeteksi:** tambah/hapus tabel; tambah/hapus kolom; perubahan nullable; "Basic changes in indexes and explicitly-named unique constraints"; "Basic changes in foreign key constraints"; perubahan tipe kolom (default aktif, `compare_type`).
- **Opsional:** CHECK constraint bernama (off by default, berbasis nama); server default (`compare_server_default=True`).
- **Tidak terdeteksi:** rename tabel dan rename kolom (muncul sebagai drop + add, harus diedit manual); "Anonymously named constraints. Give your constraints a name… See… The Importance of Naming Constraints"; Enum pada backend tanpa ENUM native.
- **Belum didukung:** "Some free-standing constraint additions and removals may not be supported, including PRIMARY KEY, EXCLUDE"; Sequence. Ini **penting untuk kita**: perubahan `office_locations`/`policy_sections` ke PK komposit harus ditulis tangan (`op.drop_constraint(..., type_="primary")` + `op.create_primary_key(...)`).
- **`alembic check`** (https://alembic.sqlalchemy.org/en/latest/autogenerate.html#running-alembic-check-to-test-for-new-upgrade-operations): menjalankan proses yang sama dengan autogenerate tanpa membuat file, dan "returns an error code plus a message if it is detected that new operations would be rendered". Bisa dipakai di CI untuk memastikan models == migrasi.

### 3.2 Revision ID dan `file_template`

- ID default dibuat oleh `alembic/util/langhelpers.py:226-227` (`sqlalchemy/alembic` @ `1bc21b8`): `def rev_id(): return uuid.uuid4().hex[-12:]`, yaitu **12 karakter hex acak**. Opsi CLI `--rev-id` ("Specify a hardcoded revision id instead of…", `alembic/config.py:743-747`) memang ada, tetapi ID tulis tangan seperti `"0004_multi_work_locations"` justru yang menyebabkan chain rusak.
- `file_template` (https://alembic.sqlalchemy.org/en/latest/tutorial.html): default `%%(rev)s_%%(slug)s`. Docs memberi contoh prefix tanggal `%%(year)d_%%(month).2d_%%(day).2d_%%(hour).2d%%(minute).2d-%%(rev)s_%%(slug)s` "so that they are listed in chronological order". Token yang tersedia: `rev`, `slug`, `epoch`, `year`, `month`, `day`, `hour`, `minute`, `second`; ada juga opsi `timezone` dan `truncate_slug_length`.
- Pilihan untuk kita: **ID acak default + nama file berprefix tanggal** (contoh docs di atas). Urutan file jadi kronologis di `ls`, dan ID tidak bisa bentrok antar-branch. Template zhanymkanov (`%%(year)d-%%(month).2d-%%(day).2d_%%(slug)s`) membuang `rev` dari nama file. Itu sah, tapi dua migrasi di hari yang sama dengan slug mirip lebih susah dibedakan.

### 3.3 Repo kita vs pedoman

| Masalah | Pedoman yang dilanggar |
|---|---|
| ID `"0001"`… ditulis tangan, `0004` merujuk ID yang tidak ada | Default `rev_id()` acak; `alembic history`/`heads` seharusnya dicek di CI |
| Migrasi tidak pernah dijalankan di prod (image tanpa Alembic) | FastAPI docs/template: migrasi sebagai skrip *prestart* |
| `create_all` + `_add_missing_columns` di startup | Cookbook Alembic hanya merestui `create_all` untuk DB **baru**, diikuti `stamp head` (§3.5). `_add_missing_columns` tidak bisa mengubah tipe, nullable, PK, atau index. |
| Tanpa `naming_convention`, `index=True` di `op.create_table` | "The Importance of Naming Constraints" |

### 3.4 `naming_convention`

Docs Alembic "The Importance of Naming Constraints" (https://alembic.sqlalchemy.org/en/latest/naming.html) menjelaskan bahwa `drop_constraint` butuh nama. Tanpa konvensi, nama ditentukan database. Contohnya Postgres memberi nama `user_order_user_account_id_fkey` ("a naming scheme used internally by Postgresql"). Dict yang disarankan docs:

```python
convention = {
  "ix": "ix_%(column_0_label)s",
  "uq": "uq_%(table_name)s_%(column_0_name)s",
  "ck": "ck_%(table_name)s_%(constraint_name)s",
  "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
  "pk": "pk_%(table_name)s"
}
metadata = MetaData(naming_convention=convention)
```

Fakta pendukung dari docs SQLAlchemy (https://docs.sqlalchemy.org/en/20/core/constraints.html#configuring-constraint-naming-conventions):
- `DEFAULT_NAMING_CONVENTION` = `{'ix': 'ix_%(column_0_label)s'}`. Itu sebabnya index lama kita bernama `ix_employees_tenant_id`.
- Konvensi `ck` dengan `%(constraint_name)s` mengharuskan CHECK diberi `name=`.
- Token multi-kolom yang tersedia: `%(column_0N_name)s` dan `%(column_0_N_name)s`.
- Nama yang terlalu panjang dipotong (lihat "Truncation of Long Names"). Batas identifier PG adalah 63 byte (PG docs 4.1.1, `NAMEDATALEN`).

Alternatif dari zhanymkanov (gaya suffix Postgres):

```python
POSTGRES_INDEXES_NAMING_CONVENTION = {
    "ix": "%(column_0_label)s_idx",
    "uq": "%(table_name)s_%(column_0_name)s_key",
    "ck": "%(table_name)s_%(constraint_name)s_check",
    "fk": "%(table_name)s_%(column_0_name)s_fkey",
    "pk": "%(table_name)s_pkey",
}
```

**Pilihan untuk Teamku:** suffix gaya Postgres untuk pk/uq/fk/ck, dan **pertahankan `ix_%(column_0_label)s`**. Alasannya, DB prod dibuat oleh `create_all` tanpa konvensi:
- PK/UNIQUE/FK anonim di sana dinamai Postgres (`tenants_pkey`, `tenants_slug_key`, …);
- index dari `index=True` dinamai SQLAlchemy `ix_<table>_<col>`.

Konvensi di bawah menghasilkan nama yang **sama persis** untuk objek yang sudah ada, sehingga baseline tidak perlu rename massal:

```python
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",                      # = default SQLAlchemy, cocok dengan index prod
    "uq": "%(table_name)s_%(column_0_N_name)s_key",      # = pola default PG
    "ck": "%(table_name)s_%(constraint_name)s_check",
    "fk": "%(table_name)s_%(column_0_N_name)s_fkey",     # = pola default PG
    "pk": "%(table_name)s_pkey",                         # = pola default PG
}
```

Catatan verifikasi: pola nama default Postgres (`<table>_pkey`, `<table>_<cols>_key`, `<table>_<cols>_fkey`) terlihat di contoh docs Alembic, tetapi tidak saya temukan sebagai spesifikasi formal di docs PostgreSQL. Sebelum baseline, cek nama aktual di prod: `SELECT conrelid::regclass, conname, contype FROM pg_constraint WHERE connamespace='public'::regnamespace;` dan `\di`.

### 3.5 `stamp`, membuang migrasi lama, dan baseline

- Cookbook "Building an Up to Date Database from Scratch" (https://alembic.sqlalchemy.org/en/latest/cookbook.html#building-an-up-to-date-database-from-scratch): `my_metadata.create_all(engine)` lalu `command.stamp(alembic_cfg, "head")`. Migrasi kemudian hanya dipakai untuk "movement between versions on out-of-date databases, not new databases". Cookbook juga menulis: "To prune old migration files, simply delete the files. Then, in the earliest, still-remaining migration file, set down_revision to None".
- `alembic stamp <rev>` hanya menulis tabel `alembic_version` tanpa menjalankan DDL (https://alembic.sqlalchemy.org/en/latest/api/commands.html).
- Cookbook yang sama menunjukkan `create_all` untuk DB **kosong** (mis. SQLite demo/test) tetap sah, **asalkan** CI membuktikan migrasi == models dengan `alembic check`. Ini sedikit melonggarkan "Alembic satu-satunya sumber skema" (lihat Rekomendasi #6).
- SQLite tidak mendukung sebagian besar `ALTER TABLE`. Kalau migrasi ingin dijalankan juga di SQLite, Alembic punya "batch mode" (`render_as_batch=True`, https://alembic.sqlalchemy.org/en/latest/batch.html). Halaman batch tidak saya baca rinci di riset ini.

### 3.6 Prosedur konkret untuk Teamku

Asumsi: DB prod tidak punya `alembic_version` (cek dulu, §1).

1. **Ambil skema prod.** `pg_dump --schema-only` dari prod (atau dari backup terbaru), lalu restore ke Postgres 16 lokal/CI sebagai `teamku_prodshape`. Simpan juga output `pg_constraint`/`pg_indexes` untuk diff.
2. **Hapus `alembic/versions/0001-0004`.** Migrasi itu tidak pernah jalan di prod, dan chain-nya rusak sehingga tidak bisa dipakai siapa pun.
3. **Set konfigurasi Alembic:** `file_template` berprefix tanggal (§3.2); di `env.py` tambahkan `compare_server_default=True`. `compare_type` sudah default.
4. **Revision 1 (baseline = skema prod hari ini).** Pasang `naming_convention` di `MetaData` tetapi **jangan ubah apa pun lainnya**. Jalankan `alembic revision --autogenerate -m "baseline"` terhadap DB **kosong**, review, lalu verifikasi kesetaraannya: pada `teamku_prodshape` jalankan `alembic stamp <baseline>` lalu `alembic check`. Hasilnya harus "No new upgrade operations detected". Kalau ada selisih (kolom hasil `_add_missing_columns` dengan default berbeda, nama index, dsb.), betulkan baseline sampai `check` bersih. Hapus `_add_missing_columns`/`create_all` dari startup setelah langkah ini lolos.
5. **Revision 2 (perubahan struktural revamp).** Pindahkan model ke `modules/<domain>/models.py` (satu `Base`/`MetaData` bersama). Ganti PK `office_locations` dan `policy_sections` menjadi komposit `(tenant_id, id)`, dan audit tabel lain yang ID-nya dibuat per tenant. Tambahkan FK `tenant_id → tenants.id` dan index FK yang memang dibutuhkan. Jalankan `alembic revision --autogenerate -m "tenant scoped keys"`. **Tulis tangan** bagian PK (autogenerate tidak mendeteksi perubahan PK, §3.1), review semuanya, lalu uji `upgrade head` → `alembic check` → `downgrade -1` → `upgrade head` di `teamku_prodshape` yang **berisi data** (restore dump penuh). Dengan begitu duplikat ID antar-tenant dan PK baru teruji pada data nyata.
6. **Pengiriman ke prod:**
   - `Dockerfile` meng-install `alembic` + `psycopg[binary]` (rencana sync; `asyncpg` bisa dibuang) dan meng-copy `alembic/` + `alembic.ini`.
   - Langkah *prestart* (pola `prestart.sh` template resmi; di Dokploy bisa berupa command container `sh -c "alembic upgrade head && uvicorn ..."`): `alembic upgrade head`.
   - **Satu kali** sebelum deploy pertama: backup DB, lalu `alembic stamp <baseline>` di prod. `upgrade head` kemudian hanya menjalankan Revision 2.
7. **Guard CI:** service Postgres 16; `alembic upgrade head` dari kosong; `alembic check`; pastikan `alembic heads` hanya mengembalikan satu head. Ini mencegah chain rusak terulang.

---

## 4. Konvensi penamaan Postgres

| Topik | PG docs / wiki | Skill Supabase `supabase-postgres-best-practices` | sqlstyle.guide (Simon Holywell) | zhanymkanov | Skema Teamku saat ini |
|---|---|---|---|---|---|
| Huruf | Unquoted identifier di-fold ke lowercase (PG16 §4.1.1). Wiki: "Don't use NamesLikeThis, use names_like_this." | `schema-lowercase-identifiers`: "Unquoted lowercase identifiers are portable and tool-friendly"; contoh `users(user_id, first_name)` | lowercase | `lower_case_snake` | sudah snake_case ✔ |
| Plural vs singular tabel | tidak beropini | **tidak beropini eksplisit**; contoh memakai plural (`users`, `orders`, `customers`, `profiles`) | "Use a collective name or, less ideally, a plural form… `staff` and `employees`" | **singular** (`post`, `post_like`) | plural ✔ (kecuali mass noun) |
| PK | wiki: "Don't use serial", pakai identity | `schema-primary-keys`: `bigint generated always as identity`; UUIDv7 untuk ID terdistribusi; hindari UUIDv4 di tabel besar | "avoid simply using `id`"; suffix `_id` | `profile_id` konsisten di semua tabel | `id` string (PK teks dari aplikasi) |
| FK | | `schema-foreign-key-indexes`: "Postgres does not automatically index foreign key columns"; nama contoh `orders_customer_id_idx`, constraint `profiles_birthchart_id_fkey` | | `<entity>_id` | `tenant_id`, `employee_id`, … ✔ tapi **tanpa FK constraint** |
| Waktu | wiki: "Don't use timestamp (without time zone)… use timestamptz" | `schema-data-types`: "Time: use timestamptz, not timestamp" | `_date` untuk tanggal | `_at` untuk datetime, `_date` untuk date | `DateTime(timezone=True)` + `_at` ✔ |
| Teks | wiki: "Don't use varchar(n) by default… varchar (without the (n)) or text" | "Strings: use text, not varchar(n) unless constraint needed" | | | `String` tanpa panjang → `VARCHAR` ✔ (setara `text`) |
| Uang | wiki: "Don't use money… Numeric, or (rarely) integer" | "Money: use numeric, not float" | | | `salary Integer` (rupiah bulat; masih wajar per wiki) |
| Multi-tenant | | `security-rls-basics`: "Enable Row Level Security for Multi-Tenant Data… Bug or bypass means all data is exposed!" | | | filter aplikasi saja |

Repo/versi: `supabase/agent-skills` (2,766★, commit terakhir `c9be0e9` 2026-10-02; folder skill terakhir diubah `1207767` 2026-07-30; frontmatter `version: "1.1.1"`, `author: supabase`), `treffynnon/sqlstyle.guide` (1,524★, `70b612f` 2026-03-17, pemilik akun: Simon Holywell), PG wiki `Don't_Do_This` (revisi 2024-11-21; halaman `action=raw` dibatasi login, jadi dibaca dari HTML).

**Di mana sumber tidak sepakat:** plural vs singular (sqlstyle plural/kolektif vs zhanymkanov singular; Supabase netral), dan `id` vs `<table>_id` (sqlstyle menghindari `id`; SQLAlchemy/FastAPI template/Supabase contoh PK memakai `id`). Karena revamp ini tanpa perubahan fitur, **rename tabel/kolom tidak sebanding risikonya**: autogenerate tidak mendeteksi rename, dan rename juga mengubah kontrak frontend lewat nama field. Pertahankan plural dan `id`, lalu tulis keputusan ini sebagai konvensi agar konsisten untuk tabel baru.

**RLS** adalah pertahanan lapis kedua yang kuat. Namun SQLite (mode demo/test) tidak punya RLS, dan RLS butuh `SET app.tenant_id` per transaksi, yang merupakan perubahan desain tersendiri. Catat sebagai kandidat ADR terpisah; jangan masuk PR revamp ini.

---

## 5. Agent skill lain yang terverifikasi

| Skill / plugin | Repo & maintainer | Status | Cara pasang di Claude Code | Relevansi |
|---|---|---|---|---|
| `fastapi` (resmi) | dibundel di package `fastapi` (`fastapi/fastapi`, tiangolo/FastAPI team) | ikut versi package terpasang | `cd apps/api && uv sync && uvx library-skills` → pilih `.claude/skills` (atau `uvx library-skills --claude`). Hasilnya symlink relatif ke `.venv/...`, yang rusak sebelum `uv sync` (README library-skills). | Tinggi |
| `library-skills` (tool skill) | `tiangolo/library-skills`, 810★, `114fa2c` 2026-10-08 | aktif | `uvx library-skills --tool-skill` | Opsional |
| `postgres-best-practices` / `supabase` | `supabase/agent-skills` (org Supabase), 2,766★, `c9be0e9` 2026-10-02 | aktif, MIT | `claude plugin marketplace add supabase/agent-skills` lalu `claude plugin install postgres-best-practices@supabase-agent-skills` | Tinggi untuk skema/index/migrasi. Plugin `supabase` **tidak** relevan (kita tidak memakai Supabase). |
| `pydantic`, `logfire` | `pydantic/skills` (org Pydantic), 140★, `585b93f` 2026-10-11; marketplace `pydantic-skills` | aktif | `claude plugin marketplace add pydantic/skills` lalu `claude plugin install pydantic@pydantic-skills` | Sedang (schemas v2). `logfire` hanya kalau memakai Logfire. Plugin `logfire` juga terdaftar di marketplace resmi Anthropic. |
| `pyright-lsp` | `anthropics/claude-plugins-official` (`./plugins/pyright-lsp`), 37.7k★, `f359d43` 2026-10-11 | aktif | `/plugin install pyright-lsp@claude-plugins-official` (nama marketplace = `claude-plugins-official`) | Sedang (type checking saat memecah 2433 baris). |
| `anthropics/skills` | Anthropic, 180k★, `dbd4588` 2026-10-09; marketplace `anthropic-agent-skills` (plugin `document-skills`, `example-skills`, `claude-api`, …) | aktif | `claude plugin marketplace add anthropics/skills` | Rendah untuk tugas ini (tidak ada skill backend/Python/SQL). |
| `mattpocock-skills` | sudah terdaftar di `.claude/settings.json` repo; juga ada di marketplace resmi | — | — | `/tdd`, `/code-review` berguna untuk PR revamp. |

**Tidak ditemukan** (pencarian `gh api search/code filename:SKILL.md` per org pada 2026-10-12): skill di org `sqlalchemy` (termasuk Alembic) dan `pytest-dev`. `astral-sh` hanya punya skill internal untuk developer ruff/uv, bukan untuk pengguna. Marketplace resmi Anthropic (315 plugin) tidak memuat plugin FastAPI, SQLAlchemy, Alembic, atau pytest.

---

## Rekomendasi untuk revamp Teamku

1. **Struktur:** pertahankan rencana per domain `modules/<domain>/{router,schemas,service,models}.py` (pola Dispatch/zhanymkanov). Tambahkan `dependencies.py` hanya bila domain itu punya dependency sendiri. Simpan `core/db.py` (engine, `SessionLocal`, `Base` + `naming_convention`, listener tenant) dan `core/deps.py` (`SessionDep`, `TenantDep`, `ActorDep` dengan `Annotated`). `APIRouter(prefix=..., tags=[...])` dideklarasikan di router domain. Import lintas domain secara eksplisit (`from movon_hr.modules.employees import service as employee_service`).
2. **Sync vs async: tetap sync**, sesuai skill dan docs resmi FastAPI serta template resmi. Konsekuensinya: (a) ganti `create_async_engine`/asyncpg dengan `create_engine` + `psycopg` (sudah ada di `pyproject.toml`, **belum** ada di `Dockerfile`); (b) jangan memanggil I/O blocking di handler `async def`, dan jadikan semua handler/dependency yang menyentuh DB `def`; (c) atur `pool_size`/`max_overflow` dengan sadar. Default 5+10 koneksi jauh di bawah 40 thread AnyIO. Mulai dengan `pool_size=10, max_overflow=10, pool_pre_ping=True` lalu ukur. Angka ini tebakan awal, bukan dari sumber.
3. **Session:** satu `Session` per request lewat dependency `yield` (`sessionmaker(engine, expire_on_commit=False)` sesuai docs SQLAlchemy). Commit eksplisit di akhir operasi tulis; rollback dan close di `finally`.
4. **Tenant filter:** `TenantMixin` (`tenant_id` NOT NULL, FK ke `tenants.id`, index). Listener `do_orm_execute` pada `sessionmaker` dengan guard resmi (`is_select and not is_column_load and not is_relationship_load`) + `with_loader_criteria(TenantMixin, lambda cls: cls.tenant_id == tenant_id, include_aliases=True)`, dengan `tenant_id` dibaca dari `session.info` sebagai variabel closure. **Fail closed** kalau `tenant_id` kosong. Dua celah perlu ditutup terpisah: **INSERT** (set `tenant_id` di service atau `before_flush`) dan bulk `update()/delete()` (tambah cabang `is_update`/`is_delete`). Tulis test isolasi: data tenant A tidak terlihat dari session tenant B, termasuk lewat relationship.
5. **Response:** pakai **return type annotation** (`-> EmployeeRead`, `-> list[EmployeeRead]`) sebagai default, dan `response_model=` hanya ketika handler me-return objek ORM/dict (`-> Any`). Ini sedikit mengubah rencana "`response_model` di setiap endpoint", tapi efeknya identik dan sesuai skill resmi. Schema yang dibangun dari ORM memakai `ConfigDict(from_attributes=True)`.
6. **SQLite demo/test:** pakai URI shared-cache `sqlite:///file:teamku_<uuid>?mode=memory&cache=shared&uri=true` (nama unik per proses/test), **bukan** `sqlite://` + `StaticPool`, karena handler `def` berjalan paralel. Skema SQLite dibuat dengan `Base.metadata.create_all` (cookbook Alembic merestui ini untuk DB baru). Postgres hanya lewat Alembic, dan CI wajib menjalankan `alembic check` agar keduanya tidak menyimpang. **Ini sedikit melonggarkan "Alembic satu-satunya sumber skema"**: Alembic menjadi satu-satunya sumber untuk Postgres. Kalau tim ingin Alembic juga di SQLite, perlu `render_as_batch=True` dan risikonya lebih tinggi.
7. **`naming_convention`:** pakai dict di §3.4 (suffix gaya PG + `ix_%(column_0_label)s`) agar cocok dengan nama yang sudah ada di prod. Verifikasi nama aktual prod sebelum baseline.
8. **Alembic:** ikuti prosedur §3.6. Buang `0001-0004`, buat baseline yang dibuktikan dengan `stamp` + `check` di dump prod, lalu satu revision struktural (PK komposit ditulis tangan). Pakai `file_template` berprefix tanggal dengan ID acak default; jangan pakai `--rev-id`. Prod: install Alembic di image, `stamp` sekali, `upgrade head` sebagai prestart. CI: `upgrade head` + `check` + satu head. Hapus `create_all`/`_add_missing_columns` dari startup prod.
9. **Pin versi:** `sqlalchemy>=2.0,<2.1` selama revamp (2.1.4 sudah rilis dan belum diriset). Samakan isi `Dockerfile` dengan `pyproject.toml`, atau lebih baik build image dari `uv.lock` agar dependency tidak didaftar di dua tempat.
10. **Penamaan:** tabel plural snake_case, PK `id`, FK `<entity>_id`, waktu `<verb>_at` `timestamptz`, tanggal `_date`, string `String()` tanpa panjang. **Tidak ada rename** di PR ini. Tambahkan FK constraint + index FK hanya untuk `tenant_id` dan relasi yang jelas; selebihnya di PR lanjutan. RLS menjadi kandidat ADR terpisah.
11. **Skill yang dipasang:** (a) skill `fastapi` via `uvx library-skills --claude` (commit symlink di `.claude/skills/fastapi`, mengikuti template resmi); (b) `postgres-best-practices@supabase-agent-skills` (tambahkan marketplace ke `extraKnownMarketplaces` di `.claude/settings.json`); (c) opsional `pydantic@pydantic-skills` dan `pyright-lsp@claude-plugins-official`. Tambahkan satu baris di `AGENTS.md`/`apps/api/README.md`: "API memakai SQLAlchemy 2 (sync) + Pydantic terpisah, bukan SQLModel", untuk menetralkan saran SQLModel di skill FastAPI. Perubahan file konfigurasi ini **tidak** dilakukan dalam riset ini.
12. **Referensi standar tim** (urutan otoritas): docs + skill resmi FastAPI → docs SQLAlchemy 2.0 (Session basics, Session events/`with_loader_criteria`, SQLite dialect, constraints/naming) → docs Alembic (autogenerate, naming, cookbook) → `full-stack-fastapi-template` (pola sync + prestart) → `zhanymkanov/fastapi-best-practices` **hanya** untuk layout per domain dan aturan migrasi (abaikan anjuran async dan nama singular) → `Kludex/fastapi-tips` untuk pitfall threadpool/ASGI → PG wiki "Don't Do This" + skill Supabase untuk tipe data dan index.

### Hal yang menyarankan perubahan dari rencana yang disepakati

- "`response_model` di setiap endpoint" → **return type** sebagai default (Rek. #5). Efeknya sama.
- "Alembic satu-satunya sumber skema" → tetap berlaku untuk Postgres, sedangkan SQLite demo/test memakai `create_all` + guard `alembic check` (Rek. #6).
- Tenant filter otomatis **tidak** menutup INSERT, bulk update/delete, maupun query Core/`text()` (Rek. #4).
- `Dockerfile` harus ikut berubah (Alembic, psycopg, folder `alembic/`), dan pin SQLAlchemy perlu dikunci `<2.1` (Rek. #2, #9).

### Belum diverifikasi

- Apakah DB prod punya tabel `alembic_version`, dan nama constraint/index aktual di prod (tidak ada akses DB dalam riset ini).
- Klaim README `library-skills` bahwa Claude Code tidak membaca `.agents/skills`. `uvx library-skills` juga tidak dijalankan.
- Perilaku `with_loader_criteria` pada bulk `update()/delete()` lewat cabang `is_update`/`is_delete` (tidak diuji).
- Perubahan SQLAlchemy 2.0 → 2.1.
- Klaim zhanymkanov/skill tentang biaya serialisasi `response_model` vs return type (tidak diukur).
