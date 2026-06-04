import { SignJWT, jwtVerify } from "jose";

const ALG = "HS256";
export const SESSION_COOKIE = "oscar_session";

function key(secret: string): Uint8Array {
  return new TextEncoder().encode(secret);
}

/** Crée un JWT de session valable 7 jours. */
export async function createSession(secret: string): Promise<string> {
  return await new SignJWT({ ok: true })
    .setProtectedHeader({ alg: ALG })
    .setIssuedAt()
    .setExpirationTime("7d")
    .sign(key(secret));
}

/** Vérifie la signature + l'expiration. Ne lève jamais. */
export async function verifySession(token: string, secret: string): Promise<boolean> {
  if (!token) return false;
  try {
    await jwtVerify(token, key(secret), { algorithms: [ALG] });
    return true;
  } catch {
    return false;
  }
}
