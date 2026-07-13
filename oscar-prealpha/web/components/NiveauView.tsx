"use client";

import { useState } from "react";
import { useSnapshot } from "@/lib/useSnapshot";
import { useFilters } from "@/lib/store";
import { useConfidential, isSensitiveKey } from "@/lib/confidential";
import { Panel } from "./Card";
import { PageTitle } from "./PageTitle";
import { FilterSummary } from "./Filters";
import { HBar } from "./Charts";
import { SectorIndicatorTable } from "./SectorIndicatorTable";

const CEFR_ORDER = [
  "A1", "A1.1", "A1.2", "A2", "A2.1", "A2.2",
  "B1", "B1.1", "B1.2", "B2", "B2.1", "B2.2",
  "C1", "C1.1", "C1.2", "C2", "C2.1", "C2.2",
];

/** Cours « multi-niveaux » : une vraie valeur AEC (pas un agrégat). */
function isMultiLevel(label: string): boolean {
  return /^tous les niveaux/i.test(label.trim());
}

/** Rang de tri : niveaux CEFR dans l'ordre, puis Avancé/Supérieur, puis autres,
 *  et « Tous les niveaux » (multi-niveaux) toujours en dernier. */
function levelRank(label: string): number {
  const s = label.trim();
  if (/non renseign/i.test(s)) return 10001; // toujours en dernier, après multi-niveaux
  if (isMultiLevel(s)) return 9999;
  const m = s.match(/^([ABC][12](?:\.[12])?)/);
  if (m) {
    const idx = CEFR_ORDER.indexOf(m[1]);
    return idx >= 0 ? idx : 500;
  }
  if (/avanc/i.test(s)) return 600;
  if (/sup[ée]rieur/i.test(s)) return 601;
  return 700;
}

/** Libellé lisible : désambiguïse le cas multi-niveaux. */
function niveauLabel(label: string): string {
  return isMultiLevel(label) ? "Tous niveaux (cours multi-niveaux)" : label.trim();
}

export function NiveauView() {
  const { data } = useSnapshot();
  const { filterKeyed } = useConfidential();
  const setDim = useFilters((s) => s.toggleDim);
  const activeNiveaux = useFilters((s) => s.dims.niveaux);

  // Sélecteur : TOUS les indicateurs (comme Synthèse / Par secteurs), confidentiel respecté.
  const indicators = filterKeyed(data.indicators ?? []);
  const [indSel, setInd] = useState("inscriptions");
  const ind = isSensitiveKey(indSel) && !indicators.some((i) => i.key === indSel) ? "inscriptions" : indSel;
  const meta = indicators.find((i) => i.key === ind);
  const unit = (meta?.format ?? "int") as "int" | "eur" | "dec1";

  const byNiv = data.byNiveauIndicator ?? {};
  // Liste des niveaux (à partir des inscriptions, toujours présentes), triée CEFR.
  const niveaux = (byNiv.inscriptions ?? []).map((r) => r.label).sort((a, b) => levelRank(a) - levelRank(b));

  const chartData = niveaux
    .map((lab) => ({ name: niveauLabel(lab), value: byNiv[ind]?.find((r) => r.label === lab)?.value ?? 0 }))
    .filter((r) => r.value > 0);

  const kpiCols = filterKeyed(data.kpis).map((k) => ({ key: k.key, label: k.label, format: k.format }));
  const kpiTotals = Object.fromEntries(data.kpis.map((k) => [k.key, k.value]));

  return (
    <div className="space-y-5">
      <PageTitle eyebrow="Cours" title="Par niveau">
        Ventilation par niveau CEFR (A1 → C2) sur le périmètre filtré. Cliquez une ligne pour filtrer le tableau de bord sur ce niveau.
      </PageTitle>
      <FilterSummary />

      {/* Rappel de la nuance métier demandée. */}
      <div className="flex items-start gap-2 rounded-md border border-accent-100 bg-accent-50/50 px-3 py-2 text-caption text-neutral-600">
        <span className="mt-0.5 flex-shrink-0 font-semibold text-accent-700">i</span>
        <span>
          <b>« Tous niveaux (cours multi-niveaux) »</b> est un <b>type de cours réel</b> couvrant tous les niveaux — ce n'est
          <b> pas</b> une somme. Pour la vue « tous niveaux confondus », laissez le filtre Niveau vide (option « Tous »).
        </span>
      </div>

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

      <Panel title={`Par niveau · ${meta?.label ?? ""}`} subtitle="Niveaux CEFR ordonnés (multi-niveaux en fin)">
        {chartData.length ? (
          <HBar data={chartData} height={Math.max(220, chartData.length * 26)} unit={unit} />
        ) : (
          <p className="text-body-sm text-neutral-500">Aucune donnée pour ce périmètre.</p>
        )}
      </Panel>

      <Panel title="Détail par niveau" subtitle={`${niveaux.length} niveaux · tous indicateurs · clic = filtre`}>
        <div className="thin-scroll max-h-[520px] overflow-auto">
          <SectorIndicatorTable
            sectors={niveaux}
            byInd={byNiv}
            columns={kpiCols}
            totals={kpiTotals}
            firstHeader="Niveau"
            totalLabel="Total"
            onRowClick={(label) => setDim("niveaux", label)}
            activeLabels={activeNiveaux}
            renderLabel={(label) => (
              <span className="inline-flex items-center">
                {niveauLabel(label)}
                {isMultiLevel(label) && (
                  <span className="ml-1.5 rounded-xs bg-neutral-200 px-1.5 py-0.5 text-[10px] font-semibold uppercase text-neutral-600">multi</span>
                )}
              </span>
            )}
          />
        </div>
      </Panel>
    </div>
  );
}
