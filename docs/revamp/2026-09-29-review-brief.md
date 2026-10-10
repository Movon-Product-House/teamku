# Brief Review Mockup Revamp Teamku

- Tanggal: 29 September 2026
- Untuk: Tim & PM
- File desain: `mockups/design.pen` (Pencil) · ekspor: `mockups/exports/`
- Dokumen pendukung: [`2026-09-29-user-guide-gap-analysis.md`](./2026-09-29-user-guide-gap-analysis.md), [`2026-09-29-role-flows.md`](./2026-09-29-role-flows.md)

## Cara review

1. Buka PNG per section di `mockups/exports/` (9 file, lihat tabel di bawah).
2. Setiap layar punya **kode** (A1, P2a, D1, M2, H6, …) di atasnya. Tulis masukan dengan kode itu, contoh: "H3 — menu ⋯ kurang jelas".
3. Label **BARU** = fitur yang belum ada di backend. Perlu keputusan PM sebelum dibangun (lihat bagian C).

| File | Isi | Layar |
|---|---|---|
| `00-design-system.png` | Prinsip, warna, tipografi, komponen | – |
| `10-employee-mobile-auth-presensi.png` | Login, lupa & reset sandi, aktivasi, beranda (2 state), check-in 3 langkah, re-verifikasi, check-out | 15 |
| `11-employee-mobile-cuti-ask-slip-akun.png` | Cuti (+ error bentrok), Ask Teamku (+ perlu konfirmasi HR), slip (+ kosong), akun, notifikasi | 10 |
| `12-employee-desktop.png` | Beranda, check-in, cuti, Ask Teamku, slip, notifikasi (desktop) | 6 |
| `20-manager-desktop.png` | Beranda tim, persetujuan, Tim Saya, profil anggota | 4 |
| `21-manager-mobile.png` | Persetujuan cepat + sheet keputusan | 2 |
| `30-hr-onboarding-karyawan.png` | Buat workspace, onboarding, beranda HR, karyawan, undangan, arsip, profil, persetujuan semua departemen | 9 |
| `31-hr-payroll-kebijakan-pengaturan.png` | Payroll, konfirmasi terbit, kebijakan, 5 layar pengaturan | 8 |
| `32-hr-mobile.png` | Beranda, persetujuan, karyawan, ubah status, lainnya | 5 |

Total **59 layar**. Label **STATE** di caption = varian kondisi (kosong, error, sedang bekerja) dari layar utama.

## A. Yang berubah besar dari aplikasi sekarang

1. **Gaya visual baru (v2):** judul serif, kartu putih tanpa garis, tombol utama hitam, merah hanya untuk hal mendesak.
2. **Navigasi per role:** grup Saya / Tim / Perusahaan. Desktop tanpa top bar.
3. **Check-in jadi 3 langkah** (prioritas → selfie → lokasi), bukan satu halaman panjang.
4. **Persetujuan dengan konteks:** saldo pemohon, bentrok tim, rekan pengganti di satu panel.
5. **Pengaturan dipecah** jadi sub-menu (Perusahaan, Lokasi, Re-verifikasi & pengingat, Kalender, Log audit).
6. **Setiap aksi yang tidak bisa dibatalkan** (finalisasi/terbit payroll, ubah status, arsip) punya dialog konfirmasi.

## B. Bug di aplikasi sekarang yang diperbaiki desain ini

| Bug | Diperbaiki di |
|---|---|
| Di HP, tombol Batal / Tunda / Tutup hilang (CSS) | Semua dialog & sheet mobile |
| Kamera re-verifikasi tertutup dialog | P2e |
| Ask Teamku: link ke halaman terlarang, riwayat palsu, email HR palsu | P4, D4 |
| Agenda tidak bisa diperbarui (progress selalu 0%) | P2d, D1 (butuh API) |
| Akun demo + kata sandi tampil di login | A1 |
| Avatar kanan atas tidak bisa diklik | D6, S3 |

## C. Keputusan yang dibutuhkan dari PM

| # | Pertanyaan | Layar | Opsi | Saran |
|---|---|---|---|---|
| 1 | **Perjalanan dinas** (mitra #6): HR menugaskan lokasi check-in sementara. Masuk rilis pertama? | H3 menu ⋯, H5 | Rilis 1 / rilis berikutnya | Rilis berikutnya — butuh model data + aturan geofence baru |
| 2 | **Rekan pengganti saat cuti** (mitra #2b): wajib atau opsional? Rekan harus menyetujui? | P3a, D3, M2 | Wajib / opsional | Opsional dulu, persetujuan rekan tidak memblokir atasan |
| 3 | **Minta revisi** cuti: API punya status ini tapi tidak ada alur kirim ulang. | M2 (sengaja tidak ada) | Bangun alur revisi / hapus status dari API | Hapus dulu; cukup Tolak + catatan |
| 4 | **Jenis cuti Sakit & Izin**: sekarang hanya cuti tahunan. | P3a, D3 | Rilis 1 / nanti | Rilis 1 untuk Sakit (dengan lampiran surat dokter) |
| 5 | **Centang agenda** sepanjang hari (butuh API update agenda). | P2d, D1 | Bangun / hapus fitur agenda dari Beranda | Bangun — kecil dan jadi alasan orang membuka app |
| 6 | **Check-in dari laptop** (webcam + lokasi browser, akurasi lebih rendah). | D2 | Izinkan / hanya HP | Izinkan, dengan peringatan akurasi |
| 7 | **Unduh slip PDF**. | P5, D5 | Rilis 1 / nanti | Rilis 1 |
| 8 | **Kalender**: cakupan & cara berbagi tersimpan tapi belum dipakai backend. | H12 | Perbaiki backend / sembunyikan opsi | Perbaiki backend |
| 9 | **Payroll di HP**: HR hanya diarahkan ke desktop. Cukup? | HM5 | Cukup / butuh versi HP | Cukup untuk sekarang |
| 10 | **Gaya v2** (serif + monokrom) sesuai brand Teamku? Merah jadi aksen saja. | Semua | Setuju / kembalikan merah dominan | Setuju |

## D. Pertanyaan untuk tim (engineering)

1. Base implementasi: **`origin/main`**. Branch `feat/f3-*` hanya referensi. Setuju?
2. Styling: pecah `globals.css` jadi design tokens + komponen. Pilihan: **CSS Modules + tokens** atau **Tailwind v4**?
3. Urutan implementasi yang diusulkan: design tokens & komponen → app shell per role → Employee (presensi dulu) → Manager → HR.
4. Bug backend dari audit (tiket terpisah): validasi prioritas check-in, notifikasi payroll ke karyawan Keluar, validasi `work_location_id`, urutan status kebijakan, lockout login in-memory.

## E. Format masukan

Kirim sebagai daftar singkat:

```
[Kode layar] [Setuju / Ubah / Tanya] — catatan
contoh:
H6 Ubah — tambahkan kolom lembur di tabel payroll
C#2 Setuju opsional
```
