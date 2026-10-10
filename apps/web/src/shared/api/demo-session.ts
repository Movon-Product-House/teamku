// DEMO-ONLY: token sesi disalin ke localStorage dan dikirim lewat header X-Demo-User,
// padahal API sudah memasang cookie httpOnly. Ini satu-satunya tempat yang menyentuh
// token tersebut. Untuk menghapus mode demo: hapus file ini, lalu hapus pemanggilnya
// (cari "demo-session") dan header X-Demo-User di apps/api/src/movon_hr/main.py.
const KEY = "movon_user";

export function demoAuthHeaders(): Record<string, string> {
  const token = typeof window === "undefined" ? null : localStorage.getItem(KEY);
  return token ? { "X-Demo-User": token } : {};
}

export function hasDemoToken(): boolean {
  return localStorage.getItem(KEY) !== null;
}

export function storeDemoToken(token: string): void {
  localStorage.setItem(KEY, token);
}

export function clearDemoToken(): void {
  localStorage.removeItem(KEY);
}
