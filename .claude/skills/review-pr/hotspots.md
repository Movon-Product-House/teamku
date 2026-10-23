# Hotspots

Kelas bug yang berulang di review Teamku. Setiap entri: apa yang dicoba, lalu PR tempat ia pernah lolos sampai review. Coba setiap entri yang relevan terhadap diff; entri yang tidak relevan dilewati tanpa laporan.

Entri yang tidak muncul lagi dalam ~15 PR terakhir dihapus saat `/retro`. Entri yang bisa dicek mesin pindah ke lint/tes dan dihapus dari sini.

## Waktu

- **Tengah malam WIB.** Apa pun yang dikelompokkan per hari (`jakarta_date`, `jakarta_day_bounds`): sesi yang melewati 00:00 WIB, check-out keesokan hari, sesi lupa ditutup berhari-hari. Prod dan CI jalan di UTC, jadi 00:00 WIB = 17:00 UTC. (#34, #36, #49)
- **Shift malam.** Karyawan yang check-in malam dan sesinya masih terbuka besok pagi: dapat "belum check-in", "terlambat", atau pengingat yang salah? Sesi terbuka memblokir check-in baru (`attendance/service.py`). (#51, #52, #53)
- **Jam dan zona waktu browser.** Web yang menghitung dari `new Date()` (durasi, "hari ini", format jam) berbeda dari server bila jam perangkat telat atau zona waktunya bukan WIB. (#33, #36, #54)
- **Tes dekat tengah malam.** Tes yang memakai `now - X` atau tanggal relatif: apakah tetap lolos kalau dijalankan dekat 00:00 WIB? Fixture `clock` autouse memindahkan `datetime.now()` ke `TEST_NOW`; kolom `server_default=func.now()` tidak ikut. (#34, #36, #49)

## Peran dan scope

- **Diri sendiri di data tim.** Manager termasuk departemennya sendiri (`visible_query`). Permohonan miliknya muncul di daftar yang harus dia putuskan, padahal menyetujui diri sendiri ditolak 403 (`leave/service.py`). Dia juga muncul di daftar pantau timnya sendiri. (#32, #54)
- **Angka dan daftar dari sumber berbeda.** Hitungan (`absent`, badge, `pending_approvals`) dan daftar yang menampilkannya harus memakai aturan yang sama, atau keduanya tidak cocok di layar. (#32, #53)

## Client state (`apps/web`)

- **Refetch di latar belakang gagal.** TanStack mempertahankan `data` dan menyalakan `isError`. Halaman yang menukar seluruh isinya ke state error, atau form yang di-reset oleh refetch, menghilangkan pekerjaan user. (#32, #33)
- **Cache basi setelah mutasi.** Halaman legacy yang memakai fungsi fetch biasa tidak memicu invalidasi; badge/kartu lain tetap menampilkan nilai lama. (#32)
- **Query tanpa state error.** Kartu yang diam-diam hilang saat query gagal (`data ?? []`), sehingga user tidak tahu ada yang menunggu. (#54)

## Kontrak dan deploy

- **Jeda deploy web dan API.** Web dan API di-deploy terpisah: web baru dengan API lama (field belum ada) dan sebaliknya. Field baru opsional di type, atau fallback yang jujur. (#36, #49)
- **Data lama di kolom JSON.** Validasi respons yang lebih ketat daripada data yang sudah tersimpan (mis. `agenda` di `attendance`) membuat satu baris lama menjadi 500. (#34)
- **Pembulatan.** API membulatkan (jam ke 2 desimal), web membulatkan lagi ke bawah: selisih satu menit. (#49)
- **Field baru tanpa pemakai.** Field respons atau kode yang ditambahkan untuk layar yang tidak memakainya. (#53)

## Deskripsi PR

- **Merge Danger yang kurang.** Perubahan perilaku yang terlihat pengguna (alert yang muncul lebih lambat, angka yang turun) tetapi tidak disebut di Blast Radius. (#51)
- **Body basi.** Endpoint, nama, atau "Selisih yang disengaja" yang tidak lagi cocok dengan kode setelah perbaikan review. (#33)
