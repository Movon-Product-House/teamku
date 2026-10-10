# Product

## Register

product

## Users

Karyawan perusahaan klien Teamku, dalam tiga peran:

- **Employee**: termasuk pekerja lapangan. Membuka Teamku di HP beberapa kali sehari, sering sambil berdiri atau di jalan, untuk check-in (selfie + lokasi), re-verifikasi, check-out, mengajukan cuti, dan melihat slip gaji. Waktunya singkat; satu layar harus menjawab "apa yang harus saya lakukan sekarang?".
- **Manager**: memakai lapisan yang sama, ditambah Tim Saya dan Persetujuan. Kebanyakan di desktop, tetapi menyetujui cuti dari HP.
- **HR Admin**: mengelola seluruh perusahaan (karyawan, payroll, kebijakan, pengaturan) di desktop, dengan aksi berisiko tinggi seperti menerbitkan payroll.

## Product Purpose

Teamku adalah aplikasi presensi dan HR: kehadiran berbasis lokasi, cuti & izin, slip gaji, dan Ask Teamku (tanya jawab kebijakan perusahaan). Satu aplikasi dengan tiga lapisan navigasi: **Saya** (semua role), **Tim** (Manager, HR), **Perusahaan** (HR). Berhasil bila karyawan menyelesaikan presensi tanpa bingung, dan atasan/HR mengambil keputusan dengan konteks lengkap di satu tempat.

## Brand Personality

Tenang, lega, fokus. Nada bahasa Indonesia yang sopan dan langsung, tanpa jargon ("Pekerja lapangan", bukan "remote/sales"; "Cuti & Izin", bukan "Agenda & Cuti"). Antarmuka terasa seperti alat kerja yang rapi dan dewasa, bukan aplikasi promosi.

## Anti-references

- UI Teamku lama: merah dominan di mana-mana, navigasi "Workspace / Operations", dialog yang menutupi kamera, akun demo dan kata sandi tampil di layar login.
- Template dashboard SaaS: kartu angka besar + gradien, grid kartu identik, badge warna penuh di setiap baris.
- Merah sebagai dekorasi. Merah berarti mendesak.

## Design Principles

1. **Satu tindakan utama per layar.** Hanya satu tombol hitam; sisanya tombol putih atau tautan.
2. **Angka jadi pusat.** Durasi, saldo, dan gaji tampil besar dengan serif; labelnya kecil.
3. **Merah = mendesak.** Hanya untuk re-verifikasi, notifikasi belum dibaca, dan error.
4. **Employee mobile-first, Manager & HR desktop-first.** Presensi terjadi di HP.
5. **Setiap layar punya state lengkap:** loading, kosong, error, sukses, tidak berwenang. Aksi yang tidak bisa dibatalkan selalu dikonfirmasi.

## Accessibility & Inclusion

- Target WCAG 2.2 AA: kontras teks ≥ 4,5:1, fokus keyboard selalu terlihat, setiap input punya label.
- Target sentuh ≥ 44px di mobile; input 16px di mobile agar Safari iOS tidak zoom.
- Status tidak hanya dibedakan warna: selalu ada teks (titik + label).
- Hormati `prefers-reduced-motion`; animasi hanya untuk perubahan state.
- Seluruh teks Bahasa Indonesia, format tanggal dan uang Indonesia.
