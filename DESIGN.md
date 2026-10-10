---
name: Teamku v2
description: Presensi dan HR yang tenang, lega, fokus.
colors:
  canvas: "#F3F2EF"
  surface: "#FFFFFF"
  surface-2: "#EFEEEA"
  line: "#E4E2DC"
  ink: "#17171A"
  ink-2: "#55565C"
  ink-3: "#6A6B71"
  side: "#0E0E0F"
  brand: "#E3163A"
  ok: "#0E7C55"
  ok-soft: "#E3F4EC"
  warn: "#A2560A"
  warn-soft: "#FCF0DE"
  info: "#2C55C7"
  info-soft: "#E7EDFB"
  danger: "#B42318"
  danger-soft: "#FDE9E7"
typography:
  display:
    fontFamily: "Newsreader, Georgia, serif"
    fontSize: "64px"
    fontWeight: 400
    lineHeight: 1
    letterSpacing: "-0.02em"
  title:
    fontFamily: "Newsreader, Georgia, serif"
    fontSize: "46px"
    fontWeight: 400
    lineHeight: 1.1
    letterSpacing: "-0.02em"
  headline:
    fontFamily: "Newsreader, Georgia, serif"
    fontSize: "34px"
    fontWeight: 400
    lineHeight: 1.15
    letterSpacing: "-0.02em"
  title-sm:
    fontFamily: "Newsreader, Georgia, serif"
    fontSize: "32px"
    fontWeight: 400
    lineHeight: 1.15
    letterSpacing: "-0.02em"
  heading:
    fontFamily: "Plus Jakarta Sans, system-ui, sans-serif"
    fontSize: "18px"
    fontWeight: 600
    lineHeight: 1.4
  body:
    fontFamily: "Plus Jakarta Sans, system-ui, sans-serif"
    fontSize: "15px"
    fontWeight: 500
    lineHeight: 1.45
  caption:
    fontFamily: "Plus Jakarta Sans, system-ui, sans-serif"
    fontSize: "13px"
    fontWeight: 500
    lineHeight: 1.4
rounded:
  control: "10px"
  field: "12px"
  card: "20px"
  dialog: "24px"
components:
  button-primary:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.surface}"
    rounded: "{rounded.control}"
    height: "42px"
    padding: "0 16px"
  button-primary-mobile:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.surface}"
    rounded: "{rounded.field}"
    height: "52px"
    padding: "0 20px"
  button-light:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    height: "42px"
  input:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.field}"
    height: "52px"
    padding: "0 16px"
  card:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.card}"
    padding: "28px"
  badge-soft:
    backgroundColor: "{colors.ok-soft}"
    textColor: "{colors.ok}"
    rounded: "999px"
    height: "26px"
    padding: "0 10px"
  dialog:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.dialog}"
    padding: "36px"
    width: "540px"
---

# Design System: Teamku v2

Sumber desain: papan `00 · Design System` di `mockups/design.pen`. Sumber kode: `@theme` di `apps/web/src/app/globals.css` (bila berbeda, kode yang benar dan file ini diperbarui). Contoh hidup: `/design-system` di dev server dan preview Vercel.

## 1. Overview

**Creative North Star: "Meja kerja yang rapi"**

Kanvas hangat keabuan, kartu putih tanpa garis, satu tombol hitam per layar. Judul dan angka penting memakai serif besar (Newsreader); semua kontrol, label, dan isi memakai Plus Jakarta Sans. Warna status hadir sebagai titik + teks, bukan blok warna. Merah disimpan untuk hal yang benar-benar mendesak.

Sistem ini menolak tampilan Teamku lama (merah dominan) dan template dashboard SaaS (kartu angka + gradien, grid kartu identik).

**Key Characteristics:**
- Monokrom + satu aksen mendesak (strategi Restrained).
- Hierarki lewat ukuran serif vs sans, bukan warna.
- Datar: kedalaman dari kontras kanvas ↔ kartu, bayangan hanya untuk lapisan melayang.
- Employee mobile-first (390), Manager & HR desktop-first (1440).

## 2. Colors

Netral hangat dengan status bernada redup.

### Primary
- **Ink** (#17171A, `primary` / `foreground`): teks utama dan satu tombol utama per layar.

### Neutral
- **Canvas** (#F3F2EF, `background`): latar halaman.
- **Surface** (#FFFFFF, `card` / `popover`): kartu, dialog, input.
- **Surface-2** (#EFEEEA, `secondary` / `muted` / `accent`): pil, tab aktif, hover.
- **Line** (#E4E2DC, `border` / `input`): hanya untuk input dan tabel.
- **Ink-2** (#55565C, `muted-foreground`): teks kedua.
- **Ink-3** (#6A6B71, `faint-foreground`): label, ikon pasif. Mockup memakai #86878D (3,6:1, gagal AA); kode memakai nilai yang lebih gelap.
- **Side** (#0E0E0F, `sidebar`): sidebar desktop.

### Status
- **Brand** (#E3163A, `brand`): mendesak saja: re-verifikasi, notifikasi belum dibaca, pin peta.
- **Ok** (#0E7C55 / #E3F4EC, `success` / `success-muted`): tepat waktu, disetujui.
- **Warn** (#A2560A / #FCF0DE, `warning` / `warning-muted`): menunggu, terlambat.
- **Info** (#2C55C7 / #E7EDFB, `info` / `info-muted`): cuti, informasi.
- **Danger** (#B42318 / #FDE9E7, `destructive` / `destructive-muted`): ditolak, error.

### Named Rules
**The Red Means Urgent Rule.** `brand` tidak pernah dipakai untuk dekorasi, tombol utama, atau aksen biasa.
**The Token Only Rule.** Komponen hanya memakai nama token (`bg-card`, `text-faint-foreground`). Hex langsung dan palet bawaan Tailwind (`bg-red-500`) dilarang.

## 3. Typography

**Display Font:** Newsreader (fallback Georgia, serif)
**Body Font:** Plus Jakarta Sans (fallback system-ui, sans-serif)

**Character:** Serif editorial yang tenang untuk judul dan angka, sans geometris yang hangat untuk semua UI.

### Hierarchy
- **Display** (400, 64px, 1): angka utama desktop (durasi kerja, saldo, gaji). Utility `font-display text-display`.
- **Title** (400, 46px, 1.1): judul halaman desktop. `font-display text-title`.
- **Headline** (400, 34px, 1.15): judul dialog. `font-display text-headline`.
- **Title-sm** (400, 32px, 1.15): judul halaman mobile. `font-display text-title-sm`.
- **Heading** (600, 18px, 1.4): judul kartu. `font-semibold text-heading`.
- **Body** (500, 15px, 1.45): isi, maks 65–75ch. `font-medium text-body`.
- **Caption** (500, 13px, 1.4): label dan meta. `font-medium text-caption`.

### Named Rules
**The Serif For Meaning Rule.** Serif hanya untuk judul halaman/dialog dan angka utama. Tombol, label, tabel, dan input selalu sans.

## 4. Elevation

Datar secara default. Kartu tidak punya garis maupun bayangan; kedalaman datang dari kartu putih di atas kanvas. Bayangan hanya untuk lapisan yang melayang di atas konten.

### Shadow Vocabulary
- **Overlay** (`box-shadow: 0 30px 80px rgb(0 0 0 / 0.25)`, `shadow-overlay`): dialog.

## 5. Components

Semua ada di `apps/web/src/shared/ui/`. Lihat `/design-system` untuk semua varian.

### Buttons
- **Shape:** radius `control` (10px) di desktop, `field` (12px) untuk ukuran mobile `lg`.
- **Primary** (`variant="default"`): ink, teks putih, 42px. Satu per layar.
- **Light** (`secondary`): putih tanpa garis, untuk di atas kanvas. **Outline**: putih bergaris, untuk di atas kartu putih. **Ghost**, **Link**.
- **Destructive:** latar `destructive-muted`, teks `destructive` (contoh: Tolak).
- **States:** hover menggelap/`surface-2`, fokus outline ink 2px offset 2px, disabled opacity 50%.

### Status (Badge)
- Titik 7px + teks. `soft` = pil 26px berlatar `*-muted` (mobile, kartu). `plain` = tanpa latar, 13/600 (tabel dan daftar desktop). Tone: `success`, `warning`, `info`, `destructive`, `neutral`.

### Cards
- **Corner Style:** 20px. **Background:** surface. **Border/Shadow:** tidak ada. **Padding:** 28px desktop, 20px mobile. Jangan menumpuk kartu di dalam kartu.

### Inputs / Fields
- **Style:** 52px, surface, garis `line`, radius 12px, teks 15/500 (16px di mobile).
- **Focus:** garis ink + ring ink 10%. **Error:** garis `destructive` + pesan `FieldError` di bawah, terhubung lewat `aria-describedby`.
- **Label** 13/600 ink, **hint** 12/500 `faint-foreground`. Susun dengan `Field`, `FieldLabel`, `FieldDescription`, `FieldError`.

### Dialog
- 540px, radius 24px, padding 36px (24px di mobile), `shadow-overlay`, overlay ink 30% tanpa blur. Judul serif `headline`, deskripsi body `muted-foreground`. Aksi kanan bawah: Batal (outline) lalu aksi utama.

## 6. Do's and Don'ts

- **Do** pasang `data-surface="v2"` di akar setiap halaman/shell v2; atribut ini memutus style elemen legacy dan memasang font v2.
- **Do** import `cn` dari `@/shared/lib/cn`, yang sudah mengenal ukuran teks custom.
- **Do** tampilkan status sebagai titik + teks.
- **Don't** pakai `brand` (merah) untuk hal yang tidak mendesak.
- **Don't** beri garis atau bayangan pada kartu.
- **Don't** pakai serif di tombol, label, atau tabel.
