---
name: slice-screen
description: Slice one Teamku v2 revamp screen (kode seperti D3, M6, HM4, P2a) dari mockup menjadi kode di apps/web. Use when implementing, building, or slicing a revamp/mockup screen or its STATE variants.
---

# Slice screen

Satu run = satu kode layar beserta varian STATE-nya = satu branch = satu PR.
Aturan kode ada di `apps/web/README.md` dan dipaksa CI; baca bagian **Aturan** sebelum mulai. Pola acuan: `apps/web/src/features/leave/`.

## 1. Spesifikasi layar

- Cari kode layar di `docs/revamp/2026-09-29-role-flows.md` (§8 inventaris, §10 tabel per fase): nama layar, isi inti, role yang melihatnya (§2 matriks akses), dan semua varian `<kode>-*` / STATE.
- Lihat export PNG di `mockups/exports/` (tabel file per section ada di `docs/revamp/2026-09-29-review-brief.md`) untuk layout desktop dan mobile.
- Nilai persis (spacing, radius, warna, font) ada di `mockups/design.pen`, dibaca lewat Pencil MCP. File harus terbuka di aplikasi Pencil; bila tool menolak, minta user membukanya. Jangan menebak nilai dari PNG kalau Pencil tersedia.

**Selesai bila:** semua varian layar terdaftar, dan role serta breakpoint (desktop 1440, mobile) diketahui.

## 2. Kontrak data

Untuk setiap angka/teks dinamis di layar, temukan endpoint dan field-nya di `apps/api/src/movon_hr/modules/api.py` (atau type yang sudah ada di `features/*/types.ts`).

Fitur berlabel **BARU** di brief, atau data yang tidak punya endpoint, adalah **celah backend**: berhenti dan laporkan daftarnya ke user (layar, data, endpoint yang dibutuhkan). Jangan mengarang data, jangan memakai mock permanen.

**Selesai bila:** setiap elemen dinamis punya endpoint + field, atau tercatat sebagai celah dan user sudah memutuskan.

## 3. Inventaris komponen

Buat tabel dan tunjukkan ke user **sebelum coding**:

| Elemen di mockup | Keputusan | Lokasi |
|---|---|---|
| Tombol utama | pakai `Button` | `shared/ui/button.tsx` |
| Sheet keputusan | `npx shadcn add sheet` | `shared/ui/sheet.tsx` |
| Kartu saldo cuti | komponen feature | `features/leave/components/balance-card.tsx` |

Keputusan per elemen, urut dari yang paling diutamakan: sudah ada di `shared/ui/` → primitive shadcn baru (via CLI) → komponen feature. Komponen naik ke `shared/ui/` hanya bila memenuhi syarat reusable di README.

Token: bila warna/font mockup belum ada di `@theme` pada `apps/web/src/app/globals.css` (token sekarang masih sementara), tambahkan token v2 dari `design.pen` di sana dalam PR yang sama, bukan sebagai hex di komponen.

**Selesai bila:** setiap elemen visual punya baris di tabel dan user setuju.

## 4. Implementasi

Ikuti pola `features/leave`: `types.ts` → hook di `api.ts` → logika murni + `*.test.ts` → komponen → `app/.../page.tsx` re-export. Bila layar menggantikan halaman legacy, lakukan juga langkah "Memigrasi satu halaman lama" di README.

**Selesai bila:** setiap varian dari langkah 1 punya representasi di kode (loading, error, kosong, dan STATE dari mockup), dan logika bercabang punya test.

## 5. Verifikasi parity

1. `npm run check` di `apps/web` hijau.
2. Jalankan app (`npm run dev`, API lokal di `:8000`), login dengan akun demo sesuai role, buka layar.
3. Screenshot desktop (1440) dan mobile (390) lewat Playwright, bandingkan berdampingan dengan PNG mockup. Catat setiap selisih (layout, spacing, warna, teks) lalu perbaiki, atau laporkan sebagai keputusan sadar.
4. Uji keyboard: Tab mencapai semua aksi, Escape menutup dialog/sheet.

**Selesai bila:** check hijau dan tidak ada selisih parity yang belum diperbaiki atau dilaporkan.

## 6. PR

Branch `feat/screen-<kode>`, satu PR per layar. Badan PR berisi: kode layar, tabel inventaris dari langkah 3, screenshot desktop + mobile, dan daftar celah backend atau selisih parity yang disengaja.
