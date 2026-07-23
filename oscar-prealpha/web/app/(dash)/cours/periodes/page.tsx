"use client";

import { DimensionView } from "@/components/DimensionView";

const MONTHS: Record<string, number> = {
  JANVIER: 1, FEVRIER: 2, MARS: 3, AVRIL: 4, MAI: 5, JUIN: 6,
  JUILLET: 7, AOUT: 8, SEPTEMBRE: 9, OCTOBRE: 10, NOVEMBRE: 11, DECEMBRE: 12,
};

/** Sans accents ni casse : « 2023-FÉVRIER » doit correspondre à « FEVRIER ».
 *  (NFD sépare la lettre de son accent, `\p{Diacritic}` retire ce dernier.) */
function fold(s: string): string {
  return (s ?? "").normalize("NFD").replace(/\p{Diacritic}/gu, "").toUpperCase();
}

/** Tri chronologique des libellés de période AEC.
 *
 *  Ces libellés sont paramétrés dans AEC et ne suivent pas tous « ANNÉE-MOIS » :
 *  « EXAMENS 2022 », « 2025 - Semestre 1 », ou plusieurs périodes accolées
 *  (« 2024-MARS, 2024-JUILLET »). On trie donc sur la 1ʳᵉ année trouvée, puis
 *  sur le 1ᵉʳ mois reconnu, puis alphabétiquement. Même logique que
 *  `periode_sort_key` côté serveur (build_snapshot.py).
 */
function chrono(a: string, b: string): number {
  const key = (raw: string): [number, number, string] => {
    const s = fold(raw);
    const y = parseInt(s.match(/20\d{2}/)?.[0] ?? "", 10) || 9999;
    let mois = 99;
    let pos = s.length + 1;
    for (const [nom, num] of Object.entries(MONTHS)) {
      const i = s.indexOf(nom);
      if (i !== -1 && i < pos) {
        pos = i;
        mois = num;
      }
    }
    return [y, mois, s];
  };
  const ka = key(a);
  const kb = key(b);
  return ka[0] - kb[0] || ka[1] - kb[1] || ka[2].localeCompare(kb[2]);
}

export default function Page() {
  return (
    <DimensionView
      dataKey="periode"
      filterDimKey="periodes"
      eyebrow="Cours"
      title="Par période"
      firstHeader="Période"
      description="Ventilation par période telle qu'elle est saisie dans AEC. Cliquez une ligne pour filtrer."
      sortLabels={chrono}
    />
  );
}
