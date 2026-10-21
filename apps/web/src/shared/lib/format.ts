const dateFormat = new Intl.DateTimeFormat("id-ID", {
  day: "2-digit",
  month: "short",
  year: "numeric",
});
const periodFormat = new Intl.DateTimeFormat("id-ID", { month: "long", year: "numeric" });
const moneyFormat = new Intl.NumberFormat("id-ID", {
  style: "currency",
  currency: "IDR",
  maximumFractionDigits: 0,
});

/** "2026-10-09" → "09 Okt 2026". Dibaca sebagai tanggal lokal, bukan UTC. */
export function formatDate(value: string): string {
  return dateFormat.format(new Date(`${value}T00:00:00`));
}

/** "2026-10" → "Oktober 2026". */
export function formatPeriod(value: string): string {
  return periodFormat.format(new Date(`${value}-01T00:00:00`));
}

export function formatMoney(value: number): string {
  return moneyFormat.format(value);
}

const clockFormat = new Intl.DateTimeFormat("id-ID", { hour: "2-digit", minute: "2-digit" });
const dayMonthFormat = new Intl.DateTimeFormat("id-ID", { day: "numeric", month: "short" });
const dayMonthYearFormat = new Intl.DateTimeFormat("id-ID", {
  day: "numeric",
  month: "short",
  year: "numeric",
});

/** Tengah malam lokal hari `now`, dalam ms. Satu batas "hari ini" untuk semua daftar. */
export function startOfToday(now: Date = new Date()): number {
  return new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
}

/** Waktu singkat untuk daftar: "11.30" hari ini, "Kemarin", lalu "29 Agu" (dengan tahun bila bukan tahun ini). */
export function formatShortTime(value: string, now: Date = new Date()): string {
  const date = new Date(value);
  const today = startOfToday(now);
  if (date.getTime() >= today) return clockFormat.format(date);
  if (date.getTime() >= today - 86_400_000) return "Kemarin";
  return (date.getFullYear() === now.getFullYear() ? dayMonthFormat : dayMonthYearFormat).format(
    date,
  );
}
