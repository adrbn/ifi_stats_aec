"use client";

import { useState } from "react";
import { useSnapshot } from "@/lib/useSnapshot";
import { useFilters } from "@/lib/store";
import { KpiRow } from "@/components/KpiCard";
import { Panel } from "@/components/Card";
import { PageTitle } from "@/components/PageTitle";
import { AntennaBar } from "@/components/Charts";
import { EvolutionPanel } from "@/components/EvolutionPanel";
import { SectorTable } from "@/components/SectorTable";
import { FilterSummary, yearLabel } from "@/components/Filters";
import { Sankey, FlowTreemap } from "@/components/RichCharts";

const SEDE_COLORS: Record<string, string> = { IFM: "#FF8C00", IFF: "#8B5CF6", IFN: "#22C55E", IFP: "#EF4444" };

export default function SynthesePage() {
  const { data } = useSnapshot();
  const yearMode = useFilters((s) => s.yearMode);
  const toggleDim = useFilters((s) => s.toggleDim);

  const indicators = data.indicators ?? [{ key: "inscriptions", label: "Inscriptions", format: "int" as const }];
  const [ind, setInd] = useState("inscriptions");
  const indMeta = indicators.find((i) => i.key === ind) ?? indicators[0];
  const indLabel = indMeta?.label ?? "Inscriptions";
  const lower = indLabel.toLowerCase();
  const unit = (indMeta?.format ?? "int") as "int" | "eur" | "dec1";

  // Par antenne pour l'indicateur choisi. IFI = somme (additif) ou ratio global
  // (remplissage, non sommable).
  const byInd = data.byAntennaIndicator ?? {};
  const antRows = (byInd[ind] ?? []).map((r) => ({ code: r.code, color: r.color, value: r.value }));
  const sumInd = (k: string) => (byInd[k] ?? []).reduce((s, r) => s + r.value, 0);
  const ifiTotal = ind === "remplissage" ? (sumInd("cours") ? sumInd("inscriptions") / sumInd("cours") : 0) : undefined;

  // Flux / treemap : seuls les indicateurs additifs ont un sens (un treemap de
  // ratio n'en a pas) → le remplissage retombe sur les inscriptions.
  const flowKey = ind === "remplissage" ? "inscriptions" : ind;
  const flowLabel = ind === "remplissage" ? "inscriptions" : lower;
  const flowUnit: "int" | "eur" = ind === "recettes" ? "eur" : "int";
  const flows = (data.flows ?? [])
    .map((f) => ({ ...f, value: f.values?.[flowKey] ?? f.value }))
    .filter((f) => f.value > 0);

  const eyebrowYears = (data.filters.years ?? []).map((y) => yearLabel(y, yearMode)).join(", ");
  const evoYears = data.evolution.years;
  const evoSpan = `${yearLabel(evoYears[0], yearMode)}–${yearLabel(evoYears.at(-1) ?? evoYears[0], yearMode)}`;

  return (
    <div className="space-y-5">
      <PageTitle eyebrow={`Cours · ${eyebrowYears || yearLabel(data.filters.year, yearMode)}`} title="Synthèse du réseau">
        Vue d'ensemble du réseau sur le périmètre filtré. Choisissez l'indicateur pour piloter les graphes.
      </PageTitle>

      <FilterSummary />
      <KpiRow kpis={data.kpis} />

      {/* Sélecteur d'indicateur — pilote tous les graphes ci-dessous. */}
      <div className="flex flex-wrap items-center gap-2.5">
        <span className="text-eyebrow font-semibold uppercase tracking-[0.06em] text-neutral-400">Indicateur</span>
        <div className="inline-flex flex-wrap gap-1 rounded-pill bg-neutral-100 p-[3px]">
          {indicators.map((i) => (
            <button
              key={i.key}
              onClick={() => setInd(i.key)}
              className={`rounded-pill px-3 py-1.5 text-body-sm font-medium transition-all duration-150 ease-out-soft ${
                ind === i.key ? "bg-accent-500 text-white shadow-sm" : "text-neutral-600 hover:bg-surface hover:text-neutral-900"
              }`}
            >
              {i.label}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-2">
        <Panel title={`${indLabel} par antenne`} subtitle="IFI (réseau) + antennes">
          <AntennaBar rows={antRows} unit={unit} label={indLabel} total={ifiTotal} />
        </Panel>
        <EvolutionPanel
          title={`Évolution · ${lower}`}
          subtitle={evoSpan}
          years={data.evolution.years}
          series={data.evolution.series}
          metric={ind}
        />
      </div>

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-2">
        <Panel title="Flux antenne → secteur" subtitle={`Sankey · ${flowLabel}`}>
          {flows.length ? <Sankey flows={flows} sedeColors={SEDE_COLORS} height={320} /> : null}
        </Panel>
        <Panel title="Répartition hiérarchique" subtitle={`${flowLabel} · clic = filtre secteur`}>
          {flows.length ? (
            <FlowTreemap flows={flows} height={320} unit={flowUnit} label={flowLabel} onSelect={(sec) => toggleDim("secteurs", sec)} />
          ) : null}
        </Panel>
      </div>

      <Panel title="Détail par secteur" subtitle="Tous indicateurs">
        <SectorTable rows={data.sectors.rows} total={data.sectors.total} />
      </Panel>
    </div>
  );
}
