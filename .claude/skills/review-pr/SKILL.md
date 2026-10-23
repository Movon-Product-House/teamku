---
name: review-pr
description: Review satu PR Teamku (atau re-review setelah penulis membalas) pada tiga sumbu, correctness, standards, spec, lalu post sebagai satu review GitHub dengan komentar inline. Use when asked to review, re-review, or check a PR.
---

# Review PR

Satu run = satu PR = satu review GitHub. PR stacked (base bukan `main`) di-review per PR; setiap temuan dipost di PR tempat barisnya berubah.

Review yang bagus di repo ini (#32, #34, #51) **adversarial**: setiap temuan adalah skenario konkret (input atau keadaan → hasil yang salah) yang sudah dicek ke kode, bukan dugaan.

## 0. Pilih mode

`gh api repos/{owner}/{repo}/pulls/<n>/reviews` sudah memuat review dari user ini → **re-review** (langkah 5). Belum → review pertama (langkah 1–4).

## 1. Siapkan bahan

- `git fetch origin`, lalu baca kode di head PR (`git worktree add <scratchpad>/pr<n> origin/<head> --detach`), bukan checkout lokal.
- `gh pr view <n> --json title,body,baseRefName,headRefName,files`, diff terhadap base PR (`git diff origin/<base>...origin/<head>`).
- Issue yang dirujuk (`Closes #` / `Refs #`): body dan checklist FE/BE-nya.
- Sumber standards untuk setiap app yang disentuh: `apps/api/AGENTS.md`, `apps/web/AGENTS.md`, plus `DESIGN.md` bila ada perubahan UI di `apps/web`.

**Selesai bila:** diff, deskripsi PR, issue, dan daftar sumber standards ada di tangan, dan worktree head PR siap dibaca.

## 2. Tiga sumbu, paralel

Jalankan tiga subagent sekaligus. Masing-masing menerima perintah diff, path worktree, dan brief di bawah; minta laporan per temuan: `file:line` di head PR, klaim satu kalimat, skenario, saran.

- **Correctness**: cari bug dengan membaca kode di sekitar diff (pemanggil, query, aturan di modul lain), bukan hanya hunk-nya. Brief menyertakan isi [`hotspots.md`](hotspots.md) sebagai daftar kelas bug yang wajib dicoba satu per satu.
- **Standards**: setiap pelanggaran aturan di sumber standards dari langkah 1, dengan kutipan aturannya (file + kalimat). Lewati yang sudah dipaksa `scripts/check.sh` / `npm run check`.
- **Spec**: checklist issue yang belum atau salah dikerjakan; perilaku di luar scope; deskripsi PR yang tidak cocok dengan kode (Summary, **Merge Danger / Blast Radius** yang tidak menyebut perubahan perilaku, "Selisih yang disengaja"); field atau kode baru yang tidak dipakai siapa pun.

**Selesai bila:** ketiga laporan masuk.

## 3. Verifikasi dan beri severity

Buka sendiri kode di setiap temuan dan reproduksi skenarionya dengan membaca alurnya (atau menjalankan tes bila murah). Temuan yang tidak terbukti dibuang; temuan yang sama dari dua sumbu digabung.

Beri satu severity per temuan:

- **Perlu dibereskan**: bug yang terlihat pengguna atau merusak data, pelanggaran aturan tertulis, deskripsi PR yang menyesatkan.
- **Sebaiknya diputuskan**: pilihan yang sah dua arah (YAGNI, scope), penulis yang memutuskan.
- **Catatan kecil**: nit, konsistensi, follow-up; kalau di luar scope, minta dibuatkan issue.

**Selesai bila:** setiap temuan tersisa punya `file:line` yang ada di diff, skenario yang sudah dicek, dan severity.

## 4. Post

Satu review per PR lewat `gh api repos/{owner}/{repo}/pulls/<n>/reviews --input <scratchpad>/r<n>.json`. Tulis JSON-nya dengan Write (hook memblokir heredoc). Event selalu `COMMENT`; `APPROVE` hanya di re-review.

```json
{
  "event": "COMMENT",
  "body": "Review #<n>. <vonis: Tidak ada blocker. | N perlu dibereskan, M sebaiknya diputuskan.> Detail di komentar inline.\n\nYang sudah dicek dan aman:\n- <hal berisiko yang ternyata benar, dengan alasannya>",
  "comments": [
    {
      "path": "apps/api/src/...",
      "line": 98,
      "side": "RIGHT",
      "body": "**Perlu dibereskan: <klaim satu kalimat>.** <skenario konkret>. <saran perbaikan>."
    }
  ]
}
```

- `line` harus baris yang berubah atau konteks di hunk diff PR itu; temuan di luar diff masuk ke `body`.
- Bahasa Indonesia, nama kode dalam backtick. Setiap aturan yang dilanggar dikutip dengan sumbernya.
- Kosakata severity hanya tiga di atas, ditulis tebal di awal komentar.

**Selesai bila:** URL review tercetak untuk setiap PR, lalu tunjukkan ringkasan dan URL-nya ke user.

## 5. Re-review

- Baca semua thread inline dari review sebelumnya beserta balasan penulis (`gh api .../pulls/<n>/comments`), dan commit sejak review terakhir.
- Untuk setiap temuan lama: cek kodenya di head sekarang. Balasan "Fixed in `<sha>`" bukan bukti; kodenya yang jadi bukti. Penolakan yang beralasan (seperti #49, fixture `clock` autouse) diterima dan disebut.
- Review diff baru (commit sejak review terakhir) lewat langkah 2–3, terbatas pada diff itu.

Post dengan body `Re-review at <sha>: <status tiap temuan lama>.` Semua temuan **Perlu dibereskan** beres dan tidak ada yang baru → `APPROVE`; selain itu `COMMENT`.

**Selesai bila:** setiap temuan lama punya status (beres / ditunda dengan issue / diterima penolakannya), dan review ter-post.

## 6. Rawat hotspots

Temuan **Perlu dibereskan** dari run ini yang kelasnya belum ada di [`hotspots.md`](hotspots.md): usulkan ke user satu entri baru dengan nomor PR-nya. Kelas yang mekanis (pola impor, lokasi file, API terlarang) diusulkan sebagai lint atau tes, bukan hotspot.

**Selesai bila:** usulan (atau "tidak ada kelas baru") sudah disampaikan ke user.
