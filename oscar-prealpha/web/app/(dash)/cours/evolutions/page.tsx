"use client";

import { useState } from "react";
import { useSnapshot } from "@/lib/useSnapshot";
import { useFilters } from "@/lib/store";
import { PageTitle } from "@/components/PageTitle";
import { FilterSummary, yearLabel } from "@/components/Filters";
import { EvolutionPanel } from "@/components/EvolutionPanel";

export default function EvolutionsPage() {
  const { data } = useSnapshot();
  const yearMode = useFilters((s) => s.yearMode);
  const indicators = data.indicators ?? [{ key: "inscriptions", label: "Inscriptions", format: "int" as const }];
  const [metric, setMetric] = useState("inscriptions");
  const yrs = data.evolution.years;
  const span = yrs.length ? `${yearLabel(yrs[0], yearMode)}–${yearLabel(yrs.at(-1) ?? yrs[0], yearMode)}` : "";
  const single = yrs.length < 2;

  return (
    <div className="space-y-5">
      <PageTitle eyebrow="Cours" title="Évolutions pluriannuelles">
        Tendances par antenne sur {span}. {single && "Une seule période → vue histogramme (la courbe est inutile)."}
      </PageTitle>
      <FilterSummary />

      <div className="flex flex-wrap items-center gap-2.5">
        <span className="text-eyebrow font-semibold uppercase tracking-[0.06em] text-neutral-400">Indicateur</span>
        <div className="inline-flex flex-wrap gap-1 rounded-pill bg-neutral-100 p-[3px]">
          {indicators.map((i) => (
            <button
              key={i.key}
              onClick={() => setMetric(i.key)}
              className={`rounded-pill px-3 py-1.5 text-body-sm font-medium transition-all duration-150 ease-out-soft ${
                metric === i.key ? "bg-accent-500 text-white shadow-sm" : "text-neutral-600 hover:bg-surface hover:text-neutral-900"
              }`}
            >
              {i.label}
            </button>
          ))}
        </div>
      </div>

      <EvolutionPanel
        title={indicators.find((i) => i.key === metric)?.label ?? "Évolution"}
        subtitle={span}
        years={yrs}
        series={data.evolution.series}
        metric={metric}
      />
    </div>
  );
}
