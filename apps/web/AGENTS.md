# Aturan kode web (`apps/web`)

Next.js 15 (App Router) + React 19 + TanStack Query + Tailwind v4 + shadcn/ui. Perintah dan struktur folder: `README.md`. Keputusan arsitektur: `docs/adr/0001-web-frontend-architecture.md`. Token dan aturan visual: `DESIGN.md`. Gerbang sebelum push: `npm run check`.

**Pola acuan: `src/features/leave/`** (halaman Persetujuan: query, mutation, logika murni + test, Dialog shadcn). Salin polanya untuk layar baru.

## Arsitektur

- Arah import `app → features → shared`. Antar-feature hanya `types.ts`; kebutuhan lain dipindah ke `shared`.
- Import lintas folder memakai alias `@/`; di dalam satu feature boleh relatif (`../api`).
- `app/.../page.tsx` hanya me-render komponen dari `features/<domain>/components/`.
- Logika bisnis (filter, validasi, kalkulasi) di fungsi murni `features/<domain>/<logic>.ts` dengan `<logic>.test.ts`; komponen hanya merakit.
- Client state: `useState` lebih dulu. Zustand hanya untuk state UI yang dipakai komponen yang tidak bersaudara (contoh: `shared/ui/notifications.tsx`). Data API tinggal di cache TanStack Query.

## Server state

Client API di `src/shared/api/generated/` di-generate Orval dari `apps/api/openapi.json` dan tidak pernah diedit tangan. Nama fungsi/hook mengikuti aturan operationId di `apps/api/AGENTS.md` (`useListApprovals`, `useDecideApproval`).

- Data API dimuat lewat hook generate, dan type-nya dipakai apa adanya dari `@/shared/api/generated/model`, tanpa alias atau type tulisan tangan.
- Perilaku tambahan (polling, `select`, `enabled`, `meta`) dioper lewat opsi `query` di satu hook pembungkus di `features/<domain>/api.ts`, bukan di komponen: `usePolledNotifications()` = `useListNotifications({ query: { refetchInterval } })`.
- Invalidasi otomatis: setiap hook mutation generate yang sukses meng-invalidate semua query (`MutationCache` di `app/providers.tsx`), jadi tanpa `onSuccess` invalidasi dan tanpa query key per domain.
  - Query yang harus tetap (pratinjau token) memakai `meta: { keepOnMutation: true }`.
  - Panggilan yang tidak boleh memicu invalidasi (logout) memakai fungsi fetch biasa (`logout()`).
  - Fungsi fetch biasa di halaman legacy (`createLeaveRequest()`, …) tidak memicu invalidasi; cache lain (mis. saldo cuti di Beranda) basi sampai halaman itu dimigrasi.
- Setiap query punya state loading, error, dan kosong di UI; state kosong tampil hanya setelah `isSuccess`.
- Error: `errorMessage(error, fallback)` dari `@/shared/api/client`. `error` di setiap hook ber-type `ApiError<ErrorOut>`: `status` membedakan 403/404, `body.detail` berisi pesan atau daftar error field (422).
- Notifikasi lewat `notify({...})` dari `@/shared/ui/notifications`.
- API berubah: `npm run api:gen`, lalu ikuti error `tsc` ke setiap pemakaian.

## Komponen

- Urutan pilihan: komponen yang sudah ada di `src/shared/ui/` → primitive shadcn baru lewat `npx shadcn add <nama>` (satu per kebutuhan nyata layar) → komponen feature.
- Primitive shadcn (`button.tsx`, `dialog.tsx`, …) boleh diubah hanya untuk menyesuaikan design system (token, varian); perubahannya berlaku global dan tetap bebas logika domain.
- Komponen naik ke `shared/ui/` bila dipakai 2 feature atau lebih dan tidak tahu soal domain (tidak import `features/`, props berupa data generik). Selain itu tetap di `features/<domain>/components/`.
- Komponen reusable menerima `className` dan meneruskan props native (`...props`); varian lewat `cva`.
- Ikon kode baru dari `lucide-react`. `shared/ui/icon.tsx` adalah ikon lama yang dihapus setelah pemakainya habis.
- Aksesibilitas: setiap input punya `<label htmlFor>`, error memakai `aria-invalid` + `aria-describedby`, dialog memakai `Dialog` shadcn.
- Satu komponen utama per file; sub-komponen kecil yang hanya dipakai di file itu boleh tinggal di sana.
- Maksimal 600 baris per file (`npm run lint:size`). Mendekati batas: sub-komponen ke file sendiri, logika ke modul murni. File lama di `LEGACY_CAPS` (`scripts/check-file-lines.mjs`) tidak boleh bertambah panjang.

## Styling

- Akar setiap halaman/shell v2 diberi `data-surface="v2"`: memasang font v2 dan memutus style elemen legacy.
- Warna hanya lewat token (`bg-primary`, `text-muted-foreground`, `text-success`, …) dari `src/app/globals.css`; hex dan palet bawaan Tailwind (`bg-red-500`) di luar aturan.
- Tipografi lewat token: `font-display text-title` judul halaman, `text-heading` judul kartu, `text-body` isi. Weight dan line-height ikut token.
- `cn` diimpor dari `@/shared/lib/cn` (mengenal ukuran teks custom); setelah `npx shadcn add`, ganti import-nya.
- Mengubah token: edit `@theme` di `app/globals.css`, lalu `npm run design:sync`.
- `styles/legacy.css` dibekukan. Urutan `@layer`: `legacy` < `ui-reset` < `utilities`, jadi utility selalu menang atas CSS lama. Preflight Tailwind masih mati sampai revamp v2 selesai; `ui-reset` yang mencegah style elemen legacy bocor ke shadcn dan permukaan v2.

## Memigrasi satu halaman lama

1. Ganti `useEffect` + fungsi fetch generate dengan hook generate (`useListLeaveRequests`, …), plus pembungkus di `features/<domain>/api.ts` bila perlu perilaku tambahan.
2. Pindahkan logika non-UI ke fungsi murni + test.
3. Pindahkan JSX ke `features/<domain>/components/<nama>-page.tsx`, lalu jadikan `app/.../page.tsx` re-export. Tombol, dialog, dan input dari `shared/ui`.
4. Hapus path halaman itu dari override "legacy" di `biome.json` (dan dari `LEGACY_CAPS` bila ada), lalu perbaiki lint yang muncul.
5. Satu halaman per PR.

**Selesai bila:** `npm run check` hijau dan halaman tidak lagi tercantum di override legacy `biome.json`.
