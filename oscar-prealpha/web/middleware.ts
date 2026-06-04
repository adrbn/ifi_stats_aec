import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { verifySession, SESSION_COOKIE } from "@/lib/auth";

// Chemins accessibles sans session.
const PUBLIC = ["/login", "/api/auth/login"];

export async function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl;
  if (PUBLIC.some((p) => pathname === p || pathname.startsWith(p + "/"))) {
    return NextResponse.next();
  }
  const token = req.cookies.get(SESSION_COOKIE)?.value ?? "";
  const ok = await verifySession(token, process.env.OSCAR_SESSION_SECRET ?? "");
  if (ok) return NextResponse.next();

  // API protégée → 401 JSON ; pages → redirection login.
  if (pathname.startsWith("/api/")) {
    return NextResponse.json({ error: "non autorisé" }, { status: 401 });
  }
  const url = req.nextUrl.clone();
  url.pathname = "/login";
  return NextResponse.redirect(url);
}

// On exclut les assets statiques Next.
export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
