"use client";

import { useSnapshot } from "@/lib/useSnapshot";
import { Panel } from "./Card";
import { PageTitle } from "./PageTitle";
import { HBar } from "./Charts";
import { formatInt, formatEur } from "@/lib/format";

function eurDec(n: number) {
  return `${n.toFixed(2).replace(".", ",")} €`;
}

export function ProfitabilityView() {
  const { data } = useSnapshot();
  const prof = data.profitability ?? { bySector: [], byAntenna: [] };

  const sectorChart = prof.bySector.map((r) => ({ name: r.label ?? "—", value: r.arpi }));
  const top3 = [...prof.bySector].sort((a, b) => b.arpi - a.arpi).slice(0, 3);

  return (
    <div className="space-y-5">
      <PageTitle eyebrow={`Cours · ${data.filters.year}`} title="Rentabilité">
        Recette moyenne par inscription (ARPI = recettes ÷ inscriptions), par secteur et par antenne.
      </PageTitle>

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-2">
        <Panel title="ARPI par secteur" subtitle="€ par inscription">
          <HBar data={sectorChart} height={Math.max(220, sectorChart.length * 30)} color="#16A34A" unit="eur" />
          <div className="mt-3 space-y-2">
            {top3.map((r, i) => (
              <div key={r.label} className="flex items-center gap-2 rounded-md border-l-[3px] border-success bg-success-soft px-3 py-2 text-body-sm">
                <span className="font-semibold text-success">#{i + 1}</span>
                <span className="font-medium text-neutral-800">{r.label}</span>
                <span className="tnum ml-auto font-semibold text-neutral-900">{eurDec(r.arpi)}</span>
                <span className="tnum text-caption text-neutral-500">{formatInt(r.inscriptions)} inscr.</span>
              </div>
            ))}
          </div>
        </Panel>

        <Panel title="ARPI par antenne" subtitle="€ par inscription">
          <div className="space-y-2">
            {prof.byAntenna.map((r) => {
              const max = Math.max(...prof.byAntenna.map((x) => x.arpi), 1);
              return (
                <div key={r.code} className="flex items-center gap-3">
                  <span className="w-10 text-body-sm font-semibold" style={{ color: r.color }}>{r.code}</span>
                  <div className="h-5 flex-1 overflow-hidden rounded-sm bg-neutral-100">
                    <div className="h-full rounded-sm" style={{ width: `${(r.arpi / max) * 100}%`, background: r.color }} />
                  </div>
                  <span className="tnum w-20 text-right text-body-sm font-semibold text-neutral-900">{eurDec(r.arpi)}</span>
                </div>
              );
            })}
          </div>
          <div className="mt-4 overflow-hidden rounded-md border border-neutral-200">
            <table className="w-full border-collapse text-body-sm">
              <thead>
                <tr>
                  {["Antenne", "Inscriptions", "Recettes", "ARPI"].map((h, i) => (
                    <th key={h} className={`border-b border-neutral-200 bg-neutral-50 px-3.5 py-2 text-eyebrow font-semibold uppercase text-neutral-600 ${i === 0 ? "text-left" : "text-right"}`}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {prof.byAntenna.map((r) => (
                  <tr key={r.code} className="even:bg-neutral-50">
                    <td className="px-3.5 py-2 font-medium text-neutral-800">{r.code}</td>
                    <td className="tnum px-3.5 py-2 text-right">{formatInt(r.inscriptions)}</td>
                    <td className="tnum px-3.5 py-2 text-right">{formatEur(r.recettes)}</td>
                    <td className="tnum px-3.5 py-2 text-right font-semibold">{eurDec(r.arpi)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
      </div>
    </div>
  );
}
