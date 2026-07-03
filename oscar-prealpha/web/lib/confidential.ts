"use client";

import { useFilters } from "./store";

/**
 * Mode confidentiel — masque toute donnée liée aux RECETTES.
 *
 * Clés d'indicateurs sensibles = recettes + les deux paniers moyens (dérivés des
 * recettes). Toute vue affichant l'une de ces valeurs doit la masquer quand le
 * mode est actif (activé par défaut, cf. store.confidential).
 */
export const SENSITIVE_KEYS = new Set(["recettes", "panier_inscr", "panier_pers"]);

export function isSensitiveKey(key: string): boolean {
  return SENSITIVE_KEYS.has(key);
}

/** Hook : renvoie l'état confidentiel + des filtres prêts à l'emploi. */
export function useConfidential() {
  const confidential = useFilters((s) => s.confidential);
  return {
    confidential,
    /** Retire les indicateurs/KPI sensibles d'une liste `{ key }` quand actif. */
    filterKeyed<T extends { key: string }>(items: T[]): T[] {
      return confidential ? items.filter((i) => !isSensitiveKey(i.key)) : items;
    },
    /** Vrai si cette clé doit être masquée dans le contexte courant. */
    hidden(key: string): boolean {
      return confidential && isSensitiveKey(key);
    },
  };
}
