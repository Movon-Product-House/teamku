# Opsi arsitektur API Teamku (FastAPI + SQLAlchemy + PostgreSQL)

Tanggal riset: 2026-10-12. Target: `apps/api` (FastAPI, SQLAlchemy 2, Alembic, PostgreSQL 16), HRIS multi-tenant untuk UKM Indonesia, 2 engineer, satu container di Dokploy. Kode diaudit pada `main` @ `adc580a`. Catatan ini menguji **rencana sementara** revamp backend (satu PR, tanpa perubahan fitur, modular monolith `modules/<domain>/{router,schemas,service,models}.py`, SQLAlchemy sync + handler `def`, filter tenant di level session, Postgres untuk prod / SQLite in-memory untuk demo+test, `response_model` di semua endpoint) sebagai **hipotesis**, bukan keputusan.

Sumber primer: kode repo ini; Martin Fowler (bliki dan katalog PoEAA di `martinfowler.com`); Jimmy Bogard (`jimmybogard.com`); Alistair Cockburn (`alistair.cockburn.us`); Simon Brown (`simonbrown.je`); Shopify Engineering; `github.com/kgrzybek/modular-monolith-with-ddd`; *Architecture Patterns with Python* (Percival & Gregory, `cosmicpython.com`); dokumentasi SQLAlchemy 2.0, PostgreSQL 16/18, FastAPI, AnyIO, Starlette (`encode/starlette` @ `96d5023`), import-linter (`seddonym/import-linter` @ `31927f1`), APScheduler 3.x, Dokploy, testcontainers-python, SQLite; Azure Architecture Center (multitenant guide); AWS Well-Architected SaaS Lens dan AWS Prescriptive Guidance; dokumentasi Citus; Chris Richardson (`microservices.io`).

Tidak termasuk (ditulis agen lain di `2026-10-12-001-fastapi-alembic-postgres-best-practices.md`): perbandingan repo best-practice FastAPI, alur kerja Alembic, konvensi penamaan Postgres, dan agent skills.

---

## Ringkasan (jawaban dulu)

- **Gaya arsitektur:** pakai **modular monolith per domain di luar, layering tipis di dalam setiap modul** (router → service → SQLAlchemy `Session`). Tidak perlu hexagonal penuh, repository/UoW ala cosmicpython, atau event bus. Fowler sendiri menyarankan "split your top level into domain oriented modules which are internally layered" ketika layer sudah terlalu besar ([Fowler, PresentationDomainDataLayering, 2015](https://martinfowler.com/bliki/PresentationDomainDataLayering.html)). Vertical slice (Bogard) cocok sebagai cara *menulis* use case di dalam modul, tapi syaratnya tim paham refactoring, dan tidak perlu dijadikan aturan.
- **Repository/UoW: tidak perlu.** SQLAlchemy `Session` sudah merupakan Unit of Work + identity map ([SQLAlchemy, Session Basics](https://docs.sqlalchemy.org/en/20/orm/session_basics.html)). cosmicpython sendiri mencatat "Your ORM probably already has some perfectly good abstractions around atomicity" dan "You can go a long way just passing a session around" ([cosmicpython ch. 6](https://www.cosmicpython.com/book/chapter_06_uow.html)). Fungsi query per modul (`service.py`) sudah cukup.
- **Transaksi:** satu `Session` + satu transaksi per request lewat dependency `yield`. Commit dilakukan **sebelum response dikirim**, dengan `Depends(..., scope="function")` (ada sejak FastAPI 0.121; repo memakai 0.141.1) atau dengan commit eksplisit di service. Efek samping (email, Google Calendar) dijalankan **setelah commit** lewat `BackgroundTasks`. Outbox **belum** perlu, tapi ini batasan yang diterima dengan sadar (lihat §2.4).
- **Multi-tenancy:** tetap **shared tables + `tenant_id`**. Ini model yang paling murah menurut Azure dan Citus. Filter dipasang di aplikasi lewat `do_orm_execute` + `with_loader_criteria`. **Bug kritis saat ini:** PK global berupa string (`office-default`, `section-1`) bertabrakan antar-tenant. Solusinya adalah PK `uuid` global yang dibuat aplikasi, **ditambah** `tenant_id` di setiap unique constraint dan FK komposit `(tenant_id, id)` untuk relasi dalam satu tenant. **RLS ditunda.** Azure menyebut RLS "complex to design, implement, test, and maintain", sedangkan AWS menyebutnya "required" untuk pool model. Sumber primer tidak sepakat, jadi untuk MVP ini RLS layak jadi langkah kedua setelah filter ORM dan test isolasi berjalan.
- **Sync vs async:** **sync + `def` adalah pilihan yang sehat.** FastAPI: "If you just don't know, use normal `def`." Tutorial SQL resminya juga memakai `def` + `yield session`. Batasnya: threadpool AnyIO default 40 thread, dan pool SQLAlchemy default 5+10 koneksi. Gotcha utama: ContextVar yang di-set di dependency `def` **tidak** mengalir balik ke caller (AnyIO menyalin context ke thread). Karena itu tenant harus dibawa lewat objek eksplisit (`session.info`), bukan ContextVar global.
- **Masalah async yang ada sekarang:** semua 49 handler `async def` tapi memanggil I/O blocking (`urlopen` ke Google Calendar dengan timeout 15 detik di `decide`, `api.py:2307`→`api.py:717`). Ini memblokir event loop untuk semua tenant. Pindah ke `def` langsung memperbaikinya.
- **Testing:** pakai **PostgreSQL di test** (service container di CI atau testcontainers), dengan rollback per test memakai resep resmi SQLAlchemy "Joining a Session into an External Transaction". SQLite in-memory **jangan** dipakai untuk test persistence: JSONB, `DateTime(timezone=True)`, boolean, FK yang default-off, dan PK yang boleh NULL semuanya berbeda. Mode demo tanpa DB boleh tetap ada, tapi sebaiknya cukup Postgres lokal via docker compose (keputusan produk, lihat §5.3).
- **Background work:** evaluasi alert secara lazy di GET bisa diterima untuk MVP, **tapi** saat ini alert yang dibuat di GET tidak dipersist sampai ada request mutasi berikutnya (middleware hanya menyimpan untuk POST/PUT/PATCH/DELETE, `main.py:84-100`). Dengan DB per-request, masalah ini hilang sendiri. Kalau nanti butuh reminder tepat waktu, pakai **Dokploy Schedule Job** (cron → `docker exec` perintah CLI di container API). Jangan APScheduler in-process, dan jangan Celery/Redis.
- **Antar-modul:** **panggilan fungsi langsung** ke API publik modul lain (mis. `notifications.service.notify(...)`), bukan domain event in-process. Batas dijaga murah dengan **import-linter** kontrak `protected` (model/internal modul hanya boleh diimport modulnya sendiri) plus `acyclic_siblings`. Kontrak `independence` tidak cocok karena melarang import *apa pun* antar-modul, "even indirectly".
- **Rencana sementara:** sebagian besar **dipertahankan**. Yang **diubah**: SQLite untuk test diganti Postgres, dan "satu PR" dipecah, minimal persistence/ID dipisah dari restrukturisasi file. Yang **ditambah**: skema ID/constraint per tenant, test isolasi tenant, import-linter, aturan efek samping setelah commit, dan keputusan eksplisit untuk menunda RLS. Detail di bagian akhir.

---

## 0. Kondisi kode saat ini (fakta dari repo)

| Hal | Temuan | Sumber |
|---|---|---|
| Ukuran | `modules/api.py` 2433 baris, berisi semua domain + dataclass model + Pydantic schema + 49 route | `apps/api/src/movon_hr/modules/api.py` |
| State | Tiap tenant punya `DemoStore` (dict in-memory) di registry global `_stores` | `core/tenancy.py:15-37`, `api.py:256-277` |
| Tenant binding | `ContextVar` di-set oleh middleware ASGI dari cookie/header. Kode bisnis memakai `StoreFacade` (proxy atribut) | `core/tenancy.py:14-64`, `main.py:28-38` |
| Persistence | Setelah **setiap** request POST/PUT/PATCH/DELETE (status < 500), middleware memanggil `save_store` untuk **semua** tenant di registry: `DELETE` semua baris tenant di 19 tabel, lalu `INSERT` ulang. Error ditelan (`logger.exception`) | `main.py:84-100`, `core/persistence.py:618-734` |
| Startup | `create_all` + `_add_missing_columns` (ALTER TABLE otomatis), lalu memuat seluruh DB ke memori | `persistence.py:305-332`, `main.py:47-61` |
| Driver | `create_async_engine` (asyncpg) untuk app, psycopg sync untuk Alembic | `persistence.py:298-302`, `alembic/env.py`, `core/settings.py:43-53` |
| PK | `id String primary_key` global di hampir semua tabel. ID dibuat aplikasi dengan format campur: `uuid4()`, `e-{hex8}`, `location-{hex8}`, literal `office-default`, `section-{n}` | `persistence.py:57-285`, `api.py:73,225,1741,1763,1895` |
| Handler | Semuanya `async def`. Email via `run_in_threadpool`/`run_in_executor`, tetapi Google Calendar memakai `urlopen` blocking langsung di handler async | `api.py:1300-2421`, `api.py:708-719,2307`, `core/mailer.py:61-73` |
| Alert | `evaluate_attendance_alerts()` dipanggil di `GET /attendance/today` dan `GET /notifications` | `api.py:981,1988,2411` |
| Test | `TestClient(app)` tanpa `with`, jadi lifespan (dan persistence) tidak pernah jalan di test | `tests/test_*.py`, Starlette `docs/testclient.md` |
| Proses | Satu proses uvicorn tanpa `--workers` | `apps/api/Dockerfile` |
| Klaim docs | `docs/architecture.md` dan `README.md:66` menyebut Redis/Celery worker/S3. Tidak ada di dependency maupun kode | `docs/architecture.md`, `apps/api/pyproject.toml` |

**Bug yang relevan dengan keputusan arsitektur (inferensi dari membaca kode, belum direproduksi terhadap Postgres):**

1. **Tabrakan PK antar-tenant.** `PUT /settings/office` menaruh `store.office` (id default `"office-default"`) ke `office_locations` (`api.py:1763`). `office_locations.id` adalah PK global (`persistence.py:80-88`). Tenant kedua yang menyimpan pengaturan kantor akan memicu unique violation saat `INSERT`. `_policy_sections` membuat id `section-{n}` (`api.py:1895`) dengan masalah yang sama di `policy_sections`. Karena `save_store` berjalan dalam satu `engine.begin()`, seluruh simpanan tenant itu di-rollback. Karena `try` di `main.py:91-100` membungkus loop *semua* tenant, tenant berikutnya di urutan iterasi juga tidak tersimpan. Error hanya dicatat di log, response tetap 200. Akibatnya **data hilang diam-diam setelah restart**.
2. **Mutasi saat GET tidak dipersist.** Notifikasi/alert yang dibuat di GET baru tersimpan pada mutasi berikutnya (tenant mana pun). Kalau proses restart sebelum itu, alert hilang. Penanda "sudah dikirim" (`alert_receipts`) juga hilang, sehingga alert bisa muncul lagi.
3. **Tidak bisa >1 proses.** State hidup di memori proses, jadi menambah worker uvicorn atau replica akan memecah state. Ini batas keras arsitektur sekarang.

Ketiganya hilang dengan sendirinya kalau Postgres menjadi sumber kebenaran per request. Jadi menghapus `DemoStore` bukan sekadar perapian. Itu perbaikan correctness.

---

## 1. Perbandingan gaya arsitektur

### 1.1 Definisi menurut penulis aslinya

| Gaya | Definisi primer | Sumber |
|---|---|---|
| **Layered (presentation-domain-data)** | Fowler: pemisahan "presentation (UI), domain logic (aka business logic), and data access" adalah "an effective form of modularization for many applications". Kalau layer membesar, "it's usually not best to use presentation-domain-data as the higher level of modules". Sebagai gantinya, "split your top level into domain oriented modules which are internally layered". | [Fowler, 2015-08-26](https://martinfowler.com/bliki/PresentationDomainDataLayering.html) |
| **Service Layer (PoEAA)** | "Defines an application's boundary with a layer of services that establishes a set of available operations…" | [PoEAA catalog](https://martinfowler.com/eaaCatalog/serviceLayer.html) |
| **Modular monolith** | Tidak ada satu definisi kanonik. Simon Brown: "package by component", yaitu logika bisnis + persistence satu area kasar dalam satu paket di balik satu interface, dengan internal yang tidak public. Ia menulis "if people can't build monoliths properly, microservices won't help." Fowler (*MonolithFirst*): mulai dari monolith yang dirancang "carefully, paying attention to modularity", karena batas sulit ditebak di awal. Shopify: "smaller, independent units of code we called components". | [simonbrown.je/modular-monolith](https://simonbrown.je/modular-monolith), [Fowler 2015-06-03](https://martinfowler.com/bliki/MonolithFirst.html), [Shopify 2020-09-16](https://shopify.engineering/shopify-monolith) |
| **Vertical Slice Architecture** | Bogard: "built around distinct requests, encapsulating and grouping all concerns from front-end to back". Aturannya: "Minimize coupling between slices, and maximize coupling in a slice." Ia secara eksplisit menolak layer bersama seperti "repositories, services, controllers". | [Bogard, 2018-04-19](https://www.jimmybogard.com/vertical-slice-architecture/) |
| **Hexagonal / Ports & Adapters** | Cockburn: "Allow an application to equally be driven by users, programs, automated test or batch scripts, and to be developed and tested in isolation from its eventual run-time devices and databases." Port = "a purposeful conversation"; adapter mengonversi API ke perangkat. Clean Architecture (Robert C. Martin) adalah varian dengan aturan dependensi ke dalam; tidak dibaca langsung dari sumber primer dalam riset ini. | [Cockburn, 2005-09-04](https://alistair.cockburn.us/hexagonal-architecture/) |
| **Architecture Patterns with Python** | Repository = abstraksi atas persistent storage; Unit of Work = "abstraction over the idea of atomic operations"; Service Layer = tempat semua use case; plus domain events/message bus. | [cosmicpython ch. 2](https://www.cosmicpython.com/book/chapter_02_repository.html), [ch. 4](https://www.cosmicpython.com/book/chapter_04_service_layer.html), [ch. 6](https://www.cosmicpython.com/book/chapter_06_uow.html), [ch. 8](https://www.cosmicpython.com/book/chapter_08_events_and_message_bus.html) |

### 1.2 Biaya dan kecocokan untuk Teamku (2 engineer, ±49 endpoint sekarang, ±60+ setelah revamp)

| Gaya | Biaya utama | Cocok kalau… | Kecocokan Teamku |
|---|---|---|---|
| Layered global (`routers/`, `services/`, `repositories/` di root) | Satu fitur tersebar di 3–4 folder. Fowler menyebut ini bukan level atas yang baik saat aplikasi membesar | Aplikasi kecil satu domain | **Rendah.** Teamku punya ±10 domain jelas (auth, employees, attendance, leave, payroll, policies, notifications, settings, audit, trips) |
| Modular monolith (per domain, layering tipis di dalam) | Perlu menentukan API publik tiap modul dan menjaga arah import. Shopify mencatat aturan "always add some friction", dan antarmuka tanpa membereskan dependensi hanya menjadi "an added layer of indirection" | Banyak domain, satu deploy, tim kecil sampai menengah | **Tinggi.** Sejalan dengan ADR 0001 di web (feature-based `features/<domain>/`) dan daftar fitur baru di `docs/revamp/2026-09-29-role-flows.md` §8 yang masing-masing jatuh ke satu domain |
| Modular monolith "penuh" (gaya kgrzybek: skema DB per modul, komunikasi **hanya** asinkron lewat event bus + outbox/inbox, arsitektur test) | Sangat tinggi. Repo itu sendiri menyebut dirinya "not another simple application" dan bertujuan edukatif | Tim banyak, domain kompleks, rencana ekstraksi service | **Rendah.** Payroll butuh membaca employees+attendance+leave secara konsisten; memaksa asinkron justru menambah masalah konsistensi |
| Vertical slice | Duplikasi antar-slice. Bogard: "it does assume that your team understands code smells and refactoring" | Banyak use case independen, tim disiplin refactor | **Sedang**, sebagai gaya penulisan *di dalam* modul (satu fungsi per use case di `service.py`), bukan aturan folder per endpoint (60 folder terlalu ramai untuk 2 orang) |
| Hexagonal/clean penuh (port untuk DB, adapter, entity terpisah dari ORM) | Mapping ganda entity↔ORM, banyak interface satu implementasi | Banyak adapter nyata yang bergantian, atau domain yang ingin diuji tanpa DB | **Rendah untuk DB.** **Tinggi untuk integrasi eksternal**: email (`console`/`resend`) sudah port+adapter (`core/mailer.py`), dan Google Calendar + AI provider layak diperlakukan sama. Itu "port" yang memang punya ≥2 implementasi (fake untuk test + real) |
| cosmicpython (repo + UoW + service layer + message bus) | cosmicpython: "Any extra layer of indirection always increases maintenance costs"; "If your app is just a simple CRUD … wrapper around a database … you don't need a domain model or a repository"; event bus membuat "no single place in the system where you can understand how a request will be fulfilled" | Domain kaya invarian (alokasi stok), banyak orkestrasi | **Ambil sebagian:** service layer per modul (ya), repository/UoW (tidak, §2), message bus (tidak, §7) |

### 1.3 Apakah saling melengkapi?

Ya. Gaya-gaya ini menjawab pertanyaan pada level yang berbeda:

- **Level atas (antar-domain):** modular monolith menentukan apa yang boleh saling import.
- **Di dalam modul:** layering tipis (router HTTP ↔ service ↔ `Session`) atau slice per use case. Fowler menyebutnya "domain oriented modules which are internally layered", dan Bogard menulis slice yang saling lepas. Keduanya bisa digabung: setiap fungsi publik di `service.py` adalah satu slice (input → query/mutasi → output), tanpa repository bersama.
- **Di tepi sistem (I/O eksternal):** port + adapter hanya untuk email, kalender, LLM, dan geocoding (Maps URL), karena di sana fake untuk test benar-benar dibutuhkan.

**Rekomendasi:** *modular monolith per domain, layering tipis di dalam, port/adapter hanya untuk integrasi eksternal*. Alasannya: (1) konsisten dengan keputusan frontend (ADR 0001); (2) fitur baru di revamp (perjalanan dinas, handover cuti, lifecycle karyawan, daftar undangan, profil perusahaan) masing-masing punya rumah yang jelas; (3) biaya tambahan di atas FastAPI biasa hampir nol, hanya konvensi folder + satu kontrak import-linter.

---

## 2. Repository/Unit of Work, batas transaksi, dan efek samping

### 2.1 Session sudah merupakan UoW

- SQLAlchemy: Session menyimpan objek di identity map ("a data structure that maintains unique copies of each object") dan mem-flush perubahan dengan pola "unit of work" ([Session Basics](https://docs.sqlalchemy.org/en/20/orm/session_basics.html)). Definisi Fowler untuk UoW: "Maintains a list of objects affected by a business transaction and coordinates the writing out of changes…" ([PoEAA](https://martinfowler.com/eaaCatalog/unitOfWork.html)). Itulah yang dilakukan Session.
- cosmicpython mengakuinya: "SQLAlchemy already uses a UoW in the shape of the `Session` object". Kontra di tabel trade-off-nya: "Your ORM probably already has some perfectly good abstractions around atomicity" dan "You can go a long way just passing a session around" ([ch. 6](https://www.cosmicpython.com/book/chapter_06_uow.html)). Untuk Repository, kontranya: "An ORM already buys you some decoupling" dan "Any extra layer of indirection always increases maintenance costs" ([ch. 2](https://www.cosmicpython.com/book/chapter_02_repository.html)).
- Alasan cosmicpython tetap membungkus Session adalah untuk unit test domain tanpa DB (fake repository). Untuk Teamku, logika murni yang berisiko (geofence, perhitungan payroll, slot reverifikasi, aturan cuti) bisa diuji sebagai **fungsi murni tanpa Session sama sekali**. Itu lebih murah daripada fake repository. Sisanya diuji terhadap Postgres sungguhan (§5).

**Keputusan:** tidak ada kelas `Repository`/`UnitOfWork`. Fungsi service menerima `Session` dan memakai `select()` langsung. Kalau ada query yang dipakai ulang lintas use case di satu modul, jadikan fungsi privat di modul itu. Tambahkan repository hanya kalau suatu modul benar-benar butuh dua backend penyimpanan.

### 2.2 Satu transaksi per request

SQLAlchemy menyarankan lifecycle session dikelola "separate and external" dari fungsi yang mengakses data. Untuk web app, satu session per request, commit bila request menulis, dan close di akhir ([Session Basics](https://docs.sqlalchemy.org/en/20/orm/session_basics.html)). Tutorial resmi FastAPI memakai `def get_session(): with Session(engine) as session: yield session` dan path operation `def` ([FastAPI SQL databases](https://fastapi.tiangolo.com/tutorial/sql-databases/)).

**Pro:** satu request = satu batas atomik, jadi tidak ada "setengah tersimpan". Ini juga menggantikan `save_store` delete+insert dengan UPDATE/INSERT yang semestinya. Tenant context cukup di-set sekali per session.

**Kontra / gotcha:**
- **Waktu commit relatif terhadap response.** FastAPI: secara default kode setelah `yield` berjalan "after the response is sent". Akibatnya, kalau commit ditaruh di sana dan gagal (mis. unique violation), klien sudah menerima 200. FastAPI kini menyediakan `Depends(get_session, scope="function")`, yang menutup dependency "after the path operation function returns, but **before** the response is sent" ([dependencies with yield](https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-with-yield/)). Fitur ini muncul di rilis 0.121.0 (dicek lewat `gh api repos/fastapi/fastapi/releases`), dan repo terkunci di 0.141.1. **Pilih salah satu:** (a) dependency `scope="function"` yang commit saat sukses dan rollback saat exception, atau (b) service memanggil `session.commit()` eksplisit, mengikuti preferensi cosmicpython: "we tend to prefer requiring the explicit commit", "we prefer to roll back by default" ([ch. 6](https://www.cosmicpython.com/book/chapter_06_uow.html)). Opsi (a) paling sedikit kode. Opsi (b) lebih eksplisit untuk use case yang commit lalu memicu efek samping.
- **Transaksi panjang.** Jangan memanggil HTTP eksternal (Google, Resend, LLM) di dalam transaksi terbuka, karena koneksi pool tertahan sampai 15 detik.
- **Session tidak thread-safe.** "Session per thread, AsyncSession per task" ([Session Basics](https://docs.sqlalchemy.org/en/20/orm/session_basics.html)). Satu request bisa memakai lebih dari satu thread (dependency `def` dan handler `def` masing-masing dijalankan di threadpool, sebagaimana dicatat tutorial SQL FastAPI tentang `check_same_thread=False`). Itu aman selama session tidak dipakai *bersamaan*, dan FastAPI menjalankannya berurutan.

### 2.3 Di mana efek samping dijalankan

Efek samping sekarang: email (invite, reset, cuti, alert), event Google Calendar (approve/cancel cuti), notifikasi in-app (ini data di DB, jadi **bukan** efek samping eksternal dan cukup ditulis dalam transaksi yang sama), dan panggilan LLM (bagian dari response, sinkron).

Opsi:

1. **Inline sebelum commit** (pola sekarang untuk kalender). Kalau commit gagal, email/event sudah terkirim untuk data yang tidak ada. Ini **ditolak**.
2. **`BackgroundTasks` setelah commit.** FastAPI: background task berjalan "after returning a response", dan cocok untuk "small background tasks (like sending an email notification)". Untuk proses lain/berat, arahkan ke Celery ([FastAPI background tasks](https://fastapi.tiangolo.com/tutorial/background-tasks/)). Dengan commit `scope="function"`, urutannya menjadi: handler → commit → response → background task. Kelemahannya: kalau proses mati di antara commit dan task, efek samping hilang (tidak ada retry). Ini sama dengan risiko `dispatch_email` hari ini, yang sudah ditandai `ponytail:` di `core/mailer.py:66-68`.
3. **Transactional outbox.** Pesan disimpan "as part of the transaction that updates the business entities", lalu relay terpisah meneruskannya. Kontranya: relay bisa mengirim duplikat sehingga consumer harus idempotent, dan rawan lupa ([Richardson, microservices.io](https://microservices.io/patterns/data/transactional-outbox.html)). Butuh proses relay (cron/worker), retry, dan idempotency key ke Resend/Google.

**Proporsional untuk MVP:** opsi 2, ditambah **status di baris data** untuk efek samping yang hasilnya penting bagi pengguna. Pola ini sebagian sudah ada: `calendar_sync_status` di `LeaveRequest` dan `email_status` di response invite. Background task meng-update status `ok/failed` dalam session baru. Dengan begitu kegagalan terlihat dan bisa di-retry manual (tombol "kirim ulang undangan" / "sinkron ulang kalender"). Ini sudah "setengah outbox" tanpa infrastruktur baru. **Naikkan ke outbox penuh** (tabel `outbox` + Dokploy Schedule Job sebagai relay) kalau ada efek samping yang tidak boleh hilang diam-diam, mis. slip gaji yang diwajibkan sampai ke email, atau saat volume membuat retry manual tidak praktis.

### 2.4 Batasan yang diterima dengan sadar

- Email/kalender bisa hilang kalau container restart tepat setelah commit. Mitigasinya status `pending` di baris yang tidak pernah berubah, sehingga terlihat di UI/admin.
- Invite punya fallback `invite_url` di response, jadi kehilangan email tidak memblokir alur.

---

## 3. Strategi multi-tenancy

### 3.1 Empat model

| Model | Kelebihan | Risiko | Sumber |
|---|---|---|---|
| **Shared tables + `tenant_id`** (AWS: *pool*) | Azure: "highest density of tenants to infrastructure … lowest financial cost", "single database or resource to manage, back up, and secure". Citus: "much simpler to manage a single database for all tenants" | Kebocoran data kalau satu query lupa filter; noisy neighbor; restore satu tenant butuh restore ke resource terpisah lalu memilih data tenant itu | [Azure storage-data](https://learn.microsoft.com/en-us/azure/architecture/guide/multitenant/approaches/storage-data) (ms.date 2026-08-21), [Citus multi-tenant](https://docs.citusdata.com/en/stable/use_cases/multi_tenant.html), [AWS SaaS Lens](https://docs.aws.amazon.com/wellarchitected/latest/saas-lens/silo-pool-and-bridge-models.html) |
| **Shared tables + RLS** | Isolasi dipaksa di DB. AWS: RLS "removes the burden of maintaining this isolation from software developers" | Azure: "complex to design, implement, test, and maintain. Many multitenant solutions don't use row-level security because of those complexities." Pengaruh performa, perlu indeks tambahan. Owner/superuser bypass (§3.3) | [AWS Prescriptive Guidance RLS](https://docs.aws.amazon.com/prescriptive-guidance/latest/saas-multitenant-managed-postgresql/rls.html), [Azure PostgreSQL multitenant](https://learn.microsoft.com/en-us/azure/architecture/guide/multitenant/service/postgresql) |
| **Schema per tenant** | Isolasi logis, restore/ekspor per tenant lebih mudah | Migrasi Alembic harus dijalankan N kali. Azure tentang skema: "plan how to deploy schema updates across your estate" dan anti-pattern "Version dependencies". `search_path`/routing per request. Azure menyebut schema-based sharding cocok untuk "between 1 and 10,000 tenants", tapi dalam konteks elastic cluster | [Azure storage-data](https://learn.microsoft.com/en-us/azure/architecture/guide/multitenant/approaches/storage-data), [Azure PostgreSQL](https://learn.microsoft.com/en-us/azure/architecture/guide/multitenant/service/postgresql) |
| **Database per tenant** (AWS: *silo*) | Isolasi terkuat, kunci enkripsi/backup per tenant | Biaya lebih tinggi. Azure: tanpa otomasi, "the complexity of manually deploying and managing the databases becomes overwhelming" | [Azure storage-data](https://learn.microsoft.com/en-us/azure/architecture/guide/multitenant/approaches/storage-data) |

Azure juga mengingatkan: "if your solution doesn't need to scale to a large number of tenants or if you aren't concerned about performance or data isolation, then it's better to keep your solution simple". Isolasi lebih tinggi dibutuhkan kalau tenant memakai kunci enkripsi sendiri, punya kebijakan backup sendiri, atau punya syarat lokasi data. Tidak satu pun berlaku untuk UKM di MVP ini (asumsi produk, perlu konfirmasi PM).

**Keputusan:** shared tables + `tenant_id`, sama seperti hari ini, tapi dengan filter yang benar.

### 3.2 Filter tenant di level aplikasi (SQLAlchemy)

Mekanisme resmi: `with_loader_criteria()` di dalam event `SessionEvents.do_orm_execute`, "intended to add limiting criteria to a particular kind of entity in a query, globally", dengan contoh "filtering for access control roles". Kriteria otomatis ikut ke relationship loader (lazy/selectin) karena `propagate_to_loaders=True` secara default. Gunakan `include_aliases=True` agar `aliased()` ikut terfilter ([ORM query API](https://docs.sqlalchemy.org/en/20/orm/queryguide/api.html), [Session events](https://docs.sqlalchemy.org/en/20/orm/session_events.html)).

Batas dan gotcha:
- Hook hanya berlaku untuk eksekusi **ORM** (`select/update/delete` lewat `Session.execute`). Dokumentasi tidak menyatakan apa yang terjadi pada Core `Connection.execute` atau `text()`. **Tidak terverifikasi dari dokumen.** Asumsikan *tidak* terfilter, dan larang SQL mentah di modul domain (bisa dicegah dengan import-linter `forbidden` untuk `sqlalchemy.text` jika perlu, atau cukup lewat code review).
- INSERT tidak difilter. `tenant_id` harus diisi saat membuat objek, mis. dari `session.info["tenant_id"]` lewat event `before_flush`, atau secara eksplisit di service.
- Lambda di `with_loader_criteria` hanya dievaluasi "once per unique class". Nilai tenant harus berupa parameter bind (closure variable di-*track* sebagai bagian cache key secara default), bukan hasil pemanggilan fungsi di dalam lambda.
- Ada jalur yang **sengaja** lintas tenant: login (mencari email di semua tenant), preview/accept invite by token, reset password, dan callback OAuth Google (state → tenant). Jalur ini butuh session "tanpa tenant" yang eksplisit (mis. `session.info["tenant_id"] = None` hanya di modul auth) dan harus dites.
- **Tenant disimpan di `session.info`, bukan ContextVar global.** Lihat §4.3: ContextVar yang di-set di dependency `def` tidak terlihat di thread lain.

### 3.3 Apakah RLS layak sebagai defense-in-depth?

Fakta PostgreSQL ([docs 16, ddl-rowsecurity](https://www.postgresql.org/docs/16/ddl-rowsecurity.html)):
- "Superusers and roles with the BYPASSRLS attribute always bypass the row security system". "Table owners normally bypass row security as well", kecuali dengan `FORCE ROW LEVEL SECURITY`. Jadi app harus konek dengan **role non-owner** yang terpisah dari role migrasi Alembic. Ini perubahan operasional di Dokploy (dua user DB).
- Tanpa policy, berlaku default-deny.
- "Referential integrity checks, such as unique or primary key constraints and foreign key references, always bypass row security", sehingga ada potensi "covert channel". Contoh nyatanya justru bug kita: PK global `office-default` membocorkan keberadaan baris tenant lain lewat unique violation.
- Tenant context di-set per transaksi dengan `set_config('app.current_tenant', :tid, true)`. Argumen `is_local=true` berarti "the new value will only apply during the current transaction" ([functions-admin](https://www.postgresql.org/docs/16/functions-admin.html)), dan nilainya dibaca di policy dengan `current_setting(...)`. Ini pola yang dicontohkan AWS. Scope transaksi (bukan session) penting supaya koneksi yang kembali ke pool tidak membawa tenant lama.

Sumber primer **tidak sepakat**: AWS menyebut RLS "required to maintain tenant data isolation in a pooled model with PostgreSQL", sedangkan Azure menyebutnya opsional dan sering dihindari karena kompleks.

**Penilaian untuk Teamku:** data HR (gaji, lokasi GPS) sensitif, jadi defense-in-depth punya nilai nyata. Tapi biaya awalnya (role terpisah, policy di setiap tabel lewat migrasi, test bahwa policy aktif, jalur lintas-tenant untuk auth) sebaiknya tidak masuk PR restrukturisasi. **Urutan yang disarankan:** (1) filter ORM + `tenant_id` di unique/FK + **test isolasi otomatis** (dua tenant, setiap endpoint list/get dipanggil dengan tenant lain, harus 404/kosong); (2) RLS sebagai tiket terpisah setelah semua tabel berpindah ke ORM. Desain di §3.2 (tenant di `session.info`, satu titik pembukaan transaksi) membuat langkah 2 hanya menambah satu `set_config` di event `after_begin`.

### 3.4 Composite PK `(tenant_id, id)` vs ID global

- Citus mewajibkan PK/FK menyertakan kolom distribusi (`company_id`) dan menyebut yang sebenarnya dibutuhkan adalah "to ensure uniqueness on a per-tenant basis". Contohnya `primary key (tenant_id, event_id)` ([Citus data modeling](https://docs.citusdata.com/en/stable/sharding/data_modeling.html), [Citus multi-tenant](https://docs.citusdata.com/en/stable/use_cases/multi_tenant.html)). Itu syarat sharding Citus, bukan syarat PostgreSQL biasa.
- PostgreSQL 16 punya `gen_random_uuid()`. `uuidv7()` (time-ordered) ada di dokumentasi PostgreSQL 18 ([functions-uuid](https://www.postgresql.org/docs/18/functions-uuid.html)), tidak di 16. Di Python 3.12, `uuid.uuid7` tidak tersedia (stdlib baru menambahkannya di 3.14; ini dari pengetahuan umum, tidak diverifikasi dalam riset ini).

**Rekomendasi:**
- **PK = `id uuid` global** yang dibuat aplikasi (`uuid4()`; bisa juga `gen_random_uuid()` sebagai server default). Ini langsung membunuh kelas bug `office-default`/`section-1`, membuat URL/ID di frontend tetap satu kolom, dan tidak menyulitkan relationship ORM.
- **`tenant_id NOT NULL` + indeks** di setiap tabel tenant. **Setiap unique bisnis menyertakan `tenant_id`**, misalnya `UNIQUE (tenant_id, email)` di employees. Pengecualian: kalau email login memang global unik lintas perusahaan, itu harus keputusan eksplisit, karena login hari ini mencari email lintas tenant.
- **FK komposit opsional** untuk relasi penting: `UNIQUE (tenant_id, id)` di parent dan `FOREIGN KEY (tenant_id, parent_id) REFERENCES parent (tenant_id, id)` di child. DB lalu menolak child yang menunjuk parent milik tenant lain. Ini proteksi murah tanpa RLS. Terapkan minimal di employees ← attendance/leave/payroll items/sessions.
- ID tampilan yang manusiawi (mis. "section-1") cukup menjadi kolom `position`/`slug`, bukan PK.
- Composite PK penuh `(tenant_id, id)` **tidak** disarankan. Manfaatnya (siap Citus) spekulatif, dan biayanya muncul di setiap relationship ORM dan setiap URL.

---

## 4. Sync vs async

### 4.1 Apa kata sumber

- FastAPI: library yang "doesn't have support for using `await` … declare your path operation functions … with just `def`". "If you just don't know, use normal `def`." Fungsi `def` "run in an external threadpool that is then awaited", dan hal yang sama berlaku untuk dependency `def` ([FastAPI async](https://fastapi.tiangolo.com/async/)).
- Starlette `run_in_threadpool` = `anyio.to_thread.run_sync` (`encode/starlette@96d5023:starlette/concurrency.py`). AnyIO: "The default AnyIO worker thread limiter has a value of 40", bisa diubah lewat `to_thread.current_default_thread_limiter().total_tokens` ([AnyIO threads](https://anyio.readthedocs.io/en/stable/threads.html)).
- SQLAlchemy asyncio: lazy loading "will fail under asyncio as no implicit IO is allowed", sehingga perlu `selectinload`/`AsyncAttrs`, `expire_on_commit=False`. `AsyncSession` "is not safe for use in multiple, concurrent tasks", dan `AsyncEngine` tidak boleh dipakai bersama lintas event loop ([SQLAlchemy asyncio](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)). Dokumen ini **tidak** mengklaim async lebih cepat.
- Pool default `QueuePool`: `pool_size=5`, `max_overflow=10`, timeout 30 detik ([SQLAlchemy pooling](https://docs.sqlalchemy.org/en/20/core/pooling.html)).

### 4.2 Penilaian

Beban HRIS UKM: puncak saat clock-in pagi (semua karyawan semua tenant dalam ±30 menit), selebihnya ringan. Kebanyakan request berupa satu sampai beberapa query pendek. Dengan `def`:
- Konkurensi efektif = min(40 thread, 15 koneksi pool). Request ke-16 yang butuh DB menunggu sampai 30 detik. **Selaraskan keduanya:** misalnya `pool_size=10, max_overflow=10` dan biarkan 40 thread. Pastikan `max_connections` Postgres (default 100, dari pengetahuan umum, tidak diverifikasi di sini) cukup untuk app + Alembic + backup.
- Panggilan eksternal yang lambat (Google 15 detik, Resend 10 detik, LLM) memakan thread, bukan event loop. Ini sudah jauh lebih baik daripada sekarang, di mana `urlopen` di handler `async def` membekukan *seluruh* server.
- Async baru layak kalau ada ribuan koneksi idle/long-poll/websocket. Itu tidak ada di scope revamp.

**Kesimpulan:** sync + `def` sehat dan sesuai rekomendasi default FastAPI. Bonusnya: driver cukup satu (psycopg 3 sync, yang sudah dipakai Alembic), sehingga `asyncpg` dan `sqlalchemy[asyncio]` bisa dibuang dari dependency dan Dockerfile.

### 4.3 Gotcha

1. **ContextVar di threadpool.** AnyIO: "the current context is copied to the worker thread", tapi perubahan di thread tidak mengalir balik ke task pemanggil ([AnyIO threads](https://anyio.readthedocs.io/en/stable/threads.html)). Akibatnya, kalau tenant di-bind di dependency `def` dengan `ContextVar.set`, handler `def` (thread lain, salinan context dari task) **tidak** melihatnya. Middleware ASGI hari ini aman karena berjalan di task sebelum handler. Pola yang lebih kokoh adalah dependency mengembalikan objek (`TenantSession`/`CurrentUser`) dan tenant disimpan di `session.info`. Jangan pakai state global.
2. **Handler `async def` yang tersisa** tidak boleh memanggil fungsi blocking. Aturan sederhananya: semua handler `def`, kecuali yang benar-benar `await`.
3. **TestClient** menjalankan app di thread latar lewat `anyio.start_blocking_portal()`. Lifespan hanya jalan kalau `TestClient` dipakai sebagai context manager (Starlette `docs/testclient.md` @ `96d5023`). Test sekarang memakai `TestClient(app)` tanpa `with`, jadi lifespan tidak pernah jalan. Engine async yang dibuat di loop lain bisa bermasalah (peringatan multi event loop SQLAlchemy). Engine sync menghindari kelas masalah ini.
4. **`BackgroundTasks` `def`** juga berjalan di threadpool. Task harus membuka session sendiri, karena session request sudah ditutup.

---

## 5. Strategi testing

### 5.1 Risiko SQLite sebagai pengganti Postgres

Dari dokumentasi SQLite sendiri ([quirks](https://www.sqlite.org/quirks.html)): pengembang yang mulai dengan SQLite lalu pindah ke PostgreSQL bisa gagal karena SQLite "very forgiving of the type of data". SQLite tidak punya BOOLEAN ("represented as integers 1 and 0") maupun DATETIME (disimpan sebagai TEXT/INTEGER/REAL), FK "turned off by default", dan PK bisa berisi NULL. SQLAlchemy: tanggal SQLite disimpan sebagai string ISO, contoh formatnya tanpa offset zona waktu, dan FK baru aktif dengan `PRAGMA foreign_keys = ON` di setiap koneksi. Database `:memory:` hanya hidup dalam satu koneksi DBAPI, sehingga butuh `StaticPool` yang "does not support any form of concurrency" ([SQLAlchemy SQLite dialect](https://docs.sqlalchemy.org/en/20/dialects/sqlite.html)).

Dampak konkret untuk Teamku:
- `JSONB` (`policy_answer_audit.cited_sections`) adalah tipe dialek Postgres (`persistence.py:27,284`). Di SQLite perlu `JSON().with_variant(...)`, dan operator JSONB tidak tersedia.
- Logika absensi bergantung pada zona waktu (`JAKARTA`, `DateTime(timezone=True)`). Penanganan aware/naive datetime di SQLite tidak didokumentasikan untuk dipertahankan, sehingga perbandingan waktu bisa lolos di test tapi gagal di prod. **Tidak diverifikasi secara eksperimen** dalam riset ini.
- Bug yang paling penting dicegah (unique per tenant, FK komposit, konflik PK) justru bergantung pada constraint, dan di SQLite constraint lebih longgar.
- Test isolasi tenant dan (nanti) RLS **hanya** bermakna di Postgres.

### 5.2 Rekomendasi

- **Test terhadap PostgreSQL 16 sungguhan.** Di CI GitHub Actions, pakai `services: postgres:16`. Secara lokal, pakai docker compose yang sama atau testcontainers (`PostgresContainer("postgres:16")`, [testcontainers-python](https://testcontainers-python.readthedocs.io/en/latest/modules/postgres/README.html)). Cukup **satu** mekanisme. Service container CI + `docker compose up db` lokal tidak menambah dependency Python, jadi lebih ponytail daripada testcontainers.
- **Skema dibuat sekali per sesi test** dengan `alembic upgrade head`. Cara ini sekaligus menguji migrasi, dan konsisten dengan ide menghapus `create_all` + `_add_missing_columns` di runtime.
- **Rollback per test** dengan resep resmi "Joining a Session into an External Transaction": `connection = engine.connect()`, `trans = connection.begin()`, `Session(bind=connection, join_transaction_mode="create_savepoint")`. Commit di kode aplikasi menjadi SAVEPOINT, lalu `trans.rollback()` di teardown membatalkan semuanya ([SQLAlchemy session_transaction](https://docs.sqlalchemy.org/en/20/orm/session_transaction.html)). Session itu disuntikkan ke app lewat `app.dependency_overrides[get_session]`.
- Catatan: kalau commit dilakukan di dependency `scope="function"`, resep ini tetap berlaku karena commit hanya melepas SAVEPOINT. Background task yang membuka session baru **tidak** ikut transaksi test. Di test, jalankan task terhadap session yang sama atau abaikan task tersebut (mailer console).
- **Logika murni** (geofence, payroll, slot reverify) diuji tanpa DB sebagai fungsi biasa, sehingga cepat dan tidak perlu fixture.

### 5.3 Mode demo tanpa DB

Rencana sementara ingin SQLite in-memory untuk demo. Ada dua opsi:
1. **Hapus mode tanpa DB.** Demo = Postgres (docker compose lokal, atau satu DB demo di Dokploy) + perintah seed. Satu jalur kode, satu dialek.
2. Pertahankan SQLite untuk demo saja, tapi bayar biaya `with_variant` untuk JSONB dan perilaku datetime/boolean yang berbeda di jalur yang tidak dites.

Opsi 1 lebih murah dalam jangka panjang. Satu-satunya biayanya: developer frontend butuh Docker untuk menjalankan API lokal. **Perlu keputusan tim.** Riset ini tidak tahu apakah ada demo publik yang bergantung pada mode tanpa DB.

---

## 6. Background work (alert absensi)

**Sekarang:** `evaluate_attendance_alerts()` dijalankan di GET `/attendance/today` dan `/notifications` (`api.py:1988,2411`). Fungsi itu memeriksa semua karyawan aktif tenant, lalu meng-emit `missed_clock_in`/reminder dan mengekspirasi slot reverifikasi.

**Penilaian:**
- Untuk MVP, **lazy evaluation bisa diterima** selama efeknya idempotent (sudah ada `alert_receipts` per `(employee, kind, local_date)`) dan ditulis dalam transaksi request. Setelah pindah ke DB per request, masalah "alert dari GET tidak dipersist" (§0) hilang. Tambahkan `UNIQUE (tenant_id, employee_id, kind, local_date)` di `alert_receipts` supaya dua request bersamaan tidak membuat alert ganda.
- Kekurangannya bersifat produk: alert hanya muncul kalau ada yang membuka aplikasi, dan email reminder tidak terkirim ke karyawan yang tidak membuka aplikasi. Kalau PM butuh reminder tepat waktu, barulah scheduler dibutuhkan.

**Kalau scheduler dibutuhkan, urutan termurah:**
1. **Dokploy Schedule Job** tipe *Application*: menjalankan perintah "inside specific application containers" via cron ([Dokploy schedule jobs](https://docs.dokploy.com/docs/core/schedule-jobs)), mis. `python -m movon_hr.jobs.attendance_alerts` tiap 5 menit. Tidak perlu container atau dependency baru. Syaratnya: container API harus running, dan job ini harus terlihat di repo (dokumentasikan di runbook).
2. **APScheduler in-process: hindari.** FAQ resminya, untuk berbagi job store antar proses: "Short answer: You can't". Itu "will lead to incorrect scheduler behavior" ([APScheduler 3.x FAQ](https://apscheduler.readthedocs.io/en/3.x/faq.html)). Begitu ada >1 worker/replica, job akan jalan ganda.
3. **Celery + Redis: tidak.** FastAPI hanya menyarankannya untuk komputasi berat lintas proses/server. Klaim Redis/Celery di `docs/architecture.md` dan `README.md:66` sebaiknya dikoreksi supaya sesuai kenyataan.

---

## 7. Komunikasi antar-modul dan penegakan batas

### 7.1 Panggilan langsung vs domain event in-process

- kgrzybek melarang panggilan langsung: "Modules communicate each other only asynchronously using Events Bus - direct method calls are not allowed", dengan outbox/inbox untuk reliabilitas ([repo](https://github.com/kgrzybek/modular-monolith-with-ddd)). Itu desain untuk tim besar yang menyiapkan ekstraksi service.
- cosmicpython mencatat biaya message bus in-process: "It's not obvious when we call `commit` that we're also going to go and send email", "there is no single place in the system where you can understand how a request will be fulfilled", plus risiko "circular dependencies between your event handlers, and infinite loops" ([ch. 8](https://www.cosmicpython.com/book/chapter_08_events_and_message_bus.html)).
- Untuk Teamku, alur lintas modulnya sedikit dan sinkron. Contohnya: leave approve → notifications + calendar + email; payroll → membaca employees/attendance/leave; attendance → membaca leave (`has_approved_leave`); trips → leave/attendance.

**Keputusan:** **panggilan fungsi langsung ke API publik modul lain**, dalam session/transaksi yang sama (session dioper sebagai argumen). Event in-process baru dipertimbangkan kalau satu aksi memicu ≥3 konsumen yang terus bertambah. Itu belum terjadi.

### 7.2 Menjaga batas murah dengan import-linter

Kontrak yang tersedia: `forbidden`, `protected` ("Prevent modules from being directly imported, except by modules in an allow-list"), `layers`, `independence` ("Prevent a set of modules depending on each other", termasuk impor tidak langsung), dan `acyclic_siblings` ([import-linter contract types](https://import-linter.readthedocs.io/en/stable/contract_types/), sumber `seddonym/import-linter@31927f1:docs/contract_types/`).

- **`independence` tidak cocok**, karena panggilan langsung leave → notifications akan langsung melanggarnya.
- **Yang cocok:**
  1. `protected`: `movon_hr.modules.<x>.models` (dan internal lain) hanya boleh diimport oleh `movon_hr.modules.<x>`. Contoh resmi memakai wildcard `mypackage.**.models`. Karena allow-list harus per modul, praktisnya satu kontrak per modul, ±10 blok TOML. Inilah padanan "package-private" Simon Brown di Python.
  2. `acyclic_siblings` pada `movon_hr.modules` agar tidak ada siklus antar-modul (leave ↔ attendance adalah kandidat siklus yang nyata).
  3. `layers` dengan `containers = ["movon_hr.modules.*"]` dan layer `router` > `service` > `models`, supaya service tidak mengimport FastAPI router dan sebaliknya.
  4. `forbidden`: `movon_hr.core` tidak boleh mengimport `movon_hr.modules`. Hari ini `core/tenancy.py:28` dan `core/persistence.py:33` mengimport `modules.api`, yang berarti dependensinya terbalik.
- Jalankan `lint-imports` di CI bersama ruff/pytest. Pelajaran Shopify: mulai dengan aturan sedikit, karena aturan "always add some friction". Tegakkan di CI, bukan lewat disiplin ([Shopify](https://shopify.engineering/shopify-monolith)).

Nilai tambahnya untuk agen AI dan untuk 2 engineer yang bekerja paralel cukup jelas: pelanggaran batas gagal di CI, bukan di code review.

---

## Rekomendasi arsitektur untuk Teamku

1. **Modular monolith per domain**: `modules/<domain>/` dengan `router.py` (HTTP saja: parsing, auth dependency, `response_model`), `schemas.py` (Pydantic in/out), `service.py` (use case, satu fungsi per aksi, menerima `Session` + konteks user), dan `models.py` (SQLAlchemy ORM). File tambahan hanya kalau dibutuhkan, mis. `rules.py` untuk logika murni seperti geofence/payroll. Domain awal: `auth`, `employees`, `attendance`, `leave`, `payroll`, `policies` (+ asisten AI), `notifications`, `settings` (kantor/lokasi/kalender/profil perusahaan), `audit`. Fitur revamp yang baru (`trips`, `invites` list, lifecycle karyawan, handover cuti) masuk ke modul yang sesuai atau ke modul baru.
2. **Tanpa Repository/UoW.** `Session` adalah UoW. Satu session per request lewat dependency `yield` dengan **`scope="function"`** (commit sebelum response, rollback saat exception).
3. **`DemoStore`, `StoreFacade`, `save_store`, dan middleware `persist_after_mutation` dihapus.** Postgres menjadi sumber kebenaran per request. Ini memperbaiki data hilang (§0) dan membuka jalan ke >1 worker.
4. **Sync SQLAlchemy + handler `def`**, driver psycopg 3. Buang `asyncpg`/`sqlalchemy[asyncio]`. Selaraskan `pool_size + max_overflow` dengan threadpool (mis. 10+10).
5. **Tenancy: shared tables + `tenant_id`**, filter via `do_orm_execute` + `with_loader_criteria(include_aliases=True)`, dengan tenant di `session.info` (bukan ContextVar). `tenant_id` diisi otomatis saat flush. Jalur lintas-tenant (login, invite token, reset, OAuth callback) eksplisit dan dites.
6. **ID: `uuid` global** untuk semua PK baru. `UNIQUE (tenant_id, …)` untuk semua keunikan bisnis. FK komposit `(tenant_id, x_id)` untuk relasi ke `employees`. Hapus literal ID (`office-default`, `section-n`).
7. **RLS ditunda** ke tiket terpisah setelah semua tabel di ORM. Desain session sudah disiapkan untuk menambah `set_config('app.current_tenant', …, true)` di `after_begin` + role DB non-owner.
8. **Efek samping eksternal setelah commit** via `BackgroundTasks`, dengan kolom status (`email_status`, `calendar_sync_status`) agar kegagalan terlihat dan bisa di-retry manual. Integrasi eksternal (mail, Google Calendar, AI, geocoding) memakai port + adapter fake/real seperti `core/mailer.py`. Outbox ditunda.
9. **Test di PostgreSQL 16** (CI service container + compose lokal), skema via `alembic upgrade head`, rollback per test dengan `join_transaction_mode="create_savepoint"`, ditambah **satu suite isolasi tenant** (dua tenant, semua endpoint baca). Logika murni dites tanpa DB.
10. **Alert absensi tetap lazy** (idempotent + unique constraint). Kalau reminder tepat waktu dibutuhkan, tambahkan Dokploy Schedule Job yang menjalankan perintah CLI. Tidak ada APScheduler/Celery/Redis. Koreksi `docs/architecture.md`.
11. **Batas modul dijaga import-linter** (`protected` per modul, `acyclic_siblings`, `layers` dengan containers, `forbidden` core→modules) di CI. Antar-modul memakai panggilan fungsi langsung, tanpa event bus.
12. **`create_all` + `_add_missing_columns` di startup dihapus.** Alembic satu-satunya pemilik skema, dijalankan sebelum release (sesuai `docs/runbook.md`). Detail Alembic ada di catatan 001.
13. **Catat sebagai ADR backend** (`docs/adr/0002-…`) agar sejajar dengan ADR 0001 web.

### Perbandingan dengan rencana sementara

| Item rencana sementara | Putusan | Alasan |
|---|---|---|
| Revamp dalam **satu PR** | **Ubah** | Rencana ini mengganti model persistence (in-memory → per request), skema ID/constraint (migrasi data dari ID string), driver (async → sync), dan struktur file sekaligus. Satu PR membuat review dan bisect hampir mustahil untuk 2 orang. Usulan minimal: PR-1 struktur modul + `def` + `response_model` (perilaku tetap, store masih in-memory); PR-2 ORM + session per request + migrasi ID/constraint + test Postgres; PR-3 import-linter + koreksi docs. Kalau tim tetap ingin satu PR, setidaknya commit dipisah per langkah itu. |
| **Tanpa perubahan fitur** | **Pertahankan, dengan catatan** | Kontrak API (path, payload) tetap. Tapi perilaku yang **memang bug** akan berubah: data tenant kedua yang tadinya hilang setelah restart, alert dari GET yang tidak tersimpan, dan respons 200 saat penyimpanan gagal. Format ID juga berubah (uuid), sehingga frontend yang menyimpan/membandingkan ID literal (mis. `office-default`) perlu dicek. |
| Modular monolith `modules/<domain>/{router,schemas,service,models}.py` | **Pertahankan** | Sesuai Fowler ("domain oriented modules which are internally layered"), Simon Brown (package by component), dan ADR 0001 web. **Tambah:** `rules.py` opsional untuk logika murni, adapter eksternal di `core/` atau `integrations/`, dan larangan `core → modules`. |
| Sync SQLAlchemy + handler `def` | **Pertahankan** | Sesuai rekomendasi default FastAPI dan tutorial SQL resminya. Memperbaiki event loop yang terblokir `urlopen`. **Tambah:** buang asyncpg, selaraskan pool dengan threadpool 40, dan jangan bind tenant lewat ContextVar di dependency `def`. |
| Filter tenant di level session | **Pertahankan + perjelas** | Pakai `do_orm_execute` + `with_loader_criteria`, tenant di `session.info`, `tenant_id` diisi saat flush. **Tambah:** jalur lintas-tenant eksplisit, larangan SQL mentah di modul domain (hook hanya untuk ORM), test isolasi tenant, `tenant_id` di setiap unique, FK komposit ke employees, PK uuid. RLS: tunda, catat sebagai keputusan. |
| Postgres prod / **SQLite in-memory untuk demo + test** | **Ubah** | Test harus di Postgres: JSONB, timezone, boolean, FK/constraint, dan isolasi tenant berbeda di SQLite (SQLite quirks, SQLAlchemy SQLite dialect). Demo: sebaiknya Postgres juga (compose + seed). SQLite untuk demo saja hanya kalau ada kebutuhan nyata, karena itu jalur yang tidak dites. |
| `response_model` di semua endpoint | **Pertahankan** | Membuka generate type dari OpenAPI yang ditolak ADR 0001 karena skema respons kosong. Penyaringan field sensitif yang sekarang dilakukan manual (`public_employee` + `SENSITIVE_EMPLOYEE_FIELDS`, `api.py:546-552`; handler lain langsung `asdict()`, mis. `api.py:2308`) menjadi deklaratif, sehingga field baru tidak bocor tanpa sengaja. |
| (tidak ada di rencana) Batas transaksi | **Tambah** | Dependency `yield` dengan `scope="function"` supaya commit terjadi sebelum response. Efek samping eksternal setelah commit via `BackgroundTasks` + kolom status. |
| (tidak ada di rencana) Penegakan batas modul | **Tambah** | import-linter di CI (`protected`, `acyclic_siblings`, `layers`, `forbidden`). Murah, dan mencegah modul kembali menjadi satu file besar. |
| (tidak ada di rencana) Background job | **Tambah sebagai keputusan "belum"** | Lazy + idempotent untuk sekarang. Dokploy Schedule Job kalau reminder tepat waktu dibutuhkan. Tidak ada Celery/Redis. |

---

## Yang tidak bisa diverifikasi / batasan riset

- Perilaku `do_orm_execute`/`with_loader_criteria` terhadap Core `Connection.execute` dan `text()` tidak dinyatakan di dokumentasi yang dibaca. Asumsinya tidak terfilter.
- Bug tabrakan PK antar-tenant dan "data tenant berikutnya ikut tidak tersimpan" adalah **inferensi dari membaca kode** (`api.py:1763,1895`, `persistence.py:80-88,618-734`, `main.py:91-100`), belum direproduksi terhadap Postgres. Untuk memastikan: buat 2 tenant, `PUT /settings/office` dari keduanya, restart, lalu cek data.
- Perilaku penyimpanan datetime timezone-aware di SQLite lewat SQLAlchemy tidak didokumentasikan secara eksplisit di halaman dialek yang dibaca.
- `uuid.uuid7` di Python 3.14 dan `uuidv7()` sebagai fitur baru PostgreSQL 18 berasal dari pengetahuan umum. Halaman docs PG18 menampilkan fungsinya tapi tidak menyebut versi rilisnya.
- Default `max_connections` PostgreSQL (100) dari pengetahuan umum, tidak dicek ulang.
- Artikel Clean Architecture (Robert C. Martin) tidak dibaca langsung.
- Halaman `simonbrown.je` yang dibaca adalah ringkasan artikel modular monolith/package by component di situsnya. Kutipan "if people can't build monoliths properly, microservices won't help" berasal dari tweet 2015 yang di-embed di halaman tersebut.
- Kebutuhan bisnis yang menentukan beberapa putusan (apakah email login global unik lintas perusahaan, apakah demo publik bergantung pada mode tanpa DB, apakah reminder harus tepat waktu) adalah keputusan produk, bukan temuan riset.
