"use client";

import { useSnapshot } from "@/lib/useSnapshot";
import { KpiRow } from "@/components/KpiCard";
import { Panel } from "@/components/Card";
import { PageTitle } from "@/components/PageTitle";
import { AntennaBar, EvolutionLine } from "@/components/Charts";
import { SectorTable } from "@/components/SectorTable";
import { FilterSummary } from "@/components/Filters";
import { Sankey, FlowTreemap } from "@/components/RichCharts";

const SEDE_COLORS: Record<string, string> = { IFM: "#FF8C00", IFF: "#8B5CF6", IFN: "#22C55E", IFP: "#EF4444" };

export default function SynthesePage() {
  const { data } = useSnapshot();
  const flows = data.flows ?? [];
  return (
    <div className="space-y-5">
      <PageTitle eyebrow={`Cours · ${(data.filters.years ?? []).join(", ") || data.filters.year}`} title="Synthèse du réseau">
        Vue d'ensemble : inscriptions, cours, recettes, remplissage sur le périmètre filtré.
      </PageTitle>

      <FilterSummary />
      <KpiRow kpis={data.kpis} />

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-2">
        <Panel title="Inscriptions par antenne" subtitle="Périmètre filtré">
          <AntennaBar rows={data.byAntenna} />
        </Panel>
        <Panel title="Évolution des inscriptions" subtitle={`${data.evolution.years[0]}–${data.evolution.years.at(-1)}`}>
          <EvolutionLine years={data.evolution.years} series={data.evolution.series} />
        </Panel>
      </div>

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-2">
        <Panel title="Flux antenne → secteur" subtitle="Sankey · inscriptions">
          {flows.length ? <Sankey flows={flows} sedeColors={SEDE_COLORS} height={320} /> : null}
        </Panel>
        <Panel title="Répartition hiérarchique" subtitle="Treemap antenne · secteur">
          {flows.length ? <FlowTreemap flows={flows} height={320} /> : null}
        </Panel>
      </div>

      <Panel title="Détail par secteur" subtitle="Inscriptions, recettes et remplissage">
        <SectorTable rows={data.sectors.rows} total={data.sectors.total} />
      </Panel>
    </div>
  );
}
