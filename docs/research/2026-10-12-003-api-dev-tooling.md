# Dev tooling untuk Teamku API (lint, type check, hook, CI)

Tanggal riset: 2026-10-12. Target: `apps/api` (FastAPI + SQLAlchemy 2 Core + Alembic + Pydantic v2, dikelola `uv`) sebagai fondasi PR revamp arsitektur API. Kode diukur pada `main` = `origin/main` @ `adc580a`. Semua tool dijalankan read-only di WSL2 (uv 0.12.23, venv lokal Python 3.13.12). Tidak ada file repo yang diubah. Untuk uji migrasi dipakai container `postgres:17` sementara dan salinan folder `alembic/` di `/tmp`.

Sumber primer: kode repo ini; dokumentasi Ruff (`docs.astral.sh/ruff`) dan release notes `astral-sh/ruff` 0.16.0 dan 0.17.0; README dan release `astral-sh/ty`, `facebook/pyrefly`, `python/mypy`, `microsoft/pyright`, `DetachHead/basedpyright`, `j178/prek` (termasuk `docs/compatibility.md`, `docs/monorepos.md`, `docs/local-hooks.md`), `pre-commit/pre-commit`, `evilmartians/lefthook`, `astral-sh/setup-uv`, `astral-sh/uv`; dokumentasi `pyrefly.org`, `docs.pydantic.dev`, `docs.sqlalchemy.org`, `docs.github.com`; metadata PyPI (`pypi.org/pypi/<nama>/json`). Data GitHub dan PyPI diambil 2026-10-12.

Di luar cakupan (sudah ada di catatan lain): referensi FastAPI, konvensi Alembic dan penamaan Postgres, serta agent skills ada di `2026-10-12-001-fastapi-alembic-postgres-best-practices.md`. Arsitektur, tenancy, dan strategi testing ada di `2026-10-12-002-api-architecture-options.md`.

---

## Ringkasan (jawaban dulu)

- **Ruff berubah besar sejak 0.16.** Ruff 0.16.0 (2026-07-23) menaikkan rule default dari 59 menjadi 413. Ruff 0.17.0 (2026-10-09) mengeluarkan 7 rule `DTZ` dari default, jadi totalnya sekarang **407** (terukur lewat `--show-settings`). Default ini sudah mencakup `F`, sebagian `E`, `I`, `UP`, `B`, `SIM`, `ASYNC`, `RUF`, `C4`, sebagian `PL*`, `S`, `PT`, dan `TRY`. Cukup tambahkan `FAST`, `DTZ`, `S`, `C90`, dan `PLR0911/0912/0915`. Hasilnya: **60 temuan**, 43 di antaranya `FAST002` (pindah ke `Annotated[...]`), plus `ruff format` yang akan menulis ulang 16 dari 35 file.
- **Type checker: pakai pyrefly** (Meta). Ia **stabil** (1.0.0 dirilis 2026-05-12, sekarang 1.3.2, PyPI "Production/Stable"), butuh ~0,5 detik, dan dukungan Pydantic v2-nya built-in. Hasilnya **27 error** di `src`, sebagian besar bug tipe sungguhan (`list[object]`, `str | None` yang tidak dicek). ty (Astral) memang tercepat (~0,3 detik, 38 diagnostik), tapi statusnya masih **beta 0.0.x**, dan diagnostiknya bisa berubah di antara dua versi mana pun, jadi belum cocok untuk gate CI. mypy 2.4.0 menemukan 21 error, butuh 7,3 detik saat cold dan 0,3 detik saat warm. pyright menemukan 26 error dalam 5–8,5 detik.
- **Gate CI dengan pyrefly sekarang, di PR revamp.** File yang error (`api.py`, `persistence.py`, `policy_*.py`, `mailer.py`, `ai_provider.py`) memang akan ditulis ulang di PR itu.
- **Hook: prek** (Rust, kompatibel penuh dengan `.pre-commit-config.yaml`, punya workspace mode untuk monorepo, dipakai CPython dan FastAPI). Sudah dicoba: **wajib ada config di root**. Hook di `apps/api/prek.toml` berjalan dengan cwd `apps/api` dan nama file relatif. Web saat ini tidak memakai husky atau lint-staged sama sekali.
- **CI: `.github/workflows/api.yml`** dengan dua job. Job `check` menjalankan `uv sync --locked` lalu `./scripts/check.sh`. Job `migrations` memakai service Postgres 16 dan menjalankan `alembic upgrade head`, `alembic check`, lalu round-trip downgrade/upgrade.
- **Temuan penting saat uji migrasi di `main`:**
  1. `alembic upgrade head` **gagal** dengan `KeyError: '0003_policy_assistant'`, karena `0004_multi_work_locations.py:7` menunjuk `down_revision = "0003_policy_assistant"` padahal revision 0003 adalah `"0003"`.
  2. Setelah rantai itu diperbaiki di salinan `/tmp`, `alembic check` **gagal**: tabel `calendar_settings` dan tiga kolom `leave_requests.*calendar*` ada di metadata tapi tidak punya migrasi. Job CI migrasi akan langsung menangkap dua masalah ini.
- **Satu perintah:** `apps/api/scripts/check.sh` (setara `npm run check` di web). `uv` belum punya task runner (issue astral-sh/uv#5903 masih open), dan skrip shell tidak menambah dependency.
- **Ditunda:** import-linter (setelah batas modul revamp stabil), pytest-cov, pytest-xdist, pytest-randomly, testcontainers, `uv audit` di CI (masih experimental). **Skip:** deptry, vulture, basedpyright.

---

## 1. Kondisi sekarang (terukur)

| Hal | Nilai | Sumber |
|---|---|---|
| Ruff | `ruff>=0.6,<1`, lock **0.16.5**; config hanya `line-length = 100`, `target-version = "py312"` | `apps/api/pyproject.toml:17-25`, `apps/api/uv.lock` |
| Type checker | tidak ada | `apps/api/pyproject.toml` |
| Hook | tidak ada `.pre-commit-config.yaml`, `prek.toml`, `lefthook.yml`, `.husky`; `core.hooksPath` kosong; `apps/web/package.json` tidak punya husky, lint-staged, atau `prepare` | repo |
| CI | hanya `.github/workflows/web.yml` (`npm ci` → `npm run check` → `npm run build`) | `.github/workflows/web.yml` |
| Python | `requires-python >=3.12`; image `python:3.12-slim`; venv lokal **3.13.12** (tidak ada `.python-version`) | `apps/api/pyproject.toml:4`, `apps/api/Dockerfile:1` |
| Test | 82 test lulus dalam 14,6 detik; satu test (`test_mailer.py::test_dispatch_does_not_wait_for_resend`) makan 5,0 detik | `uv run pytest -q --durations=5` |
| File terpanjang | `modules/api.py` 2433 baris, `core/persistence.py` 744 baris | `wc -l` |
| `pytest` dev dep | `>=8,<9` (lock 8.4.2). `uv audit` melaporkan GHSA-6w46-j5rx-g56g / CVE-2025-71176 (tmpdir), fixed di 9.0.3 | `uv audit` |

Ruff 0.16.5 dengan config sekarang (default baru) hanya menemukan **1 error** (`BLE001` di `api.py:1833`). `ruff format --check` melaporkan **14 file perlu diformat** dari 28 (`src` + `tests`), atau **16 dari 35** bila `alembic/` ikut dihitung. Format belum pernah dijalankan konsisten.

---

## 2. Ruff: rule selection dan `ruff format`

### 2.1 Default rule set sekarang sudah lebar

- Ruff **0.16.0** (rilis 2026-07-23): *"Ruff now enables a much larger set of rules by default (413, up from 59)"*. Ada 18 rule `E`/`F` yang opinionated dikeluarkan (`E402`, `E731`, `E741`, `F403`, …). Daftarnya ada di <https://docs.astral.sh/ruff/default-rules/>. Sumber: <https://github.com/astral-sh/ruff/releases/tag/0.16.0>.
- Ruff **0.17.0** (rilis 2026-10-09, terbaru): `DTZ001`, `DTZ005`, `DTZ006`, `DTZ007`, `DTZ011`, `DTZ012`, dan `DTZ901` *"are no longer enabled by default"*, sedangkan `F406` masuk default. Default `target-version` naik ke 3.11. Sumber: <https://github.com/astral-sh/ruff/releases/tag/0.17.0>. Repo `astral-sh/ruff`: 50.005 star, MIT.
- Terukur dengan `uvx ruff@0.17.0 check --show-settings`: **407 rule aktif**. Sebaran per prefix: PYI 47, UP 42, F 39, RUF 36, PLE 33, B 29, SIM 21, PLW 20, FURB 17, C4 17, PLR 13, ASYNC 10, DTZ 10, YTT 10, PLC 8, PIE 8, PT 6, TRY 5, LOG 5, S 3, I 1 (`I001`), E hanya `E722`/`E902`, dan lainnya. **`FAST`, `C901`, `PLR0911/0912/0915`, `DTZ001/005/011`, dan sebagian besar `S` tidak termasuk default.**
- Konsekuensinya, rule yang dulu harus dipilih manual (`E,F,I,UP,B,SIM,ASYNC,RUF,PL…`) **sudah ada di default**. Cukup `extend-select` beberapa family. Karena default rule bisa berubah di minor version (0.16 dan 0.17 dua-duanya breaking), **pin ruff ke minor**: `ruff>=0.17,<0.18`. *(Catatan 2026-10-12: plan 001 memakai `ruff>=0.16.10,<0.17` karena cooldown 7 hari, sebab 0.17.0 baru berumur 2 hari. Rule yang aktif sama, karena DTZ ditambahkan lewat `extend-select`.)*

### 2.2 Rule FastAPI (`FAST`)

Ada tiga rule, semuanya stabil (bukan preview, menurut `ruff rule --all`) dan berlabel *"Derived from the FastAPI linter"*:

| Kode | Nama | Isi | Docs |
|---|---|---|---|
| `FAST001` | fast-api-redundant-response-model | `response_model=` sama dengan return type, jadi redundan (fix selalu tersedia) | <https://docs.astral.sh/ruff/rules/fast-api-redundant-response-model/> |
| `FAST002` | fast-api-non-annotated-dependency | `Depends`/`Query` sebagai default value dinilai deprecated; dokumentasi FastAPI merekomendasikan `typing.Annotated` (fix kadang tersedia, unsafe) | <https://docs.astral.sh/ruff/rules/fast-api-non-annotated-dependency/> |
| `FAST003` | fast-api-unused-path-parameter | path param di route tidak ada di signature fungsi | <https://docs.astral.sh/ruff/rules/fast-api-unused-path-parameter/> |

### 2.3 Rule tambahan yang relevan, dengan ukuran cleanup

Perintah: `uvx ruff@0.17.0 check src tests alembic --extend-select FAST,DTZ,S,C90,PLR0911,PLR0912,PLR0915` dengan `S101`/`S105`/`S106` di-ignore untuk `tests/**`.

| Rule | Temuan | Catatan |
|---|---|---|
| `FAST002` | 43 | semua route di `api.py`; 43 unsafe fix tersedia. Route ditulis ulang di revamp, jadi langsung pakai `Annotated` |
| `S310` | 5 | `urllib.request.urlopen` di `api.py:686,717` dll. URL-nya tetap; ganti ke `httpx` atau beri `# noqa: S310` dengan alasan |
| `I001` | 3 | `alembic/` (autofix). Folder `alembic/` di root proyek membuat ruff menganggap paket `alembic` first-party; set `lint.isort.known-third-party = ["alembic"]` lalu jalankan `--fix` |
| `C901` | 2 | `persistence.save_store` (16 > 10), `api.evaluate_attendance_alerts` (11 > 10) |
| `PLR0911/0912/0915` | 3 | `save_store` (15 cabang, 57 statement), `api.py:1025` (7 return) |
| `BLE001` | 1 | sudah default; `api.py:1833` |
| `DTZ011` | 1 | `date.today()` di tests. **`src` sudah bersih dari datetime naif**, jadi `DTZ` murah dan berguna sebagai penjaga |
| `S105`, `S311` | 1 + 1 | perlu dicek satu per satu |
| **Total** | **60** | ditambah `ruff format` pada 16 file |

Pembanding: `--select ALL` menghasilkan 460 temuan di `src` dan 1041 di `src` + `tests`, didominasi docstring (`D1xx`), `E501`, `COM812`, `CPY001`, `S101`, dan `PLR2004`. Itu terlalu berisik untuk tim 2 orang.

Yang **tidak** dipilih, beserta alasannya:
- `PLR2004` (magic value): 14 di `src`, 113 di `tests`, kebanyakan status code HTTP.
- `D` (docstring), `ANN`: type checker sudah menutup sebagian besar gunanya.
- `E501`: formatter sudah mengurus panjang baris.
- `TID252` (ban relative import): 0 temuan sekarang. Boleh ditambah kalau tim ingin, tapi tidak wajib.
- `TID251` (banned-api): baru berguna kalau ada API tertentu yang ingin dilarang. Belum ada.

### 2.4 Panjang file maksimum

Ruff **tidak punya** rule panjang file. Sudah dicek dari `ruff rule --all` (971 rule): yang ada hanya `E501`/`W505` (panjang baris) dan `PYI053`/`PYI054`. Padanan aturan 600 baris di web (`apps/web/scripts/check-file-lines.mjs`) cukup ditulis sebagai satu test stdlib, sehingga otomatis ikut jalan di pytest, `check.sh`, dan CI (lihat §8).

---

## 3. Type checker

### 3.1 Status dan maturity (dari sumber resmi proyeknya)

| Tool | Versi terbaru (tanggal) | Maturity menurut proyek | Maintainer, star | Sumber |
|---|---|---|---|---|
| **pyrefly** | 1.3.2 (2026-09-28); 1.0.0 dirilis 2026-05-12 | README: *"current development status is stable"*; PyPI `5 - Production/Stable`; *"default type checker for Instagram's 20-million-line Python codebase"* | Meta, 7.079 | <https://github.com/facebook/pyrefly>, <https://pypi.org/pypi/pyrefly/json> |
| **ty** | 0.0.86 (2026-10-09) | README: *"ty is currently in beta"*; *"breaking changes, including changes to diagnostics, may occur between any two versions"*; milestone "Stable" masih open (104 open / 724 closed); PyPI `4 - Beta` | Astral, 19.848 | <https://github.com/astral-sh/ty>, <https://github.com/astral-sh/ty/milestone/4> |
| **mypy** | 2.4.0 (2026-10-01; tag `v2.4.0`, repo tidak memakai GitHub Releases) | PyPI `5 - Production/Stable` | python/mypy, 20.675 | <https://pypi.org/pypi/mypy/json> |
| **pyright** | 1.1.414 (2026-09-09) | PyPI `5 - Production/Stable`. Paket PyPI adalah wrapper komunitas (RobertCraigie/pyright-python) yang mengunduh Node | Microsoft, 15.679 | <https://github.com/microsoft/pyright>, <https://pypi.org/pypi/pyright/json> |
| **basedpyright** | 1.40.2 (2026-10-04) | PyPI tanpa classifier status | DetachHead (fork komunitas), 3.627 | <https://github.com/DetachHead/basedpyright> |

### 3.2 Hasil pada `apps/api/src` (11 file, ~3.700 baris)

Semua dijalankan dengan interpreter `.venv` proyek. Waktu adalah wall-clock termasuk start `uvx`, setelah tool ter-cache.

| Tool | Mode | Diagnostik | Waktu |
|---|---|---|---|
| ty 0.0.86 | default | **38** error (23 `invalid-argument-type`, 15 `unresolved-attribute`); `src` + `tests`: 41 | ~0,3 dtk |
| pyrefly 1.3.2 | tanpa config = preset `basic` | 0 (11 suppressed) | ~0,5 dtk |
| pyrefly 1.3.2 | preset `default` | **27** (14 `missing-attribute`, 9 `bad-argument-type`, 2 `unsupported-operation`, 1 `bad-index`, 1 `bad-assignment`); `src` + `tests`: 32 | ~0,5 dtk |
| pyrefly 1.3.2 | preset `strict` | 184 (143 `implicit-any-type-argument`) | ~0,45 dtk |
| mypy 2.4.0 | default | **21** di 6 file (13 `attr-defined`, 4 `arg-type`, …) | 7,3 dtk cold / 0,3 dtk warm cache |
| mypy 2.4.0 | default + plugin `pydantic.mypy` | 21 (sama) | 8,7 dtk cold |
| mypy 2.4.0 | `--strict` | 124 | 6,3 dtk cold |
| pyright 1.1.414 | default (basic) | **26** | 8,5 dtk pertama / 5,2 dtk |
| basedpyright 1.40.2 | default (`recommended`) | 110 error + 1155 warning (662 `reportAny`) | 11,7 / 4,5 dtk |
| `uv check` (uv 0.12.23, menjalankan ty) | proyek penuh | 46 diagnostik; *"`uv check` is experimental and may change without warning"* | — |

Keempat checker sepakat pada titik error yang sama. Ini masalah tipe nyata, bukan noise:
- `core/policy_retrieval.py:35-51` dan `core/ai_provider.py:36-40` memberi anotasi `list[object]` lalu mengakses `.title` atau `.effective_date`.
- `core/mailer.py:81-84` memanggil `SecretStr | None` dan `str | None` tanpa narrowing sebelum masuk ke `resend.Emails.send`.
- `core/persistence.py:301` meneruskan `settings.database_url: str | None` ke `create_async_engine`.
- `persistence.py:521` dan `api.py:863` membangun dataclass dari `dict` tak bertipe lewat `**row`.

### 3.3 Pydantic, SQLAlchemy, FastAPI

- **Pydantic:** *"Pydantic works well with mypy right out of the box"*, dan plugin `pydantic.mypy` menambah pengecekan `__init__` model (<https://docs.pydantic.dev/latest/integrations/mypy/>). Pada kode ini plugin tidak mengubah jumlah error (21 → 21). Pyrefly: *"Pyrefly includes built-in support for Pydantic … we support Pydantic v2 and above"* (<https://pyrefly.org/en/docs/pydantic/>). ty: issue "Advanced Pydantic support" (astral-sh/ty#3959) masih open. Judul issue itu mengisyaratkan dukungan dasar sudah ada, tapi cakupan persisnya **tidak diverifikasi**.
- **SQLAlchemy:** *"The SQLAlchemy Mypy Plugin is DEPRECATED, and will be removed in the SQLAlchemy 2.1 release … Modern SQLAlchemy now offers fully pep-484 compliant mapping syntaxes"* (<https://docs.sqlalchemy.org/en/20/orm/extensions/mypy.html>). SQLAlchemy 2.1.4 sudah rilis (2026-10-07; lock masih 2.0.52). Artinya `Mapped[...]` / `mapped_column()` tidak butuh plugin di checker mana pun. Persistence sekarang memakai Core `Table(...)` (`persistence.py:54+`), bukan ORM `Mapped`.
- **FastAPI:** cukup typing standar (`Annotated`, Pydantic), tanpa plugin. Tidak ada checker yang butuh konfigurasi khusus FastAPI.

### 3.4 Rekomendasi

**pyrefly, preset `default`, di-gate di CI mulai PR revamp.** Alasannya:
1. Satu-satunya checker cepat yang statusnya stabil (1.x). ty sama cepatnya tapi beta, dan diagnostiknya boleh berubah tiap versi, sehingga gate CI bisa merah setelah bump versi.
2. Pydantic v2 didukung built-in, tanpa plugin.
3. 27 error-nya berada di file yang ditulis ulang di PR revamp, jadi biaya membuat CI hijau rendah.
4. `uv run pyrefly check` otomatis memakai venv proyek (terverifikasi: 27 error di `src`).

Penting: **tanpa `[tool.pyrefly]`, pyrefly memakai preset `basic`** yang nyaris tidak mengecek apa pun (0 error di sini). Dokumentasi menyebut *"If no migratable configuration is found … Pyrefly uses the basic preset"* (<https://pyrefly.org/en/docs/configuration/>). Jadi config wajib ada. Pin minor (`pyrefly>=1.3,<1.4`) karena rilis baru bisa menambah pengecekan.

Evaluasi ulang ty setelah milestone "Stable" tutup. Ada nilai plus ekosistem Astral (ruff, uv, `uv check`), dan migrasinya cuma ganti satu baris perintah.

---

## 4. Git hooks

| | prek | pre-commit | lefthook |
|---|---|---|---|
| Versi terbaru | 0.5.5 (2026-10-05) | 4.6.2 (2026-08-10) | 2.2.1 (2026-10-08) |
| Star, lisensi | 8.599, MIT | 15.622, MIT | 8.894, MIT |
| Runtime | binary Rust tunggal; install `uv tool install prek` atau `uv add --dev prek` | butuh Python | binary Go; install via npm, pip(x), gem, brew |
| Maturity | PyPI `5 - Production/Stable`; versi 0.x; README: *"Although prek is pretty new, it's already powering … CPython, Apache Airflow, FastAPI"* | mapan | mapan |
| Monorepo | **workspace mode**: config bersarang per proyek, hook jalan di direktori proyek | satu config root | `root:` per command |
| Format config | `prek.toml` atau `.pre-commit-config.yaml` | `.pre-commit-config.yaml` | `lefthook.yml` |

Sumber: <https://github.com/j178/prek> (README, `docs/compatibility.md`, `docs/monorepos.md`, `docs/local-hooks.md`), <https://github.com/pre-commit/pre-commit>, <https://github.com/evilmartians/lefthook>. Data PyPI dan rilis diambil 2026-10-12.

Kompatibilitas prek (`docs/compatibility.md`): *"Existing `.pre-commit-config.yaml` and `.pre-commit-config.yml` files work in `prek`"*, dan hook repository serta `.pre-commit-hooks.yaml` juga jalan. Perintah utama (`install`, `run`, …) tetap sama. Yang tidak diimplementasikan hanya `pre-commit hazmat`.

**Diuji langsung** (repo git sementara, prek 0.5.5):
- Dengan hanya `api/prek.toml`, perintah `prek run` gagal: *"No `prek.toml` or `.pre-commit-config.yaml` found in the current directory or parent directories"*. **Config root wajib ada.**
- Dengan root `prek.toml` (builtin `check-merge-conflict`) ditambah `api/prek.toml`, hook API berjalan dengan cwd `…/api` dan menerima nama file relatif (`a.py`), baik lewat `prek run --all-files` maupun lewat `git commit` setelah `prek install`.

**Pilihan: prek.** Hook yang dibutuhkan ada di sisi Python, dan prek memang dibuat untuk ekosistem uv. Workspace mode juga membuat config API terpisah dengan path yang benar tanpa trik `--directory`. lefthook sama layaknya (dan bisa dipasang lewat npm untuk web), tapi web saat ini tidak memakai hook apa pun, jadi tidak ada yang perlu disatukan. Hook bersifat **opt-in per developer**. Gate sebenarnya tetap di CI dan `check.sh`.

Config minimal yang direkomendasikan ada di §9.

---

## 5. CI (GitHub Actions)

- `astral-sh/setup-uv`: rilis terbaru **v10.3.0** (2026-10-09). Repo ini **tidak menerbitkan tag mayor bergerak** (`v10` → 404; tag yang ada `v10.3.0`, `v10.2.0`, …), dan README-nya sendiri mem-pin SHA: `astral-sh/setup-uv@1c37ad07a6a961277cf70c0d37d6f313000f5884 # v10.3.0`. Input yang relevan:
  - `working-directory` (tempat mencari `pyproject.toml` dan `.python-version`)
  - `enable-cache` (default `"auto"`, aktif di runner GitHub-hosted)
  - `cache-dependency-glob` (default sudah mencakup `**/uv.lock` dan `**/pyproject.toml`)
  - `python-version`

  Sumber: <https://github.com/astral-sh/setup-uv>.
- Panduan resmi uv untuk GitHub Actions memakai `uv sync --locked` lalu `uv run pytest` (<https://github.com/astral-sh/uv/blob/main/docs/guides/integration/github.md>). `--locked` gagal bila `uv.lock` tidak sinkron dengan `pyproject.toml`, jadi `uv lock --check` terpisah tidak perlu.
- Service Postgres di Actions: <https://docs.github.com/en/actions/tutorials/use-containerized-services/create-postgresql-service-containers>. Pakai `postgres:16` agar sama dengan produksi (`postgres:16` di `infra/`).
- `alembic check` (*"Check if revision command with autogenerate has pending upgrade ops"*, `alembic check --help`, Alembic 1.19.2 di lock) butuh DB yang sudah `upgrade head`. `alembic.ini` sudah punya `prepend_sys_path = src`, jadi `PYTHONPATH` tidak perlu.
- **Hasil uji lokal (Postgres 17 sementara, URL `MOVON_DATABASE_URL`):**
  1. `alembic upgrade head` pada `main` **gagal**: `KeyError: '0003_policy_assistant'`. Penyebabnya `apps/api/alembic/versions/0004_multi_work_locations.py:7` (`down_revision = "0003_policy_assistant"`), padahal `0003_policy_assistant.py:12` berisi `revision = "0003"`.
  2. Setelah satu baris itu dikoreksi **di salinan `/tmp`**, `upgrade head` sukses dalam 1,1 detik, round-trip `downgrade base` lalu `upgrade head` juga sukses, tapi **`alembic check` gagal**: *"New upgrade operations detected: add_table calendar_settings; add_column leave_requests.calendar_sync_status, employee_calendar_event_id, team_calendar_event_id"*. Skema yang dibuat lewat migrasi tidak sama dengan metadata aplikasi.

  Keduanya harus dibereskan di PR revamp sebelum job migrasi di-gate.

Sketsa workflow ada di §9.

---

## 6. Tool lain

| Tool | Keputusan | Alasan dan bukti |
|---|---|---|
| **Cek panjang file (600 baris)** | **pakai sekarang** | Ruff tidak punya rule-nya (§2.4). Cukup satu test stdlib (§9), tanpa dependency. Saat ini `api.py` (2433) dan `persistence.py` (744) melanggar, dan keduanya dipecah di revamp, jadi tidak perlu `LEGACY_CAPS` |
| **`uv sync --locked`** | **pakai sekarang** (CI) | menolak lock yang basi |
| **`.python-version` = 3.12** | **pakai sekarang** | venv lokal 3.13.12 sementara Docker 3.12; `setup-uv` dan `uv` membaca file ini |
| **import-linter** 2.15 (2026-09-04, PyPI Production/Stable, 1.213 star) | **nanti** (segera setelah revamp) | contract `layers`, `independence`, `forbidden`, `protected`, `acyclic_siblings` (repo `seddonym/import-linter`, `docs/contract_types/`) pas untuk modular monolith. Tapi batas modul baru lahir di PR revamp; tulis contract setelah strukturnya disepakati di `2026-10-12-002` |
| **pytest-cov / coverage** (7.1.0 / 7.16.2, stabil) | **nanti** | belum ada target coverage; angka tanpa target tidak mengubah keputusan |
| **pytest-xdist** 3.8.0 | **skip** | suite 14,6 detik, dan 5,0 detik di antaranya satu test yang menunggu (`test_dispatch_does_not_wait_for_resend`). Perbaiki test itu dulu |
| **pytest-randomly** 5.0.0 | **nanti** | berguna bila muncul kebocoran state antar-test (store in-memory sekarang). Tambahkan bila ada flaky |
| **testcontainers** 4.15.0 (PyPI tanpa classifier status) | **nanti** | service container di CI sudah cukup untuk migrasi. Relevan bila strategi test di `2026-10-12-002` memutuskan test integrasi DB lokal |
| **`uv audit`** | **nanti** (manual/berkala) | perintahnya ada di uv 0.12.23 tapi *"`uv audit` is experimental and may change without warning"*. Sekarang menemukan 3 kerentanan di 47 paket (pytest 8.4.2 ×2, mako 1.4.1 ×1) dalam ~1 detik. Saat revamp, naikkan pin `pytest` ke `>=9.0.3`. **pip-audit** 2.10.1 (stabil) adalah alternatif bila ingin gate audit di CI sekarang |
| **deptry** 0.25.1 (PyPI `3 - Alpha`) | **skip** | dari 8 temuan, mayoritas false positive: nama modul `argon2` ≠ paket `argon2-cffi`; `uvicorn`, `asyncpg`, `psycopg`, `alembic` dipakai di runtime atau CLI. Satu-satunya temuan nyata: `starlette` di-import langsung (`api.py:23`) padahal hanya transitif lewat FastAPI |
| **vulture** 2.16 | **skip** | 72 baris temuan pada confidence ≥60, mayoritas handler route FastAPI yang dipanggil lewat decorator. Ruff `F401`/`F841` sudah menutup kasus nyata |
| **basedpyright** | **skip** | 1.265 diagnostik, terlalu bising untuk MVP |

---

## 7. Satu perintah untuk manusia dan agent

- `uv` **belum punya task runner**. Issue "Using `uv run` as a task runner" (astral-sh/uv#5903) masih open. Ada `uv check` (menjalankan ty) dan `uv format` (menjalankan ruff), tapi `uv check` experimental dan memakai ty, bukan checker pilihan kita.
- Opsi: `Makefile` (butuh `make`), `just` (dependency baru), poethepoet (dependency baru), atau **skrip shell**. Pilih skrip shell `apps/api/scripts/check.sh`. Tim sudah memakai skrip bash (`scripts/run-api.sh`), tidak ada tool baru, dan CI cukup memanggil skrip yang sama, persis seperti `web.yml` memanggil `npm run check`.
- Usulan baris AGENTS.md (bagian back-end, sejajar dengan baris web):

  > Back-end (`apps/api`): run `./scripts/check.sh` in `apps/api` before pushing (ruff lint + format check, pyrefly, pytest).

---

## 8. Catatan versi dan pin

- `ruff`: lock 0.16.5, terbaru 0.17.0. Bump bersamaan dengan config baru, lalu jalankan `ruff format` dan `ruff check --fix` sekali.
- `pytest`: pin `<9` menahan fix kerentanan. Terbaru 9.1.1 (2026-06-19).
- Library inti (konteks, bukan tooling): `fastapi` lock 0.141.1 vs terbaru 0.143.0 (PyPI masih `4 - Beta`); `sqlalchemy` 2.0.52 vs 2.1.4; `alembic` 1.19.2 vs 1.20.0; `pydantic` 2.13.5 vs 2.14.1.
- `Dockerfile` meng-install dependency via `pip` tanpa lock (`apps/api/Dockerfile:3`). Ini di luar cakupan tooling dev, tapi berarti versi di CI ≠ versi produksi sampai Dockerfile memakai `uv sync --locked`.

---

## 9. Rekomendasi tooling untuk Teamku API

Set minimal untuk PR revamp:

1. **Ruff 0.17 + rule tambahan + format.** Di `apps/api/pyproject.toml`:

   ```toml
   [dependency-groups]
   dev = [
       "pytest>=9.0.3,<10",
       "httpx>=0.27,<1",
       "ruff>=0.17,<0.18",
       "pyrefly>=1.3,<1.4",
   ]

   [tool.ruff]
   line-length = 100
   target-version = "py312"

   [tool.ruff.lint]
   # Default ruff 0.17 = 407 rule (F, I, UP, B, SIM, ASYNC, RUF, C4, PL*, PT, TRY, sebagian S/E).
   extend-select = [
       "FAST",                                   # FastAPI: Annotated, response_model, path param
       "DTZ",                                    # datetime naif (keluar dari default di 0.17)
       "S",                                      # bandit penuh
       "C90", "PLR0911", "PLR0912", "PLR0915",   # kompleksitas
   ]

   [tool.ruff.lint.per-file-ignores]
   "tests/**" = ["S101", "S105", "S106"]

   [tool.ruff.lint.isort]
   known-third-party = ["alembic"]  # folder alembic/ di root membuat ruff menganggapnya first-party
   ```

   Lalu `uv lock`, `uv run ruff format .`, `uv run ruff check --fix .`, dan bereskan sisa ~56 temuan (43 di antaranya `FAST002`, yang selesai sendiri bila route baru memakai `Annotated`).

2. **pyrefly sebagai type checker, di-gate.** Tambahkan di `pyproject.toml`:

   ```toml
   [tool.pyrefly]
   project-includes = ["src"]   # tambah "tests" setelah src bersih (5 error tambahan)
   preset = "default"           # wajib: tanpa config, pyrefly jatuh ke preset "basic"
   ```

   Lalu perbaiki 27 error yang ada.

3. **`.python-version`** berisi `3.12` di `apps/api/`, supaya lokal, CI, dan Docker sama.

4. **Test panjang file** di `apps/api/tests/test_file_lengths.py`:

   ```python
   from pathlib import Path

   MAX_LINES = 600
   SRC = Path(__file__).resolve().parents[1] / "src"


   def test_source_files_stay_under_max_lines() -> None:
       too_long = {
           str(p.relative_to(SRC)): n
           for p in SRC.rglob("*.py")
           if (n := len(p.read_text(encoding="utf-8").splitlines())) > MAX_LINES
       }
       assert not too_long, f"Pecah file > {MAX_LINES} baris: {too_long}"
   ```

5. **`apps/api/scripts/check.sh`** (executable), satu perintah untuk manusia, agent, dan CI:

   ```bash
   #!/usr/bin/env bash
   set -euo pipefail
   cd "$(dirname "${BASH_SOURCE[0]}")/.."
   uv run ruff check .
   uv run ruff format --check .
   uv run pyrefly check
   uv run pytest -q
   ```

   Tambahkan juga baris AGENTS.md dari §7.

6. **Hook prek (opt-in).** Install sekali per developer: `uv tool install prek && prek install` dari root repo.

   `prek.toml` (root, wajib ada agar workspace mode jalan):

   ```toml
   [[repos]]
   repo = "builtin"
   hooks = [{ id = "check-merge-conflict" }, { id = "check-added-large-files" }]
   ```

   `apps/api/prek.toml` (hook jalan dengan cwd `apps/api`):

   ```toml
   [[repos]]
   repo = "local"

   [[repos.hooks]]
   id = "ruff-check"
   name = "ruff check"
   language = "system"
   entry = "uv run ruff check --fix"
   types = ["python"]

   [[repos.hooks]]
   id = "ruff-format"
   name = "ruff format"
   language = "system"
   entry = "uv run ruff format"
   types = ["python"]
   ```

   pyrefly dan pytest tidak masuk hook, cukup di `check.sh` dan CI, supaya commit tetap cepat.

7. **CI `.github/workflows/api.yml`:**

   ```yaml
   name: api

   on:
     pull_request:
       paths: ["apps/api/**", ".github/workflows/api.yml"]
     push:
       branches: [main]
       paths: ["apps/api/**", ".github/workflows/api.yml"]

   jobs:
     check:
       runs-on: ubuntu-latest
       defaults:
         run:
           working-directory: apps/api
       steps:
         - uses: actions/checkout@v4
         - uses: astral-sh/setup-uv@1c37ad07a6a961277cf70c0d37d6f313000f5884 # v10.3.0
           with:
             working-directory: apps/api
             enable-cache: true
         - run: uv sync --locked
         - run: ./scripts/check.sh

     migrations:
       runs-on: ubuntu-latest
       services:
         postgres:
           image: postgres:16
           env:
             POSTGRES_USER: movon
             POSTGRES_PASSWORD: movon
             POSTGRES_DB: movon
           ports: ["5432:5432"]
           options: >-
             --health-cmd pg_isready --health-interval 5s
             --health-timeout 5s --health-retries 10
       env:
         MOVON_DATABASE_URL: postgresql+asyncpg://movon:movon@localhost:5432/movon
       defaults:
         run:
           working-directory: apps/api
       steps:
         - uses: actions/checkout@v4
         - uses: astral-sh/setup-uv@1c37ad07a6a961277cf70c0d37d6f313000f5884 # v10.3.0
           with:
             working-directory: apps/api
             enable-cache: true
         - run: uv sync --locked
         - run: uv run alembic upgrade head
         - run: uv run alembic check
         - run: uv run alembic downgrade base && uv run alembic upgrade head
   ```

   Job `migrations` baru akan hijau setelah `down_revision` di `0004` diperbaiki dan migrasi untuk `calendar_settings` serta kolom kalender di `leave_requests` ditambahkan (§5). `actions/checkout@v4` disamakan dengan `web.yml`; versi terbaru checkout adalah v7.0.1.

### Ditunda

- **import-linter**: tulis contract setelah batas modul revamp disepakati.
- **pytest-cov**: tambahkan saat ada target coverage.
- **pytest-randomly**: tambahkan saat muncul test flaky karena state.
- **testcontainers**: hanya bila strategi test memutuskan test integrasi DB di lokal.
- **`uv audit` di CI**: tunggu sampai tidak experimental (atau pakai `pip-audit` bila butuh gate sekarang).
- **ty**: evaluasi ulang saat milestone "Stable" tutup.
- **Gate pyrefly untuk `tests/`**: setelah `src` bersih.

---

## 10. Yang tidak bisa diverifikasi

- Cakupan persis dukungan Pydantic di ty (hanya diketahui issue "Advanced Pydantic support" #3959 masih open).
- Halaman `docs.astral.sh/ruff/default-rules/` dirender lewat JavaScript, sehingga isinya tidak terbaca lewat `curl`. Jumlah 407 rule diambil dari `ruff check --show-settings` lokal (0.17.0), bukan dari halaman itu.
- Waktu eksekusi diukur di satu mesin WSL2. Angka di runner GitHub akan berbeda; urutan relatifnya yang lebih bisa dipegang.
- `alembic check` diuji di Postgres 17 lokal, bukan 16. Perbedaan versi ini tidak diharapkan memengaruhi deteksi tabel/kolom, tapi belum dicoba di 16.
