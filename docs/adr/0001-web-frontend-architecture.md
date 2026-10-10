# 0001 — Arsitektur front-end web: feature-based + TanStack Query

- Status: diterima
- Tanggal: 2026-10-09

## Konteks

`apps/web` tumbuh tanpa fondasi. Setiap halaman berupa satu file client yang mengambil data sendiri lewat `useEffect`, type API ditulis ulang per halaman, token disebar lewat localStorage, ada CSS global 65KB, dan tidak ada lint, test, maupun CI. Dua engineer akan mengerjakan revamp v2 (`docs/revamp/`) secara paralel, sehingga butuh pola yang seragam.

## Keputusan

- **Struktur feature-based**: `app/` hanya routing, `features/<domain>/` berisi types, api hooks, logika murni, dan komponen, sedangkan `shared/` untuk hal generik. Arah import: `app → features → shared`.
- **TanStack Query** untuk seluruh server state, dan **Zustand** hanya untuk state UI lintas komponen.
- **Tailwind v4** tanpa preflight selama migrasi. CSS lama dibekukan di `layer(legacy)` di bawah layer utilities.
- **shadcn/ui (Radix)** sebagai primitive UI di `shared/ui/`. Komponen ditambahkan hanya saat dibutuhkan; warna lewat token semantik di `globals.css`. Layer `ui-reset` melindungi komponen ini dari CSS legacy selama preflight dimatikan.
- **Batas 600 baris per file** dan **nama file kebab-case**, dipaksa oleh `scripts/check-file-lines.mjs` dan Biome.
- **Biome** menggantikan ESLint + Prettier. **Vitest** untuk logika murni. CI GitHub Actions menjalankan `npm run check` + build.
- **Auth**: cookie httpOnly `teamku_session` menjadi sumber kebenaran, dan `middleware.ts` menjaga `/app/*`. Token demo di localStorage/`X-Demo-User` dipertahankan sementara, tetapi diisolasi di dua file (lihat `apps/web/README.md`).

## Alternatif yang ditolak

- **RSC + fetch di server**: lebih "Next-native", tetapi harus meneruskan cookie ke FastAPI dan menulis ulang semua halaman sekaligus. Query bisa dimigrasi per halaman.
- **Generate type dari OpenAPI**: endpoint FastAPI belum memakai `response_model`, sehingga skema respons kosong. Bisa ditinjau ulang setelah API menambahkannya.
- **Redux/global store untuk data API**: duplikasi cache yang sudah dikelola Query.

## Konsekuensi

- Halaman lama tetap jalan dan dimigrasi satu per satu. Override "legacy" di `biome.json` menunjukkan halaman yang tersisa.
- Logika demo bisa dihapus dengan menghapus dua file; `tsc` akan menunjukkan sisa pemanggilnya.
