"use client";

import { useState } from "react";
import { useSnapshot } from "@/lib/useSnapshot";
import { Panel } from "./Card";
import { PageTitle } from "./PageTitle";
import { GroupedYearBar } from "./Charts";
import { formatInt, formatEur, formatDec1 } from "@/lib/format";
import { useConfidential } from "@/lib/confidential";

function VarBadge({ v }: { v: number | null }) {
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
  const { hidden } = useConfidential();
  const showRecettes = !hidden("recettes");
  const yoy = data.yoy ?? { years: [], rows: [] };
  const [metric, setMetric] = useState<"inscriptions" | "recettes">("inscriptions");
  const activeMetric = metric === "recettes" && !showRecettes ? "inscriptions" : metric;

  return (
    <div className="space-y-5">
      <PageTitle eyebrow="Cours" title="Année vs année">
        Variations pluriannuelles des grands indicateurs du réseau, {yoy.years[0]}–{yoy.years.at(-1)}.
      </PageTitle>

      <Panel title="Évolution annuelle" right={
        <div className="inline-flex gap-1 rounded-pill bg-neutral-100 p-[3px]">
          {(showRecettes ? (["inscriptions", "recettes"] as const) : (["inscriptions"] as const)).map((m) => (
            <button key={m} onClick={() => setMetric(m)}
              className={`rounded-pill px-3 py-1 text-body-sm font-medium capitalize transition-all ${activeMetric === m ? "bg-accent-500 text-white shadow-sm" : "text-neutral-600 hover:text-neutral-900"}`}>
              {m === "inscriptions" ? "Inscriptions" : "Recettes"}
            </button>
          ))}
        </div>
      }>
        <GroupedYearBar rows={yoy.rows} metric={activeMetric} />
      </Panel>

      <Panel title="Tableau comparatif" subtitle="Variation calculée vs l'année précédente">
        <div className="overflow-x-auto rounded-md border border-neutral-200">
          <table className="w-full min-w-[560px] border-collapse text-body-sm">
            <thead>
              <tr>
                {["Année", "Inscriptions", "Δ", "Cours", ...(showRecettes ? ["Recettes", "Δ"] : []), "Remplissage"].map((h, i) => (
                  <th key={`${h}-${i}`} className={`border-b border-neutral-200 bg-neutral-50 px-3.5 py-2.5 text-eyebrow font-semibold uppercase text-neutral-600 ${i === 0 ? "text-left" : "text-right"}`}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {yoy.rows.map((r) => (
                <tr key={r.year} className="even:bg-neutral-50 hover:bg-accent-50">
                  <td className="tnum px-3.5 py-2.5 font-semibold text-neutral-900">{r.year}</td>
                  <td className="tnum px-3.5 py-2.5 text-right">{formatInt(r.inscriptions)}</td>
                  <td className="px-3.5 py-2.5 text-right"><VarBadge v={r.inscriptionsVar} /></td>
                  <td className="tnum px-3.5 py-2.5 text-right">{formatInt(r.cours)}</td>
                  {showRecettes && <td className="tnum px-3.5 py-2.5 text-right">{formatEur(r.recettes)}</td>}
                  {showRecettes && <td className="px-3.5 py-2.5 text-right"><VarBadge v={r.recettesVar} /></td>}
                  <td className="tnum px-3.5 py-2.5 text-right">{r.cours ? formatDec1(r.inscriptions / r.cours) : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  );
}
