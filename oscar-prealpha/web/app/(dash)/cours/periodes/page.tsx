"use client";

import { DimensionView } from "@/components/DimensionView";

const MONTHS: Record<string, number> = {
  JANVIER: 1, FEVRIER: 2, MARS: 3, AVRIL: 4, MAI: 5, JUIN: 6,
  JUILLET: 7, AOUT: 8, SEPTEMBRE: 9, OCTOBRE: 10, NOVEMBRE: 11, DECEMBRE: 12,
};

/** Tri chronologique d'une période « ANNÉE-MOIS » (2025-OCTOBRE). */
function chrono(a: string, b: string): number {
  const key = (s: string): number => {
    const [y, m] = s.split("-");
    return (parseInt(y, 10) || 9999) * 100 + (MONTHS[(m ?? "").trim()] ?? 99);
  };
  return key(a) - key(b);
}

export default function Page() {
  return (
    <DimensionView
      dataKey="periode"
      filterDimKey="periodes"
      eyebrow="Cours"
      title="Par période"
      firstHeader="Période"
      description="Ventilation par période (année-mois), calculée sur la date de début réelle du cours. Cliquez une ligne pour filtrer."
      sortLabels={chrono}
    />
  );
}
