---
title: "chore: Deploy apps/web ke Dokploy (teamku.movoncreative.dev)"
type: plan
date: 2026-10-22
status: in-progress
scope: deployment-only
---

# chore: Deploy `apps/web` ke Dokploy

## Summary

Pindahkan web dari Vercel ke Dokploy di server yang sama dengan API (`103.150.226.99`, panel `server.movoncreative.dev`), di domain `teamku.movoncreative.dev`. Arsitektur tidak berubah: browser hanya bicara ke domain web, Next mem-proxy `/api/*` ke FastAPI, cookie sesi tetap first-party. Bedanya, proxy sekarang lewat jaringan internal Docker, bukan internet.

Langkah deploy di Dokploy dikerjakan lewat MCP, env API lewat UI. Perbaikan kode (D3, D4) masuk PR #50.

## Status (2026-10-23)

Langkah 1–5 sudah diterapkan, dan deploy pertama berhasil (2026-10-22):

- `/` → 307 ke `/login`, `/login` → 200.
- Sertifikat Let's Encrypt valid sampai 2027-01-20.
- `/api/me` → 401 `Sesi tidak valid` dari FastAPI, jadi proxy internal ke API jalan.
- Log runtime bersih (`Ready in 278ms`).
- Login `employee@movon.test` lewat `/api/auth/login` → 200, cookie `teamku_session` ter-set, `/api/me` dengan cookie itu → 200.

2026-10-23: env API (langkah 6) sudah di-set dan redirect URI Google Calendar sudah ditambahkan. Project Vercel di-pause (langkah 8). D1–D5 sudah diputuskan, lihat di bawah.

Belum dikerjakan: cek tampilan di browser (langkah 5), verifikasi link email (langkah 6), `watchPaths` API (langkah 7), dan hapus project Vercel (D2).

ID Dokploy: app web `OHsNStwHssFaX2TvzllJt` (`teamku-web-95comu`), domain `FaKPB8uuutkDVegZAcCF8`.

## Kondisi Awal (diverifikasi 2026-10-22)

- F1. App `web` sudah dibuat: applicationId `OHsNStwHssFaX2TvzllJt`, appName `teamku-web-95comu`, project Teamku / environment production. Saat dibuat masih kosong: belum ada repo, `buildType: nixpacks`, belum ada domain, belum pernah deploy.
- F2. DNS wildcard `*.movoncreative.dev` sudah ke `103.150.226.99` (DNS-only, tidak lewat proxy Cloudflare), jadi challenge HTTP-01 Let's Encrypt bisa langsung jalan.
- F3. `apps/web/Dockerfile` sudah siap Dokploy: multi-stage, `output: "standalone"` (aktif karena `VERCEL` tidak di-set), `node server.js`, port 3000, user `node`.
- F4. `MOVON_API_ORIGIN` adalah **build arg**, bukan env runtime: Next membakukan `rewrites()` ke `routes-manifest.json` saat build. Guard `scripts/require-api-origin.mjs` hanya aktif kalau `VERCEL` atau `CI` di-set, jadi di Dokploy build yang lupa arg ini tetap "sukses" tapi mem-proxy ke `127.0.0.1:8000`.
- F5. API `teamku-api-hha3j9` dan web sama-sama ada di `dokploy-network`, jadi `http://teamku-api-hha3j9:8000` bisa dijangkau dari container web.
- F6. API memakai `MOVON_APP_BASE_URL` (`app_base_url`) untuk link email auth (invite/reset), link attendance alert, redirect Google Calendar setelah connect, dan default redirect URI OAuth Google. Nilainya masih mengarah ke domain web lama.
- F7. `watchPaths` API kosong (`[]`), jadi setiap push ke main ikut rebuild API, termasuk push yang hanya mengubah web.
- F8. `/design-system` hanya disembunyikan kalau `VERCEL_ENV === "production"`. Di Dokploy variabel itu tidak ada, jadi halaman ini **terbuka di production** (terverifikasi: 200 setelah deploy).
- F9. `NEXT_PUBLIC_DEMO_ACCOUNTS` dibaca saat build, tapi Dockerfile tidak punya `ARG` untuk variabel itu, jadi build arg dari Dokploy tidak akan sampai.
- F10. Dokploy menandai deploy "done" begitu build sukses, walaupun container crash-loop. Verifikasi selalu lewat domain live dan log.

## Keputusan

- K1. Proxy ke API lewat internal network (`http://teamku-api-hha3j9:8000`), bukan `https://api-teamku.movoncreative.dev`. Satu hop lebih sedikit, tanpa TLS, dan tetap jalan walaupun domain API bermasalah. Domain publik API tetap dipertahankan untuk debugging dan OpenAPI.
- K2. Tidak perlu CORS untuk web: request browser same-origin. `MOVON_CORS_ORIGINS` tidak diubah.

## Langkah

### 1. Source (MCP `application-saveGithubProvider`) — selesai

- `githubId: kk_4t2guth4qK7TqxI2vq` (Movon Dokploy), owner `Movon-Product-House`, repo `teamku`, branch `main`.
- `buildPath: apps/web/`, `watchPaths: ["apps/web/**"]`, `triggerType: push`.

### 2. Build type (MCP `application-saveBuildType`) — selesai

- `buildType: dockerfile`, `dockerfile: Dockerfile`, context path kosong (pakai `buildPath`).

### 3. Build args (MCP `application-saveEnvironment`, field `buildArgs`) — selesai

Env app web masih `null` waktu itu, jadi aman diisi lewat MCP. Larangan "jangan saveEnvironment blind" berlaku untuk app yang env-nya sudah terisi, seperti API. Untuk app web pun berlaku begitu sekarang: `saveEnvironment` mengganti seluruh `env` dan `buildArgs` sekaligus.

```
MOVON_API_ORIGIN=http://teamku-api-hha3j9:8000
```

Env runtime dibiarkan kosong: server standalone tidak butuh apa-apa selain `HOSTNAME`, yang sudah di-set di Dockerfile.

### 4. Domain (MCP `domain-create`) — selesai

- host `teamku.movoncreative.dev`, port `3000`, path `/`, `https: true`, `certificateType: letsencrypt`.

### 5. Deploy dan verifikasi — selesai, kecuali login di browser

- MCP `application-deploy`, lalu cek log build lewat `deployment-readLogs` dan log runtime lewat `application-readLogs`.
- Cek:
  - `curl -sI https://teamku.movoncreative.dev/` → 307 ke `/login`, dengan sertifikat LE valid. ✅
  - `curl -s https://teamku.movoncreative.dev/api/me` → 401 JSON dari FastAPI, bukan 404/500 dari Next. Ini membuktikan F4 dan K1. ✅
  - Login manual di browser, lalu cek cookie sesi ter-set di `teamku.movoncreative.dev` dan halaman beranda memuat data. ⏳

### 6. Env API (lewat UI Dokploy, bukan MCP) — selesai, kecuali verifikasi email

MCP meredaksi env dan `saveEnvironment` mengganti seluruh string env, jadi env API diedit di UI.

- `MOVON_APP_BASE_URL=https://teamku.movoncreative.dev`, lalu redeploy API.
- Kalau Google Calendar dipakai: tambahkan redirect URI `https://teamku.movoncreative.dev/api/v1/settings/calendar/google/callback` di Google Cloud Console. Kalau env redirect URI Google di-set eksplisit, ganti juga.
- Verifikasi: kirim satu email reset password atau invite ke alamat tim, lalu pastikan link-nya mengarah ke domain baru.

### 7. Watch paths API (MCP `application-saveGithubProvider` untuk app API) — belum

Dicek 2026-10-23: `watchPaths` API masih `[]`, jadi push docs-only (#48) ikut me-rebuild API.

- Isi `watchPaths: ["apps/api/**"]`. Field lain (repo, branch, `buildPath: apps/api/`, `githubId`) harus dikirim ulang persis seperti yang sekarang, karena call ini mengganti seluruh konfigurasi source.

### 8. Cutover dan bersih-bersih — sebagian

- ✅ Project Vercel `teamku-web` di-pause dan Ignored Build Step `exit 0`, jadi tidak ada deploy ganda.
- ⏳ Git integration Vercel masih tersambung, jadi tiap PR masih dapat check `Vercel` merah ("Deployment was blocked"). Putus bersama penghapusan project (D2).
- ✅ `README.md`, `apps/web/README.md`, `DESIGN.md`, `.env.example` sudah menunjuk Dokploy (PR #50). `docs/plans/2026-09-12-001-migrate-web-to-vercel-plan.md` ditandai `superseded`.

## Keputusan (dulu terbuka)

- D1. Login demo (`NEXT_PUBLIC_DEMO_ACCOUNTS=1`) tidak ditampilkan di production.
- D2. Auto-deploy Vercel diputus (project di-pause). Project dan Git integration-nya dihapus setelah seminggu stabil.
- D3. `/design-system` (F8): cek di `apps/web/src/app/design-system/page.tsx` diganti jadi `NODE_ENV === "production"` (PR #50). Halaman ada di `next dev`, hilang di build production mana pun.
- D4. Guard `MOVON_API_ORIGIN` (F4): `apps/web/Dockerfile` men-set `ENV CI=1` di stage build (PR #50). Bukan `ARG CI` seperti usulan awal, supaya guard selalu aktif tanpa build arg tambahan di Dokploy.
- D5. `ARG NEXT_PUBLIC_DEMO_ACCOUNTS` (F9) disarankan di review PR #50, supaya picker demo bisa dinyalakan/dimatikan lewat Build-time Arguments Dokploy (butuh redeploy). Default kosong, jadi tetap mati sesuai D1.

## Rollback

Web di Vercel tidak disentuh sampai langkah 8. Kalau Dokploy bermasalah, kembalikan `MOVON_APP_BASE_URL` di API ke domain lama dan redeploy API. Domain `teamku.movoncreative.dev` cukup dinonaktifkan (`domain-toggleEnable`).
