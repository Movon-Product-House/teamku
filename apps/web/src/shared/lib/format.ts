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
