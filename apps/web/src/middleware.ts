import { type NextRequest, NextResponse } from "next/server";

// Harus sama dengan settings.session_cookie_name di apps/api. Cookie dipasang API
// lewat proxy /api, jadi first-party untuk origin web dan terbaca di sini.
const SESSION_COOKIE = "teamku_session";

// Hanya cek keberadaan cookie; validitas sesi tetap diputuskan API (401 → /login).
export function middleware(request: NextRequest) {
  if (request.cookies.has(SESSION_COOKIE)) return NextResponse.next();
  return NextResponse.redirect(new URL("/login", request.url));
}

export const config = { matcher: ["/app/:path*"] };
