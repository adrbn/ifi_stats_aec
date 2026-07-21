"use client";

import { DimensionView } from "@/components/DimensionView";

// Ordre pédagogique (du plus âgé au plus jeune) ; « (Non renseigné) » en fin.
const AGE_ORDER = ["ADULTES", "ADOLESCENTS", "ENFANTS 6-11 ANS", "ENFANTS 2-6 ANS"];
function byAge(a: string, b: string): number {
  const rank = (s: string) => {
    const i = AGE_ORDER.indexOf(s.trim().toUpperCase());
    return i >= 0 ? i : 900 + (s === "(Non renseigné)" ? 99 : 0);
  };
  return rank(a) - rank(b);
}

export default function Page() {
  return (
    <DimensionView
      dataKey="age"
      filterDimKey="ages"
      eyebrow="Cours"
      title="Par tranches d'âge"
      firstHeader="Tranche d'âge"
      description="Ventilation par tranche d'âge (Adultes, Adolescents, Enfants). Cliquez une ligne pour filtrer le tableau de bord."
      sortLabels={byAge}
    />
  );
}
