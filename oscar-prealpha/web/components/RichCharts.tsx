"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  Treemap,
  XAxis,
  YAxis,
} from "recharts";
import { formatInt, formatEur, formatDec1 } from "@/lib/format";

const tip = {
  background: "#fff",
  border: "1px solid var(--neutral-200)",
  borderRadius: 6,
  boxShadow: "0 1px 3px rgba(15,23,42,0.06)",
  fontSize: 12,
  fontFamily: "var(--font-sans)",
  color: "var(--neutral-900)",
};

const SECTOR_PALETTE = [
  "#3B82F6", "#F97316", "#10B981", "#A855F7", "#EAB308",
  "#06B6D4", "#EC4899", "#14B8A6", "#F59E0B", "#6366F1",
  "#84CC16", "#EF4444", "#8B5CF6", "#0EA5E9", "#D946EF", "#22D3EE",
];

function fmt(v: number, unit: "int" | "eur" | "dec1") {
  return unit === "eur" ? formatEur(v) : unit === "dec1" ? formatDec1(v) : formatInt(v);
}

/** Horizontal bar + donut side-by-side for one indicator over categories. */
export function IndicatorBarPie({
  data,
  unit = "int",
  colors,
  height = 300,
}: {
  data: { label: string; value: number }[];
  unit?: "int" | "eur" | "dec1";
  colors?: string[];
  height?: number;
}) {
  const pal = colors ?? SECTOR_PALETTE;
  const rows = [...data].sort((a, b) => b.value - a.value);
  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
      <ResponsiveContainer width="100%" height={height}>
        <BarChart layout="vertical" data={rows} margin={{ top: 4, right: 28, bottom: 4, left: 8 }}>
          <CartesianGrid horizontal={false} stroke="var(--neutral-100)" />
          <XAxis type="number" tickLine={false} axisLine={false} tickFormatter={(v) => fmt(v, unit)} />
          <YAxis type="category" dataKey="label" tickLine={false} axisLine={false} width={140} tick={{ fontSize: 11 }} />
          <Tooltip cursor={{ fill: "var(--accent-50)" }} contentStyle={tip} formatter={(v: number) => fmt(v, unit)} />
          <Bar dataKey="value" radius={[0, 3, 3, 0]} maxBarSize={26}>
            {rows.map((r, i) => (
              <Cell key={r.label} fill={pal[i % pal.length]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      <ResponsiveContainer width="100%" height={height}>
        <PieChart>
          <Pie data={rows} dataKey="value" nameKey="label" innerRadius="52%" outerRadius="80%" paddingAngle={1} stroke="#fff" strokeWidth={1}>
            {rows.map((r, i) => (
              <Cell key={r.label} fill={pal[i % pal.length]} />
            ))}
          </Pie>
          <Tooltip contentStyle={tip} formatter={(v: number, n) => [fmt(v, unit), n]} />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}

/** Sector × antenna heatmap (YlOrRd), with a Total column. */
export function Heatmap({
  rows,
  cols,
  values,
  unit = "int",
}: {
  rows: string[];
  cols: string[];
  values: number[][];
  unit?: "int" | "dec1";
}) {
  const flat = values.flat();
  const max = Math.max(...flat, 1);
  const rowTotals = values.map((r) => r.reduce((a, b) => a + b, 0));
  const color = (v: number) => {
    const t = Math.min(1, v / max);
    // YlOrRd-ish ramp
    const stops = ["#FFFFD9", "#FED976", "#FD8D3C", "#E31A1C", "#800026"];
    const idx = Math.min(stops.length - 1, Math.floor(t * (stops.length - 1)));
    return stops[idx];
  };
  return (
    <div className="overflow-x-auto">
      <table className="border-collapse text-body-sm">
        <thead>
          <tr>
            <th className="px-3 py-2 text-left text-eyebrow font-semibold uppercase text-neutral-500"></th>
            {cols.map((c) => (
              <th key={c} className="px-3 py-2 text-center text-eyebrow font-semibold uppercase text-neutral-600">{c}</th>
            ))}
            <th className="px-3 py-2 text-center text-eyebrow font-semibold uppercase text-neutral-600">Total</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r, ri) => (
            <tr key={r}>
              <td className="whitespace-nowrap px-3 py-2 font-medium text-neutral-800">{r}</td>
              {cols.map((c, ci) => {
                const v = values[ri][ci];
                const t = Math.min(1, v / max);
                return (
                  <td key={c} className="px-3 py-2 text-center tnum" style={{ background: color(v), color: t > 0.6 ? "#fff" : "var(--neutral-800)" }}>
                    {unit === "dec1" ? formatDec1(v) : formatInt(v)}
                  </td>
                );
              })}
              <td className="px-3 py-2 text-center tnum font-semibold text-neutral-900">{formatInt(rowTotals[ri])}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** Treemap of flows (Sede › Secteur) — inscriptions. */
export function FlowTreemap({
  flows,
  height = 320,
}: {
  flows: { source: string; target: string; value: number }[];
  height?: number;
}) {
  // group by source
  const map = new Map<string, { name: string; children: { name: string; size: number }[] }>();
  for (const f of flows) {
    if (!map.has(f.source)) map.set(f.source, { name: f.source, children: [] });
    map.get(f.source)!.children.push({ name: `${f.source}·${f.target}`, size: f.value });
  }
  const data = [...map.values()];
  return (
    <ResponsiveContainer width="100%" height={height}>
      <Treemap data={data} dataKey="size" stroke="#fff" content={<TreeCell />} />
    </ResponsiveContainer>
  );
}

function TreeCell(props: any) {
  const { x, y, width, height, name, index } = props;
  const fill = SECTOR_PALETTE[(index ?? 0) % SECTOR_PALETTE.length];
  return (
    <g>
      <rect x={x} y={y} width={width} height={height} style={{ fill, stroke: "#fff", strokeWidth: 2 }} />
      {width > 56 && height > 22 && (
        <text x={x + 6} y={y + 16} fill="#fff" fontSize={11} fontFamily="var(--font-sans)">
          {String(name).split("·").pop()}
        </text>
      )}
    </g>
  );
}

/** Lightweight SVG Sankey: Sede (left) → Secteur (right). */
export function Sankey({
  flows,
  height = 360,
  sedeColors,
}: {
  flows: { source: string; target: string; value: number }[];
  height?: number;
  sedeColors: Record<string, string>;
}) {
  const W = 720;
  const sources = Array.from(new Set(flows.map((f) => f.source)));
  const targets = Array.from(new Set(flows.map((f) => f.target)));
  const total = flows.reduce((a, f) => a + f.value, 0) || 1;
  const gap = 6;

  const sourceTot: Record<string, number> = {};
  const targetTot: Record<string, number> = {};
  flows.forEach((f) => {
    sourceTot[f.source] = (sourceTot[f.source] || 0) + f.value;
    targetTot[f.target] = (targetTot[f.target] || 0) + f.value;
  });

  const usable = height - gap * Math.max(sources.length, targets.length);
  const sy: Record<string, { y: number; h: number; cur: number }> = {};
  let yy = 0;
  sources.forEach((s) => {
    const h = (sourceTot[s] / total) * usable;
    sy[s] = { y: yy, h, cur: yy };
    yy += h + gap;
  });
  const ty: Record<string, { y: number; h: number; cur: number }> = {};
  yy = 0;
  targets.forEach((t) => {
    const h = (targetTot[t] / total) * usable;
    ty[t] = { y: yy, h, cur: yy };
    yy += h + gap;
  });

  return (
    <ResponsiveContainer width="100%" height={height}>
      <svg viewBox={`0 0 ${W} ${height}`} preserveAspectRatio="xMidYMid meet">
        {flows.map((f, i) => {
          const sh = (f.value / total) * usable;
          const s = sy[f.source];
          const t = ty[f.target];
          const y0 = s.cur;
          const y1 = t.cur;
          s.cur += sh;
          t.cur += sh;
          const x0 = 120;
          const x1 = W - 160;
          const mid = (x0 + x1) / 2;
          const col = sedeColors[f.source] ?? "#94A3B8";
          return (
            <path
              key={i}
              d={`M${x0},${y0 + sh / 2} C${mid},${y0 + sh / 2} ${mid},${y1 + sh / 2} ${x1},${y1 + sh / 2}`}
              stroke={col}
              strokeWidth={Math.max(1, sh)}
              fill="none"
              opacity={0.35}
            />
          );
        })}
        {sources.map((s) => (
          <g key={s}>
            <rect x={108} y={sy[s].y} width={12} height={sy[s].h} fill={sedeColors[s] ?? "#94A3B8"} rx={2} />
            <text x={102} y={sy[s].y + sy[s].h / 2 + 4} textAnchor="end" fontSize={12} fontFamily="var(--font-sans)" fill="var(--neutral-700)">{s}</text>
          </g>
        ))}
        {targets.map((t) => (
          <g key={t}>
            <rect x={W - 160} y={ty[t].y} width={12} height={ty[t].h} fill="#94A3B8" rx={2} />
            <text x={W - 144} y={ty[t].y + ty[t].h / 2 + 4} textAnchor="start" fontSize={11} fontFamily="var(--font-sans)" fill="var(--neutral-700)">{t}</text>
          </g>
        ))}
      </svg>
    </ResponsiveContainer>
  );
}

/** Double donut: by antenna + by sector. */
export function DoubleDonut({
  antenna,
  sector,
  height = 300,
}: {
  antenna: { label: string; value: number; color: string }[];
  sector: { label: string; value: number }[];
  height?: number;
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <PieChart>
        <Pie data={antenna} dataKey="value" nameKey="label" outerRadius="45%" stroke="#fff" strokeWidth={1}>
          {antenna.map((a) => (
            <Cell key={a.label} fill={a.color} />
          ))}
        </Pie>
        <Pie data={sector} dataKey="value" nameKey="label" innerRadius="55%" outerRadius="80%" paddingAngle={1} stroke="#fff" strokeWidth={1}>
          {sector.map((s, i) => (
            <Cell key={s.label} fill={SECTOR_PALETTE[i % SECTOR_PALETTE.length]} />
          ))}
        </Pie>
        <Tooltip contentStyle={tip} formatter={(v: number, n) => [formatInt(v), n]} />
      </PieChart>
    </ResponsiveContainer>
  );
}
