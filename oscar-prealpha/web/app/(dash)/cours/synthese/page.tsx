"use client";

import { useState } from "react";
import { useSnapshot } from "@/lib/useSnapshot";
import { useFilters } from "@/lib/store";
import { useConfidential, isSensitiveKey } from "@/lib/confidential";
import { KpiRow } from "@/components/KpiCard";
import { Panel } from "@/components/Card";
import { PageTitle } from "@/components/PageTitle";
import { AntennaBar, Donut } from "@/components/Charts";
import { EvolutionPanel } from "@/components/EvolutionPanel";
import { SectorIndicatorTable } from "@/components/SectorIndicatorTable";
import { NonRattacheDiag } from "@/components/NonRattacheDiag";
import { FilterSummary, yearLabel } from "@/components/Filters";
import { Sankey, FlowTreemap, AcquisitionRetention } from "@/components/RichCharts";

const SEDE_COLORS: Record<string, string> = { IFM: "#FF8C00", IFF: "#8B5CF6", IFN: "#22C55E", IFP: "#EF4444" };

export default function SynthesePage() {
  const { data } = useSnapshot();
  const yearMode = useFilters((s) => s.yearMode);
  const toggleDim = useFilters((s) => s.toggleDim);
  const { filterKeyed } = useConfidential();

  // Mode confidentiel : on retire les indicateurs de recettes du sélecteur.
  const indicators = filterKeyed(data.indicators ?? [{ key: "inscriptions", label: "Inscriptions", format: "int" as const }]);
  const [indSel, setInd] = useState("inscriptions");
  // Si l'indicateur choisi devient masqué, on retombe sur les inscriptions.
  const ind = isSensitiveKey(indSel) && !indicators.some((i) => i.key === indSel) ? "inscriptions" : indSel;
  const indMeta = indicators.find((i) => i.key === ind) ?? indicators[0];
  const indLabel = indMeta?.label ?? "Inscriptions";
  const lower = indLabel.toLowerCase();
  const unit = (indMeta?.format ?? "int") as "int" | "eur" | "dec1";

  // Par antenne pour l'indicateur choisi. IFI = somme (additif) ou ratio global
  // (remplissage / paniers, non sommables).
  const byInd = data.byAntennaIndicator ?? {};
  const antRows = (byInd[ind] ?? []).map((r) => ({ code: r.code, color: r.color, value: r.value }));
  const sumInd = (k: string) => (byInd[k] ?? []).reduce((s, r) => s + r.value, 0);
  const kpiVal = (k: string) => data.kpis.find((x) => x.key === k)?.value;
  // Indicateurs « ratio » (non sommables) : le total IFI n'est pas la somme des
  // antennes. Remplissage = ratio global recalculé ; paniers = valeur KPI globale
  // (le panier/personne a un dénominateur — élèves distincts — non additif).
  const isRatio = ind === "remplissage" || ind === "panier_inscr" || ind === "panier_pers";
  // IFI = TOTAL RÉSEAU (4 antennes), via networkTotals (non filtré par antenne) →
  // reste juste même quand une seule antenne est sélectionnée. Repli sur l'ancien
  // calcul si networkTotals absent (snapshot statique / hors-ligne).
  const ifiTotal =
    data.networkTotals?.[ind] ??
    (ind === "remplissage"
      ? (sumInd("cours") ? sumInd("inscriptions") / sumInd("cours") : 0)
      : ind === "panier_inscr" || ind === "panier_pers"
        ? (kpiVal(ind) ?? 0)
        : undefined);

  // Flux / treemap : seuls les indicateurs additifs ont un sens (un treemap de
  // ratio n'en a pas) → les ratios retombent sur les inscriptions.
  const flowKey = isRatio ? "inscriptions" : ind;
  const flowLabel = isRatio ? "inscriptions" : lower;
  const flowUnit: "int" | "eur" = ind === "recettes" ? "eur" : "int";
  const flows = (data.flows ?? [])
    .map((f) => ({ ...f, value: f.values?.[flowKey] ?? f.value }))
    .filter((f) => f.value > 0);

  const eyebrowYears = (data.filters.years ?? []).map((y) => yearLabel(y, yearMode)).join(", ");
  const evoYears = data.evolution.years;
  const evoSpan = `${yearLabel(evoYears[0], yearMode)}–${yearLabel(evoYears.at(-1) ?? evoYears[0], yearMode)}`;

  // Détail par secteur : mêmes colonnes que les étiquettes KPI (même ordre) ;
  // la ligne TOTAL reprend les valeurs KPI (juste même pour élèves différents).
  const kpiCols = filterKeyed(data.kpis).map((k) => ({ key: k.key, label: k.label, format: k.format }));
  const kpiTotals = Object.fromEntries(data.kpis.map((k) => [k.key, k.value]));
  const sectorList = (data.bySectorIndicator?.inscriptions ?? []).map((x) => x.label);

  // Acquisition vs fidélisation : nouveaux / réinscrits par antenne (+ total IFI).
  const nouv = byInd.nouveaux ?? [];
  const reins = byInd.reinscrits ?? [];
  const acqRows = [
    { name: "IFI", highlight: true, nouveaux: sumInd("nouveaux"), reinscrits: sumInd("reinscrits") },
    ...nouv.map((n) => ({ name: n.code, nouveaux: n.value, reinscrits: reins.find((r) => r.code === n.code)?.value ?? 0 })),
  ];
  // Répartition par public (tranche d'âge) — composition des inscriptions.
  const publicData = (data.breakdowns?.age?.rows ?? []).map((r) => ({ name: r.label, value: r.inscriptions })).filter((r) => r.value > 0);

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
        <Panel title="Flux antenne → secteur" subtitle={`Sankey · ${flowLabel} · survolez un nœud`}>
          {flows.length ? <Sankey flows={flows} sedeColors={SEDE_COLORS} height={320} unit={flowUnit} label={flowLabel} /> : null}
        </Panel>
        <Panel title="Répartition hiérarchique" subtitle={`${flowLabel} · clic = filtre secteur`}>
          {flows.length ? (
            <FlowTreemap flows={flows} height={320} unit={flowUnit} label={flowLabel} onSelect={(sec) => toggleDim("secteurs", sec)} />
          ) : null}
        </Panel>
      </div>

      <div className="grid grid-cols-1 items-start gap-5 xl:grid-cols-2">
        <Panel title="Acquisition vs fidélisation" subtitle="Nouveaux / réinscrits par antenne · taux de réinscription">
          <AcquisitionRetention rows={acqRows} />
        </Panel>
        <Panel title="Répartition par public" subtitle="Inscriptions par tranche d'âge">
          {publicData.length ? <Donut data={publicData} height={260} /> : <p className="text-body-sm text-neutral-500">Aucune donnée.</p>}
        </Panel>
      </div>

      <Panel title="Détail par secteur" subtitle="Mêmes indicateurs que les étiquettes ci-dessus">
        <SectorIndicatorTable sectors={sectorList} byInd={data.bySectorIndicator ?? {}} columns={kpiCols} totals={kpiTotals} />
        {(data.diagnostics?.nonRattache?.length ?? 0) > 0 && (
          <div className="mt-4">
            <NonRattacheDiag rows={data.diagnostics!.nonRattache} />
          </div>
        )}
      </Panel>
    </div>
  );
}
