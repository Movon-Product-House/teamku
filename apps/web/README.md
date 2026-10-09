# Teamku Web

Next.js 15 (App Router) + React 19 + TanStack Query + Zustand + Tailwind v4 + shadcn/ui (Radix) + Biome + Vitest.
Keputusan arsitekturnya ada di [`docs/adr/0001-web-frontend-architecture.md`](../../docs/adr/0001-web-frontend-architecture.md).

## Perintah

| Perintah | Fungsi |
|---|---|
| `npm run dev` | Dev server. Request `/api/*` di-proxy ke `MOVON_API_ORIGIN` (default `http://127.0.0.1:8000`) |
| `npm run check` | Gerbang yang sama dengan CI: `biome ci` + batas panjang file + `tsc` + `vitest` |
| `npm run lint:fix` | Format + organize imports + fix lint yang aman |
| `npm run lint:size` | Cek batas 600 baris per file |
| `npm test` | Vitest |
| `npx shadcn add <nama>` | Menambah komponen shadcn ke `src/shared/ui/` (lihat aturan Komponen) |

Jalankan `npm run check` sebelum push. CI (`.github/workflows/web.yml`) menjalankan perintah yang sama, ditambah `build`.

## Struktur

```
src/
  app/                 # Routing saja. page.tsx cukup me-render komponen dari features/
  features/<domain>/   # Satu folder per domain bisnis
    types.ts           #   Bentuk data API untuk domain ini (satu sumber)
    api.ts             #   Query key + hook useQuery/useMutation
    <logic>.ts         #   Logika murni (filter, validasi, kalkulasi) + <logic>.test.ts
    components/        #   UI. Tidak memanggil api() secara langsung
  shared/
    api/client.ts      # Satu-satunya fetch wrapper (ApiError, timeout, redirect 401)
    api/demo-session.ts# DEMO-ONLY, lihat "Mode demo"
    lib/               # Helper lintas fitur (format tanggal/uang)
    ui/                # Komponen generik: primitive shadcn + komposisi Teamku
  styles/legacy.css    # CSS lama, dibekukan. Jangan ditambah
  middleware.ts        # Redirect /app/* ke /login bila cookie sesi tidak ada
```

**Contoh acuan: `features/leave/`** (halaman Persetujuan: query, mutasi, logika murni + test, Dialog shadcn). Salin polanya saat memigrasi halaman lain.

## Aturan

### Arsitektur
1. **Arah import:** `app → features → shared`. `shared` tidak boleh import dari `features`. Antar-feature hanya boleh import `types.ts`. Bila butuh lebih dari itu, pindahkan ke `shared`.
2. **Import pakai alias `@/`**, bukan `../../`. Di dalam feature yang sama boleh relatif (`../api`).
3. **Server state = TanStack Query.** Jangan memakai `useEffect` + `useState` untuk fetch. Setelah mutasi, invalidate key-nya (`queryClient.invalidateQueries`), jangan load ulang manual.
4. **Client state:** `useState` lebih dulu. Zustand hanya untuk state UI yang dipakai lintas komponen yang tidak bersaudara (contoh: `shared/ui/notifications.tsx`). Data dari API jangan disimpan di Zustand.
5. **Logika bisnis keluar dari komponen** ke fungsi murni di feature, dan diberi test. Komponen hanya merakit.
6. **Setiap query punya tiga state di UI:** loading, error, kosong. Jangan tampilkan state "kosong" sebelum data selesai dimuat (`isSuccess`).
7. **Notifikasi:** panggil `notify({...})` dari `@/shared/ui/notifications`. Jangan membuat state `NotificationDialog` lokal.
8. **Error:** pakai `errorMessage(error, fallback)` dari client. `ApiError.status` tersedia bila perlu membedakan 403/404.

### Komponen & shadcn/ui
1. **Cek `src/shared/ui/` dulu.** Bila komponennya sudah ada, pakai itu. Jangan membuat versi sendiri dari Button, Dialog, dan sejenisnya.
2. **Tambah komponen shadcn hanya saat ada layar yang membutuhkannya**, lewat `npx shadcn add <nama>`, satu komponen per kebutuhan nyata. Jangan menambah komponen "untuk nanti", dan jangan copy-paste dari situs.
3. **File primitive shadcn (`button.tsx`, `dialog.tsx`, …) boleh diubah**, tetapi hanya untuk menyesuaikan dengan design system Teamku (token, varian), dan perubahan ini berlaku global. Logika domain tidak boleh masuk ke sana.
4. **Warna hanya lewat token** (`bg-primary`, `text-muted-foreground`, `bg-destructive`, `text-success`, …) yang didefinisikan di `src/app/globals.css`. Dilarang menulis hex langsung atau memakai palet bawaan (`bg-red-500`).
5. **Kapan komponen naik ke `shared/ui/`:** bila dipakai di 2 feature atau lebih, dan tidak tahu apa-apa soal domain (tidak import dari `features/`, props berupa data generik). Bila hanya dipakai satu feature, tetap di `features/<domain>/components/`.
6. **Komponen reusable menerima `className` dan meneruskan props native** (`...props`), seperti pola shadcn. Varian memakai `cva`, bukan if-else className.
7. **Ikon:** `lucide-react` untuk kode baru. `shared/ui/icon.tsx` adalah ikon lama dan dihapus setelah semua pemakainya dimigrasi.
8. **Aksesibilitas wajib:** setiap input punya `<label htmlFor>`, error memakai `aria-invalid` + `aria-describedby`, dan dialog harus memakai `Dialog` shadcn (fokus, Escape, overlay sudah ditangani).

### Ukuran & penamaan
1. **Maksimal 600 baris per file** (`npm run lint:size`, ikut di CI). Bila mendekati batas, pecah: sub-komponen ke file sendiri, logika ke modul murni. Dua file lama yang sudah melewati batas dikunci di `scripts/check-file-lines.mjs` dan tidak boleh bertambah panjang.
2. **Nama file kebab-case** (`decision-dialog.tsx`), dipaksa oleh Biome. Nama komponen tetap PascalCase (`DecisionDialog`).
3. Satu komponen utama per file. Sub-komponen kecil yang hanya dipakai di file itu boleh tinggal di file yang sama.

### Styling
Komponen baru memakai utility Tailwind. Urutan `@layer` di `app/globals.css`: `legacy` < `ui-reset` < `utilities`. Artinya utility selalu menang atas CSS lama, dan `ui-reset` mencegah style elemen global legacy (h2, label, textarea, …) bocor ke komponen shadcn. Preflight Tailwind baru dinyalakan setelah revamp v2 selesai.

## Memigrasi satu halaman lama

1. Buat `features/<domain>/{types,api}.ts`, lalu pindahkan type dan panggilan API ke sana sebagai hook.
2. Pindahkan logika non-UI ke fungsi murni + test.
3. Pindahkan JSX ke `features/<domain>/components/<nama>-page.tsx`, lalu jadikan `app/.../page.tsx` re-export. Pakai komponen `shared/ui` untuk tombol, dialog, dan input.
4. Hapus path halaman itu dari override "legacy" di `biome.json` (dan dari `LEGACY_CAPS` bila ada), lalu perbaiki lint yang muncul.
5. `npm run check` hijau → PR. Satu halaman per PR supaya dua engineer tidak saling konflik.

## Mode demo

Akun demo dan token `X-Demo-User` di localStorage sengaja diisolasi supaya mudah dihapus:

- `src/shared/api/demo-session.ts`: penyimpanan token + header
- `src/features/auth/components/demo-account-picker.tsx`: tombol akun demo + kredensial awal di login

Cara menghapus: hapus kedua file, lalu perbaiki error `tsc` yang muncul (semua pemanggilnya ikut ketahuan), dan hapus header `X-Demo-User` di `apps/api`. Sesi tetap berjalan lewat cookie httpOnly `teamku_session`.
