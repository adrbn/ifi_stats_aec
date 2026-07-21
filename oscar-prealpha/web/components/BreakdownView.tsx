"use client";

import { useState } from "react";
import { useSnapshot } from "@/lib/useSnapshot";
import { Panel } from "./Card";
import { PageTitle } from "./PageTitle";
import { HBar } from "./Charts";
import { SectorIndicatorTable } from "./SectorIndicatorTable";
import { useConfidential, isSensitiveKey } from "@/lib/confidential";

const DIMS: { key: string; label: string }[] = [
  { key: "secteur", label: "Secteur" },
  { key: "sous_secteur", label: "Sous-secteur" },
  { key: "macro", label: "Macro-catégorie" },
  { key: "categorie", label: "Catégorie" },
  { key: "niveau", label: "Niveau" },
  { key: "format", label: "Présentiel / en ligne" },
  { key: "age", label: "Tranche d'âge" },
  { key: "periode", label: "Période" },
  { key: "matiere", label: "Matière" },
  { key: "ue", label: "UE planifiées" },
];

export function BreakdownView() {
  const { data } = useSnapshot();
  const { filterKeyed } = useConfidential();

  const [dim, setDim] = useState("secteur");
  // Sélecteur : TOUS les indicateurs (comme Synthèse / Par secteurs), confidentiel respecté.
  const indicators = filterKeyed(data.indicators ?? []);
  const [indSel, setInd] = useState("inscriptions");
  const ind = isSensitiveKey(indSel) && !indicators.some((i) => i.key === indSel) ? "inscriptions" : indSel;
  const indMeta = indicators.find((i) => i.key === ind);
  const unit = (indMeta?.format ?? "int") as "int" | "eur" | "dec1";

  const dimLabel = DIMS.find((d) => d.key === dim)?.label ?? "";
  const byDim = data.byDimensionIndicator?.[dim] ?? {};
  const labels = (byDim.inscriptions ?? []).map((r) => r.label);
  const chartData = (byDim[ind] ?? []).slice(0, 15).map((r) => ({ name: r.label, value: r.value }));

  const kpiCols = filterKeyed(data.kpis).map((k) => ({ key: k.key, label: k.label, format: k.format }));
  const kpiTotals = Object.fromEntries(data.kpis.map((k) => [k.key, k.value]));

  return (
    <div className="space-y-5">
      <PageTitle eyebrow={`Cours · ${data.filters.year}`} title="Répartition">
        Ventilez tous les indicateurs par dimension d'analyse — du secteur à la catégorie de cours.
      </PageTitle>

      <div className="flex flex-wrap items-center gap-x-6 gap-y-3">
        <Switch label="Dimension" options={DIMS.map((d) => ({ value: d.key, label: d.label }))} value={dim} onChange={setDim} />
        <Switch label="Indicateur" options={indicators.map((i) => ({ value: i.key, label: i.label }))} value={ind} onChange={setInd} />
      </div>

      <Panel title={`Top ${Math.min(15, chartData.length)} · ${dimLabel}`} subtitle={indMeta?.label}>
        {chartData.length ? (
          <HBar data={chartData} height={Math.max(220, chartData.length * 26)} unit={unit} />
        ) : (
          <p className="text-body-sm text-neutral-500">Aucune donnée pour cette dimension.</p>
        )}
      </Panel>

      <Panel title="Détail" subtitle={`${labels.length} lignes · ${dimLabel} · tous indicateurs`}>
        <div className="thin-scroll max-h-[520px] overflow-auto">
          <SectorIndicatorTable
            sectors={labels}
            byInd={byDim}
            columns={kpiCols}
            totals={kpiTotals}
            firstHeader={dimLabel}
            totalLabel="Total"
          />
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
