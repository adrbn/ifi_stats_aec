"use client";

import { useState } from "react";
import { useSnapshot } from "@/lib/useSnapshot";
import { Panel } from "./Card";
import { PageTitle } from "./PageTitle";
import { HBar } from "./Charts";
import { formatInt, formatEur, formatPct, formatDec1 } from "@/lib/format";
import type { BreakdownRow } from "@/lib/types";

const DIMS: { key: string; label: string }[] = [
  { key: "secteur", label: "Secteur" },
  { key: "sous_secteur", label: "Sous-secteur" },
  { key: "macro", label: "Macro-catégorie" },
  { key: "categorie", label: "Catégorie" },
];

const METRICS: { key: keyof BreakdownRow; label: string; unit: "int" | "eur" }[] = [
  { key: "inscriptions", label: "Inscriptions", unit: "int" },
  { key: "cours", label: "Cours", unit: "int" },
  { key: "recettes", label: "Recettes", unit: "eur" },
];

export function BreakdownView() {
  const { data } = useSnapshot();
  const [dim, setDim] = useState("secteur");
  const [metric, setMetric] = useState<keyof BreakdownRow>("inscriptions");

  const block = data.breakdowns?.[dim];
  const rows = block?.rows ?? [];
  const total = block?.total;

  const chartData = rows
    .slice(0, 15)
    .map((r) => ({ name: r.label, value: Number(r[metric]) }));

  return (
    <div className="space-y-5">
      <PageTitle eyebrow={`Cours · ${data.filters.year}`} title="Répartition">
        Ventilez les inscriptions, cours et recettes par dimension d'analyse — du secteur à la catégorie de cours.
      </PageTitle>

      <div className="flex flex-wrap items-center gap-x-6 gap-y-3">
        <Switch label="Dimension" options={DIMS.map((d) => ({ value: d.key, label: d.label }))} value={dim} onChange={setDim} />
        <Switch
          label="Indicateur"
          options={METRICS.map((m) => ({ value: m.key as string, label: m.label }))}
          value={metric as string}
          onChange={(v) => setMetric(v as keyof BreakdownRow)}
        />
      </div>

      <Panel title={`Top ${Math.min(15, rows.length)} · ${DIMS.find((d) => d.key === dim)?.label}`} subtitle={METRICS.find((m) => m.key === metric)?.label}>
        {chartData.length ? (
          <HBar data={chartData} height={Math.max(220, chartData.length * 26)} unit={metric === "recettes" ? "eur" : "int"} />
        ) : (
          <p className="text-body-sm text-neutral-500">Aucune donnée pour cette dimension.</p>
        )}
      </Panel>

      <Panel title="Détail" subtitle={`${rows.length} lignes · ${DIMS.find((d) => d.key === dim)?.label}`}>
        <div className="thin-scroll max-h-[520px] overflow-auto rounded-md border border-neutral-200">
          <table className="w-full border-collapse text-body-sm">
            <thead>
              <tr>
                {[DIMS.find((d) => d.key === dim)?.label ?? "", "Cours", "Inscriptions", "Nouv.", "% nouv.", "Recettes", "Rempl."].map((h, i) => (
                  <th key={h} className={`sticky top-0 z-10 border-b border-neutral-200 bg-neutral-50 px-3.5 py-2.5 text-eyebrow font-semibold uppercase text-neutral-600 ${i === 0 ? "text-left" : "text-right"}`}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.label} className="even:bg-neutral-50 hover:bg-accent-50">
                  <td className="px-3.5 py-2.5 font-medium text-neutral-800">{r.label}</td>
                  <td className="tnum px-3.5 py-2.5 text-right">{formatInt(r.cours)}</td>
                  <td className="tnum px-3.5 py-2.5 text-right">{formatInt(r.inscriptions)}</td>
                  <td className="tnum px-3.5 py-2.5 text-right">{formatInt(r.nouv)}</td>
                  <td className="tnum px-3.5 py-2.5 text-right">{formatPct(r.pctNouv)}</td>
                  <td className="tnum px-3.5 py-2.5 text-right">{formatEur(r.recettes)}</td>
                  <td className="tnum px-3.5 py-2.5 text-right">{formatDec1(r.remplissage)}</td>
                </tr>
              ))}
              {total && (
                <tr className="sticky bottom-0 border-t-2 border-neutral-300 bg-neutral-100 font-semibold text-neutral-900">
                  <td className="px-3.5 py-2.5">{total.label}</td>
                  <td className="tnum px-3.5 py-2.5 text-right">{formatInt(total.cours)}</td>
                  <td className="tnum px-3.5 py-2.5 text-right">{formatInt(total.inscriptions)}</td>
                  <td className="tnum px-3.5 py-2.5 text-right">{formatInt(total.nouv)}</td>
                  <td className="tnum px-3.5 py-2.5 text-right">{formatPct(total.pctNouv)}</td>
                  <td className="tnum px-3.5 py-2.5 text-right">{formatEur(total.recettes)}</td>
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

function Switch({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: { value: string; label: string }[];
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div className="flex items-center gap-2.5">
      <span className="text-eyebrow font-semibold uppercase tracking-[0.06em] text-neutral-400">{label}</span>
      <div className="inline-flex flex-wrap gap-1 rounded-pill bg-neutral-100 p-[3px]">
        {options.map((o) => (
          <button
            key={o.value}
            onClick={() => onChange(o.value)}
            className={`rounded-pill px-3 py-1.5 text-body-sm font-medium transition-all duration-150 ease-out-soft ${
              value === o.value ? "bg-accent-500 text-white shadow-sm" : "text-neutral-600 hover:bg-surface hover:text-neutral-900"
            }`}
          >
            {o.label}
          </button>
        ))}
      </div>
    </div>
  );
}
