# Teamku Web

Next.js 15 (App Router) + React 19 + TanStack Query + Zustand + Tailwind v4 + shadcn/ui (Radix) + Biome + Vitest.
Keputusan arsitekturnya ada di [`docs/adr/0001-web-frontend-architecture.md`](../../docs/adr/0001-web-frontend-architecture.md).

**Aturan kode** (arsitektur, server state dan client generate, komponen, styling, cara memigrasi halaman lama) ada di [`AGENTS.md`](AGENTS.md). File itu juga dimuat otomatis oleh agent AI saat bekerja di `apps/web`. Token dan aturan visual: [`DESIGN.md`](../../DESIGN.md); contoh hidup semua komponen di `/design-system` (lokal dan preview Vercel).

## Perintah

| Perintah | Fungsi |
|---|---|
| `npm run dev` | Dev server. Request `/api/v1/*` di-proxy apa adanya ke `MOVON_API_ORIGIN` (default `http://127.0.0.1:8000`) |
| `npm run check` | Gerbang sebelum push: generate ulang client API + `biome ci` + batas panjang file + `tsc` + `vitest`. File generate yang berubah muncul di `git status` untuk di-commit |
| `npm run api:gen` | Generate ulang client API (`src/shared/api/generated/`) dari `apps/api/openapi.json` dengan Orval. Jalankan setelah spec API berubah, lalu commit hasilnya |
| `npm run lint:fix` | Format + organize imports + fix lint yang aman |
| `npm run lint:size` | Cek batas 600 baris per file |
| `npm run design:sync` | Salin token `@theme` ke `DESIGN.md` + `shared/lib/text-sizes.ts` |
| `npm test` | Vitest |
| `npx shadcn add <nama>` | Menambah komponen shadcn ke `src/shared/ui/` |

Jalankan `npm run check` sebelum push. CI (`.github/workflows/web.yml`) menjalankan perintah yang sama, lalu gagal bila client generate berubah (lupa di-commit), ditambah `build`.

## Struktur

```
src/
  app/                 # Routing saja. page.tsx cukup me-render komponen dari features/
  features/<domain>/   # Satu folder per domain bisnis
    types.ts           #   Label UI per enum (mis. leaveStatusLabels). Bukan bentuk data API
    api.ts             #   Hook yang menambah perilaku pada hook generate (polling, select). Opsional
    <logic>.ts         #   Logika murni (filter, validasi, kalkulasi) + <logic>.test.ts
    components/        #   UI. Memanggil hook/fungsi dari shared/api/generated
  shared/
    api/client.ts      # Fetch wrapper = mutator Orval (ApiError, timeout, redirect 401)
    api/generated/     # Hasil Orval: fungsi fetch, hook TanStack Query, model. Jangan diedit
    lib/               # Helper lintas fitur (format tanggal/uang)
    ui/                # Komponen generik: primitive shadcn + komposisi Teamku
  styles/legacy.css    # CSS lama, dibekukan
  middleware.ts        # Redirect /app/* ke /login bila cookie sesi tidak ada
```

## Mode demo

Akun demo (seed API) masuk lewat login biasa dan sesinya sama dengan akun nyata: cookie httpOnly `teamku_session`. Satu-satunya bagian khusus demo adalah `src/features/auth/components/demo-account-picker.tsx`, tombol akun demo + kredensial awal di login, aktif hanya bila `NEXT_PUBLIC_DEMO_ACCOUNTS=1`.

Cara menghapus: hapus file itu, lalu perbaiki error `tsc` yang muncul di halaman login.
