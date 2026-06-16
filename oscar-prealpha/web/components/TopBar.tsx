"use client";

import { usePathname } from "next/navigation";
import { crumbFor } from "@/lib/nav";
import { useState, useEffect } from "react";
import { YearSegment, AntennaToggles, yearLabel } from "./Filters";
import { MultiSelect } from "./MultiSelect";
import { MobileNav } from "./MobileNav";
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
  const years = useFilters((s) => s.years);
  const yearMode = useFilters((s) => s.yearMode);
  const antennas = useFilters((s) => s.antennas);
  const [showDims, setShowDims] = useState(false);
  const [filtersOpen, setFiltersOpen] = useState(false); // mobile : filtres repliés par défaut
  // Masque le lien "Comparer" quand le dashboard est lui-même affiché dans le
  // comparateur (iframe) — sinon recliquer ouvre /compare en cascade.
  const [embedded, setEmbedded] = useState(false);
  useEffect(() => {
    setEmbedded(typeof window !== "undefined" && window.self !== window.top);
  }, []);
  const { data, isOffline, isLoading } = useSnapshot();
  const dimOptions = data.dimOptions ?? { secteurs: [], sousSecteurs: [], macros: [], categories: [] };
  const dimCount = Object.values(dims).reduce((n, a) => n + a.length, 0);
  // Résumé compact des filtres actifs (affiché dans l'en-tête repliable mobile).
  const yearSummary = years.length === 0
    ? (yearMode === "school" ? "Toutes années scol." : "Toutes années")
    : years.map((y) => yearLabel(y, yearMode)).join(", ");
  const antSummary = antennas.length === 4 ? "Toutes antennes" : antennas.join(", ");
  const filterSummary = `${yearSummary} · ${antSummary}${dimCount ? ` · ${dimCount} dim.` : ""}`;

  return (
    <header className="sticky top-0 z-40 border-b border-neutral-200 bg-surface/90 backdrop-blur-md backdrop-saturate-150">
      <div className="flex items-center justify-between gap-2 px-4 py-2.5 sm:gap-4 sm:px-6">
        <div className="flex min-w-0 items-center gap-1.5 text-body-sm text-neutral-500 sm:gap-2">
          <MobileNav />
          <span className="hidden font-medium text-neutral-700 sm:inline">{crumb?.group ?? "OSCAR"}</span>
          {crumb && (
            <>
              <IconChevronRight className="hidden h-3.5 w-3.5 text-neutral-300 sm:inline" />
              <span className="truncate font-semibold text-neutral-900">{crumb.label}</span>
            </>
          )}
          {isLoading ? (
            <span className="ml-1 flex-shrink-0 animate-pulse rounded-xs bg-amber-100 px-1.5 py-0.5 text-[10px] font-semibold uppercase text-amber-700 sm:ml-2">
              chargement…
            </span>
          ) : isOffline ? (
            <span className="ml-1 flex-shrink-0 rounded-xs bg-error-soft px-1.5 py-0.5 text-[10px] font-semibold uppercase text-error sm:ml-2">
              hors-ligne
            </span>
          ) : (
            <span className="ml-1 hidden flex-shrink-0 rounded-xs bg-success-soft px-1.5 py-0.5 text-[10px] font-semibold uppercase text-success sm:ml-2 sm:inline">
              données réelles
            </span>
          )}
        </div>
        <div className="flex flex-shrink-0 items-center gap-1.5 sm:gap-2">
          {!embedded && (
            <a
              href="/compare"
              className="hidden items-center gap-2 rounded-md border border-neutral-200 bg-surface px-3 py-1.5 text-body-sm font-medium text-neutral-600 transition-colors hover:text-neutral-900 lg:inline-flex"
              title="Basculer entre la v2 (Streamlit) et la v3 (nouvelle UI)"
            >
              Comparer v2 ⇄ v3
            </a>
          )}
          <button
            onClick={() => setAiOpen(true)}
            aria-label="Assistant OSCAR"
            className="inline-flex items-center gap-2 rounded-md border border-accent-100 bg-accent-50 px-2.5 py-1.5 text-body-sm font-semibold text-accent-700 transition-colors hover:bg-accent-100 sm:px-3"
          >
            <IconSparkles className="h-4 w-4 flex-shrink-0" />
            <span className="hidden sm:inline">Assistant OSCAR</span>
          </button>
          <button
            onClick={async () => {
              await fetch("/api/auth/logout", { method: "POST" });
              location.href = "/login";
            }}
            aria-label="Déconnexion"
            className="inline-flex items-center rounded-md border border-neutral-200 bg-surface px-2.5 py-1.5 text-body-sm font-medium text-neutral-600 transition-colors hover:text-neutral-900 sm:px-3"
          >
            <svg className="h-4 w-4 sm:hidden" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9" />
            </svg>
            <span className="hidden sm:inline">Déconnexion</span>
          </button>
        </div>
      </div>

      {/* Mobile/tablette : en-tête de filtres repliable (sinon il mange l'écran). */}
      <button
        onClick={() => setFiltersOpen((v) => !v)}
        aria-expanded={filtersOpen}
        className="flex w-full items-center justify-between gap-2 border-t border-neutral-100 px-4 py-2.5 text-left lg:hidden"
      >
        <span className="inline-flex min-w-0 items-center gap-2">
          <svg className="h-4 w-4 flex-shrink-0 text-neutral-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <path d="M4 6h16M7 12h10M11 18h2" />
          </svg>
          <span className="text-body-sm font-semibold text-neutral-800">Filtres</span>
          <span className="truncate text-caption text-neutral-400">{filterSummary}</span>
        </span>
        <IconChevronRight className={`h-4 w-4 flex-shrink-0 text-neutral-400 transition-transform ${filtersOpen ? "rotate-90" : ""}`} />
      </button>

      <div className={`${filtersOpen ? "block" : "hidden"} lg:block`}>
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2 border-t border-neutral-100 px-4 py-2.5 sm:gap-x-6 sm:px-6 lg:border-t">
        <FilterField label="Année">
          <YearSegment />
        </FilterField>
        <FilterField label="Antennes">
          <AntennaToggles />
        </FilterField>
        <button
          onClick={() => setShowDims((v) => !v)}
          className={`inline-flex items-center gap-1.5 rounded-pill border px-3 py-1.5 text-body-sm font-medium transition-colors sm:ml-auto ${
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
        <div className="flex flex-wrap items-center gap-2 border-t border-neutral-100 bg-neutral-50 px-4 py-2.5 sm:px-6">
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
      </div>
      {isOffline && (
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1 border-t border-error/30 bg-error-soft px-4 py-2 text-body-sm text-error sm:px-6">
          <span className="font-semibold">Serveur de données indisponible.</span>
          <span className="text-neutral-700">Le serveur se réveille peut-être — réessayez dans quelques secondes.</span>
          <button
            onClick={() => location.reload()}
            className="ml-auto rounded-sm border border-error/40 bg-surface px-2.5 py-1 text-caption font-semibold text-error transition-colors hover:bg-error hover:text-white"
          >
            Réessayer
          </button>
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
