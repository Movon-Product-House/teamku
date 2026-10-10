import { createCn } from "cn/config";
import { textSizes } from "./text-sizes";

// Ukuran teks custom dari @theme di globals.css. Tanpa ini, merge menganggap
// `text-body` sebagai warna lalu membuang `text-primary-foreground` (dan sebaliknya).
// `textSizes` dibuat oleh `npm run design:sync`.
export const cn = createCn({
  extend: { classGroups: { "font-size": [{ text: textSizes }] } },
});
