"use client";

import { useState } from "react";
import { useSnapshot } from "@/lib/useSnapshot";
import { useFilters } from "@/lib/store";
import { Panel } from "./Card";
import { PageTitle } from "./PageTitle";
import { YearBars, YearLine, IndexedLines } from "./Charts";
import { yearLabel } from "./Filters";
import { formatInt, formatEur, formatDec1 } from "@/lib/format";
import { useConfidential } from "@/lib/confidential";

type Fmt = "int" | "eur" | "dec1";
const fmtVal = (v: number, f: Fmt) => (f === "eur" ? formatEur(v) : f === "dec1" ? formatDec1(v) : formatInt(v));

// Couleur fixe par indicateur (identité stable — jamais recyclée selon le rang).
// Palette pensée DALTONISME (Okabe-Ito + Paul Tol). La « famille élèves »
// (inscriptions / élèves différents / nouveaux / réinscrits + cours), souvent
// comparée ensemble, reçoit les teintes les plus distinctes et CVD-sûres :
// bleu / orange / vert / rose / gris.
const IND_COLOR: Record<string, string> = {
  inscriptions: "#0072B2",      // bleu
  eleves_differents: "#E69F00", // orange
  nouveaux: "#009E73",          // vert
  reinscrits: "#CC79A7",        // rose
  cours: "#555555",             // gris
  heures: "#56B4E9",            // bleu ciel
  heures_eleves: "#117733",     // vert foncé
  recettes: "#E31A1C",          // rouge
  remplissage: "#AA4499",       // magenta
  panier_inscr: "#882255",      // bordeaux
  panier_pers: "#DDAA33",       // or
};
const indColor = (key: string) => IND_COLOR[key] ?? "#3B82F6";

function VarBadge({ v }: { v: number | null | undefined }) {
  if (v == null) return <span className="text-neutral-400">—</span>;
  const up = v > 0;
  const flat = v === 0;
  const cls = flat ? "text-neutral-500 bg-neutral-100" : up ? "text-success bg-success-soft" : "text-error bg-error-soft";
  return (
    <span className={`tnum inline-flex items-center gap-0.5 rounded-xs px-1.5 py-0.5 text-caption font-semibold ${cls}`}>
      {up ? "▲" : flat ? "" : "▼"} {formatDec1(Math.abs(v))} %
    </span>
  );
}

export function YoyView() {
  const { data } = useSnapshot();
  const { filterKeyed } = useConfidential();
  const yearMode = useFilters((s) => s.yearMode);
  const yoy = data.yoy ?? { years: [], rows: [] };

  // Indicateurs disponibles (confidentiel respecté) + leur format.
  const indicators = filterKeyed(data.indicators ?? []);
  const fmtOf = (key: string) => (indicators.find((i) => i.key === key)?.format ?? "int") as Fmt;
  const labelOf = (key: string) => indicators.find((i) => i.key === key)?.label ?? key;

  // Type de graphe : histogramme, courbes séparées (small multiples), ou
  // courbes superposées en base 100.
  const [chartType, setChartType] = useState<"bar" | "line" | "index100">("bar");
  // Multi-sélection d'indicateurs pour les graphiques (au moins un actif).
  const [selected, setSelected] = useState<string[]>(["inscriptions"]);
  const sel = selected.filter((k) => indicators.some((i) => i.key === k));
  const active = sel.length ? sel : ["inscriptions"];

  function toggle(key: string) {
    setSelected((cur) => {
      const has = cur.includes(key);
      const next = has ? cur.filter((k) => k !== key) : [...cur, key];
      return next.length ? next : cur; // garde au moins un indicateur
    });
  }

  const spanLabel =
    yoy.years.length > 0 ? `${yearLabel(yoy.years[0], yearMode)}–${yearLabel(yoy.years.at(-1) ?? yoy.years[0], yearMode)}` : "";

  return (
    <div className="space-y-5">
      <PageTitle eyebrow="Cours" title="Année vs année">
        Variations pluriannuelles du réseau, {spanLabel}. Sélectionnez un ou plusieurs indicateurs.
      </PageTitle>

      {/* Multi-sélection d'indicateurs — chaque indicateur a sa couleur. */}
      <div className="flex flex-wrap items-center gap-2.5">
        <span className="text-eyebrow font-semibold uppercase tracking-[0.06em] text-neutral-400">Indicateurs</span>
        <div className="inline-flex gap-1 rounded-pill bg-neutral-100 p-[3px]">
          <button
            onClick={() => setSelected(indicators.map((i) => i.key))}
            className="rounded-pill px-2.5 py-1 text-caption font-medium text-neutral-600 transition-colors hover:text-neutral-900"
          >
            Tout
          </button>
          <button
            onClick={() => setSelected(["inscriptions"])}
            className="rounded-pill px-2.5 py-1 text-caption font-medium text-neutral-600 transition-colors hover:text-neutral-900"
          >
            Réinitialiser
          </button>
        </div>
        <div className="flex flex-wrap gap-1.5">
          {indicators.map((i) => {
            const on = active.includes(i.key);
            return (
              <button
                key={i.key}
                onClick={() => toggle(i.key)}
                className={`inline-flex items-center gap-1.5 rounded-pill border px-3 py-1.5 text-body-sm font-medium transition-all ${
                  on ? "border-transparent bg-neutral-800 text-white shadow-sm" : "border-neutral-200 bg-surface text-neutral-600 hover:text-neutral-900"
                }`}
              >
                <span className="h-2.5 w-2.5 rounded-full ring-1 ring-white/40" style={{ background: indColor(i.key) }} />
                {i.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Bascule type de graphe : histogramme / courbes séparées / superposées base 100. */}
      <div className="flex items-center gap-2.5">
        <span className="text-eyebrow font-semibold uppercase tracking-[0.06em] text-neutral-400">Graphique</span>
        <div className="inline-flex flex-wrap gap-1 rounded-pill bg-neutral-100 p-[3px]">
          {([["bar", "Histogramme"], ["line", "Courbes"], ["index100", "Courbes base 100"]] as const).map(([v, lab]) => (
            <button
              key={v}
              onClick={() => setChartType(v)}
              className={`rounded-pill px-3 py-1.5 text-body-sm font-medium transition-all ${
                chartType === v ? "bg-accent-500 text-white shadow-sm" : "text-neutral-600 hover:text-neutral-900"
              }`}
            >
              {lab}
            </button>
          ))}
        </div>
      </div>

      {chartType === "index100" ? (
        /* Courbes superposées, base 100 à la 1re année : compare les ÉVOLUTIONS
           relatives des indicateurs sélectionnés sur un seul graphe. */
        <Panel
          title="Évolutions comparées · base 100"
          subtitle="Chaque indicateur ramené à 100 à la première année du périmètre"
          csv={{
            filename: "annee_vs_annee_base100",
            rows: [
              ["Année", ...active.map((k) => labelOf(k))],
              ...yoy.rows.map((r) => [yearLabel(r.year, yearMode), ...active.map((k) => r.values?.[k] ?? 0)]),
            ],
          }}
        >
          <IndexedLines
            years={yoy.rows.map((r) => yearLabel(r.year, yearMode))}
            series={active.map((key) => ({
              key,
              name: labelOf(key),
              color: indColor(key),
              values: yoy.rows.map((r) => r.values?.[key] ?? 0),
            }))}
          />
        </Panel>
      ) : (
        /* Small multiples : un graphe par indicateur sélectionné (échelle propre).
           Chaque graphe est un Panel → il hérite du menu ⋮ (copier l'image,
           export PNG, plein écran) et reçoit son propre export CSV. */
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {active.map((key) => {
            const seriesData = yoy.rows.map((r) => ({ year: yearLabel(r.year, yearMode), value: r.values?.[key] ?? 0 }));
            return (
              <Panel
                key={key}
                title={labelOf(key)}
                right={
                  <span
                    className="h-2.5 w-2.5 flex-shrink-0 rounded-full"
                    style={{ background: indColor(key) }}
                    aria-hidden
                  />
                }
                csv={{
                  filename: `annee_vs_annee_${key}`,
                  rows: [["Année", labelOf(key)], ...seriesData.map((d) => [d.year, d.value])],
                }}
              >
                {chartType === "bar" ? (
                  <YearBars data={seriesData} color={indColor(key)} unit={fmtOf(key)} />
                ) : (
                  <YearLine data={seriesData} color={indColor(key)} unit={fmtOf(key)} />
                )}
              </Panel>
            );
          })}
        </div>
      )}

      {/* Tableau comparatif : tous les indicateurs + deltas vs année précédente. */}
      <Panel title="Tableau comparatif" subtitle="Tous indicateurs · variation vs l'année précédente sélectionnée">
        <div className="thin-scroll overflow-x-auto rounded-md border border-neutral-200">
          <table className="w-full border-collapse text-body-sm">
            <thead>
              <tr>
                <th className="sticky left-0 z-10 border-b border-neutral-200 bg-neutral-50 px-3.5 py-2.5 text-left text-eyebrow font-semibold uppercase tracking-[0.06em] text-neutral-600">
                  Année
                </th>
                {indicators.map((i) => (
                  <th key={i.key} className="border-b border-neutral-200 bg-neutral-50 px-3.5 py-2.5 text-right text-eyebrow font-semibold uppercase tracking-[0.06em] text-neutral-600">
                    {i.label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {yoy.rows.map((r) => (
                <tr key={r.year} className="even:bg-neutral-50 hover:bg-accent-50">
                  <td className="sticky left-0 z-10 bg-surface px-3.5 py-2.5 font-semibold text-neutral-900">
                    {yearLabel(r.year, yearMode)}
                  </td>
                  {indicators.map((i) => (
                    <td key={i.key} className="px-3.5 py-2.5 text-right align-top">
                      <div className="tnum text-neutral-800">{fmtVal(r.values?.[i.key] ?? 0, i.format as Fmt)}</div>
                      <div className="mt-0.5"><VarBadge v={r.deltas?.[i.key]} /></div>
                    </td>
                  ))}
                </tr>
              ))}
              {yoy.rows.length === 0 && (
                <tr>
                  <td colSpan={indicators.length + 1} className="px-3.5 py-6 text-center text-neutral-500">
                    Aucune donnée sur ce périmètre.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  );
}
