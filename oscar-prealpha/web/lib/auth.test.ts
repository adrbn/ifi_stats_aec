import { describe, it, expect } from "vitest";
import { createSession, verifySession } from "./auth";

const SECRET = "test-secret-at-least-32-chars-long-xxxx";

describe("auth session", () => {
  it("crée un cookie vérifiable", async () => {
    const token = await createSession(SECRET);
    expect(await verifySession(token, SECRET)).toBe(true);
  });
  it("rejette un token altéré", async () => {
    const token = await createSession(SECRET);
    expect(await verifySession(token + "x", SECRET)).toBe(false);
  });
  it("rejette un token vide", async () => {
    expect(await verifySession("", SECRET)).toBe(false);
  });
});
