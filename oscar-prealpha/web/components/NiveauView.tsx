"use client";

import { useState } from "react";
import { useSnapshot } from "@/lib/useSnapshot";
import { useFilters } from "@/lib/store";
import { useConfidential } from "@/lib/confidential";
import { Panel } from "./Card";
import { PageTitle } from "./PageTitle";
import { FilterSummary } from "./Filters";
import { HBar } from "./Charts";
import { formatInt, formatEur, formatPct, formatDec1 } from "@/lib/format";
import type { BreakdownRow } from "@/lib/types";

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

type Metric = "inscriptions" | "cours" | "heures_eleves" | "recettes";

export function NiveauView() {
  const { data } = useSnapshot();
  const { hidden } = useConfidential();
  const showRecettes = !hidden("recettes");
  const setDim = useFilters((s) => s.toggleDim);
  const activeNiveaux = useFilters((s) => s.dims.niveaux);

  const metricsAll: { key: Metric; label: string; unit: "int" | "eur" }[] = [
    { key: "inscriptions", label: "Inscriptions", unit: "int" },
    { key: "cours", label: "Cours", unit: "int" },
    { key: "recettes", label: "Recettes", unit: "eur" },
  ];
  const metrics = showRecettes ? metricsAll : metricsAll.filter((m) => m.key !== "recettes");
  const [metricSel, setMetric] = useState<Metric>("inscriptions");
  const metric: Metric = metricSel === "recettes" && !showRecettes ? "inscriptions" : metricSel;
  const metricMeta = metrics.find((m) => m.key === metric) ?? metrics[0];

  const block = data.breakdowns?.niveau;
  const rows = [...(block?.rows ?? [])].sort((a, b) => levelRank(a.label) - levelRank(b.label));
  const total = block?.total;

  const chartData = rows
    .map((r) => ({ name: niveauLabel(r.label), value: Number(r[metric as keyof BreakdownRow] ?? 0) }))
    .filter((r) => r.value > 0);

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
          {metrics.map((m) => (
            <button
              key={m.key}
              onClick={() => setMetric(m.key)}
              className={`rounded-pill px-3 py-1.5 text-body-sm font-medium transition-all duration-150 ease-out-soft ${
                metric === m.key ? "bg-accent-500 text-white shadow-sm" : "text-neutral-600 hover:bg-surface hover:text-neutral-900"
              }`}
            >
              {m.label}
            </button>
          ))}
        </div>
      </div>

      <Panel title={`Par niveau · ${metricMeta?.label}`} subtitle="Niveaux CEFR ordonnés (multi-niveaux en fin)">
        {chartData.length ? (
          <HBar data={chartData} height={Math.max(220, chartData.length * 26)} unit={metricMeta?.unit ?? "int"} />
        ) : (
          <p className="text-body-sm text-neutral-500">Aucune donnée pour ce périmètre.</p>
        )}
      </Panel>

      <Panel title="Détail par niveau" subtitle={`${rows.length} niveaux · clic = filtre`}>
        <div className="thin-scroll max-h-[520px] overflow-auto rounded-md border border-neutral-200">
          <table className="w-full border-collapse text-body-sm">
            <thead>
              <tr>
                {["Niveau", "Cours", "Inscriptions", "Nouv.", "% nouv.", ...(showRecettes ? ["Recettes"] : []), "Rempl."].map((h, i) => (
                  <th key={h} className={`sticky top-0 z-10 border-b border-neutral-200 bg-neutral-50 px-3.5 py-2.5 text-eyebrow font-semibold uppercase text-neutral-600 ${i === 0 ? "text-left" : "text-right"}`}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => {
                const active = activeNiveaux.includes(r.label);
                return (
                  <tr
                    key={r.label}
                    onClick={() => setDim("niveaux", r.label)}
                    className={`cursor-pointer even:bg-neutral-50 hover:bg-accent-50 ${active ? "bg-accent-50 font-semibold" : ""}`}
                  >
                    <td className="px-3.5 py-2.5 font-medium text-neutral-800">
                      {niveauLabel(r.label)}
                      {isMultiLevel(r.label) && <span className="ml-1.5 rounded-xs bg-neutral-200 px-1.5 py-0.5 text-[10px] font-semibold uppercase text-neutral-600">multi</span>}
                    </td>
                    <td className="tnum px-3.5 py-2.5 text-right">{formatInt(r.cours)}</td>
                    <td className="tnum px-3.5 py-2.5 text-right">{formatInt(r.inscriptions)}</td>
                    <td className="tnum px-3.5 py-2.5 text-right">{formatInt(r.nouv)}</td>
                    <td className="tnum px-3.5 py-2.5 text-right">{formatPct(r.pctNouv)}</td>
                    {showRecettes && <td className="tnum px-3.5 py-2.5 text-right">{formatEur(r.recettes)}</td>}
                    <td className="tnum px-3.5 py-2.5 text-right">{formatDec1(r.remplissage)}</td>
                  </tr>
                );
              })}
              {total && (
                <tr className="sticky bottom-0 border-t-2 border-neutral-300 bg-neutral-100 font-semibold text-neutral-900">
                  <td className="px-3.5 py-2.5">Tous niveaux confondus</td>
                  <td className="tnum px-3.5 py-2.5 text-right">{formatInt(total.cours)}</td>
                  <td className="tnum px-3.5 py-2.5 text-right">{formatInt(total.inscriptions)}</td>
                  <td className="tnum px-3.5 py-2.5 text-right">{formatInt(total.nouv)}</td>
                  <td className="tnum px-3.5 py-2.5 text-right">{formatPct(total.pctNouv)}</td>
                  {showRecettes && <td className="tnum px-3.5 py-2.5 text-right">{formatEur(total.recettes)}</td>}
                  <td className="tnum px-3.5 py-2.5 text-right">{formatDec1(total.remplissage)}</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  );
}
