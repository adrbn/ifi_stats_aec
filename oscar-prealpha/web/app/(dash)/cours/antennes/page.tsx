"use client";

import { useSnapshot } from "@/lib/useSnapshot";
import { Panel } from "@/components/Card";
import { PageTitle } from "@/components/PageTitle";
import { AntennaBar } from "@/components/Charts";
import { FilterSummary } from "@/components/Filters";
import { formatInt, formatEur, formatDec1 } from "@/lib/format";
import { motion } from "framer-motion";

export default function AntennesPage() {
  const { data } = useSnapshot();
  const indicators = data.indicators ?? [];
  const byInd = data.byAntennaIndicator ?? {};

  return (
    <div className="space-y-5">
      <PageTitle eyebrow="Cours" title="Par antenne">
        Comparaison des antennes du réseau IFI, tous indicateurs, sur le périmètre filtré.
      </PageTitle>
      <FilterSummary />

      {/* compact per-antenna KPI cards */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {data.byAntenna.map((a, i) => (
          <motion.div
            key={a.code}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.24, delay: i * 0.04, ease: [0.16, 1, 0.3, 1] }}
            className="flex items-center gap-3 rounded-md border border-neutral-200 bg-surface p-3"
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
          {indicators.map((ind) => {
            const rows = (byInd[ind.key] ?? []).map((r) => ({ name: r.code, value: r.value, color: r.color }));
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
        <AntennaBar rows={data.byAntenna} />
      </Panel>

      <Panel title="Indicateurs détaillés" subtitle="Cours, recettes et remplissage par antenne">
        <div className="overflow-hidden rounded-md border border-neutral-200">
          <table className="w-full border-collapse text-body-sm">
            <thead>
              <tr>
                {["Antenne", "Inscriptions", "Cours", "Recettes", "Remplissage"].map((h, i) => (
                  <th key={h} className={`border-b border-neutral-200 bg-neutral-50 px-3.5 py-2.5 text-eyebrow font-semibold uppercase text-neutral-600 ${i === 0 ? "text-left" : "text-right"}`}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.byAntenna.map((a) => (
                <tr key={a.code} className="even:bg-neutral-50 hover:bg-accent-50">
                  <td className="px-3.5 py-2.5">
                    <span className="inline-flex items-center gap-2 font-medium text-neutral-800">
                      <span className="h-2 w-2 rounded-full" style={{ background: a.color }} />
                      {a.name}
                    </span>
                  </td>
                  <td className="tnum px-3.5 py-2.5 text-right">{formatInt(a.inscriptions)}</td>
                  <td className="tnum px-3.5 py-2.5 text-right">{formatInt(a.cours)}</td>
                  <td className="tnum px-3.5 py-2.5 text-right">{formatEur(a.recettes)}</td>
                  <td className="tnum px-3.5 py-2.5 text-right">{formatDec1(a.remplissage)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  );
}
