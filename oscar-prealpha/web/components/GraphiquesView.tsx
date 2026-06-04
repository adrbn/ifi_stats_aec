"use client";

import { useSnapshot } from "@/lib/useSnapshot";
import { Panel } from "./Card";
import { PageTitle } from "./PageTitle";
import { FilterSummary } from "./Filters";
import { Sankey, FlowTreemap, DoubleDonut } from "./RichCharts";

const SEDE_COLORS: Record<string, string> = {
  IFM: "#FF8C00",
  IFF: "#8B5CF6",
  IFN: "#22C55E",
  IFP: "#EF4444",
};

export function GraphiquesView() {
  const { data } = useSnapshot();
  const flows = data.flows ?? [];
  const antenna = data.byAntenna.map((a) => ({ label: a.code, value: a.inscriptions, color: a.color }));
  const sectorRows = data.bySectorIndicator?.inscriptions ?? data.sectors.rows.map((r) => ({ label: r.secteur, value: r.inscriptions }));

  return (
    <div className="space-y-5">
      <PageTitle eyebrow="Cours" title="Graphiques">
        Vues d'ensemble des flux d'inscriptions — antenne → secteur — sur le périmètre filtré.
      </PageTitle>
      <FilterSummary />

      <Panel title="Flux antenne → secteur" subtitle="Sankey · inscriptions">
        {flows.length ? <Sankey flows={flows} sedeColors={SEDE_COLORS} /> : <Empty />}
      </Panel>

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-2">
        <Panel title="Répartition hiérarchique" subtitle="Treemap antenne · secteur">
          {flows.length ? <FlowTreemap flows={flows} /> : <Empty />}
        </Panel>
        <Panel title="Double anneau" subtitle="Antennes (intérieur) · secteurs (extérieur)">
          {antenna.length ? <DoubleDonut antenna={antenna} sector={sectorRows} /> : <Empty />}
        </Panel>
      </div>
    </div>
  );
}

function Empty() {
  return <p className="py-10 text-center text-body-sm text-neutral-500">Aucune donnée sur ce périmètre.</p>;
}
