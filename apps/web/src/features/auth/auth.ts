import { ApiError, errorMessage } from "@/shared/api/client";

/** Mirrors `password_policy_error` in apps/api `core/security.py`. */
export const PASSWORD_MIN = 8;
export const PASSWORD_MAX = 128;

export type PasswordRule = { label: string; met: boolean };

export function passwordRules(password: string): PasswordRule[] {
  return [
    {
      label: `${PASSWORD_MIN}–${PASSWORD_MAX} karakter`,
      met: password.length >= PASSWORD_MIN && password.length <= PASSWORD_MAX,
    },
    { label: "Minimal satu huruf", met: /[A-Za-z]/.test(password) },
    { label: "Minimal satu angka", met: /\d/.test(password) },
  ];
}

export function passwordValid(password: string): boolean {
  return passwordRules(password).every((rule) => rule.met);
}

export type AuthAlert = { title: string; body: string };

/** A1: wrong credentials and the 429 lockout get their own copy; anything else shows the API text. */
export function loginAlert(error: unknown): AuthAlert {
  if (error instanceof ApiError && error.status === 401)
    return {
      title: "Email atau kata sandi salah",
      body: "Periksa kembali, lalu coba lagi. Setelah 5 kali gagal, akun dikunci 15 menit.",
    };
  if (error instanceof ApiError && error.status === 429)
    return {
      title: "Akun dikunci sementara",
      body: "Terlalu banyak percobaan gagal. Coba lagi dalam 15 menit, atau atur ulang kata sandi.",
    };
  return { title: "Belum bisa masuk", body: errorMessage(error, "Terjadi kesalahan. Coba lagi.") };
}

/** True when a token link is dead (unknown 404 or used/expired 410), not a network hiccup. */
export function isDeadLink(error: unknown): boolean {
  return error instanceof ApiError && (error.status === 404 || error.status === 410);
}

const DAY_MS = 86_400_000;

/** A4 card meta: "Diundang oleh Dewi (HR) · berlaku 6 hari lagi". */
export function inviteMeta(invitedBy: string | null, expiresAt: string, now = new Date()): string {
  const days = Math.ceil((new Date(expiresAt).getTime() - now.getTime()) / DAY_MS);
  const validity = days > 1 ? `berlaku ${days} hari lagi` : "berlaku sampai hari ini";
  return invitedBy ? `Diundang oleh ${invitedBy} (HR) · ${validity}` : validity;
}

/** "0:45" for the resend cooldown. */
export function formatCountdown(seconds: number): string {
  const safe = Math.max(0, Math.ceil(seconds));
  return `${Math.floor(safe / 60)}:${String(safe % 60).padStart(2, "0")}`;
}

/** "PT Sinar Nusantara" → "PT", "Movon" → "MO": the company badge on the invite card. */
export function companyInitials(company: string): string {
  const words = company.trim().split(/\s+/).filter(Boolean);
  if (words.length > 1) return words[0].slice(0, 2).toUpperCase();
  return (words[0] ?? "").slice(0, 2).toUpperCase();
}
