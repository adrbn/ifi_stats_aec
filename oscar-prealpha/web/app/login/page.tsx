"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";

export default function LoginPage() {
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const router = useRouter();

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true); setError("");
    const res = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ password }),
    });
    setBusy(false);
    if (res.ok) router.replace("/");
    else setError("Mot de passe incorrect.");
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-neutral-50 px-4">
      <form onSubmit={submit} className="w-full max-w-sm rounded-xl border border-neutral-200 bg-white p-8 shadow-sm">
        <h1 className="mb-1 text-lg font-bold tracking-[0.12em]">OSCAR</h1>
        <p className="mb-6 text-sm text-neutral-500">Accès réservé au personnel autorisé</p>
        <label className="mb-2 block text-sm font-medium" htmlFor="pwd">Mot de passe</label>
        <input
          id="pwd" type="password" value={password} autoFocus
          onChange={(e) => setPassword(e.target.value)}
          className="mb-4 w-full rounded-md border border-neutral-300 px-3 py-2 text-sm outline-none focus:border-accent-600"
        />
        {error && <p className="mb-4 text-sm text-red-600">{error}</p>}
        <button
          type="submit" disabled={busy}
          className="w-full rounded-md bg-neutral-900 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-neutral-800 disabled:opacity-60"
        >
          {busy ? "Connexion…" : "Se connecter"}
        </button>
      </form>
    </main>
  );
}
