"use client";

import { useState } from "react";
import { useSnapshot } from "@/lib/useSnapshot";
import { useFilters } from "@/lib/store";
import { useConfidential, isSensitiveKey } from "@/lib/confidential";
import { Panel } from "./Card";
import { PageTitle } from "./PageTitle";
import { FilterSummary } from "./Filters";
import { SectorTable } from "./SectorTable";
import { IndicatorBarPie, Heatmap } from "./RichCharts";
import { HBar } from "./Charts";

export function SecteursView() {
  const { data } = useSnapshot();
  const { filterKeyed } = useConfidential();
  const antennas = useFilters((s) => s.antennas);
  const indicators = filterKeyed(data.indicators ?? []);
  const [indSel, setInd] = useState("inscriptions");
  const ind = isSensitiveKey(indSel) && !indicators.some((i) => i.key === indSel) ? "inscriptions" : indSel;
  const meta = indicators.find((i) => i.key === ind);
  const unit = (meta?.format ?? "int") as "int" | "eur" | "dec1";
  const rows = data.bySectorIndicator?.[ind] ?? [];
  const sa = data.sectorAntenna;
  const byAnt = data.byAntennaIndicator?.[ind] ?? [];

  // Légende du/des centre(s) réellement affiché(s) dans le graphe : quand une
  // seule antenne est sélectionnée, le titre reste « IFI — … » (demandé) mais
  // la légende ci-dessous indique clairement de quel centre proviennent les
  // barres. Couleurs = méta antennes du snapshot.
  const antMeta = data.meta.antennas ?? [];
  const selectedAnts = antMeta.filter((a) => a.code !== "IFI" && antennas.includes(a.code));
  const allAnts = antennas.length === 4;
  const secteurSubtitle = allAnts
    ? "Toutes antennes confondues"
    : `Centre${selectedAnts.length > 1 ? "s" : ""} : ${selectedAnts.map((a) => a.name).join(", ")}`;

  return (
    <div className="space-y-5">
      <PageTitle eyebrow="Cours" title="Par secteurs">
        Analyse par secteur, tous indicateurs — vue IFI, croisement secteur × antenne, détail par antenne.
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

      <Panel title={`IFI — ${meta?.label ?? ""} par secteur`} subtitle={secteurSubtitle}>
        {!allAnts && selectedAnts.length > 0 && (
          <div className="mb-3 flex flex-wrap items-center gap-2">
            <span className="text-eyebrow font-semibold uppercase tracking-[0.06em] text-neutral-400">Centre affiché</span>
            {selectedAnts.map((a) => (
              <span key={a.code} className="inline-flex items-center gap-1.5 rounded-pill border border-neutral-200 bg-surface px-2.5 py-[3px] text-caption font-medium text-neutral-700">
                <span className="h-2 w-2 rounded-full" style={{ background: a.color }} />
                {a.name}
              </span>
            ))}
          </div>
        )}
        <IndicatorBarPie data={rows} unit={unit} />
      </Panel>

      {sa && sa.sectors.length > 0 && (
        <Panel title="Croisement secteur × antenne" subtitle={meta?.label ?? "Inscriptions"}>
          <Heatmap
            rows={sa.sectors}
            cols={sa.antennas}
            values={sa.matrices?.[ind] ?? sa.inscriptions}
            unit={unit}
          />
        </Panel>
      )}

      <Panel title={`${meta?.label ?? ""} par antenne`} subtitle="Total sur le périmètre filtré">
        <HBar data={byAnt.map((a) => ({ name: a.code, value: a.value }))} height={200} />
      </Panel>

      <Panel title="Tableau détaillé" subtitle="Tous secteurs · tous indicateurs">
        <SectorTable rows={data.sectors.rows} total={data.sectors.total} />
      </Panel>
    </div>
  );
}
