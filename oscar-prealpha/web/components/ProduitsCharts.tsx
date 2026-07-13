"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ErrorBar,
  ReferenceLine,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from "recharts";
import { ResponsiveContainer } from "./rc";
import { formatInt, formatEur } from "@/lib/format";

const tooltipStyle = {
  background: "#fff",
  border: "1px solid var(--neutral-200)",
  borderRadius: 6,
  boxShadow: "0 1px 3px rgba(15,23,42,0.06), 0 1px 2px rgba(15,23,42,0.04)",
  fontSize: 12,
  fontFamily: "var(--font-sans)",
  color: "var(--neutral-900)",
} as const;

/** Antenna code → colour, matching OSCAR SEDE_COLORS. */
export const SEDE_COLORS: Record<string, string> = {
  IFM: "#FF8C00",
  IFF: "#8B5CF6",
  IFN: "#22C55E",
  IFP: "#EF4444",
};

function sedeColor(code: string): string {
  return SEDE_COLORS[code] ?? "#3B82F6";
}

/** Price distribution histogram (Prix>0, ~30 bins, green). */
export function PrixHistogram({
  data,
  height = 280,
  color = "#22C55E",
}: {
  data: { bin: number; count: number }[];
  height?: number;
  color?: string;
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 8, right: 20, bottom: 8, left: 8 }}>
        <CartesianGrid vertical={false} />
        <XAxis
          dataKey="bin"
          tickLine={false}
          axisLine={{ stroke: "var(--neutral-300)" }}
          tickFormatter={(v) => formatInt(v)}
          interval="preserveStartEnd"
          minTickGap={24}
        />
        <YAxis tickLine={false} axisLine={false} width={40} tickFormatter={(v) => formatInt(v)} />
        <Tooltip
          cursor={{ fill: "var(--accent-50)" }}
          contentStyle={tooltipStyle}
          formatter={(v: number) => [formatInt(v), "Produits"]}
          labelFormatter={(l: number) => `~ ${formatEur(l)}`}
        />
        <Bar dataKey="count" fill={color} radius={[2, 2, 0, 0]} maxBarSize={28} />
      </BarChart>
    </ResponsiveContainer>
  );
}

/**
 * Box plot of Prix per type, approximated with recharts.
 * Each row draws a floating bar (q1→q3) with a whisker ErrorBar (min→max),
 * coloured per antenna where a dominant sede is supplied; otherwise accent.
 */
export function PrixBoxByType({
  data,
  height,
}: {
  data: { type: string; min: number; q1: number; median: number; q3: number; max: number }[];
  height?: number;
}) {
  const rows = data.map((d) => ({
    type: d.type,
    base: d.q1,
    box: Math.max(0, d.q3 - d.q1),
    median: d.median,
    min: d.min,
    max: d.max,
    // whisker errors are measured from the box top (q3)
    whiskerLow: Math.max(0, d.q3 - d.min),
    whiskerHigh: Math.max(0, d.max - d.q3),
  }));
  const h = height ?? Math.max(240, rows.length * 34 + 40);
  return (
    <ResponsiveContainer width="100%" height={h}>
      <BarChart layout="vertical" data={rows} margin={{ top: 4, right: 28, bottom: 4, left: 8 }}>
        <CartesianGrid horizontal={false} />
        <XAxis type="number" tickLine={false} axisLine={false} tickFormatter={(v) => formatInt(v)} />
        <YAxis type="category" dataKey="type" tickLine={false} axisLine={false} width={150} />
        <Tooltip
          cursor={{ fill: "var(--accent-50)" }}
          contentStyle={tooltipStyle}
          formatter={(_v, _n, p) => {
            const d = p.payload as (typeof rows)[number];
            return [
              `min ${formatEur(d.min)} · Q1 ${formatEur(d.base)} · méd ${formatEur(d.median)} · Q3 ${formatEur(d.base + d.box)} · max ${formatEur(d.max)}`,
              "Prix",
            ];
          }}
        />
        {/* transparent spacer up to q1 */}
        <Bar dataKey="base" stackId="b" fill="transparent" />
        {/* the box itself (q1→q3) */}
        <Bar dataKey="box" stackId="b" fill="#3B82F6" fillOpacity={0.35} stroke="#3B82F6" maxBarSize={20}>
          <ErrorBar dataKey="whiskerHigh" width={4} strokeWidth={1.5} stroke="#1E40AF" direction="x" />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

/** Scatter of Prix vs Tarif réduit, coloured by antenna, with a y=x reference line. */
export function ReducedScatter({
  data,
  height = 320,
}: {
  data: { prix: number; tarifReduit: number; sede: string; nom: string; type: string }[];
  height?: number;
}) {
  const maxPrix = data.reduce((m, d) => Math.max(m, d.prix), 0);
  const codes = Array.from(new Set(data.map((d) => d.sede)));
  const bySede = codes.map((code) => ({
    code,
    points: data.filter((d) => d.sede === code),
  }));
  return (
    <ResponsiveContainer width="100%" height={height}>
      <ScatterChart margin={{ top: 12, right: 20, bottom: 12, left: 8 }}>
        <CartesianGrid />
        <XAxis
          type="number"
          dataKey="prix"
          name="Prix"
          tickLine={false}
          axisLine={{ stroke: "var(--neutral-300)" }}
          tickFormatter={(v) => formatInt(v)}
          domain={[0, "dataMax"]}
        />
        <YAxis
          type="number"
          dataKey="tarifReduit"
          name="Tarif réduit"
          tickLine={false}
          axisLine={false}
          width={52}
          tickFormatter={(v) => formatInt(v)}
          domain={[0, "dataMax"]}
        />
        <ZAxis range={[36, 36]} />
        <ReferenceLine
          segment={[
            { x: 0, y: 0 },
            { x: maxPrix, y: maxPrix },
          ]}
          stroke="var(--neutral-400)"
          strokeDasharray="4 4"
          ifOverflow="extendDomain"
        />
        <Tooltip
          cursor={{ strokeDasharray: "3 3" }}
          contentStyle={tooltipStyle}
          formatter={(v: number, n) => [formatEur(v), n]}
          labelFormatter={() => ""}
        />
        {bySede.map((s) => (
          <Scatter key={s.code} name={s.code} data={s.points} fill={sedeColor(s.code)} fillOpacity={0.75} />
        ))}
      </ScatterChart>
    </ResponsiveContainer>
  );
}

/** Vertical grouped bar: x = type, one bar per antenna code. */
export function TypeBySedeBar({
  data,
  height,
}: {
  data: { type: string; IFM: number; IFF: number; IFN: number; IFP: number }[];
  height?: number;
}) {
  const codes: { code: keyof typeof SEDE_COLORS; color: string }[] = [
    { code: "IFM", color: SEDE_COLORS.IFM },
    { code: "IFF", color: SEDE_COLORS.IFF },
    { code: "IFN", color: SEDE_COLORS.IFN },
    { code: "IFP", color: SEDE_COLORS.IFP },
  ];
  const h = height ?? Math.max(280, data.length * 36 + 60);
  return (
    <ResponsiveContainer width="100%" height={h}>
      <BarChart data={data} margin={{ top: 16, right: 20, bottom: 80, left: 8 }}>
        <CartesianGrid vertical={false} />
        <XAxis
          dataKey="type"
          tickLine={false}
          axisLine={{ stroke: "var(--neutral-300)" }}
          interval={0}
          angle={-40}
          textAnchor="end"
          height={80}
          tick={{ fontSize: 11 }}
        />
        <YAxis tickLine={false} axisLine={false} width={40} tickFormatter={(v) => formatInt(v)} />
        <Tooltip cursor={{ fill: "var(--accent-50)" }} contentStyle={tooltipStyle} formatter={(v: number) => formatInt(v)} />
        {codes.map((k) => (
          <Bar key={k.code} dataKey={k.code} fill={k.color} radius={[2, 2, 0, 0]} maxBarSize={16} />
        ))}
      </BarChart>
    </ResponsiveContainer>
  );
}

/** Simple vertical bar coloured per antenna (SEDE_COLORS). */
export function SedeBar({
  data,
  height = 260,
}: {
  data: { code: string; value: number }[];
  height?: number;
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 16, right: 20, bottom: 8, left: 8 }}>
        <CartesianGrid vertical={false} />
        <XAxis dataKey="code" tickLine={false} axisLine={{ stroke: "var(--neutral-300)" }} />
        <YAxis tickLine={false} axisLine={false} width={48} tickFormatter={(v) => formatInt(v)} />
        <Tooltip cursor={{ fill: "var(--accent-50)" }} contentStyle={tooltipStyle} formatter={(v: number) => [formatInt(v), "Produits"]} />
        <Bar dataKey="value" radius={[3, 3, 0, 0]} maxBarSize={64}>
          {data.map((d) => (
            <Cell key={d.code} fill={sedeColor(d.code)} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
