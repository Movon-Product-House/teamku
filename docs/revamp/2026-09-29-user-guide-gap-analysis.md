# Analisis Gap: Teamku User Guide V1 vs Kode Saat Ini

- Tanggal: 29 September 2026
- Sumber: `tmp/Teamku User Guide_V1.docx` (PM, v1.0, 26 Sep 2026) + `tmp/docs-revisi-teamku.xlsx` (catatan revisi calon mitra)
- **Baseline: `origin/main` (`d76cad8`).** Keputusan 29 Sep 2026: revamp dimulai dari awal di atas `origin/main`. Branch `feat/f3-*` / `feat/f2-*` hanya jadi referensi.
- Tujuan: dasar untuk refactor + revamp UI/UX, sebelum dibuat mockup di `mockups/design.pen`

---

## 0. Temuan paling penting (baca dulu)

1. **Baseline revamp = `origin/main`.** Fitur F1–F3 (edit karyawan, 5 status + arsip, profil perusahaan, panel undangan, aturan password, label "Email HR resmi", show/hide password) **tidak ada di `main`**. Semuanya hanya ada di rantai branch `feat/f3-*` → `feat/f2-invite-panel-activation-link`. Revamp akan membangun ulang kebutuhan ini dari awal; branch lama hanya referensi.
2. **User Guide V1 ditulis dari kode `main`**, jadi sebagian besar cocok dengan baseline. Ketidaksesuaian ada di §3.
3. **Ada beberapa bug UX nyata** yang langsung terlihat user. Lihat §4.1.
4. **UI saat ini tidak punya design system.** Semua style ada di satu `globals.css` 64 KB yang di-minify manual, warna hex tersebar, ukuran teks 9–11 px, ikon campur (SVG + karakter Unicode + emoji). Lihat §5.

---

## 1. Ringkasan isi User Guide V1

| Bagian | Isi pokok |
|---|---|
| Mulai cepat | Login → cek role di panel akun → Beranda → izinkan kamera & lokasi → lonceng notifikasi |
| Bagian 1 | Login, lupa sandi, undangan, buat workspace; elemen navigasi (sidebar, pencarian, notifikasi, panel akun, nav mobile); matriks akses 3 role; menu per role |
| Employee | 6 user story: Beranda, check-in (prioritas → kamera → foto → setuju lokasi → konfirmasi), re-verifikasi, check-out, cuti, Ask Teamku, slip gaji |
| Manager | 5 user story: ringkasan departemen, direktori tim, riwayat lokasi, persetujuan cuti, fitur personal |
| HR Admin | 6 user story: buat workspace, tambah/undang karyawan, status & lokasi karyawan, persetujuan semua dept, payroll Draft→Finalized→Published, lokasi presensi, re-verifikasi & alert, kalender, kebijakan Draft→Published→Archived |
| Bagian 6 | Tabel status (presensi, cuti, payroll, karyawan), privasi & batas MVP, troubleshooting, kapan hubungi HR |

Menu per role (dari guide, sesuai `Shell.tsx`):

| Role | Workspace | Operations |
|---|---|---|
| Employee | Beranda, Kehadiran, Agenda & Cuti, Ask Teamku | Slip Gaji |
| Manager | + Karyawan | Persetujuan, Slip Gaji |
| HR Admin | + Karyawan | Persetujuan, Payroll, Slip Gaji, Pengaturan, Kebijakan |

---

## 2. Peta fitur: guide ↔ halaman ↔ kode

| Fitur (guide) | Route | File | Status vs guide |
|---|---|---|---|
| Login / lupa / reset / undangan / signup | `/login`, `/forgot-password`, `/reset-password`, `/invite`, `/signup` | `app/*/page.tsx`, `AuthShell.tsx` | Sesuai. Branch baru menambah aturan password + label "Email HR resmi" |
| Shell: sidebar, cari, lonceng, akun, nav mobile | semua `/app/*` | `components/Shell.tsx` | Sebagian tidak sesuai (lihat §3) |
| Beranda | `/app/overview` | `app/app/overview/page.tsx` | Sesuai secara data, banyak elemen palsu (lihat §4) |
| Presensi (check-in, re-verifikasi, check-out) | `/app/attendance/today` | `attendance/today/page.tsx` | Sesuai alurnya, ada bug kamera re-verifikasi |
| Cuti & izin | `/app/time/time-off` | `time/time-off/page.tsx` | Sesuai, hanya 1 jenis cuti |
| Ask Teamku | `/app/ask-teamku` | `ask-teamku/page.tsx` | Sesuai inti, banyak link salah & data dummy |
| Direktori + profil | `/app/people`, `/app/people/[id]` | `people/*.tsx` | Guide usang vs branch baru |
| Persetujuan | `/app/approvals` | `approvals/page.tsx` | Sesuai; "Perlu revisi" tidak ada di UI (guide sudah jujur soal ini) |
| Payroll | `/app/payroll/runs` | `payroll/runs/page.tsx` | Sesuai |
| Slip gaji | `/app/payroll/payslips` | `payroll/payslips/page.tsx` | Sesuai |
| Pengaturan (lokasi, re-verifikasi, alert, kalender, + profil perusahaan di branch baru) | `/app/settings` | `settings/page.tsx`, `CompanyProfileCard.tsx` | Sesuai; guide belum memuat profil perusahaan |
| Kebijakan | `/app/settings/policies` | `settings/policies/page.tsx` | Sesuai |

---

## 3. Ketidaksesuaian guide ↔ kode (frontend)

| # | Guide bilang | Kode sebenarnya | Aksi |
|---|---|---|---|
| G1 | "Pilih avatar di kanan atas untuk melihat nama dan role, lalu keluar" | Avatar kanan atas (`.top-avatar`) hanya `<span>`, tidak bisa diklik. Nama + role + tombol keluar ada di **bawah sidebar**. Di mobile sidebar hilang; keluar lewat ikon logout di topbar | Revamp: jadikan avatar = menu akun (nama, role, workspace, keluar) |
| G2 | "Pencarian atas: Cari karyawan atau menu" | Hanya daftar menu statis. Tidak ada pencarian karyawan, tidak ada input, `⌘K` tidak terpasang | Revamp: command palette sungguhan (menu + karyawan untuk Manager/HR) |
| G3 | Menu "Agenda & Cuti" | Halaman itu hanya **Cuti & izin**. Agenda ada di Kehadiran/Beranda | Ganti label menu jadi "Cuti & Izin" |
| G4 | Direktori HR: Tangguhkan / Aktifkan | Sesuai di `main`. Tidak ada edit data, status resign/handover, atau arsip (permintaan mitra #1, #2) | Masuk scope revamp |
| G5 | Undangan: tautan 7 hari | Sesuai di `main`, tapi tidak ada daftar/status undangan, kirim ulang, atau batalkan (permintaan mitra #4) | Masuk scope revamp |
| G6 | Signup: "email kerja", tidak ada info aturan password | Sesuai di `main` (permintaan mitra #5, #7 belum ada) | Masuk scope revamp |
| G7 | Istilah "Sales atau lapangan" | UI Kehadiran pakai istilah **"Pekerja remote"**, direktori pakai "Sales / Lapangan", notifikasi profil pakai "pekerja remote" | Satukan istilah: "Lapangan" |
| G8 | Nav mobile: "menu bawah untuk fitur utama" | Menu bawah = 4 item pertama (Beranda, Kehadiran, Agenda & Cuti, Ask Teamku). Slip Gaji & semua Operations hanya lewat hamburger | Revamp: tab bar per role + "Lainnya" |
| G9 | "Kartu Agenda menampilkan jumlah agenda dari prioritas check-in" | Benar, tapi baris agenda di Beranda adalah **teks placeholder** ("Agenda kerja hari ini", "N agenda perlu ditindaklanjuti"), bukan item nyata | Lihat §4 |

> Catatan: hasil cek backend (klaim guide vs API) ada di §6.

---

## 4. Masalah UX per halaman

### 4.1 Bug nyata (prioritas tinggi)

| # | Masalah | Bukti | Dampak |
|---|---|---|---|
| B1 | **Di mobile (≤760 px) semua `.secondary-button` disembunyikan** | `globals.css` `@media(max-width:760px){… .secondary-button{display:none} …}`. Hanya `.settings-actions` & `.ask-help` yang di-override | Tombol **Batal** di dialog persetujuan, **Tunda sebentar** di re-verifikasi, **Tutup** di notifikasi, **Simpan langsung** di tambah karyawan, **Perbarui** di slip gaji, **Tambah bagian** di kebijakan, **Batal** konfirmasi — hilang di HP |
| B2 | **Kamera re-verifikasi tidak terlihat** | Dialog re-verifikasi memanggil `startCamera()`, tapi `<video>` ada di kartu halaman **di belakang backdrop modal** | Pekerja kantor ambil selfie tanpa bisa melihat wajahnya |
| B3 | **Ask Teamku: link salah & terlarang** | "Cuti & Leave", "Sakit & Izin", "Ajukan Cuti" → `/app/approvals` (Employee tidak punya akses). "Slip Gaji", "Payroll", "Absensi" → `/app/overview`. "Profil Saya" → `/app/people` (Employee tidak punya akses). "Kebijakan Perusahaan" → `/app/settings/policies` (HR saja, redirect) | Employee diarahkan ke halaman salah / ditolak |
| B4 | **Ask Teamku: "Riwayat Percakapan" palsu** | Array hardcode + waktu palsu ("2 jam yang lalu") | Menyesatkan user |
| B5 | **Hubungi HR = `mailto:hr@company.local`** | Hardcode 3x | Link mati. Branch baru sudah punya `tenant.hr_email` → pakai itu |
| B6 | **Jawaban Ask Teamku muncul paling bawah** | Render setelah Topik Populer + Butuh bantuan | User harus scroll untuk melihat jawaban |
| B7 | **Kredensial demo tampil di halaman login** | `login/page.tsx`: tombol akun demo + "Semua akun menggunakan kata sandi Demo123!" + prefill | Tidak pantas untuk produksi / calon mitra |
| B8 | **Agenda tidak bisa diperbarui** | Tidak ada endpoint/UI update agenda. Beranda bilang "Perbarui status dari halaman presensi" + tombol "+ Tambah agenda" → ke Kehadiran yang tidak punya fitur itu | Progress agenda selalu 0% |
| B9 | **Kebijakan: pakai `confirm()` bawaan browser, error publish/arsip tidak ditangani, pesan sukses tampil dengan style error (`field-error`)** | `settings/policies/page.tsx` | Inkonsisten, error diam |
| B10 | **Payroll: Finalisasi & Publikasikan tanpa konfirmasi** | Langsung `POST` | Aksi yang tidak bisa dibatalkan tanpa pengaman |

### 4.2 Beranda (`/app/overview`)
- Elemen dekoratif palsu: "date picker" yang bukan picker, jam analog statis (jarum tidak bergerak), emoji/karakter sebagai ikon (◷ □ ☘ ▧ ▤ ⌂ ⌖ ◉).
- Manager/HR: kartu "Kehadiran tim" mencampur data tim ("3 dari 10 hadir") dengan tombol personal "Mulai check-in". Perlu dipisah: **kartu saya** vs **ringkasan tim**.
- Shift "09.00–18.00" & batas telat 09.00 hardcode (guide sudah jujur).
- Salam: jam ≥17 = "Selamat sore" terus sampai malam.
- Status bar bawah ("Belum check-in") mengulang info kartu atas.
- Tidak ada **"perlu tindakan"** untuk Manager/HR (mis. N cuti menunggu — API sudah kirim `pending_approvals` tapi tidak ditampilkan).

### 4.3 Kehadiran (`/app/attendance/today`)
- Alur benar, tapi 1 halaman memuat 3 mode (belum check-in / sedang bekerja / selesai) dengan kamera besar selalu tampil, walau sudah check-in.
- Urutan langkah di UI ≠ guide: guide "isi prioritas → kamera → foto → setujui lokasi → konfirmasi"; UI kamera di atas, prioritas di bawah. Stepper kanan ("Alur kerja Anda") tidak sinkron dengan sub-langkah check-in.
- Fallback lokasi hardcode `Jakarta HQ (-6.2, 106.8166, 300 m)` jika user belum punya lokasi.
- Eyebrow bahasa Inggris ("Attendance", "Today's flow").

### 4.4 Cuti & izin (`/app/time/time-off`)
- Hanya "cuti tahunan"; tidak ada jenis (sakit, izin), lampiran, atau pilihan handover (diminta calon mitra).
- Hitung hari kerja di frontend hanya Sen–Jum, tidak tahu libur nasional (teks sudah memberi disclaimer).
- Tombol **Batalkan** tanpa konfirmasi.

### 4.5 Persetujuan (`/app/approvals`)
- Kolom "Jenis" selalu "Cuti tahunan".
- Tabel 7 kolom di HP = scroll horizontal; perlu tampilan kartu.
- Tidak ada info **saldo sisa** pemohon & **bentrok jadwal tim** saat memutuskan.
- Aksi "Minta revisi" didukung API tapi tidak ada di UI.

### 4.6 Direktori & profil (`/app/people`, `/app/people/[id]`)
- Tabel 8 kolom; kolom Gaji tampil "Tidak berwenang" untuk Manager di setiap baris → lebih baik kolom disembunyikan.
- Dropdown status di dalam baris tabel (branch baru) mudah salah klik; lebih aman lewat menu aksi / profil.
- Panel Undangan di bawah tabel panjang → mudah terlewat. Lebih baik tab "Karyawan | Undangan | Arsip".
- Profil: aksi HR tersebar (Edit data, Tandai lapangan, select lokasi) tanpa pengelompokan; koordinat mentah tampil di timeline.

### 4.7 Payroll & slip gaji
- Status mentah bahasa Inggris (`draft`, `finalized`, `published`) di badge.
- Slip gaji: tidak ada rincian komponen, tidak ada unduh PDF.

### 4.8 Pengaturan (`/app/settings`)
- Satu halaman panjang berisi 5 area (profil perusahaan, lokasi, re-verifikasi, alert, kalender). Perlu sub-navigasi / tab.
- Kebijakan adalah menu terpisah, padahal URL-nya di bawah `/settings`.

### 4.9 Auth
- Hero login bahasa Inggris ("Presence with purpose.") + "powered by movon digital house".
- Signup (branch baru) sudah bagus: aturan password, hint email HR.

---

## 5. Kondisi teknis frontend (untuk refactor)

| Area | Kondisi | Usulan |
|---|---|---|
| Styling | 1 file `globals.css` 64 KB, di-minify manual, ±11 breakpoint berbeda, warna hex hardcode ratusan kali, hanya 12 CSS variable | Design tokens (warna, spacing, radius, tipografi) + CSS modules / Tailwind; satu set breakpoint |
| Tipografi | Teks tabel 9–11 px, badge 9 px, label 10 px | Minimum 12 px (label), 14 px (body) |
| Komponen | Tidak ada komponen dasar: tiap halaman bikin sendiri button, dialog, tabel, badge status, empty state | `Button`, `Dialog/ConfirmDialog`, `DataTable` (+ versi kartu mobile), `StatusBadge`, `EmptyState`, `PageHeader`, `Field` |
| Data fetching | Tiap halaman ulang: `localStorage.getItem("movon_user")`, `/me` dipanggil berulang (Shell + tiap halaman), polling 60 dtk dobel (Shell + Kehadiran) | `useSession()` context sekali; hook `useApi` |
| Kode | Banyak komponen ditulis 1 baris panjang (approvals, time-off, payroll, policies, ask-teamku) | Format ulang + pecah komponen |
| Label/status | Map label status diduplikasi di beberapa file (cuti ×3, role ×4) | Satu modul `labels.ts` |
| Ikon | SVG `Icon` + karakter Unicode + emoji bercampur | Satu set ikon (mis. Lucide) |
| Bahasa | Eyebrow campur Inggris/Indonesia | Semua Indonesia (atau i18n) |
| Akses | Dialog tanpa focus trap / Esc; baris tabel clickable tanpa keyboard | Pola dialog & row yang aksesibel |

---

## 6. Hasil cek backend (klaim guide vs API)

Audit terhadap `apps/api/src/movon_hr/modules/api.py`. Audit dijalankan di branch terbaru; poin inti (1–12, 14–20) sama di `main` (diverifikasi: potongan 2%, `revision_requested`, `PUT /policies`, change-password, audit-logs ada di `main`). Poin #13 (5 status, arsip) dan email unik lintas undangan hanya berlaku di branch. Nomor baris = file itu kecuali disebut lain. Hasil: **12 sesuai, 6 sebagian, 1 salah, 1 tidak ada**.

| # | Klaim guide | Hasil | Catatan |
|---|---|---|---|
| 1 | Pesan login gagal generik + lockout | ✅ | 5 gagal / 15 menit → 429 (724-731). Lockout **in-memory**: reset saat restart, tidak dibagi antar proses |
| 2 | Signup = tenant baru + HR Admin pertama | ✅ | HR email default = email pendaftar (1462) |
| 3 | Reset via email; undangan 7 hari | ✅ | Link reset berlaku **1 jam**, sekali pakai, logout sesi lain (1664-1716) — guide tidak menyebut |
| 4 | Ringkasan Beranda per role | ◐ | Telat = check-in **≥ 09:00** (1773), jadi tepat 09:00 dihitung telat. `pending_approvals` dikirim API tapi UI tidak pakai |
| 5 | Check-in: prioritas ≥3 karakter, selfie, persetujuan lokasi, geofence | ◐ | **Minimal 3 karakter hanya di frontend**, API tidak validasi (1326). Toleransi GPS maks 50 m (864). Akurasi >100 m → `low_accuracy` |
| 6 | Re-verifikasi | ◐ | **Pekerja lapangan tidak pernah dapat permintaan re-verifikasi** (2410) — guide bilang "hanya diminta lokasi". Pengaturan re-verifikasi & alert **hanya berlaku di lokasi default**; lokasi tambahan selalu `reverify_enabled=False` (1359-1363) |
| 7 | Check-out wajib ringkasan + lokasi | ❌ | **Lokasi check-out opsional di API** (1331-1333). Logout tidak menutup sesi ✅ |
| 8 | Validasi cuti | ✅ | Tidak ada cek **saldo cukup**, tanggal lampau boleh, hanya tipe `time_off` |
| 9 | Persetujuan | ◐ | `revision_requested` = **jalan buntu**: tidak ada endpoint kirim ulang/edit, dan tidak bisa dibatalkan (2575). Setelan kalender scope/divisi/mode **disimpan tapi diabaikan** saat sync (765-788) |
| 10 | Payroll Draft→Finalized→Published | ◐ | Potongan **flat 2% hardcode** (1229). Publish kirim notifikasi ke semua record karyawan **termasuk yang Keluar** (2713-2719) |
| 11 | Slip hanya milik sendiri | ✅ | Hanya dari run Published |
| 12 | Manager tidak terima gaji, tidak bisa kelola | ✅ | |
| 13 | HR tidak bisa nonaktifkan diri; suspend cabut sesi | ✅ | 5 status + arsip (butuh `terminated` dulu). HR terakhir tidak bisa di-demote |
| 14 | Lokasi presensi | ◐ | **Tidak ada endpoint edit/hapus lokasi tambahan.** `work_location_id` tidak divalidasi saat create/invite → id salah jatuh diam-diam ke lokasi default (880) |
| 15 | Alert: in-app saja | ◐ | **Juga kirim email** untuk clock-in/out terlewat (1095-1103) — guide bilang in-app saja. Ada alert `limit_reverify` / `limit_geofence` yang tidak disebut |
| 16 | Kalender Google / Microsoft | ◐ | Microsoft diterima API tapi tidak ada integrasi. Scope & mode tidak diterapkan (lihat #9) |
| 17 | Kebijakan Draft→Published→Archived | ◐ | **Urutan tidak dipaksa**: arsip bisa dipublikasikan lagi, published bisa diedit. AI demo selalu `supported` (`core/ai_provider.py:39`) |
| 18 | Notifikasi | ✅ | Tidak ada tandai-baca per item |
| 19 | Email unik | ✅ | Lebih kuat: unik **lintas semua perusahaan**, case-insensitive, termasuk undangan aktif |
| 20 | Perjalanan dinas & handover cuti | ❌ | **Tidak ada.** "handover" hanya status karyawan |

Kemampuan backend yang **tidak disebut guide** (dan belum punya UI):
- `PUT /policies/{id}` (edit kebijakan) — UI hanya bisa buat baru
- `POST /auth/change-password` — tidak ada halaman ganti sandi / profil saya
- `GET /audit-logs` (HR) — tidak ada UI
- Keputusan `revision_requested`
- Hapus event kalender saat cuti disetujui dibatalkan; status sync kalender per cuti
- Email ke manager & HR saat cuti diajukan / dibatalkan / diputuskan
- `POST /settings/office/from-maps-url` (ambil koordinat dari link Maps) — sudah dipakai UI

Implikasi untuk revamp:
- UI butuh halaman **Profil saya** (ganti sandi) dan **Log audit** (HR) — backend sudah siap.
- Aksi "Minta revisi" jangan ditambahkan ke UI sebelum backend punya alur kirim ulang.
- Guide perlu koreksi di #3, #6, #7, #15.
- Bug backend untuk tiket terpisah: #5 (validasi prioritas), #10 (notifikasi ke karyawan Keluar), #14 (validasi lokasi), #17 (urutan status kebijakan), lockout in-memory.

---

## 7. Status catatan revisi calon mitra (`docs-revisi-teamku.xlsx`)

| # | Permintaan | Di `origin/main` | Di branch lama (referensi) |
|---|---|---|---|
| 1 | Tombol edit (email, nama, gaji) | ❌ | ✅ `feat/f3-edit-employee` |
| 2a | Status: ditangguhkan, menuju resign, handover; hapus karyawan yang keluar | ❌ (hanya Aktif/Ditangguhkan) | ✅ 5 status + Arsip |
| 2b | Alur handover/persetujuan rekan pengganti saat cuti | ❌ | ❌ |
| 3 | Profil perusahaan (email HR resmi, daftar admin) | ❌ | ✅ `CompanyProfileCard` |
| 4 | Panel status undangan | ❌ | ✅ panel Undangan |
| 5 | Label signup "Email HR resmi" | ❌ | ✅ |
| 6 | Perjalanan dinas (check-in di lokasi dinas) | ❌ | ❌ |
| 7 | Info aturan password + pesan "periksa kata sandi" | ❌ | ✅ |

Semua 8 baris masuk scope revamp di atas `main`.

---

## 8. Usulan arah revamp (untuk mockup)

Prinsip: **role-first, satu tindakan utama per layar, mobile-first untuk Employee**, desktop-first untuk HR.

1. **App shell baru**: sidebar dikelompokkan (Saya / Tim / Perusahaan), avatar = menu akun, command palette sungguhan, tab bar mobile per role + "Lainnya".
2. **Beranda per role**: Employee = kartu "Hari ini" (status + 1 tombol aksi) + saldo cuti + slip. Manager/HR = kartu saya (kecil) + **"Perlu tindakan"** (cuti menunggu, anomali lokasi, undangan gagal) + rekap tim.
3. **Presensi sebagai wizard 3 langkah** (Prioritas → Selfie → Lokasi & konfirmasi) di layar fokus; kamera hanya muncul saat langkah selfie; re-verifikasi punya kamera di dalam dialognya sendiri.
4. **Cuti**: form dengan jenis cuti + (nanti) pilih rekan handover; riwayat sebagai timeline.
5. **Persetujuan**: daftar kartu + panel detail samping (saldo pemohon, bentrok tim), aksi Setujui / Tolak / Minta revisi.
6. **Karyawan**: tab Karyawan | Undangan | Arsip (fitur baru di atas `main`); tabel ringkas, aksi di menu "⋯"; profil dengan tab Profil | Kehadiran & lokasi | Aktivasi.
7. **Pengaturan**: sub-nav kiri (Perusahaan, Lokasi, Re-verifikasi, Pengingat, Kalender, Kebijakan).
8. **Ask Teamku**: chat-style, jawaban di atas, sumber sebagai kartu kutipan, link ke halaman yang benar sesuai role, "Hubungi HR" pakai email HR resmi.
9. **Design system**: token warna (merah Teamku sebagai aksen, bukan dominan), skala tipografi 12/14/16/20/24/32, komponen dasar di atas, status badge konsisten Bahasa Indonesia.

Daftar layar mockup yang diusulkan (urut prioritas):
1. Design tokens + komponen dasar
2. App shell (desktop + mobile) per role
3. Beranda Employee (mobile + desktop) & Beranda HR/Manager
4. Presensi wizard + re-verifikasi
5. Persetujuan
6. Karyawan (direktori + profil)
7. Cuti & izin
8. Pengaturan
9. Ask Teamku
10. Payroll + slip gaji
11. Login / signup
