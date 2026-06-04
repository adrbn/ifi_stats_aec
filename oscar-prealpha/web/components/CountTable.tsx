"use client";

import { formatInt, formatPct } from "@/lib/format";

export function CountTable({
  label,
  rows,
  max,
}: {
  label: string;
  rows: { label: string; count: number; pct: number }[];
  max?: number;
}) {
  const data = max ? rows.slice(0, max) : rows;
  return (
    <div className="thin-scroll max-h-[420px] overflow-auto rounded-md border border-neutral-200">
      <table className="w-full border-collapse text-body-sm">
        <thead>
          <tr>
            {[label, "Nb", "%"].map((h, i) => (
              <th key={h} className={`sticky top-0 z-10 border-b border-neutral-200 bg-neutral-50 px-3.5 py-2 text-eyebrow font-semibold uppercase text-neutral-600 ${i === 0 ? "text-left" : "text-right"}`}>
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((r) => (
            <tr key={r.label} className="even:bg-neutral-50 hover:bg-accent-50">
              <td className="px-3.5 py-2 font-medium text-neutral-800">{r.label}</td>
              <td className="tnum px-3.5 py-2 text-right">{formatInt(r.count)}</td>
              <td className="tnum px-3.5 py-2 text-right text-neutral-500">{formatPct(r.pct)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
