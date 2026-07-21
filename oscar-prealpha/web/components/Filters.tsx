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

/** Libellé d'un intervalle selon le mode : civile « 2024 » / scolaire « 2024-25 »
 *  / trimestre « 2024-25 T1 » (clé = année scolaire × 10 + n° trimestre). */
export function yearLabel(y: number, mode: YearMode): string {
  if (mode === "trimester") {
    const sy = Math.floor(y / 10);
    const t = y % 10;
    return `${sy}-${String((sy + 1) % 100).padStart(2, "0")} T${t}`;
  }
  return mode === "school" ? `${y}-${String((y + 1) % 100).padStart(2, "0")}` : String(y);
}

/** Sélecteur d'INTERVALLE : année civile / année scolaire / trimestre. */
export function YearModeToggle() {
  const yearMode = useFilters((s) => s.yearMode);
  const setYearMode = useFilters((s) => s.setYearMode);
  const opts: { value: YearMode; label: string }[] = [
    { value: "civil", label: "Année civile" },
    { value: "school", label: "Année scolaire" },
    { value: "trimester", label: "Trimestre" },
  ];
  return (
    <div className="inline-flex gap-1 rounded-pill bg-neutral-100 p-[3px]" title="Intervalle : année civile (jan→déc), scolaire (sep→août), ou trimestre (T1 sep-déc · T2 janv-avril · T3 mai-août)">
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

/** Pastille de sélection réutilisable (« Tout » + valeurs). */
function Pills({
  allActive,
  onAll,
  items,
}: {
  allActive: boolean;
  onAll: () => void;
  items: { key: string | number; label: string; active: boolean; onClick: () => void }[];
}) {
  return (
    <div className="inline-flex flex-wrap gap-1 rounded-pill bg-neutral-100 p-[3px]">
      <button
        onClick={onAll}
        className={`rounded-pill px-3 py-1.5 text-body-sm font-medium italic transition-all duration-150 ease-out-soft ${
          allActive ? "bg-accent-500 text-white shadow-sm" : "text-neutral-500 hover:bg-surface hover:text-neutral-900"
        }`}
      >
        Tout
      </button>
      {items.map((it) => (
        <button
          key={it.key}
          onClick={it.onClick}
          className={`tnum rounded-pill px-3 py-1.5 text-body-sm font-medium transition-all duration-150 ease-out-soft ${
            it.active ? "bg-accent-500 text-white shadow-sm" : "text-neutral-600 hover:bg-surface hover:text-neutral-900"
          }`}
        >
          {it.label}
        </button>
      ))}
    </div>
  );
}

const QUARTER_LABEL: Record<number, string> = {
  1: "T1 · sept-déc",
  2: "T2 · janv-avr",
  3: "T3 · mai-août",
};

export function YearSegment() {
  const years = useFilters((s) => s.years);
  const yearMode = useFilters((s) => s.yearMode);
  const toggleYear = useFilters((s) => s.toggleYear);
  const setAllYears = useFilters((s) => s.setAllYears);
  const triYears = useFilters((s) => s.triYears);
  const triQuarters = useFilters((s) => s.triQuarters);
  const toggleTriYear = useFilters((s) => s.toggleTriYear);
  const setAllTriYears = useFilters((s) => s.setAllTriYears);
  const toggleTriQuarter = useFilters((s) => s.toggleTriQuarter);
  const setAllTriQuarters = useFilters((s) => s.setAllTriQuarters);
  const { data } = useSnapshot();

  // Mode TRIMESTRE : sélecteur à 2 axes (années scolaires × T1/T2/T3) — bien
  // plus lisible qu'une longue liste de « 2025-26 T1 ».
  if (yearMode === "trimester") {
    const keys = data.meta.years.length ? data.meta.years : [];
    const schoolYears = Array.from(new Set(keys.map((k) => Math.floor(k / 10)))).sort((a, b) => a - b);
    return (
      <div className="inline-flex flex-col gap-2">
        <YearModeToggle />
        <div className="inline-flex flex-wrap items-center gap-2">
          <span className="text-eyebrow font-semibold uppercase tracking-[0.06em] text-neutral-400">Année</span>
          <Pills
            allActive={triYears.length === 0}
            onAll={setAllTriYears}
            items={schoolYears.map((sy) => ({
              key: sy,
              label: `${sy}-${String((sy + 1) % 100).padStart(2, "0")}`,
              active: triYears.includes(sy),
              onClick: () => toggleTriYear(sy),
            }))}
          />
          <span className="text-eyebrow font-semibold uppercase tracking-[0.06em] text-neutral-400">Trimestre</span>
          <Pills
            allActive={triQuarters.length === 0}
            onAll={setAllTriQuarters}
            items={[1, 2, 3].map((q) => ({
              key: q,
              label: QUARTER_LABEL[q],
              active: triQuarters.includes(q),
              onClick: () => toggleTriQuarter(q),
            }))}
          />
        </div>
      </div>
    );
  }

  const available = data.meta.years.length ? data.meta.years : [2023, 2024, 2025];
  return (
    <div className="inline-flex flex-wrap items-center gap-2">
      <YearModeToggle />
      <Pills
        allActive={years.length === 0}
        onAll={setAllYears}
        items={available.map((y) => ({
          key: y,
          label: yearLabel(y, yearMode),
          active: years.includes(y),
          onClick: () => toggleYear(y),
        }))}
      />
    </div>
  );
}

export function AntennaToggles() {
  const antennas = useFilters((s) => s.antennas);
  const toggleAntenna = useFilters((s) => s.toggleAntenna);
  const setAntennas = useFilters((s) => s.setAntennas);
  const allActive = antennas.length === ANTENNAS.length;
  return (
    <div className="inline-flex flex-wrap gap-1.5">
      {/* Total IFI (réseau) — sélectionne toutes les antennes. */}
      <button
        onClick={() => setAntennas(ANTENNAS.map((a) => a.code))}
        title="Total IFI : tout le réseau (toutes antennes)"
        style={allActive ? { background: "#3B82F6", borderColor: "#3B82F6" } : { borderColor: "var(--neutral-200)" }}
        className={`inline-flex items-center gap-1.5 rounded-pill border px-3 py-1.5 text-body-sm font-semibold transition-all duration-150 ease-out-soft ${
          allActive ? "text-white" : "bg-surface text-neutral-700 hover:text-neutral-900"
        }`}
      >
        <span className="h-2 w-2 rounded-full" style={{ background: allActive ? "rgba(255,255,255,0.9)" : "#3B82F6" }} />
        IFI
      </button>
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
  const triYears = useFilters((s) => s.triYears);
  const triQuarters = useFilters((s) => s.triQuarters);
  const antennas = useFilters((s) => s.antennas);
  const reset = useFilters((s) => s.reset);
  let yearsLabel: string;
  if (yearMode === "trimester") {
    const yPart = triYears.length ? triYears.map((sy) => `${sy}-${String((sy + 1) % 100).padStart(2, "0")}`).join(", ") : "toutes années";
    const qPart = triQuarters.length ? triQuarters.map((q) => `T${q}`).join(", ") : "tous trimestres";
    yearsLabel = triYears.length || triQuarters.length ? `${yPart} · ${qPart}` : "Tous trimestres";
  } else {
    const allLabel = yearMode === "school" ? "Toutes années scolaires" : "Toutes années";
    yearsLabel = years.length === 0 ? allLabel : years.map((y) => yearLabel(y, yearMode)).join(", ");
  }
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
