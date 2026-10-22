# Orval: client API ber-type di `apps/web` dari OpenAPI `apps/api`

Tanggal riset: 2026-10-22. Kode diukur pada `main` = `origin/main` @ `a25fd6c`. Riset ini read-only: tidak ada file repo yang diubah selain catatan ini. Semua uji coba Orval dijalankan di folder scratch di luar repo, memakai spec yang di-dump dari `apps/api` saat ini.

> **Pembaruan (implementasi #46):** beberapa rekomendasi di bawah diubah saat diskusi. Hook TanStack Query **di-generate** (bukan tulisan tangan), dengan invalidasi otomatis lewat `MutationCache` sebagai ganti query key per domain. Orval di-pin `8.43.0` (8.44.0 baru sehari). Enum memakai `type X = Literal[...]` + CHECK constraint di DB, union respons memakai discriminator `result`, error 4xx memakai `ErrorOut`, dan semua schema API dinamai `XIn`/`XOut`. Keputusan final ada di ADR 0001 serta `apps/api/AGENTS.md` dan `apps/web/AGENTS.md`; nama operasi dan enum di bawah memakai nama sebelum rename (aturan nama di `apps/api/AGENTS.md`).

Sumber primer: kode repo ini; dokumentasi Orval (`orval.dev/docs/reference/configuration/output`, `orval.dev/docs/guides/custom-client`, `orval.dev/docs/guides/fetch-client`); kode sumber paket npm `orval@8.44.0` dan `@orval/core@8.44.0` (file `dist/*.d.mts` dan `dist/config-*.mjs`); metadata npm registry (`npm view orval`), diambil 2026-10-22; dokumentasi FastAPI `fastapi.tiangolo.com/advanced/generate-clients/`.

---

## Ringkasan (jawaban dulu)

- **Bisa dan murah.** Spec OpenAPI bisa di-dump **tanpa server, tanpa DB, tanpa env** (`app.openapi()` lewat `uv run`). Hasilnya OpenAPI **3.1.0**, 54 operasi, 79 schema. Semua endpoint JSON sudah punya schema respons. Orval 8.44.0 men-generate client dari spec itu dalam ~1,2 detik, dan **`tsc --strict` lolos tanpa error** memakai opsi compiler `apps/web`.
- **Rekomendasi: `client: "fetch"` saja (fungsi + type), bukan hook `react-query`.** Mutator-nya adalah `api()` yang sudah ada di `shared/api/client.ts`. Hook `useQuery` tetap ditulis tangan di `features/<domain>/api.ts`. Alasannya: query key hasil generate berbasis URL (`["/api/v1/me"]`, terverifikasi), sedangkan repo memakai key per domain dan invalidasi per prefix (`["leave"]`). Tidak ada dependency baru selain `orval` (devDependency).
- **Perlu tiga perubahan kecil di API** supaya hasilnya rapi: (1) `generate_unique_id_function` → `route.name` (sekarang nama fungsinya `attendance_today_api_v1_attendance_today_get`), (2) `tags=[...]` per router (sekarang tidak ada tag sama sekali) supaya mode `tags-split` menghasilkan file < 600 baris, (3) `include_in_schema=False` untuk `/health/*`.
- **Jaminan konsistensi:** spec di-commit (`apps/api/openapi.json`). `scripts/check.sh` gagal bila spec basi, `npm run check` gagal bila client hasil generate basi, dan `tsc` gagal bila pemakaian di FE tidak cocok dengan kontrak baru. `web.yml` ditambah path `apps/api/openapi.json`, supaya PR yang hanya mengubah BE pun menjalankan cek FE.
- **Gotcha terbesar: enum.** API memvalidasi nilai enum dengan `Field(pattern="^(a|b)$")`, jadi OpenAPI-nya hanya `type: string` + `pattern`, dan Orval menghasilkan `string`. Union yang sekarang ditulis tangan di FE (`LeaveStatus`) akan hilang kalau langsung diganti. Solusinya `Literal[...]` di schema Pydantic (follow-up BE, tidak wajib untuk mulai).
- **Migrasi bertahap**, bukan sekaligus: 56 pemanggilan `api(` di 18 file (30 path statis unik). Client hasil generate bisa hidup berdampingan dengan pemanggilan manual. Masukkan langkahnya ke resep "Memigrasi satu halaman lama".
- **Skip (YAGNI):** zod/runtime validation, mock MSW, hook hasil generate, `useDates`. Alasannya ada di §2.

---

## 1. Kondisi sekarang

### 1.1 `apps/web`

| Hal | Nilai | Sumber |
|---|---|---|
| Framework | Next **15.5.25**, React 19, App Router | `apps/web/package.json`, `apps/web/README.md:3` |
| Data fetching | TanStack Query **5.104.1** untuk semua server state; Zustand hanya untuk state UI | `apps/web/package.json`, `apps/web/README.md:45`, `docs/adr/0001-web-frontend-architecture.md:13` |
| Fetch wrapper | Satu fungsi `api<T>(path, init)`. Prefix `BASE = "/api"`, `credentials: "include"`, timeout 15 detik, `Content-Type: application/json`, 401 → redirect `/login`, error → `ApiError(message, status)` dengan pesan dari `detail` bila string | `apps/web/src/shared/api/client.ts:3,25-57` |
| Auth | Cookie httpOnly `teamku_session`, same-origin lewat proxy Next. Tidak ada header token | `apps/web/src/middleware.ts`, `apps/web/README.md` (Mode demo) |
| Base URL | Browser selalu memanggil `/api/*`. Next me-rewrite ke `${MOVON_API_ORIGIN}/api/v1/*` | `apps/web/next.config.ts` (`rewrites`) |
| Server/client | Hanya client. `client.ts` memakai `window`, dan tidak ada `"use server"`/`cookies()` di `src`. ADR 0001 menolak RSC fetch | grep `src`; `docs/adr/0001-web-frontend-architecture.md:22` |
| Type API | Ditulis tangan per feature di `features/<domain>/types.ts` ("satu sumber"), plus type inline di 10 halaman legacy `app/app/**/page.tsx` | `apps/web/README.md:26`, grep |
| Query key | Per domain, invalidasi per prefix: `leaveKeys.all = ["leave"]`, `approvalsKey = ["leave","approvals"]` dibagi halaman Persetujuan dan badge shell | `apps/web/src/features/leave/api.ts:6-9`, `apps/web/src/shared/api/approvals.ts:7` |
| Gate | `npm run check` = `biome ci` + batas 600 baris (`scripts/check-file-lines.mjs`) + `design:sync --check` + `tsc` + `vitest` | `apps/web/package.json` |
| Biome | Nama file wajib kebab-case; `vcs.root = "../.."` | `apps/web/biome.json:7,27` |
| CI | `web.yml` hanya terpicu oleh `apps/web/**` | `.github/workflows/web.yml:5,8` |

ADR 0001 sudah menyebut opsi ini dan menundanya: *"Generate type dari OpenAPI: endpoint FastAPI belum memakai `response_model` … Bisa ditinjau ulang setelah API menambahkannya"* (`docs/adr/0001-web-frontend-architecture.md:23`). Syarat itu sekarang sudah terpenuhi lewat revamp API (`docs/plans/2026-10-12-001-refactor-api-foundation-plan.md:18,73`). Plan itu memang mengeluarkan "generate type web dari OpenAPI" dari cakupannya (`:389`).

**Contoh drift yang sudah terjadi** (bukti bahwa masalahnya nyata):
- `useDecideApproval` men-type respons `POST /approvals/{id}` sebagai `ApprovalRequest`, yang punya `employee_name`, `department`, `days` (`apps/web/src/features/leave/api.ts:23`). Padahal API me-return `LeaveOut`, yang tidak punya ketiga field itu (`apps/api/src/movon_hr/modules/leave/router.py:47,54`). Sekarang tidak meledak hanya karena hasilnya tidak dibaca.
- `approver_comment?: string` di FE (`apps/web/src/features/leave/types.ts:13`), sedangkan di spec field itu required `string | null`.

### 1.2 `apps/api`

| Hal | Nilai | Sumber |
|---|---|---|
| Endpoint spec | `openapi_url="/api/v1/openapi.json"`, tanpa gating per environment (ikut terbuka di prod, begitu juga `/docs`) | `apps/api/src/movon_hr/main.py:21-25` |
| Versi OpenAPI | `3.1.0` (FastAPI 0.142.x) | hasil dump |
| `operationId` | Default FastAPI, contoh `list_employees_api_v1_employees_get`. `generate_unique_id_function` tidak di-set | `main.py:21-25`, hasil dump |
| Tag | **Tidak ada.** Semua `APIRouter()` tanpa `tags` | `modules/*/router.py` (mis. `leave/router.py:18`) |
| Respons | Semua endpoint JSON punya schema (return annotation). Pengecualian: `GET /settings/calendar/google/callback` (redirect 302, schema `{}`) | hasil dump; plan `:73` |
| Status code | Semua sukses `200`. Hanya `422` (`HTTPValidationError`) yang dideklarasikan. Error domain `{"detail": str}` dari `HTTPException` (64 tempat) **tidak** ada di spec | hasil dump; plan `:181` |
| List | Envelope `{items: T[]}`, sebagian ditambah `total` (`EmployeeList`). Tidak ada paginasi/query param (satu-satunya query param ada di OAuth callback) | hasil dump |
| Security scheme | Tidak dideklarasikan (`securitySchemes` tidak ada). Auth lewat cookie, dibaca dependency | hasil dump |
| Uang | `int` rupiah (`gross_rupiah: integer`), tidak ada `Decimal` | `PayslipOut` di spec |
| Upload file | Tidak ada (`multipart` tidak muncul) | hasil dump |

**Dump spec tanpa server/DB:** terverifikasi. Dengan environment kosong (`env -i HOME PATH`) dan tanpa Postgres yang berjalan:

```bash
cd apps/api
uv run python -c 'import json; from movon_hr.main import app; print(json.dumps(app.openapi(), indent=2))'
```

Ini berhasil (exit 0, 125 KB), karena semua field `Settings` punya default (`core/settings.py`) dan `create_async_engine` tidak membuka koneksi saat import (`core/db.py:30`). `env_file=".env"` relatif terhadap cwd, tetapi tidak ada nilai settings yang masuk ke spec.

---

## 2. Opsi Orval yang relevan

**Versi:** `orval@8.44.0` (latest, dirilis 2026-10-21). `engines.node = ">=22.18.0"` (`npm view orval`). `apps/web` memasang `"node": "22.x"`, dan CI memakai `setup-node` 22 (versi 22.x terbaru), jadi aman. Developer lokal di bawah 22.18 harus upgrade. Major 8.0.0 dirilis 2026-01-14. Ritme rilisnya cepat: 12 minor antara 8.33.0 (2026-09-13) dan 8.44.0 (2026-10-21). **Pin versi exact** (`"orval": "8.44.0"`) supaya hasil generate deterministik dan cek drift tidak gagal karena upgrade diam-diam. Ini sejalan dengan cooldown `exclude-newer = "7 days"` di API (`apps/api/pyproject.toml:33`).

| Opsi | Nilai/perilaku | Sumber | Untuk Teamku |
|---|---|---|---|
| `client` | `fetch`, `react-query`, `swr`, `zod`, `axios`, … (default `axios-functions`) | output reference | **`fetch`** |
| `httpClient` | `fetch` (default) / `axios` / `angular` | output reference | default |
| `mode` | `single`, `split`, `tags`, `tags-split`, … (default `single`) | output reference | **`tags-split`** setelah API punya tag |
| `override.mutator` | `{ path, name }`. Fungsi dipanggil `api<T>(url, { ...options, method, headers, body })` | custom-client guide; hasil generate | **`api` dari `shared/api/client.ts`** |
| `override.fetch.includeHttpResponseReturnType` | default `true` (return `{status, data}`); `false` = return data langsung | output reference, fetch-client guide | **`false`**, mengikuti `api<T>()` sekarang |
| `override.operationName` | `(operation, route, verb) => string` | output reference | tidak perlu bila API men-set `route.name` |
| `namingConvention` | nama file: `camelCase` (default) / `kebab-case` / … | output reference | **`kebab-case`** (aturan Biome) |
| `formatter` | `prettier` / `biome` / `oxfmt`. `biome` menjalankan `biome check --write <paths>` | output reference; `orval/dist/config-*.mjs` (`case SupportedFormatter.BIOME`) | **`biome`** |
| `clean` | menghapus *seluruh* isi `target` dan `schemas` | output reference | `true`, folder khusus |
| `override.enumGenerationType` | `const` (default) / `enum` / `union` | output reference | default, relevan setelah `Literal` |
| `useDates` | default `false` (date tetap `string`) | output reference | default; FE sudah memformat string |
| `input.override.transformer` | fungsi untuk memodifikasi spec sebelum generate | `@orval/core` `.d.mts` | tidak perlu bila BE dibereskan |

**Yang di-skip:**
- **Hook `react-query`.** Terverifikasi: key-nya `getMeQueryKey = () => ["/api/v1/me"]`, yaitu berbasis URL. Ini bentrok dengan aturan invalidasi per domain (`README.md:45`, `leaveKeys.all`). Bisa diakali dengan mutator `override.query.queryKey`, tapi itu bagian bergerak tambahan, dan setiap hook hasil generate punya 4 overload. Hook tulisan tangan di atas fungsi hasil generate cukup 3 baris.
- **Zod / `runtimeValidation`.** Kontraknya dijaga di build time (tsc + cek drift). Validasi runtime baru berguna bila API bisa berubah di luar repo ini, dan sekarang tidak demikian.
- **Mock MSW (`mock: true`).** Test FE sekarang menguji logika murni (vitest), bukan network. Tambahkan bila nanti ada test komponen yang butuh network.
- **Next.js server component.** Tidak dipakai (ADR 0001). Kalau suatu saat dipakai, mutator butuh origin absolut dan meneruskan cookie, karena `client.ts` memakai `window` dan URL relatif. Dokumentasi Orval yang diperiksa tidak punya panduan khusus App Router/RSC (tidak terverifikasi lebih jauh).

---

## 3. Uji coba (spec `main` saat ini)

Config uji: `client: "fetch"`, mutator dengan signature identik `api<T>(url: string, init: RequestInit = {}): Promise<T>`, `includeHttpResponseReturnType: false`.

| Varian | Hasil |
|---|---|
| `mode: "single"`, operationId default + `operationName` manual | 1 file endpoint **1697 baris** (1436 setelah Biome) + 83 file model. `tsc --strict` lolos |
| `mode: "tags-split"`, spec diberi tag per modul + `operationId = route.name` (lewat `input.override.transformer`, untuk mensimulasikan perubahan BE) | 16 file endpoint, terbesar `settings.ts` **316 baris**, nama fungsi `attendanceToday`, `checkIn`, `login`, `acceptInvite`, … `tsc` lolos |
| Biome dengan rule repo (`apps/web/biome.json`) pada output | Sebelum format: 96 diagnostik `format` + 2 `organizeImports`, **0 lint error**. Setelah `biome check --write`: bersih. Nama file `kebab-case` lolos `useFilenamingConvention` |

Contoh hasil (tipe):

```ts
export interface LeaveOut {
  id: string;
  status: string;                  // pattern di BE → string, bukan union
  approver_comment: string | null; // anyOf [string, null] → T | null, required
  created_at: string;              // format date-time → string
  // ...
}
export const checkIn = async (checkInBody: CheckIn, options?: Parameters<typeof api>[1]):
  Promise<CheckInOut | IdempotentOut> => api<CheckInOut | IdempotentOut>(getCheckInUrl(), {...})
```

Catatan kecil: setiap mutation membawa helper `getHeaders` sendiri (46 salinan di mode single). Ini cuma noise generator, tidak berpengaruh ke runtime.

---

## 4. Workflow & jaminan konsistensi

**Di mana spec tinggal:** commit di **`apps/api/openapi.json`**. BE pemilik kontrak, dan diff kontrak terlihat di PR BE. Mengambilnya dari API yang sedang berjalan ditolak: CI butuh server, hasilnya tidak deterministik, dan tidak ada jejak di git.

**Rantai pemeriksaan:**

1. **API (`apps/api/scripts/check.sh`)**: tambah satu baris yang mem-dump spec lalu `diff -u openapi.json -`. Kalau gagal, pesannya berisi perintah regenerate. Tidak butuh DB.
2. **Web (`npm run check`)**: tambah `orval` lalu `test -z "$(git status --porcelain -- src/shared/api/generated)"`. Pakai `git status`, bukan `git diff`, supaya file baru yang belum di-track ikut tertangkap. Polanya sama dengan `design:sync --check`: secara lokal file ikut diperbarui, jadi developer tinggal commit.
3. **`tsc`** (sudah ada di `npm run check`): menangkap pemakaian yang rusak, misalnya field yang dihapus atau tipe yang berubah.
4. **`.github/workflows/web.yml`**: tambah `"apps/api/openapi.json"` ke `paths` (`:5,:8`). Tanpa ini, PR yang hanya menyentuh BE tidak menjalankan cek FE.

Hasilnya: perubahan kontrak di BE memaksa `openapi.json` ikut di-commit (langkah 1). Itu memicu job web, dan job web gagal kalau client belum di-regenerate (langkah 2) atau FE belum disesuaikan (langkah 3). FE dan BE tidak bisa beda versi di `main`.

**Biome & batas baris:** dengan `formatter: "biome"`, output lolos `biome ci` tanpa perlu override. `check-file-lines.mjs` memindai semua `src/**` (`:16-18`, `MAX_LINES = 600`). Mode `tags-split` + tag di BE membuat semua file di bawah batas (terbesar 316). Bila tag belum ada, folder `generated` harus dikecualikan dari skrip itu.

**Arah import:** `src/shared/api/generated/` ada di `shared`, jadi `features` boleh mengimpornya (`README.md` aturan Arsitektur 1). Mutator `shared/api/client.ts` juga di `shared`.

---

## 5. Jalur migrasi

**Ukuran:** 56 pemanggilan `api(` di 18 file, 30 path statis unik. Rinciannya: 10 halaman legacy `app/app/**/page.tsx` (termasuk `settings/page.tsx` 1258 baris dan `attendance/today/page.tsx` 658 baris), `app/signup/page.tsx`, 5 file `features/*/api.ts` + `shared/api/approvals.ts`, dan `features/shell/use-logout.ts`. Type tulisan tangan: ±50 deklarasi `type`/`interface` di 28 file, sebagian memang type UI. Di sisi API ada 54 operasi dan 79 schema.

**Bertahap, bukan sekaligus.** Fungsi hasil generate memanggil `api()` yang sama, sehingga keduanya bisa hidup berdampingan selama migrasi. Masukkan ke resep "Memigrasi satu halaman lama" (`README.md:76`) langkah 1: `features/<domain>/types.ts` me-re-export atau menyempitkan model dari `@/shared/api/generated/model`, dan `api.ts` memanggil fungsi hasil generate di dalam `useQuery`/`useMutation` dengan key domain yang sudah ada. Satu PR per halaman tetap berlaku. PR pertama yang wajar: setup + `features/leave` (contoh acuan di README), yang sekalian membereskan drift `decide` di §1.1.

Satu hal yang harus diselesaikan di PR setup: path di spec adalah `/api/v1/...`, sedangkan browser memanggil `/api/...` (rewrite Next). Ubah satu baris di `api()`: path yang diawali `/api/v1/` diubah menjadi `/api/`, sedangkan path lain tetap diberi prefix `BASE`, supaya pemanggil manual tidak rusak. Kalau semua pemanggil sudah pindah, cabang lama dihapus.

---

## 6. Risiko & gotcha

| # | Hal | Status di Teamku | Penanganan |
|---|---|---|---|
| 1 | **Enum lewat `pattern`** | `ApprovalInput.decision`, `role`, `status`, `language`, `provider`, … ditulis `Field(pattern="^(a\|b)$")` (`modules/*/schemas.py`), dan respons (`LeaveOut.status`) cuma `str`. Hasilnya `string` di TS | Follow-up BE: `Literal["approved", …]`, sehingga OpenAPI berisi `enum` dan Orval menghasilkan const + union. Sementara itu FE mempertahankan union-nya sendiri (`LeaveStatus`) dan menyempitkan tipe hasil generate |
| 2 | Nullable `anyOf [T, null]` dari Pydantic v2 | Terverifikasi menjadi `T \| null`, dan field-nya tetap required di schema output | Tidak perlu apa-apa. Ini justru membetulkan `?:` yang salah di FE |
| 3 | Union respons tanpa discriminator | 3 endpoint: `check-in` (`CheckInOut \| IdempotentOut`), `reverify` (3 tipe), `POST /employees` (`EmployeeOut \| NewEmployeeOut`). Tidak ada `oneOf`/`discriminator` di spec | FE mempersempit dengan `"idempotent" in r`. Discriminator di BE (`Literal` + `Field(discriminator=…)`) hanya kalau penyempitan ini terasa menyakitkan |
| 4 | OpenAPI 3.1 | Orval 8 memakai `@scalar/openapi-parser`, dan spec 3.1.0 FastAPI ter-generate + `tsc` bersih | Tidak ada |
| 5 | Date/datetime | `format: date`/`date-time` → `string` (`useDates: false`) | Biarkan. Helper format FE sudah menerima string |
| 6 | Decimal | Tidak ada; uang `int` rupiah | Tidak ada |
| 7 | Upload file | Tidak ada endpoint multipart | Tidak ada |
| 8 | Error tidak ada di spec | Hanya 422 yang dideklarasikan; `{detail: str}` tidak | `ApiError` di mutator tetap menjadi kontrak error (`client.ts:47-55`). Tipe `TError` hasil generate tidak dipakai |
| 9 | Prefix `/api/v1` vs proxy `/api` | Lihat §5 | Satu baris di `api()` |
| 10 | operationId jelek & tanpa tag | `list_employees_api_v1_employees_get`, mode `tags-split` jatuh ke satu grup | `generate_unique_id_function=lambda route: route.name` (54 nama fungsi saat ini unik, sudah dicek) + `tags=[...]` per `APIRouter`, sesuai saran FastAPI (`/advanced/generate-clients/`) |
| 11 | Endpoint non-JSON | `/health/*` dan OAuth callback 302 ikut ter-generate | `include_in_schema=False` untuk health. Callback biarkan saja (FE menavigasi ke sana, tidak mem-fetch) |
| 12 | Ritme rilis Orval | Mingguan; output bisa berubah antar-minor | Pin exact; upgrade lewat PR sendiri yang berisi diff hasil generate |
| 13 | `clean: true` | Menghapus seluruh folder target | Folder khusus `src/shared/api/generated/`, jangan dicampur kode tulisan tangan |
| 14 | Spec terbuka di prod | `/api/v1/openapi.json` dan `/docs` aktif di prod (`main.py:24`) | Di luar cakupan codegen (dump lokal tidak butuh endpoint ini). Bila ingin ditutup: `openapi_url=None` di prod; dump tetap jalan karena memanggil `app.openapi()` langsung |

---

## Rekomendasi

**Setup minimal** (satu PR, FE + BE kecil):

BE (`apps/api`), tanpa perubahan fitur:
1. `FastAPI(..., generate_unique_id_function=lambda route: route.name)` di `main.py`.
2. `APIRouter(tags=["<modul>"])` di 10 router; `include_in_schema=False` di dua endpoint health.
3. Commit `openapi.json`, lalu tambah ke `scripts/check.sh`:
   ```bash
   uv run python -c 'import json; from movon_hr.main import app; print(json.dumps(app.openapi(), indent=2))' \
     | diff -u openapi.json - || { echo "openapi.json basi: jalankan perintah dump di README"; exit 1; }
   ```
   Perintah dump (dengan `> openapi.json`) dicatat di tabel Perintah `apps/api/README.md`.

FE (`apps/web`):
1. `npm i -D -E orval@8.44.0` (satu-satunya dependency baru).
2. `orval.config.ts`:
   ```ts
   import { defineConfig } from "orval";

   export default defineConfig({
     teamku: {
       input: { target: "../api/openapi.json" },
       output: {
         target: "src/shared/api/generated/endpoints.ts",
         schemas: "src/shared/api/generated/model",
         client: "fetch",
         mode: "tags-split",
         namingConvention: "kebab-case",
         formatter: "biome",
         clean: true,
         override: {
           mutator: { path: "src/shared/api/client.ts", name: "api" },
           fetch: { includeHttpResponseReturnType: false },
         },
       },
     },
   });
   ```
3. `package.json`: `"api:gen": "orval"`, dan `check` ditambah `&& orval && test -z \"$(git status --porcelain -- src/shared/api/generated)\"`.
4. `client.ts`: path `/api/v1/…` diterima apa adanya lalu dipetakan ke `/api/…` (§5). Signature `api()` tidak berubah.
5. `web.yml`: tambah `apps/api/openapi.json` ke `paths`.
6. Migrasikan `features/leave` sebagai contoh acuan; halaman lain menyusul lewat resep migrasi yang sudah ada.
7. Perbarui ADR 0001 (alternatif "Generate type dari OpenAPI" sekarang dipakai) dan README web (resep migrasi, langkah 1).

Hook tetap ditulis tangan, misalnya:

```ts
export function useApprovals() {
  return useQuery({ queryKey: leaveKeys.approvals(), queryFn: () => approvals(), select: (d) => d.items });
}
```

**Pertanyaan terbuka untuk tim:**
1. **Hook hasil generate atau tulisan tangan?** Rekomendasinya tulisan tangan, karena key per domain dan invalidasi prefix. Kalau tim lebih suka hook generate, perlu mutator `queryKey` dan aturan invalidasi baru di README.
2. **`Literal` untuk enum di BE:** dikerjakan di PR setup, atau tiket terpisah? Sentuhannya ±12 field di `schemas.py` ditambah field status di schema output.
3. **Lokasi spec:** `apps/api/openapi.json` (BE pemilik kontrak, perlu path tambahan di `web.yml`) atau `apps/web/openapi.json` (CI web otomatis terpicu, tapi `check.sh` API menulis ke luar foldernya)?
4. **Kebijakan upgrade Orval:** pin exact plus upgrade manual, atau cooldown otomatis seperti `exclude-newer` di API?
5. **Tutup `/docs` dan `openapi.json` di prod?** Tidak berkaitan dengan codegen, tapi sekalian diputuskan.
