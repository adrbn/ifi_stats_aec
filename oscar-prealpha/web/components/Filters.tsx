"use client";

import { useFilters } from "@/lib/store";
import type { YearMode } from "@/lib/store";
import { useSnapshot } from "@/lib/useSnapshot";
import type { AntennaCode } from "@/lib/types";

const ANTENNAS: { code: AntennaCode; label: string; color: string }[] = [
  { code: "IFM", label: "IFM", color: "#FF8C00" },
  { code: "IFF", label: "IFF", color: "#8B5CF6" },
  { code: "IFN", label: "IFN", color: "#22C55E" },
  { code: "IFP", label: "IFP", color: "#EF4444" },
];

/** Libellé d'une année selon le mode : civile « 2024 » / scolaire « 2024-25 ». */
export function yearLabel(y: number, mode: YearMode): string {
  return mode === "school" ? `${y}-${String((y + 1) % 100).padStart(2, "0")}` : String(y);
}

/** Bascule année civile ⇄ scolaire. */
export function YearModeToggle() {
  const yearMode = useFilters((s) => s.yearMode);
  const setYearMode = useFilters((s) => s.setYearMode);
  const opts: { value: YearMode; label: string }[] = [
    { value: "civil", label: "Civile" },
    { value: "school", label: "Scolaire" },
  ];
  return (
    <div className="inline-flex gap-1 rounded-pill bg-neutral-100 p-[3px]" title="Année civile (jan→déc) ou scolaire (sep→août)">
      {opts.map((o) => {
        const active = yearMode === o.value;
        return (
          <button
            key={o.value}
            onClick={() => setYearMode(o.value)}
            className={`rounded-pill px-3 py-1.5 text-body-sm font-medium transition-all duration-150 ease-out-soft ${
              active ? "bg-accent-500 text-white shadow-sm" : "text-neutral-500 hover:bg-surface hover:text-neutral-900"
            }`}
          >
            {o.label}
          </button>
        );
      })}
    </div>
  );
}

export function YearSegment() {
  const years = useFilters((s) => s.years);
  const yearMode = useFilters((s) => s.yearMode);
  const toggleYear = useFilters((s) => s.toggleYear);
  const setAllYears = useFilters((s) => s.setAllYears);
  const { data } = useSnapshot();
  const available = data.meta.years.length ? data.meta.years : [2023, 2024, 2025];
  const allActive = years.length === 0;

  return (
    <div className="inline-flex flex-wrap items-center gap-2">
      <YearModeToggle />
      <div className="inline-flex flex-wrap gap-1 rounded-pill bg-neutral-100 p-[3px]">
        <button
          onClick={setAllYears}
          className={`rounded-pill px-3 py-1.5 text-body-sm font-medium italic transition-all duration-150 ease-out-soft ${
            allActive ? "bg-accent-500 text-white shadow-sm" : "text-neutral-500 hover:bg-surface hover:text-neutral-900"
          }`}
        >
          Toutes
        </button>
        {available.map((y) => {
          const active = years.includes(y);
          return (
            <button
              key={y}
              onClick={() => toggleYear(y)}
              className={`tnum rounded-pill px-3 py-1.5 text-body-sm font-medium transition-all duration-150 ease-out-soft ${
                active ? "bg-accent-500 text-white shadow-sm" : "text-neutral-600 hover:bg-surface hover:text-neutral-900"
              }`}
            >
              {yearLabel(y, yearMode)}
            </button>
          );
        })}
      </div>
    </div>
  );
}

export function AntennaToggles() {
  const antennas = useFilters((s) => s.antennas);
  const toggleAntenna = useFilters((s) => s.toggleAntenna);
  return (
    <div className="inline-flex flex-wrap gap-1.5">
      {ANTENNAS.map((a) => {
        const active = antennas.includes(a.code);
        return (
          <button
            key={a.code}
            onClick={() => toggleAntenna(a.code)}
            style={active ? { background: a.color, borderColor: a.color } : { borderColor: "var(--neutral-200)" }}
            className={`inline-flex items-center gap-1.5 rounded-pill border px-3 py-1.5 text-body-sm font-medium transition-all duration-150 ease-out-soft ${
              active ? "text-white" : "bg-surface text-neutral-700 hover:text-neutral-900"
            }`}
          >
            <span className="h-2 w-2 rounded-full" style={{ background: active ? "rgba(255,255,255,0.9)" : a.color }} />
            {a.label}
          </button>
        );
      })}
    </div>
  );
}

export function FilterSummary() {
  const years = useFilters((s) => s.years);
  const yearMode = useFilters((s) => s.yearMode);
  const antennas = useFilters((s) => s.antennas);
  const reset = useFilters((s) => s.reset);
  const yearsLabel =
    years.length === 0
      ? yearMode === "school" ? "Toutes années scolaires" : "Toutes années"
      : years.map((y) => yearLabel(y, yearMode)).join(", ");
  const antLabel = antennas.length === 4 ? "Toutes antennes" : antennas.join(", ");
  return (
    <div className="flex flex-wrap items-center gap-1.5 rounded-md border border-neutral-200 bg-surface px-3 py-2">
      <span className="mr-1 text-eyebrow font-semibold uppercase text-neutral-500">Filtres actifs</span>
      <Chip label={yearsLabel} />
      <Chip label={antLabel} />
      <button
        onClick={reset}
        className="ml-auto rounded-sm px-2 py-1 text-caption text-neutral-500 transition-colors hover:bg-error-soft hover:text-error"
      >
        Réinitialiser
      </button>
    </div>
  );
}

function Chip({ label }: { label: string }) {
  return (
    <span className="tnum inline-flex items-center gap-1.5 rounded-pill bg-accent-50 px-2.5 py-[3px] text-caption font-medium text-accent-700">
      {label}
    </span>
  );
}
