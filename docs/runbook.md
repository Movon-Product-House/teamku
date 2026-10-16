# Runbook API

Panduan operasional `apps/api` di prod (Dokploy) dan lokal. Semua perintah `python …` di bawah dijalankan di dalam container API (PATH sudah berisi `.venv/bin`); di lokal, jalankan dari `apps/api` dengan prefix `uv run`.

## Konfigurasi

- `MOVON_DATABASE_URL` wajib berformat `postgresql+psycopg://user:pass@host:5432/db` (PostgreSQL 18).
- `MOVON_CORS_ORIGINS` berformat JSON, misalnya `["https://teamku.example"]`.
- `MOVON_SESSION_COOKIE_SECURE=true` di belakang HTTPS. Cookie sesi selalu HttpOnly.
- Email lewat Resend: `MOVON_MAIL_PROVIDER=resend`, `MOVON_RESEND_API_KEY`, dan `MOVON_MAIL_FROM` diisi bersamaan (API menolak start kalau hanya sebagian). Tanpa itu, email undangan dan reset hanya di-log.
- Google Calendar: `MOVON_GOOGLE_CLIENT_ID`, `MOVON_GOOGLE_CLIENT_SECRET`, `MOVON_GOOGLE_REDIRECT_URI`.

## Start container (prestart)

`CMD` image menjalankan, berurutan:

1. `alembic upgrade head`
2. `python -m movon_hr.seed --if-empty`: seed perusahaan demo hanya kalau tabel `tenants` masih kosong. Log `Tenants exist; demo seed skipped.` berarti data lama dipertahankan.
3. `uvicorn movon_hr.main:app --host 0.0.0.0 --port 8000`

Kalau migrasi gagal, container berhenti sebelum uvicorn jalan. Cek log deploy.

## Migrasi

- Skema hanya diubah lewat revisi Alembic di `apps/api/alembic/versions/`. API tidak membuat tabel saat startup.
- Migrasi bersifat forward-only. Tidak ada downgrade di prod; perbaikan dikirim sebagai revisi baru.
- Cek status: `alembic current`, `alembic heads` (harus tepat satu).

## Job terjadwal

Dua job, keduanya idempoten dan aman dijalankan ulang. Exit code bukan nol berarti gagal, sehingga run di Dokploy berwarna merah.

| Job | Perintah | Jadwal | Isi |
|---|---|---|---|
| `attendance-alerts` | `python -m movon_hr.jobs attendance-alerts` | `*/5 * * * *` | Evaluasi alert presensi dan expire slot reverify untuk semua tenant, lalu kirim email alert. |
| `cleanup` | `python -m movon_hr.jobs cleanup` | `0 3 * * *` | Hapus sesi kedaluwarsa, `password_resets` yang kedaluwarsa atau sudah dipakai, `login_attempts` di luar jendela lockout, dan `oauth_states` yang kedaluwarsa. |

Di Dokploy keduanya dipasang sebagai **Schedule** pada application API (`scheduleType: application`, dijalankan dengan `docker exec` di container API), timezone `Asia/Jakarta`, shell `sh`. Menjalankan manual: tombol "Run" di Dokploy, atau `docker exec <container> python -m movon_hr.jobs <job>`.

## Backup

Pasang jadwal backup Dokploy untuk service Postgres prod dan uji restore sesekali. Data di DB adalah satu-satunya state API.

## Log

- Log API (request, migrasi, seed, hasil kirim email): tab **Logs** application API di Dokploy, atau `docker logs <container>`.
- Log job: riwayat run di tab **Schedules** Dokploy (satu log per run). Setiap run mencetak `attendance-alerts tenant=… emails=…` atau `cleanup <tabel> deleted=…`.
- Log tidak boleh berisi payload HR atau secret. Mailer console menyembunyikan isi email di luar `development`.
