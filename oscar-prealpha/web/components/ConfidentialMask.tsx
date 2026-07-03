"use client";

import { useFilters } from "@/lib/store";

/**
 * Placeholder affiché à la place d'une section entièrement composée de données
 * de recettes lorsque le mode confidentiel est actif. Propose de le désactiver.
 */
export function ConfidentialMask({ label = "Contenu masqué (recettes)" }: { label?: string }) {
  const setConfidential = useFilters((s) => s.setConfidential);
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-md border border-dashed border-neutral-300 bg-neutral-50 px-6 py-14 text-center">
      <svg className="h-7 w-7 text-neutral-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <rect x="3" y="11" width="18" height="10" rx="2" />
        <path d="M7 11V7a5 5 0 0 1 10 0v4" />
      </svg>
      <div className="text-body-sm font-semibold text-neutral-700">{label}</div>
      <p className="max-w-sm text-caption text-neutral-500">
        Le mode confidentiel est activé : les données liées aux recettes sont masquées.
      </p>
      <button
        onClick={() => setConfidential(false)}
        className="rounded-md border border-neutral-300 bg-surface px-3 py-1.5 text-body-sm font-medium text-neutral-700 transition-colors hover:border-accent-400 hover:text-accent-700"
      >
        Afficher les recettes
      </button>
    </div>
  );
}
