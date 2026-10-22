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
- **Auth**: cookie httpOnly `teamku_session` menjadi sumber kebenaran, dan `middleware.ts` menjaga `/app/*`. Token tidak pernah disimpan di JS: salinan demo di localStorage/header `X-Demo-User` dihapus (#41), akun demo pun login lewat cookie.
- **Client API di-generate dari OpenAPI** (2026-10-22, #46). `apps/api/openapi.json` (di-commit, dijaga test di API) adalah kontraknya. Orval meng-generate fungsi fetch, hook TanStack Query, dan model ke `shared/api/generated/` dengan `api()` sebagai mutator. `npm run check` meregenerate client, CI web gagal bila hasilnya berbeda dengan yang di-commit, dan CI web ikut jalan saat spec berubah. Browser memanggil path spec apa adanya (`/api/v1/...`); rewrite Next meneruskannya ke API tanpa mengubah path. Type data API tidak lagi ditulis tangan.
- **Invalidasi cache otomatis** (#46): setiap mutation sukses meng-invalidate semua query lewat `MutationCache`, menggantikan query key per domain. Batasnya refetch ekstra untuk query yang sedang tampil; dipersempit per mutation (`meta`) bila nanti terasa berat.

## Alternatif yang ditolak

- **RSC + fetch di server**: lebih "Next-native", tetapi harus meneruskan cookie ke FastAPI dan menulis ulang semua halaman sekaligus. Query bisa dimigrasi per halaman.
- ~~**Generate type dari OpenAPI**: endpoint FastAPI belum memakai `response_model`, sehingga skema respons kosong.~~ Dipakai sejak #46, setelah revamp API memberi setiap endpoint schema respons (lihat Keputusan).
- **Hook hasil generate dengan query key per domain** (#46): key Orval berbasis URL, sehingga invalidasi per prefix domain (`["leave"]`) tidak lagi bisa. Diganti invalidasi otomatis.
- **Redux/global store untuk data API**: duplikasi cache yang sudah dikelola Query.

## Konsekuensi

- Halaman lama tetap jalan dan dimigrasi satu per satu. Override "legacy" di `biome.json` menunjukkan halaman yang tersisa.
- Logika demo bisa dihapus dengan menghapus dua file; `tsc` akan menunjukkan sisa pemanggilnya.
