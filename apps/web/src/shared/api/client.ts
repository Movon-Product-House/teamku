// Browser requests stay same-origin: Next.js forwards /api/v1/* to FastAPI unchanged
// (next.config.ts), avoiding localhost/IPv6 mismatches and keeping CORS out of the UI contract.
const TIMEOUT_MS = 15_000;

const PUBLIC_AUTH_PATHS = new Set([
  "/api/v1/auth/login",
  "/api/v1/auth/signup",
  "/api/v1/auth/forgot-password",
  "/api/v1/auth/reset-password",
  "/api/v1/auth/accept-invite",
]);
const PUBLIC_PAGES = ["/login", "/signup", "/invite", "/forgot-password", "/reset-password"];

export class ApiError<Body = unknown> extends Error {
  constructor(
    message: string,
    readonly status: number,
    /** Parsed error body (ErrorOut for API errors); absent on a timeout. */
    readonly body?: Body,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

/** Read by Orval: the error type of every generated hook. */
export type ErrorType<Body> = ApiError<Body>;

/** The fetch mutator of the generated client (orval.config.ts); `url` is a spec path (/api/v1/...). */
export async function api<T>(url: string, init: RequestInit = {}): Promise<T> {
  const controller = init.signal ? undefined : new AbortController();
  const timeout = controller ? window.setTimeout(() => controller.abort(), TIMEOUT_MS) : undefined;
  let response: Response;
  try {
    response = await fetch(url, {
      ...init,
      credentials: "include",
      signal: init.signal || controller?.signal,
      headers: {
        "Content-Type": "application/json",
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
    if (response.status === 401 && shouldRedirectToLogin(url)) {
      window.location.assign("/login");
    }
    const body = await response.json().catch(() => ({}));
    // FastAPI mengirim detail berupa array untuk error validasi 422.
    const message = typeof body.detail === "string" ? body.detail : "Terjadi kesalahan";
    throw new ApiError(message, response.status, body);
  }
  return response.json();
}

function shouldRedirectToLogin(url: string): boolean {
  if (typeof window === "undefined" || PUBLIC_AUTH_PATHS.has(url)) return false;
  return !PUBLIC_PAGES.some((page) => window.location.pathname.startsWith(page));
}

export function errorMessage(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback;
}
