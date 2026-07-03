"use client";

import { useSnapshot } from "@/lib/useSnapshot";
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

// Indicateurs ADDITIFS : la part d'une antenne dans le total réseau a un sens
// (%). Les ratios / comptes distincts (remplissage, paniers, élèves différents)
// ne sont pas additifs → pas de %.
const ADDITIVE = new Set(["inscriptions", "cours", "nouveaux", "reinscrits", "heures", "heures_eleves", "recettes"]);

export default function AntennesPage() {
  const { data } = useSnapshot();
  const { filterKeyed } = useConfidential();
  const byInd = data.byAntennaIndicator ?? {};
  const net = data.networkTotals ?? {};

  const indicators = filterKeyed(data.indicators ?? []);
  const visibleKeys = new Set(indicators.map((i) => i.key));
  const orderedInds = [
    ...ANT_ORDER.map((k) => indicators.find((i) => i.key === k)).filter(Boolean),
    ...indicators.filter((i) => !ANT_ORDER.includes(i.key)),
  ].filter((i) => i && visibleKeys.has(i.key)) as { key: string; label: string; format: "int" | "eur" | "dec1" }[];

  const kpiVal = (key: string) => data.kpis.find((k) => k.key === key)?.value;
  // IFI = TOTAL RÉSEAU (4 antennes), toujours — indépendant du filtre antenne.
  // Priorité : networkTotals (backend, non filtré antenne) ; repli : KPI global /
  // ratio / somme des antennes présentes.
  const ifiTotalFor = (key: string): number => {
    if (net[key] !== undefined) return net[key];
    const kv = kpiVal(key);
    if (kv !== undefined) return kv;
    if (key === "remplissage") {
      const inscr = (byInd.inscriptions ?? []).reduce((s, r) => s + r.value, 0);
      const cours = (byInd.cours ?? []).reduce((s, r) => s + r.value, 0);
      return cours ? inscr / cours : 0;
    }
    return (byInd[key] ?? []).reduce((s, r) => s + r.value, 0);
  };
  // Part d'une valeur dans le total réseau (seulement pour les indicateurs additifs).
  const pctOfNetwork = (key: string, value: number): number | null => {
    if (!ADDITIVE.has(key)) return null;
    const t = ifiTotalFor(key);
    return t > 0 ? (value / t) * 100 : null;
  };
  const fmtVal = (v: number, f: "int" | "eur" | "dec1") =>
    f === "eur" ? formatEur(v) : f === "dec1" ? formatDec1(v) : formatInt(v);
  const fmtPct = (p: number) => `${p >= 10 ? Math.round(p) : p.toFixed(1)} %`;

  const netInscr = ifiTotalFor("inscriptions");
  // Cartes : IFI (total réseau) en tête + chaque antenne avec sa part du réseau.
  const cardRows = [
    { code: "IFI", name: "IFI · Réseau", color: IFI_BLUE, inscriptions: netInscr, pct: null as number | null },
    ...data.byAntenna.map((a) => ({ code: a.code, name: a.name, color: a.color, inscriptions: a.inscriptions, pct: pctOfNetwork("inscriptions", a.inscriptions) })),
  ];

  // Lignes d'un indicateur pour les petits multiples : IFI (réseau) + antennes,
  // avec la part de chaque antenne (additifs).
  const indRows = (key: string) => [
    { name: "IFI", value: ifiTotalFor(key), color: IFI_BLUE, pct: null as number | null },
    ...(byInd[key] ?? []).map((r) => ({ name: r.code, value: r.value, color: r.color, pct: pctOfNetwork(key, r.value) })),
  ];
  const valueOf = (key: string, code: string) => (byInd[key] ?? []).find((r) => r.code === code)?.value ?? 0;

  return (
    <div className="space-y-5">
      <PageTitle eyebrow="Cours" title="Par antenne">
        Comparaison des antennes du réseau IFI, tous indicateurs. La ligne « IFI » = <b>total réseau (4 antennes)</b>, toujours affiché
        pour situer une antenne par rapport à l'ensemble (valeur + part du réseau).
      </PageTitle>
      <FilterSummary />

      {/* Cartes compactes : IFI (total réseau) en tête + part de chaque antenne. */}
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
              {a.pct != null && <div className="tnum text-caption font-medium text-accent-600">{fmtPct(a.pct)} du réseau</div>}
            </div>
          </motion.div>
        ))}
      </div>

      {/* Petits multiples : IFI (réseau) + antennes, avec la part de chaque antenne. */}
      <Panel title="Tous les indicateurs par antenne" subtitle="Petits multiples · IFI = total réseau">
        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 xl:grid-cols-3">
          {orderedInds.map((ind) => {
            const rows = indRows(ind.key);
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
                      {r.pct != null && <span className="tnum w-10 text-right text-caption text-accent-600">{fmtPct(r.pct)}</span>}
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

      <Panel title="Indicateurs détaillés" subtitle="IFI = total réseau ; part du réseau sous chaque valeur d'antenne">
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
              {data.byAntenna.map((a) => (
                <tr key={a.code} className="even:bg-neutral-50 hover:bg-accent-50">
                  <td className="px-3.5 py-2.5">
                    <span className="inline-flex items-center gap-2 font-medium text-neutral-800">
                      <span className="h-2 w-2 rounded-full" style={{ background: a.color }} />
                      {a.name}
                    </span>
                  </td>
                  {orderedInds.map((ind) => {
                    const v = valueOf(ind.key, a.code);
                    const p = pctOfNetwork(ind.key, v);
                    return (
                      <td key={ind.key} className="px-3.5 py-2.5 text-right">
                        <div className="tnum">{fmtVal(v, ind.format)}</div>
                        {p != null && <div className="tnum text-caption text-neutral-400">{fmtPct(p)}</div>}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  );
}
