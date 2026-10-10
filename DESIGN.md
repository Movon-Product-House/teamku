---
name: Teamku v2
description: Presensi dan HR yang tenang, lega, fokus.
# GENERATED:BEGIN — npm run design:sync (sumber: apps/web/src/app/globals.css)
colors:
  background: "#F3F2EF"
  foreground: "#17171A"
  card: "#FFFFFF"
  card-foreground: "#17171A"
  popover: "#FFFFFF"
  popover-foreground: "#17171A"
  primary: "#17171A"
  primary-foreground: "#FFFFFF"
  secondary: "#EFEEEA"
  secondary-foreground: "#17171A"
  muted: "#EFEEEA"
  muted-foreground: "#55565C"
  faint-foreground: "#6A6B71"
  accent: "#EFEEEA"
  accent-foreground: "#17171A"
  border: "#E4E2DC"
  input: "#E4E2DC"
  ring: "#17171A"
  sidebar: "#0E0E0F"
  sidebar-foreground: "#FFFFFF"
  brand: "#E3163A"
  destructive: "#B42318"
  destructive-muted: "#FDE9E7"
  success: "#0E7C55"
  success-muted: "#E3F4EC"
  warning: "#A2560A"
  warning-muted: "#FCF0DE"
  info: "#2C55C7"
  info-muted: "#E7EDFB"
typography:
  display:
    fontFamily: "Newsreader, ui-serif, Georgia, serif"
    fontSize: "64px"
    fontWeight: 400
    lineHeight: 1
    letterSpacing: "-0.02em"
  title:
    fontFamily: "Newsreader, ui-serif, Georgia, serif"
    fontSize: "46px"
    fontWeight: 400
    lineHeight: 1.1
    letterSpacing: "-0.02em"
  headline:
    fontFamily: "Newsreader, ui-serif, Georgia, serif"
    fontSize: "34px"
    fontWeight: 400
    lineHeight: 1.15
    letterSpacing: "-0.02em"
  title-sm:
    fontFamily: "Newsreader, ui-serif, Georgia, serif"
    fontSize: "32px"
    fontWeight: 400
    lineHeight: 1.15
    letterSpacing: "-0.02em"
  heading:
    fontFamily: "Plus Jakarta Sans, ui-sans-serif, system-ui, sans-serif"
    fontSize: "18px"
    fontWeight: 600
    lineHeight: 1.4
  body:
    fontFamily: "Plus Jakarta Sans, ui-sans-serif, system-ui, sans-serif"
    fontSize: "15px"
    fontWeight: 500
    lineHeight: 1.45
  caption:
    fontFamily: "Plus Jakarta Sans, ui-sans-serif, system-ui, sans-serif"
    fontSize: "13px"
    fontWeight: 500
    lineHeight: 1.4
rounded:
  control: "10px"
  field: "12px"
  card: "20px"
  dialog: "24px"
# GENERATED:END
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.primary-foreground}"
    rounded: "{rounded.control}"
    height: "42px"
    padding: "0 16px"
  button-primary-mobile:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.primary-foreground}"
    rounded: "{rounded.field}"
    height: "52px"
    padding: "0 20px"
  button-light:
    backgroundColor: "{colors.card}"
    textColor: "{colors.foreground}"
    rounded: "{rounded.control}"
    height: "42px"
  input:
    backgroundColor: "{colors.card}"
    textColor: "{colors.foreground}"
    rounded: "{rounded.field}"
    height: "52px"
    padding: "0 16px"
  card:
    backgroundColor: "{colors.card}"
    rounded: "{rounded.card}"
    padding: "28px"
  badge-soft:
    backgroundColor: "{colors.success-muted}"
    textColor: "{colors.success}"
    rounded: "999px"
    height: "26px"
    padding: "0 10px"
  dialog:
    backgroundColor: "{colors.popover}"
    rounded: "{rounded.dialog}"
    padding: "36px"
    width: "540px"
---

# Design System: Teamku v2

Sumber desain: papan `00 · Design System` di `mockups/design.pen`. Sumber nilai di kode: `@theme` di `apps/web/src/app/globals.css`. Bagian frontmatter di antara penanda `GENERATED` dibuat ulang oleh `npm run design:sync` (CI gagal bila tidak sinkron); bagian lain ditulis tangan dan hanya memakai nama token. Contoh hidup: `/design-system` di dev server dan preview Vercel.

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
- **Ink** (`primary` / `foreground`): teks utama dan satu tombol utama per layar.

### Neutral
- **Canvas** (`background`): latar halaman.
- **Surface** (`card` / `popover`): kartu, dialog, input.
- **Surface-2** (`secondary` / `muted` / `accent`): pil, tab aktif, hover.
- **Line** (`border` / `input`): hanya untuk input dan tabel.
- **Ink-2** (`muted-foreground`): teks kedua.
- **Ink-3** (`faint-foreground`): label, ikon pasif. Lebih gelap dari mockup (#86878D, 3,6:1) agar lolos WCAG AA.
- **Side** (`sidebar`): sidebar desktop.

### Status
- **Brand** (`brand`): mendesak saja: re-verifikasi, notifikasi belum dibaca, pin peta.
- **Ok** (`success` / `success-muted`): tepat waktu, disetujui.
- **Warn** (`warning` / `warning-muted`): menunggu, terlambat.
- **Info** (`info` / `info-muted`): cuti, informasi.
- **Danger** (`destructive` / `destructive-muted`): ditolak, error.

### Named Rules
**The Red Means Urgent Rule.** `brand` tidak pernah dipakai untuk dekorasi, tombol utama, atau aksen biasa.
**The Token Only Rule.** Komponen hanya memakai nama token (`bg-card`, `text-faint-foreground`). Hex langsung dan palet bawaan Tailwind (`bg-red-500`) dilarang.

## 3. Typography

**Display Font:** Newsreader (fallback Georgia, serif)
**Body Font:** Plus Jakarta Sans (fallback system-ui, sans-serif)

**Character:** Serif editorial yang tenang untuk judul dan angka, sans geometris yang hangat untuk semua UI.

### Hierarchy
Setiap utility `text-*` sudah membawa ukuran, line-height, letter-spacing, dan weight; cukup tambahkan `font-display` untuk yang serif.

- **Display**: angka utama desktop (durasi kerja, saldo, gaji). Utility `font-display text-display`.
- **Title**: judul halaman desktop. `font-display text-title`.
- **Headline**: judul dialog. `font-display text-headline`.
- **Title-sm**: judul halaman mobile. `font-display text-title-sm`.
- **Heading**: judul kartu. `text-heading`.
- **Body**: isi, maks 65–75ch. `text-body`.
- **Caption**: label dan meta. `text-caption`.

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
