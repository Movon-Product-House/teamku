// Batas panjang file kode di src/: MAX_LINES baris. File yang lebih panjang harus dipecah
// (komponen → sub-komponen, logika → modul murni di feature yang sama).
//
// LEGACY_CAPS: file lama yang sudah melewati batas sebelum aturan ini dibuat. Angkanya
// adalah plafon (tidak boleh bertambah) dan entri dihapus begitu file dipecah/dimigrasi.
import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";

const MAX_LINES = 600;
const LEGACY_CAPS = {
  "src/app/app/settings/page.tsx": 1273,
  "src/app/app/attendance/today/page.tsx": 659,
};

const root = new URL("..", import.meta.url).pathname;
const files = readdirSync(join(root, "src"), { recursive: true })
  .filter((file) => /\.(ts|tsx|mjs|js)$/.test(file))
  .map((file) => join("src", file));

const failures = [];
for (const file of files) {
  const lines = readFileSync(join(root, file), "utf8").split("\n").length - 1;
  const cap = LEGACY_CAPS[file] ?? MAX_LINES;
  if (lines > cap) failures.push(`${file}: ${lines} baris (maks ${cap})`);
  else if (file in LEGACY_CAPS && lines <= MAX_LINES)
    failures.push(`${file}: sudah ${lines} baris, hapus dari LEGACY_CAPS`);
}

if (failures.length > 0) {
  console.error(`File melebihi batas ${MAX_LINES} baris:\n  ${failures.join("\n  ")}`);
  process.exit(1);
}
console.log(`check-file-lines: ${files.length} file OK (maks ${MAX_LINES} baris)`);
