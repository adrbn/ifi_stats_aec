"use client";

import { useSnapshot } from "@/lib/useSnapshot";
import { useFilters } from "@/lib/store";
import { useConfidential } from "@/lib/confidential";
import { Panel } from "@/components/Card";
import { PageTitle } from "@/components/PageTitle";
import { AntennaBar } from "@/components/Charts";
import { FilterSummary } from "@/components/Filters";
import { formatInt, formatEur, formatDec1 } from "@/lib/format";
import { motion } from "framer-motion";

const IFI_BLUE = "#3B82F6";

// Ordre demandé des indicateurs « par antenne ».
const ANT_ORDER = ["inscriptions", "cours", "heures", "heures_eleves", "eleves_differents", "reinscrits", "nouveaux", "remplissage", "recettes"];

export default function AntennesPage() {
  const { data } = useSnapshot();
  const { filterKeyed } = useConfidential();
  const antennas = useFilters((s) => s.antennas);
  // IFI = total réseau : n'a de sens QUE si les 4 antennes sont dans le périmètre.
  // Sinon la « somme des antennes filtrées » = l'antenne seule (doublon trompeur)
  // → on masque la ligne/carte IFI (bug corrigé).
  const showIFI = antennas.length === 4;
  const indicators = filterKeyed(data.indicators ?? []);
  const byInd = data.byAntennaIndicator ?? {};
  // Indicateurs réordonnés selon ANT_ORDER (puis tout reliquat éventuel), en
  // retirant les indicateurs masqués par le mode confidentiel.
  const visibleKeys = new Set(indicators.map((i) => i.key));
  const orderedInds = [
    ...ANT_ORDER.map((k) => indicators.find((i) => i.key === k)).filter(Boolean),
    ...indicators.filter((i) => !ANT_ORDER.includes(i.key)),
  ].filter((i) => i && visibleKeys.has(i.key)) as { key: string; label: string; format: "int" | "eur" | "dec1" }[];

  const ifiInscr = data.byAntenna.reduce((s, a) => s + (a.inscriptions ?? 0), 0);
  const ifiCours = data.byAntenna.reduce((s, a) => s + (a.cours ?? 0), 0);
  const ifiRempl = ifiCours ? ifiInscr / ifiCours : 0;
  const cardRows = [
    ...(showIFI ? [{ code: "IFI", name: "IFI · Réseau", color: IFI_BLUE, inscriptions: ifiInscr }] : []),
    ...data.byAntenna,
  ];
  // Total IFI d'un indicateur : valeur KPI globale si dispo (juste pour les
  // comptes distincts/ratios), sinon somme des antennes (indicateurs additifs).
  const kpiVal = (key: string) => data.kpis.find((k) => k.key === key)?.value;
  const ifiTotalFor = (key: string): number => {
    const kv = kpiVal(key);
    if (kv !== undefined) return kv;
    if (key === "remplissage") return ifiRempl;
    return (byInd[key] ?? []).reduce((s, r) => s + r.value, 0);
  };
  const fmtVal = (v: number, f: "int" | "eur" | "dec1") =>
    f === "eur" ? formatEur(v) : f === "dec1" ? formatDec1(v) : formatInt(v);
  const indRowsWithIFI = (key: string) => {
    const base = (byInd[key] ?? []).map((r) => ({ name: r.code, value: r.value, color: r.color }));
    return showIFI ? [{ name: "IFI", value: ifiTotalFor(key), color: IFI_BLUE }, ...base] : base;
  };
  const valueOf = (key: string, code: string) => (byInd[key] ?? []).find((r) => r.code === code)?.value ?? 0;

  return (
    <div className="space-y-5">
      <PageTitle eyebrow="Cours" title="Par antenne">
        Comparaison des antennes du réseau IFI, tous indicateurs, sur le périmètre filtré.
        {showIFI ? " La ligne « IFI » = total réseau." : " (Sélectionnez « IFI » / les 4 antennes pour afficher le total réseau.)"}
      </PageTitle>
      <FilterSummary />

      {/* compact per-antenna KPI cards (IFI total en tête, en bleu) */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
        {cardRows.map((a, i) => (
          <motion.div
            key={a.code}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.24, delay: i * 0.04, ease: [0.16, 1, 0.3, 1] }}
            className={`flex items-center gap-3 rounded-md border p-3 ${a.code === "IFI" ? "border-accent-300 bg-accent-50/40" : "border-neutral-200 bg-surface"}`}
          >
            <span className="h-2 w-2 flex-shrink-0 rounded-full" style={{ background: a.color }} />
            <div className="min-w-0">
              <div className="truncate text-eyebrow font-semibold uppercase text-neutral-500">{a.name}</div>
              <div className="tnum text-h2 font-bold text-neutral-900">{formatInt(a.inscriptions)}</div>
            </div>
          </motion.div>
        ))}
      </div>

      {/* small multiples: one mini bar per indicator across antennas */}
      <Panel title="Tous les indicateurs par antenne" subtitle="Petits multiples">
        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 xl:grid-cols-3">
          {orderedInds.map((ind) => {
            const rows = indRowsWithIFI(ind.key);
            const max = Math.max(...rows.map((r) => r.value), 1);
            return (
              <div key={ind.key} className="rounded-md border border-neutral-200 p-3">
                <div className="mb-2 text-eyebrow font-semibold uppercase text-neutral-500">{ind.label}</div>
                <div className="space-y-1.5">
                  {rows.map((r) => (
                    <div key={r.name} className="flex items-center gap-2">
                      <span className="w-9 text-caption font-semibold" style={{ color: r.color }}>{r.name}</span>
                      <div className="h-4 flex-1 overflow-hidden rounded-sm bg-neutral-100">
                        <div className="h-full rounded-sm" style={{ width: `${(r.value / max) * 100}%`, background: r.color }} />
                      </div>
                      <span className="tnum w-20 text-right text-caption text-neutral-700">
                        {ind.format === "eur" ? formatEur(r.value) : ind.format === "dec1" ? formatDec1(r.value) : formatInt(r.value)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </Panel>

      <Panel title="Inscriptions par antenne">
        <AntennaBar rows={data.byAntenna.map((a) => ({ code: a.code, color: a.color, value: a.inscriptions }))} label="Inscriptions" />
      </Panel>

      <Panel title="Indicateurs détaillés" subtitle="Tous les indicateurs par antenne">
        <div className="overflow-x-auto rounded-md border border-neutral-200">
          <table className="w-full min-w-[720px] border-collapse text-body-sm">
            <thead>
              <tr>
                <th className="border-b border-neutral-200 bg-neutral-50 px-3.5 py-2.5 text-left text-eyebrow font-semibold uppercase text-neutral-600">Antenne</th>
                {orderedInds.map((ind) => (
                  <th key={ind.key} className="border-b border-neutral-200 bg-neutral-50 px-3.5 py-2.5 text-right text-eyebrow font-semibold uppercase text-neutral-600">
                    {ind.label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {showIFI && (
                <tr className="border-b-2 border-accent-200 bg-accent-50/40 font-semibold text-neutral-900">
                  <td className="px-3.5 py-2.5">
                    <span className="inline-flex items-center gap-2">
                      <span className="h-2 w-2 rounded-full" style={{ background: IFI_BLUE }} />
                      IFI · Réseau
                    </span>
                  </td>
                  {orderedInds.map((ind) => (
                    <td key={ind.key} className="tnum px-3.5 py-2.5 text-right">{fmtVal(ifiTotalFor(ind.key), ind.format)}</td>
                  ))}
                </tr>
              )}
              {data.byAntenna.map((a) => (
                <tr key={a.code} className="even:bg-neutral-50 hover:bg-accent-50">
                  <td className="px-3.5 py-2.5">
                    <span className="inline-flex items-center gap-2 font-medium text-neutral-800">
                      <span className="h-2 w-2 rounded-full" style={{ background: a.color }} />
                      {a.name}
                    </span>
                  </td>
                  {orderedInds.map((ind) => (
                    <td key={ind.key} className="tnum px-3.5 py-2.5 text-right">{fmtVal(valueOf(ind.key, a.code), ind.format)}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  );
}
