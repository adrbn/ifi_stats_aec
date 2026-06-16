"use client";

import type { SectorRow } from "@/lib/types";
import { formatInt, formatEur, formatPct, formatDec1 } from "@/lib/format";

function Cells({ r }: { r: SectorRow }) {
  return (
    <>
      <td className="tnum px-3.5 py-2.5 text-right">{formatInt(r.cours)}</td>
      <td className="tnum px-3.5 py-2.5 text-right">{formatInt(r.inscriptions)}</td>
      <td className="tnum px-3.5 py-2.5 text-right">{formatInt(r.nouv)}</td>
      <td className="tnum px-3.5 py-2.5 text-right">{formatPct(r.pctNouv)}</td>
      <td className="tnum px-3.5 py-2.5 text-right">{formatEur(r.recettes)}</td>
      <td className="tnum px-3.5 py-2.5 text-right">{formatDec1(r.remplissage)}</td>
    </>
  );
}

export function SectorTable({
  rows,
  total,
}: {
  rows: SectorRow[];
  total: SectorRow;
}) {
  const headers = ["Secteur", "Cours", "Inscriptions", "Nouv. inscrits", "% nouv.", "Recettes", "Remplissage"];
  return (
    <div className="overflow-x-auto rounded-md border border-neutral-200">
      <table className="w-full min-w-[640px] border-collapse text-body-sm">
        <thead>
          <tr>
            {headers.map((h, i) => (
              <th
                key={h}
                className={`sticky top-0 border-b border-neutral-200 bg-neutral-50 px-3.5 py-2.5 text-eyebrow font-semibold uppercase tracking-[0.06em] text-neutral-600 ${
                  i === 0 ? "text-left" : "text-right"
                }`}
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.secteur} className="even:bg-neutral-50 hover:bg-accent-50">
              <td className="px-3.5 py-2.5 font-medium text-neutral-800">{r.secteur}</td>
              <Cells r={r} />
            </tr>
          ))}
          <tr className="border-t-2 border-neutral-300 bg-neutral-100 font-semibold text-neutral-900">
            <td className="px-3.5 py-2.5">{total.secteur}</td>
            <Cells r={total} />
          </tr>
        </tbody>
      </table>
    </div>
  );
}
