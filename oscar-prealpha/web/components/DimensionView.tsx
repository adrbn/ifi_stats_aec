"use client";

import { useState } from "react";
import { useSnapshot } from "@/lib/useSnapshot";
import { useFilters, type DimKey } from "@/lib/store";
import { useConfidential, isSensitiveKey } from "@/lib/confidential";
import { Panel } from "./Card";
import { PageTitle } from "./PageTitle";
import { FilterSummary } from "./Filters";
import { HBar } from "./Charts";
import { SectorIndicatorTable } from "./SectorIndicatorTable";

const NON_RENSEIGNE = "(Non renseigné)";

/** Vue générique « par dimension » (période, tranche d'âge, …) : mêmes
 *  composants que « Par niveau » — sélecteur tous indicateurs + graphe +
 *  tableau détaillé tous indicateurs, clic = filtre. */
export function DimensionView({
  dataKey,
  filterDimKey,
  eyebrow,
  title,
  description,
  firstHeader,
  sortLabels,
}: {
  dataKey: string; // clé dans data.byDimensionIndicator (ex. "periode", "age")
  filterDimKey: DimKey; // clé de filtre store (ex. "periodes", "ages")
  eyebrow: string;
  title: string;
  description: string;
  firstHeader: string;
  sortLabels?: (a: string, b: string) => number;
}) {
  const { data } = useSnapshot();
  const { filterKeyed } = useConfidential();
  const toggleDim = useFilters((s) => s.toggleDim);
  const active = useFilters((s) => s.dims[filterDimKey]);

  const indicators = filterKeyed(data.indicators ?? []);
  const [indSel, setInd] = useState("inscriptions");
  const ind = isSensitiveKey(indSel) && !indicators.some((i) => i.key === indSel) ? "inscriptions" : indSel;
  const meta = indicators.find((i) => i.key === ind);
  const unit = (meta?.format ?? "int") as "int" | "eur" | "dec1";

  const byDim = data.byDimensionIndicator?.[dataKey] ?? {};
  // « (Non renseigné) » toujours en dernier ; sinon ordre fourni (ex. chrono) ou
  // ordre backend (inscriptions décroissantes).
  const defaultSort = (a: string, b: string) =>
    a === NON_RENSEIGNE ? 1 : b === NON_RENSEIGNE ? -1 : 0;
  const labels = (byDim.inscriptions ?? []).map((r) => r.label).sort(sortLabels ?? defaultSort);

  const chartData = labels
    .map((lab) => ({ name: lab, value: byDim[ind]?.find((r) => r.label === lab)?.value ?? 0 }))
    .filter((r) => r.value > 0)
    .slice(0, 20);

  const kpiCols = filterKeyed(data.kpis).map((k) => ({ key: k.key, label: k.label, format: k.format }));
  const kpiTotals = Object.fromEntries(data.kpis.map((k) => [k.key, k.value]));

  return (
    <div className="space-y-5">
      <PageTitle eyebrow={eyebrow} title={title}>
        {description}
      </PageTitle>
      <FilterSummary />

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

      <Panel title={`${title} · ${meta?.label ?? ""}`} subtitle={chartData.length > 20 ? "20 premiers" : undefined}>
        {chartData.length ? (
          <HBar data={chartData} height={Math.max(220, chartData.length * 26)} unit={unit} />
        ) : (
          <p className="text-body-sm text-neutral-500">Aucune donnée pour ce périmètre.</p>
        )}
      </Panel>

      <Panel title="Détail" subtitle={`${labels.length} lignes · tous indicateurs · clic = filtre`}>
        <div className="thin-scroll max-h-[560px] overflow-auto">
          <SectorIndicatorTable
            sectors={labels}
            byInd={byDim}
            columns={kpiCols}
            totals={kpiTotals}
            firstHeader={firstHeader}
            totalLabel="Total"
            onRowClick={(label) => toggleDim(filterDimKey, label)}
            activeLabels={active}
          />
        </div>
      </Panel>
    </div>
  );
}
