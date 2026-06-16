"use client";

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
  const flows = data.flows ?? [];
  const eyebrowYears = (data.filters.years ?? []).map((y) => yearLabel(y, yearMode)).join(", ");
  const evoYears = data.evolution.years;
  return (
    <div className="space-y-5">
      <PageTitle eyebrow={`Cours · ${eyebrowYears || yearLabel(data.filters.year, yearMode)}`} title="Synthèse du réseau">
        Vue d'ensemble : inscriptions, cours, recettes, remplissage sur le périmètre filtré.
      </PageTitle>

      <FilterSummary />
      <KpiRow kpis={data.kpis} />

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-2">
        <Panel title="Inscriptions par antenne" subtitle="IFI (réseau) + antennes">
          <AntennaBar rows={data.byAntenna} />
        </Panel>
        <EvolutionPanel
          title="Évolution des inscriptions"
          subtitle={`${yearLabel(evoYears[0], yearMode)}–${yearLabel(evoYears.at(-1) ?? evoYears[0], yearMode)}`}
          years={data.evolution.years}
          series={data.evolution.series}
        />
      </div>

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-2">
        <Panel title="Flux antenne → secteur" subtitle="Sankey · inscriptions">
          {flows.length ? <Sankey flows={flows} sedeColors={SEDE_COLORS} height={320} /> : null}
        </Panel>
        <Panel title="Répartition hiérarchique" subtitle="Antenne · secteur — clic = filtre secteur">
          {flows.length ? <FlowTreemap flows={flows} height={320} onSelect={(sec) => toggleDim("secteurs", sec)} /> : null}
        </Panel>
      </div>

      <Panel title="Détail par secteur" subtitle="Inscriptions, recettes et remplissage">
        <SectorTable rows={data.sectors.rows} total={data.sectors.total} />
      </Panel>
    </div>
  );
}
