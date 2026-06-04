"use client";

import { usePathname } from "next/navigation";
import { crumbFor } from "@/lib/nav";
import { useState } from "react";
import { YearSegment, AntennaToggles } from "./Filters";
import { MultiSelect } from "./MultiSelect";
import { useFilters, type DimKey } from "@/lib/store";
import { useSnapshot } from "@/lib/useSnapshot";
import { IconSparkles, IconChevronRight } from "./icons";

const DIM_LABELS: { key: DimKey; label: string }[] = [
  { key: "secteurs", label: "Secteur" },
  { key: "sousSecteurs", label: "Sous-secteur" },
  { key: "macros", label: "Macro-cat." },
  { key: "categories", label: "Catégorie" },
];

export function TopBar() {
  const pathname = usePathname();
  const crumb = crumbFor(pathname);
  const setAiOpen = useFilters((s) => s.setAiOpen);
  const dims = useFilters((s) => s.dims);
  const toggleDim = useFilters((s) => s.toggleDim);
  const clearDim = useFilters((s) => s.clearDim);
  const [showDims, setShowDims] = useState(false);
  const { data, isOffline } = useSnapshot();
  const dimOptions = data.dimOptions ?? { secteurs: [], sousSecteurs: [], macros: [], categories: [] };
  const dimCount = Object.values(dims).reduce((n, a) => n + a.length, 0);

  return (
    <header className="sticky top-0 z-40 border-b border-neutral-200 bg-surface/90 backdrop-blur-md backdrop-saturate-150">
      <div className="flex items-center justify-between gap-4 px-6 py-2.5">
        <div className="flex items-center gap-2 text-body-sm text-neutral-500">
          <span className="font-medium text-neutral-700">{crumb?.group ?? "OSCAR"}</span>
          {crumb && (
            <>
              <IconChevronRight className="h-3.5 w-3.5 text-neutral-300" />
              <span className="font-semibold text-neutral-900">{crumb.label}</span>
            </>
          )}
          {isOffline ? (
            <span className="ml-2 rounded-xs bg-error-soft px-1.5 py-0.5 text-[10px] font-semibold uppercase text-error">
              backend hors-ligne
            </span>
          ) : (
            <span className="ml-2 rounded-xs bg-success-soft px-1.5 py-0.5 text-[10px] font-semibold uppercase text-success">
              données réelles{data.meta.updated ? "" : ""}
            </span>
          )}
        </div>
        <button
          onClick={() => setAiOpen(true)}
          className="inline-flex items-center gap-2 rounded-md border border-accent-100 bg-accent-50 px-3 py-1.5 text-body-sm font-semibold text-accent-700 transition-colors hover:bg-accent-100"
        >
          <IconSparkles className="h-4 w-4" />
          Assistant OSCAR
        </button>
      </div>
      <div className="flex flex-wrap items-center gap-x-6 gap-y-2 border-t border-neutral-100 px-6 py-2.5">
        <FilterField label="Année">
          <YearSegment />
        </FilterField>
        <FilterField label="Antennes">
          <AntennaToggles />
        </FilterField>
        <button
          onClick={() => setShowDims((v) => !v)}
          className={`ml-auto inline-flex items-center gap-1.5 rounded-pill border px-3 py-1.5 text-body-sm font-medium transition-colors ${
            dimCount || showDims
              ? "border-accent-500 bg-accent-50 text-accent-700"
              : "border-neutral-200 bg-surface text-neutral-600 hover:text-neutral-900"
          }`}
        >
          Affiner par dimension{dimCount ? ` · ${dimCount}` : ""}
          <IconChevronRight className={`h-3 w-3 transition-transform ${showDims ? "rotate-90" : ""}`} />
        </button>
      </div>
      {showDims && (
        <div className="flex flex-wrap items-center gap-2 border-t border-neutral-100 bg-neutral-50 px-6 py-2.5">
          {DIM_LABELS.map((d) => (
            <MultiSelect
              key={d.key}
              label={d.label}
              options={dimOptions[d.key]}
              selected={dims[d.key]}
              onToggle={(v) => toggleDim(d.key, v)}
              onClear={() => clearDim(d.key)}
              disabled={isOffline || dimOptions[d.key].length === 0}
            />
          ))}
          {dimCount > 0 && (
            <button
              onClick={() => DIM_LABELS.forEach((d) => clearDim(d.key))}
              className="rounded-sm px-2 py-1 text-caption text-neutral-500 transition-colors hover:bg-error-soft hover:text-error"
            >
              Tout effacer
            </button>
          )}
          <span className="text-caption text-neutral-400">Les options s'affinent en cascade (Secteur → Sous-secteur → Macro → Catégorie).</span>
        </div>
      )}
      {isOffline && (
        <div className="flex items-center gap-2 border-t border-error/30 bg-error-soft px-6 py-2 text-body-sm text-error">
          <span className="font-semibold">Backend hors-ligne.</span>
          <span className="text-neutral-700">
            Aucune donnée affichée (pas de données fictives). Démarrez l'API :
            <code className="mx-1 rounded-xs bg-surface px-1.5 py-0.5 text-neutral-800">cd oscar-prealpha/web/api && ./run.sh</code>
          </span>
        </div>
      )}
    </header>
  );
}

function FilterField({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center gap-2.5">
      <span className="text-eyebrow font-semibold uppercase tracking-[0.06em] text-neutral-400">
        {label}
      </span>
      {children}
    </div>
  );
}
