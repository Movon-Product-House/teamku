// Menyalin token dari blok @theme di src/app/globals.css (satu-satunya sumber nilai) ke:
//   1. frontmatter DESIGN.md (root repo), di antara penanda GENERATED, untuk agent & tool desain;
//   2. src/shared/lib/text-sizes.ts, daftar ukuran teks custom yang dibutuhkan cn().
// `--check` hanya membandingkan dan gagal bila ada yang belum disinkronkan (dipakai CI).
import { readFileSync, writeFileSync } from "node:fs";
import { join, relative } from "node:path";

const root = new URL("..", import.meta.url).pathname;
const paths = {
  css: join(root, "src/app/globals.css"),
  design: join(root, "../../DESIGN.md"),
  textSizes: join(root, "src/shared/lib/text-sizes.ts"),
};
const BEGIN = "# GENERATED:BEGIN — npm run design:sync (sumber: apps/web/src/app/globals.css)";
const END = "# GENERATED:END";

function readTheme(css) {
  const match = css.match(/@theme\s*\{([\s\S]*?)\n\}/);
  if (!match) throw new Error("Blok @theme tidak ditemukan di globals.css");
  const tokens = new Map();
  for (const line of match[1].split("\n")) {
    const decl = line.match(/^\s*(--[\w-]+):\s*([^;]+);\s*(?:\/\*(.*)\*\/)?/);
    if (decl) tokens.set(decl[1], { value: decl[2].trim(), note: decl[3]?.trim() ?? "" });
  }
  return tokens;
}

// `var(--font-plus-jakarta-sans), …` → "Plus Jakarta Sans, …" (nama variabel next/font = nama keluarga).
function fontStack(value) {
  return value.replace(/var\(--font-([\w-]+)\)/, (_, name) =>
    name
      .split("-")
      .map((word) => word[0].toUpperCase() + word.slice(1))
      .join(" "),
  );
}

const px = (value) => (value.endsWith("rem") ? `${Number.parseFloat(value) * 16}px` : value);
const quote = (value) => JSON.stringify(value);
const groups = (tokens, prefix) =>
  [...tokens].filter(
    ([name]) => name.startsWith(prefix) && !name.slice(prefix.length).includes("--"),
  );

function frontmatter(tokens) {
  const lines = [BEGIN, "colors:"];
  for (const [name, { value }] of groups(tokens, "--color-"))
    lines.push(`  ${name.slice(8)}: ${quote(value.startsWith("#") ? value.toUpperCase() : value)}`);

  const fonts = {
    serif: fontStack(tokens.get("--font-display").value),
    sans: fontStack(tokens.get("--font-sans").value),
  };
  lines.push("typography:");
  for (const [name, { value, note }] of groups(tokens, "--text-")) {
    const sub = (key) => tokens.get(`${name}--${key}`)?.value;
    lines.push(`  ${name.slice(7)}:`);
    lines.push(`    fontFamily: ${quote(/\bserif\b/.test(note) ? fonts.serif : fonts.sans)}`);
    lines.push(`    fontSize: ${quote(px(value))}`);
    if (sub("font-weight")) lines.push(`    fontWeight: ${sub("font-weight")}`);
    if (sub("line-height")) lines.push(`    lineHeight: ${sub("line-height")}`);
    if (sub("letter-spacing")) lines.push(`    letterSpacing: ${quote(sub("letter-spacing"))}`);
  }

  lines.push("rounded:");
  for (const [name, { value }] of groups(tokens, "--radius-"))
    lines.push(`  ${name.slice(9)}: ${quote(value)}`);
  lines.push(END);
  return lines.join("\n");
}

function textSizesModule(tokens) {
  const names = groups(tokens, "--text-").map(([name]) => quote(name.slice(7)));
  return `// GENERATED oleh scripts/sync-design-tokens.mjs dari @theme di globals.css. Jangan diedit.
export const textSizes = [${names.join(", ")}];
`;
}

const tokens = readTheme(readFileSync(paths.css, "utf8"));
const design = readFileSync(paths.design, "utf8");
const start = design.indexOf(BEGIN);
const end = design.indexOf(END);
if (start === -1 || end === -1)
  throw new Error(`Penanda GENERATED tidak ditemukan di ${paths.design}`);

const outputs = [
  [paths.design, design.slice(0, start) + frontmatter(tokens) + design.slice(end + END.length)],
  [paths.textSizes, textSizesModule(tokens)],
];

const stale = outputs.filter(([path, next]) => {
  try {
    return readFileSync(path, "utf8") !== next;
  } catch {
    return true;
  }
});

if (process.argv.includes("--check")) {
  if (stale.length > 0) {
    console.error(
      `Token belum sinkron dengan globals.css: ${stale.map(([path]) => relative(process.cwd(), path)).join(", ")}\nJalankan: npm run design:sync`,
    );
    process.exit(1);
  }
  console.log("design-tokens: sinkron");
} else {
  for (const [path, next] of stale) writeFileSync(path, next);
  console.log(`design-tokens: ${stale.length} file diperbarui`);
}
