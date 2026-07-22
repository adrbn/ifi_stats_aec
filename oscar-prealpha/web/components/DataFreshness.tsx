"use client";

import { useEffect, useState } from "react";

interface Updates {
  cours: string | null;
  produits: string | null;
  profils: string | null;
}

const DOMAINS: { key: keyof Updates; label: string; color: string }[] = [
  { key: "cours", label: "Cours", color: "#2563eb" },
  { key: "produits", label: "Produits", color: "#16a34a" },
  { key: "profils", label: "Profils", color: "#d97706" },
];

/** Date lisible « 21 juillet 2026 à 18:14 » (ou « — » si absente/invalide). */
function fmt(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return (
    d.toLocaleDateString("fr-FR", { day: "numeric", month: "long", year: "numeric" }) +
    " à " +
    d.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" })
  );
}

/** Bandeau « Fraîcheur des données » : date de dernière mise à jour de chaque
 *  jeu de données (Cours / Produits / Profils). */
export function DataFreshness() {
  const [u, setU] = useState<Updates | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let alive = true;
    fetch("/api/data-updates", { cache: "no-store" })
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => alive && setU(d))
      .catch(() => alive && setU(null))
      .finally(() => alive && setLoaded(true));
    return () => {
      alive = false;
    };
  }, []);

  return (
    <section className="border-t border-neutral-200 py-10">
      <div className="text-eyebrow font-semibold uppercase tracking-[0.1em] text-neutral-400">
        Fraîcheur des données
      </div>
      <p className="mt-1 text-body-sm text-neutral-500">
        Dernière mise à jour du chargement des données de chaque domaine.
      </p>
      <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-3">
        {DOMAINS.map((dom) => (
          <div key={dom.key} className="rounded-md border border-neutral-200 bg-surface p-4">
            <div className="flex items-center gap-2">
              <span className="h-2.5 w-2.5 rounded-full" style={{ background: dom.color }} />
              <span className="text-body font-semibold text-neutral-900">{dom.label}</span>
            </div>
            <div className="mt-2 text-caption uppercase tracking-[0.06em] text-neutral-400">
              Dernière mise à jour
            </div>
            <div className="tnum text-body-sm text-neutral-700">
              {!loaded ? "…" : fmt(u?.[dom.key])}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
