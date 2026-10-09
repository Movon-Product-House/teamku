import { clearDemoToken, demoAuthHeaders } from "./demo-session";

// Browser requests stay same-origin. Next.js forwards this prefix to FastAPI,
// avoiding localhost/IPv6 mismatches and keeping CORS out of the UI contract.
const BASE = "/api";
const TIMEOUT_MS = 15_000;

const PUBLIC_AUTH_PATHS = new Set([
  "/auth/login",
  "/auth/signup",
  "/auth/forgot-password",
  "/auth/reset-password",
  "/auth/accept-invite",
]);
const PUBLIC_PAGES = ["/login", "/signup", "/invite", "/forgot-password", "/reset-password"];

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const controller = init.signal ? undefined : new AbortController();
  const timeout = controller ? window.setTimeout(() => controller.abort(), TIMEOUT_MS) : undefined;
  let response: Response;
  try {
    response = await fetch(`${BASE}${path}`, {
      ...init,
      credentials: "include",
      signal: init.signal || controller?.signal,
      headers: {
        "Content-Type": "application/json",
        ...demoAuthHeaders(),
        ...(init.headers || {}),
      },
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new ApiError("Server tidak merespons. Silakan coba lagi.", 0);
    }
    throw error;
  } finally {
    if (timeout) window.clearTimeout(timeout);
  }
  if (!response.ok) {
    if (response.status === 401 && shouldRedirectToLogin(path)) {
      clearDemoToken();
      window.location.assign("/login");
    }
    const body = await response.json().catch(() => ({}));
    // FastAPI mengirim detail berupa array untuk error validasi 422.
    const message = typeof body.detail === "string" ? body.detail : "Terjadi kesalahan";
    throw new ApiError(message, response.status);
  }
  return response.json();
}

function shouldRedirectToLogin(path: string): boolean {
  if (typeof window === "undefined" || PUBLIC_AUTH_PATHS.has(path)) return false;
  return !PUBLIC_PAGES.some((page) => window.location.pathname.startsWith(page));
}

export function errorMessage(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback;
}
