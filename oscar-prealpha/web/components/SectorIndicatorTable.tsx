"use client";

import { formatInt, formatEur, formatDec1 } from "@/lib/format";

type Fmt = "int" | "eur" | "dec1";
const fmt = (v: number, f: Fmt) => (f === "eur" ? formatEur(v) : f === "dec1" ? formatDec1(v) : formatInt(v));

interface Col {
  key: string;
  label: string;
  format: Fmt;
}

/**
 * Tableau secteur × indicateurs. Les colonnes (et leur ordre) sont fournies par
 * l'appelant — typiquement la liste des KPI en haut de page, pour que le détail
 * par secteur affiche exactement les mêmes indicateurs dans le même ordre. La
 * ligne TOTAL reprend les valeurs globales (les KPI), donc elle est juste même
 * pour les indicateurs non additifs (élèves différents, remplissage).
 */
export function SectorIndicatorTable({
  sectors,
  byInd,
  columns,
  totals,
}: {
  sectors: string[];
  byInd: Record<string, { label: string; value: number }[]>;
  columns: Col[];
  totals: Record<string, number>;
}) {
  const valueOf = (sector: string, key: string) =>
    byInd[key]?.find((x) => x.label === sector)?.value ?? 0;

  return (
    <div className="overflow-x-auto rounded-md border border-neutral-200">
      <table className="w-full min-w-[640px] border-collapse text-body-sm">
        <thead>
          <tr>
            <th className="sticky top-0 border-b border-neutral-200 bg-neutral-50 px-3.5 py-2.5 text-left text-eyebrow font-semibold uppercase tracking-[0.06em] text-neutral-600">
              Secteur
            </th>
            {columns.map((c) => (
              <th
                key={c.key}
                className="sticky top-0 border-b border-neutral-200 bg-neutral-50 px-3.5 py-2.5 text-right text-eyebrow font-semibold uppercase tracking-[0.06em] text-neutral-600"
              >
                {c.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sectors.map((s) => (
            <tr key={s} className="even:bg-neutral-50 hover:bg-accent-50">
              <td className="px-3.5 py-2.5 font-medium text-neutral-800">{s}</td>
              {columns.map((c) => (
                <td key={c.key} className="tnum px-3.5 py-2.5 text-right">
                  {fmt(valueOf(s, c.key), c.format)}
                </td>
              ))}
            </tr>
          ))}
          <tr className="border-t-2 border-neutral-300 bg-neutral-100 font-semibold text-neutral-900">
            <td className="px-3.5 py-2.5">TOTAL IFI</td>
            {columns.map((c) => (
              <td key={c.key} className="tnum px-3.5 py-2.5 text-right">
                {fmt(totals[c.key] ?? 0, c.format)}
              </td>
            ))}
          </tr>
        </tbody>
      </table>
    </div>
  );
}
