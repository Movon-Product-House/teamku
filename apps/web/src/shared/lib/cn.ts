import { createCn } from "cn/config";

// Ukuran teks custom dari @theme di globals.css. Tanpa ini, merge menganggap
// `text-body` sebagai warna lalu membuang `text-primary-foreground` (dan sebaliknya).
// Tambahkan nama baru di sini setiap kali menambah token --text-* di globals.css.
export const cn = createCn({
  extend: {
    classGroups: {
      "font-size": [
        { text: ["display", "title", "headline", "title-sm", "heading", "body", "caption"] },
      ],
    },
  },
});
