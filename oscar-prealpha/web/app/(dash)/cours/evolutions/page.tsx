"use client";

import { useState } from "react";
import { useSnapshot } from "@/lib/useSnapshot";
import { Panel } from "@/components/Card";
import { PageTitle } from "@/components/PageTitle";
import { FilterSummary } from "@/components/Filters";
import { EvolutionLine } from "@/components/Charts";

export default function EvolutionsPage() {
  const { data } = useSnapshot();
  const indicators = data.indicators ?? [{ key: "inscriptions", label: "Inscriptions", format: "int" as const }];
  const [metric, setMetric] = useState("inscriptions");
  const span = `${data.evolution.years[0]}–${data.evolution.years.at(-1)}`;
  const single = data.evolution.years.length < 2;

  return (
    <div className="space-y-5">
      <PageTitle eyebrow="Cours" title="Évolutions pluriannuelles">
        Tendances par antenne sur {span}. {single && "Sélectionnez ≥ 2 années pour une vraie courbe."}
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

      <Panel title={indicators.find((i) => i.key === metric)?.label ?? "Évolution"} subtitle={span}>
        <EvolutionLine years={data.evolution.years} series={data.evolution.series} metric={metric} />
      </Panel>
    </div>
  );
}
