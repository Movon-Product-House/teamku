import { ApiError, errorMessage } from "@/shared/api/client";

export type AuthAlert = { title: string; body: string };

/** A1: wrong credentials and the 429 lockout get their own copy; anything else shows the API text. */
export function loginAlert(error: unknown): AuthAlert {
  // 422 is a safety net: the API answers a wrong password with 401 whatever its length.
  if (error instanceof ApiError && (error.status === 401 || error.status === 422))
    return {
      title: "Email atau kata sandi salah",
      body: "Periksa kembali, lalu coba lagi. Setelah beberapa kali gagal, akun dikunci sementara.",
    };
  if (error instanceof ApiError && error.status === 429)
    return {
      title: "Akun dikunci sementara",
      body: "Terlalu banyak percobaan gagal. Coba lagi dalam beberapa menit, atau atur ulang kata sandi.",
    };
  return { title: "Belum bisa masuk", body: errorMessage(error, "Terjadi kesalahan. Coba lagi.") };
}

/** True when a token link is dead (unknown 404 or used/expired 410), not a network hiccup. */
export function isDeadLink(error: unknown): boolean {
  return error instanceof ApiError && (error.status === 404 || error.status === 410);
}

const DAY_MS = 86_400_000;
const JAKARTA_DATE = new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Jakarta" });

/** Whole calendar days from `from` to `to` on the Asia/Jakarta calendar (0 = same day). */
function calendarDaysBetween(from: Date, to: Date): number {
  const day = (date: Date) => Date.parse(`${JAKARTA_DATE.format(date)}T00:00:00Z`);
  return Math.round((day(to) - day(from)) / DAY_MS);
}

/** A4 card meta: "Diundang oleh Dewi (HR) · berlaku 6 hari lagi". */
export function inviteMeta(invitedBy: string | null, expiresAt: string, now = new Date()): string {
  const days = calendarDaysBetween(now, new Date(expiresAt));
  const validity =
    days <= 0
      ? "berlaku sampai hari ini"
      : days === 1
        ? "berlaku sampai besok"
        : `berlaku ${days} hari lagi`;
  return invitedBy ? `Diundang oleh ${invitedBy} (HR) · ${validity}` : validity;
}

/** "0:45" for the resend cooldown. */
export function formatCountdown(seconds: number): string {
  const safe = Math.max(0, Math.ceil(seconds));
  return `${Math.floor(safe / 60)}:${String(safe % 60).padStart(2, "0")}`;
}

/** "PT Sinar Nusantara" → "PT", "Movon" → "MO": the company badge on the invite card. */
export function companyInitials(company: string): string {
  return company.trim().slice(0, 2).toUpperCase();
}
