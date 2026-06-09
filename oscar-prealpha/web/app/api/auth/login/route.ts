import { NextResponse } from "next/server";
import { createSession, SESSION_COOKIE } from "@/lib/auth";

async function sha256Hex(s: string): Promise<string> {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(s));
  return Array.from(new Uint8Array(buf)).map((b) => b.toString(16).padStart(2, "0")).join("");
}

export async function POST(req: Request) {
  const { password } = await req.json().catch(() => ({ password: "" }));
  const expected = process.env.OSCAR_PASSWORD_SHA256 ?? "";
  const secret = process.env.OSCAR_SESSION_SECRET ?? "";
  if (!expected || !secret) {
    return NextResponse.json({ error: "auth non configurée" }, { status: 500 });
  }
  if ((await sha256Hex(String(password))) !== expected) {
    return NextResponse.json({ error: "mot de passe incorrect" }, { status: 401 });
  }
  const token = await createSession(secret);
  const res = NextResponse.json({ ok: true });
  res.cookies.set(SESSION_COOKIE, token, {
    httpOnly: true, secure: true, sameSite: "lax", path: "/", maxAge: 60 * 60 * 24 * 7,
  });
  return res;
}
