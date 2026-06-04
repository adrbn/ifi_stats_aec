"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ErrorBar,
  Legend,
  ResponsiveContainer,
  Scatter,
  ComposedChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { formatInt } from "@/lib/format";

const tooltipStyle = {
  background: "#fff",
  border: "1px solid var(--neutral-200)",
  borderRadius: 6,
  boxShadow: "0 1px 3px rgba(15,23,42,0.06), 0 1px 2px rgba(15,23,42,0.04)",
  fontSize: 12,
  fontFamily: "var(--font-sans)",
  color: "var(--neutral-900)",
};

const ACCENT = "#3B82F6";

export interface SedeSeries {
  code: string;
  name: string;
  color: string;
  histogram: { bin: string; count: number }[];
  box: { min: number; q1: number; median: number; q3: number; max: number };
}

/**
 * Age histogram. In "sum" mode renders the overall distribution as a single
 * series of bars. In "compare" mode overlays one (semi-transparent) bar series
 * per antenna, sharing the same 2-year bins.
 */
export function AgeHistogram({
  overall,
  bySede,
  mode,
  height = 360,
}: {
  overall: { bin: string; count: number }[];
  bySede: SedeSeries[];
  mode: "sum" | "compare";
  height?: number;
}) {
  if (mode === "sum") {
    return (
      <ResponsiveContainer width="100%" height={height}>
        <BarChart data={overall} margin={{ top: 12, right: 20, bottom: 8, left: 8 }}>
          <CartesianGrid vertical={false} />
          <XAxis dataKey="bin" tickLine={false} axisLine={{ stroke: "var(--neutral-300)" }} interval={3} tick={{ fontSize: 11 }} />
          <YAxis tickLine={false} axisLine={false} width={48} tickFormatter={(v) => formatInt(v)} />
          <Tooltip cursor={{ fill: "var(--accent-50)" }} contentStyle={tooltipStyle} formatter={(v: number) => [formatInt(v), "Clients"]} labelFormatter={(l) => `Âge ${l}`} />
          <Bar dataKey="count" radius={[2, 2, 0, 0]} maxBarSize={22} fill={ACCENT} />
        </BarChart>
      </ResponsiveContainer>
    );
  }

  // compare: merge per-antenna histograms keyed by bin
  const bins = overall.map((b) => b.bin);
  const merged = bins.map((bin) => {
    const row: Record<string, number | string> = { bin };
    bySede.forEach((s) => {
      const hit = s.histogram.find((h) => h.bin === bin);
      row[s.code] = hit ? hit.count : 0;
    });
    return row;
  });
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={merged} margin={{ top: 12, right: 20, bottom: 8, left: 8 }}>
        <CartesianGrid vertical={false} />
        <XAxis dataKey="bin" tickLine={false} axisLine={{ stroke: "var(--neutral-300)" }} interval={3} tick={{ fontSize: 11 }} />
        <YAxis tickLine={false} axisLine={false} width={48} tickFormatter={(v) => formatInt(v)} />
        <Tooltip cursor={{ fill: "var(--accent-50)" }} contentStyle={tooltipStyle} formatter={(v: number) => formatInt(v)} labelFormatter={(l) => `Âge ${l}`} />
        <Legend wrapperStyle={{ fontSize: 12, color: "var(--neutral-600)", paddingTop: 8 }} />
        {bySede.map((s) => (
          <Bar key={s.code} dataKey={s.code} fill={s.color} fillOpacity={0.6} radius={[2, 2, 0, 0]} maxBarSize={16} />
        ))}
      </BarChart>
    </ResponsiveContainer>
  );
}

/**
 * Box plot of age by Sede. Recharts has no native box trace, so we draw the
 * IQR box + whiskers with a stacked invisible base, an error-bar whisker, and
 * a median marker — one antenna per category.
 */
export function AgeBoxBySede({ rows, height = 320 }: { rows: SedeSeries[]; height?: number }) {
  const data = rows.map((r) => ({
    name: r.name,
    color: r.color,
    base: r.box.q1, // invisible offset to lift the box to q1
    iqr: Math.max(r.box.q3 - r.box.q1, 0), // visible box height
    median: r.box.median,
    min: r.box.min,
    max: r.box.max,
    // whisker error bars are relative to the box center (q1 + iqr/2)
    whiskerLo: r.box.q1 + Math.max(r.box.q3 - r.box.q1, 0) / 2 - r.box.min,
    whiskerHi: r.box.max - (r.box.q1 + Math.max(r.box.q3 - r.box.q1, 0) / 2),
    center: r.box.q1 + Math.max(r.box.q3 - r.box.q1, 0) / 2,
  }));

  return (
    <ResponsiveContainer width="100%" height={height}>
      <ComposedChart data={data} margin={{ top: 12, right: 20, bottom: 8, left: 8 }}>
        <CartesianGrid vertical={false} />
        <XAxis dataKey="name" tickLine={false} axisLine={{ stroke: "var(--neutral-300)" }} tick={{ fontSize: 12 }} />
        <YAxis tickLine={false} axisLine={false} width={48} tickFormatter={(v) => formatInt(v)} domain={[0, "dataMax + 5"]} />
        <Tooltip
          contentStyle={tooltipStyle}
          cursor={{ fill: "var(--accent-50)" }}
          formatter={(_v, _n, p) => {
            const d = p?.payload;
            if (!d) return ["", ""];
            return [`min ${formatInt(d.min)} · Q1 ${formatInt(d.base)} · méd. ${formatInt(d.median)} · Q3 ${formatInt(d.base + d.iqr)} · max ${formatInt(d.max)}`, "Âge"];
          }}
        />
        {/* invisible base lifts the visible box to q1 */}
        <Bar dataKey="base" stackId="box" fill="transparent" maxBarSize={48} isAnimationActive={false} />
        {/* visible IQR box, with whiskers anchored at the box center */}
        <Bar dataKey="iqr" stackId="box" maxBarSize={48} radius={[2, 2, 2, 2]} isAnimationActive={false}>
          {data.map((d) => (
            <Cell key={d.name} fill={d.color} fillOpacity={0.55} stroke={d.color} strokeWidth={1} />
          ))}
          <ErrorBar dataKey="whiskerHi" width={6} strokeWidth={1.5} stroke="var(--neutral-500)" direction="y" />
          <ErrorBar dataKey="whiskerLo" width={6} strokeWidth={1.5} stroke="var(--neutral-500)" direction="y" />
        </Bar>
        {/* median markers */}
        <Scatter dataKey="median" isAnimationActive={false}>
          {data.map((d) => (
            <Cell key={d.name} fill={d.color} />
          ))}
        </Scatter>
      </ComposedChart>
    </ResponsiveContainer>
  );
}

const MACRO_COLORS: Record<string, string> = {
  A0: "#e0f2fe",
  A1: "#7dd3fc",
  A2: "#38bdf8",
  B1: "#0284c7",
  B2: "#0369a1",
  C1: "#075985",
  C2: "#0c4a6e",
  Autre: "#94a3b8",
};

/** CEFR macro-level bar chart (A0..C2, Autre last) with per-level colours. */
export function MacroLevelBar({ rows, height = 300 }: { rows: { label: string; count: number }[]; height?: number }) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={rows} margin={{ top: 16, right: 20, bottom: 8, left: 8 }}>
        <CartesianGrid vertical={false} />
        <XAxis dataKey="label" tickLine={false} axisLine={{ stroke: "var(--neutral-300)" }} />
        <YAxis tickLine={false} axisLine={false} width={48} tickFormatter={(v) => formatInt(v)} />
        <Tooltip cursor={{ fill: "var(--accent-50)" }} contentStyle={tooltipStyle} formatter={(v: number) => [formatInt(v), "Clients"]} />
        <Bar dataKey="count" radius={[3, 3, 0, 0]} maxBarSize={56}>
          {rows.map((r) => (
            <Cell key={r.label} fill={MACRO_COLORS[r.label] ?? "#94a3b8"} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

/**
 * Grouped bar where each x category carries one bar per antenna. Used for
 * tranches/nationality/motivation/canal by Sede. `unit` controls tick + tooltip
 * formatting (count vs percentage).
 */
export function GroupedSedeBar({
  data,
  xKey,
  keys,
  unit = "int",
  height = 320,
}: {
  data: Record<string, number | string>[];
  xKey: string;
  keys: { code: string; name: string; color: string }[];
  unit?: "int" | "pct";
  height?: number;
}) {
  const longLabels = data.some((d) => String(d[xKey]).length > 10) || data.length > 6;
  const fmt = (v: number) => (unit === "pct" ? `${String(v).replace(".", ",")} %` : formatInt(v));
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 16, right: 20, bottom: longLabels ? 16 : 8, left: 8 }}>
        <CartesianGrid vertical={false} />
        <XAxis
          dataKey={xKey}
          tickLine={false}
          axisLine={{ stroke: "var(--neutral-300)" }}
          interval={0}
          angle={longLabels ? -30 : 0}
          textAnchor={longLabels ? "end" : "middle"}
          height={longLabels ? 96 : 30}
          tick={{ fontSize: 11 }}
        />
        <YAxis tickLine={false} axisLine={false} width={48} tickFormatter={(v) => (unit === "pct" ? `${v}%` : formatInt(v))} />
        <Tooltip cursor={{ fill: "var(--accent-50)" }} contentStyle={tooltipStyle} formatter={(v: number, n) => [fmt(v), n]} />
        <Legend wrapperStyle={{ fontSize: 12, color: "var(--neutral-600)", paddingTop: 8 }} />
        {keys.map((k) => (
          <Bar key={k.code} dataKey={k.code} name={k.name} fill={k.color} radius={[3, 3, 0, 0]} maxBarSize={26} />
        ))}
      </BarChart>
    </ResponsiveContainer>
  );
}

const BRACKET_PALETTE = ["#3B82F6", "#F97316", "#10B981", "#A855F7", "#EAB308", "#06B6D4", "#EC4899"];

/** Grouped bar with a generic colour palette for the key series (e.g. tranches by Sede). */
export function GroupedPaletteBar({
  data,
  xKey,
  keys,
  height = 340,
}: {
  data: Record<string, number | string>[];
  xKey: string;
  keys: string[];
  height?: number;
}) {
  const longLabels = data.some((d) => String(d[xKey]).length > 10) || data.length > 5;
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 16, right: 20, bottom: longLabels ? 24 : 8, left: 8 }}>
        <CartesianGrid vertical={false} />
        <XAxis
          dataKey={xKey}
          tickLine={false}
          axisLine={{ stroke: "var(--neutral-300)" }}
          interval={0}
          angle={longLabels ? -25 : 0}
          textAnchor={longLabels ? "end" : "middle"}
          height={longLabels ? 110 : 30}
          tick={{ fontSize: 10 }}
        />
        <YAxis tickLine={false} axisLine={false} width={48} tickFormatter={(v) => formatInt(v)} />
        <Tooltip cursor={{ fill: "var(--accent-50)" }} contentStyle={tooltipStyle} formatter={(v: number, n) => [formatInt(v), n]} />
        <Legend wrapperStyle={{ fontSize: 12, color: "var(--neutral-600)", paddingTop: 8 }} />
        {keys.map((k, i) => (
          <Bar key={k} dataKey={k} fill={BRACKET_PALETTE[i % BRACKET_PALETTE.length]} radius={[3, 3, 0, 0]} maxBarSize={22} />
        ))}
      </BarChart>
    </ResponsiveContainer>
  );
}
