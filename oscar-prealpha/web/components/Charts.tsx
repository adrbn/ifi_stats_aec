"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  ReferenceLine,
  Tooltip,
  XAxis,
  YAxis,
  Legend,
} from "recharts";
import { ResponsiveContainer } from "./rc";
import type { EvolutionSeries } from "@/lib/types";
import { formatInt, formatEur, formatDec1 } from "@/lib/format";

const tooltipStyle = {
  background: "#fff",
  border: "1px solid var(--neutral-200)",
  borderRadius: 6,
  boxShadow: "0 1px 3px rgba(15,23,42,0.06), 0 1px 2px rgba(15,23,42,0.04)",
  fontSize: 12,
  fontFamily: "var(--font-sans)",
  color: "var(--neutral-900)",
};

// Bleu IFI (réseau global) — cohérent avec ANTENNA_META["IFI"].color côté backend.
const IFI_BLUE = "#3B82F6";

type Unit = "int" | "eur" | "dec1";
const fmtUnit = (v: number, unit: Unit) =>
  unit === "eur" ? formatEur(v) : unit === "dec1" ? formatDec1(v) : formatInt(v);

/**
 * Barres par antenne pour un indicateur quelconque. `rows` porte une `value`
 * générique. Total IFI (bleu) en tête : somme par défaut, ou `total` fourni
 * (ex. remplissage = ratio global, non sommable). `label` nomme l'indicateur.
 */
export function AntennaBar({
  rows,
  showTotal = true,
  total,
  unit = "int",
  label = "Inscriptions",
  height = 260,
}: {
  rows: { code: string; color: string; value: number }[];
  showTotal?: boolean;
  total?: number;
  unit?: Unit;
  label?: string;
  height?: number;
}) {
  const antennas = rows.map((r) => ({ name: r.code, value: r.value, color: r.color }));
  const totalVal = total ?? antennas.reduce((s, d) => s + d.value, 0);
  const data = showTotal ? [{ name: "IFI", value: totalVal, color: IFI_BLUE }, ...antennas] : antennas;
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 16, right: 20, bottom: 8, left: 8 }}>
        <CartesianGrid vertical={false} />
        <XAxis dataKey="name" tickLine={false} axisLine={{ stroke: "var(--neutral-300)" }} />
        <YAxis tickLine={false} axisLine={false} width={unit === "eur" ? 60 : 48} tickFormatter={(v) => fmtUnit(v, unit)} />
        <Tooltip
          cursor={{ fill: "var(--accent-50)" }}
          contentStyle={tooltipStyle}
          formatter={(v: number, _n, p) => [fmtUnit(v, unit), p?.payload?.name === "IFI" ? `Total IFI · ${label}` : label]}
        />
        <Bar dataKey="value" radius={[3, 3, 0, 0]} maxBarSize={64}>
          {data.map((d) => (
            <Cell key={d.name} fill={d.color} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

export function HBar({
  data,
  height = 320,
  color = "#3B82F6",
  unit = "int",
}: {
  data: { name: string; value: number }[];
  height?: number;
  color?: string;
  unit?: Unit;
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart layout="vertical" data={data} margin={{ top: 4, right: 24, bottom: 4, left: 8 }}>
        <CartesianGrid horizontal={false} />
        <XAxis type="number" tickLine={false} axisLine={false} tickFormatter={(v) => fmtUnit(v, unit)} />
        <YAxis type="category" dataKey="name" tickLine={false} axisLine={false} width={130} />
        <Tooltip cursor={{ fill: "var(--accent-50)" }} contentStyle={tooltipStyle} formatter={(v: number) => fmtUnit(v, unit)} />
        <Bar dataKey="value" radius={[0, 3, 3, 0]} maxBarSize={26} fill={color} />
      </BarChart>
    </ResponsiveContainer>
  );
}

export function GroupedYearBar({
  rows,
  metric,
}: {
  rows: { year: number; inscriptions: number; recettes: number }[];
  metric: "inscriptions" | "recettes";
}) {
  const data = rows.map((r) => ({ year: r.year, value: r[metric] }));
  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={data} margin={{ top: 16, right: 20, bottom: 8, left: 8 }}>
        <CartesianGrid vertical={false} />
        <XAxis dataKey="year" tickLine={false} axisLine={{ stroke: "var(--neutral-300)" }} />
        <YAxis tickLine={false} axisLine={false} width={52} tickFormatter={(v) => formatInt(v)} />
        <Tooltip cursor={{ fill: "var(--accent-50)" }} contentStyle={tooltipStyle} formatter={(v: number) => formatInt(v)} />
        <Bar dataKey="value" radius={[3, 3, 0, 0]} maxBarSize={56} fill="#3B82F6" />
      </BarChart>
    </ResponsiveContainer>
  );
}

/** Mini-histogramme par année pour UN indicateur (small multiple). Sa propre
 *  échelle Y (jamais mélanger deux indicateurs sur un même axe). Les libellés
 *  d'année (« 2025 » / « 2025-26 ») sont déjà mis en forme par l'appelant. */
export function YearBars({
  data,
  color,
  unit = "int",
  height = 190,
}: {
  data: { year: string; value: number }[];
  color: string;
  unit?: Unit;
  height?: number;
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 12, right: 12, bottom: 4, left: 4 }}>
        <CartesianGrid vertical={false} stroke="var(--neutral-200)" />
        <XAxis dataKey="year" tickLine={false} axisLine={{ stroke: "var(--neutral-300)" }} tick={{ fontSize: 11 }} />
        <YAxis tickLine={false} axisLine={false} width={unit === "eur" ? 58 : 44} tick={{ fontSize: 11 }} tickFormatter={(v) => fmtUnit(v, unit)} />
        <Tooltip cursor={{ fill: "var(--accent-50)" }} contentStyle={tooltipStyle} formatter={(v: number) => [fmtUnit(v, unit), ""]} />
        <Bar dataKey="value" radius={[3, 3, 0, 0]} maxBarSize={48} fill={color} />
      </BarChart>
    </ResponsiveContainer>
  );
}

/** Variante COURBE du small multiple (mêmes données/échelle que YearBars). */
export function YearLine({
  data,
  color,
  unit = "int",
  height = 190,
}: {
  data: { year: string; value: number }[];
  color: string;
  unit?: Unit;
  height?: number;
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={{ top: 12, right: 12, bottom: 4, left: 4 }}>
        <CartesianGrid vertical={false} stroke="var(--neutral-200)" />
        <XAxis dataKey="year" tickLine={false} axisLine={{ stroke: "var(--neutral-300)" }} tick={{ fontSize: 11 }} />
        <YAxis tickLine={false} axisLine={false} width={unit === "eur" ? 58 : 44} tick={{ fontSize: 11 }} tickFormatter={(v) => fmtUnit(v, unit)} />
        <Tooltip cursor={{ stroke: "var(--neutral-300)" }} contentStyle={tooltipStyle} formatter={(v: number) => [fmtUnit(v, unit), ""]} />
        <Line type="monotone" dataKey="value" stroke={color} strokeWidth={2} dot={{ r: 3, fill: color, strokeWidth: 0 }} activeDot={{ r: 5 }} />
      </LineChart>
    </ResponsiveContainer>
  );
}

/** Plusieurs indicateurs sur UN graphe, ramenés en base 100 à la 1re année
 *  (première valeur non nulle) → comparaison des ÉVOLUTIONS relatives sans
 *  mélanger des échelles hétérogènes. Une couleur + une entrée de légende par
 *  indicateur ; ligne de référence à 100. */
export function IndexedLines({
  years,
  series,
  height = 320,
}: {
  years: string[];
  series: { key: string; name: string; color: string; values: number[] }[];
  height?: number;
}) {
  const based = series.map((s) => {
    const base = s.values.find((v) => v !== 0) ?? 0;
    return { ...s, idx: s.values.map((v) => (base ? (v / base) * 100 : 0)) };
  });
  const data = years.map((y, i) => {
    const row: Record<string, number | string> = { year: y };
    based.forEach((s) => (row[s.key] = Math.round(s.idx[i] * 10) / 10));
    return row;
  });
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={{ top: 16, right: 24, bottom: 8, left: 8 }}>
        <CartesianGrid vertical={false} stroke="var(--neutral-200)" />
        <XAxis dataKey="year" tickLine={false} axisLine={{ stroke: "var(--neutral-300)" }} tick={{ fontSize: 12 }} />
        <YAxis tickLine={false} axisLine={false} width={44} tick={{ fontSize: 12 }} tickFormatter={(v) => String(v)} />
        <ReferenceLine y={100} stroke="var(--neutral-300)" strokeDasharray="3 3" />
        <Tooltip contentStyle={tooltipStyle} formatter={(v: number, n) => [`${formatDec1(v)} (base 100)`, n as string]} />
        <Legend iconType="plainline" wrapperStyle={{ fontSize: 12, color: "var(--neutral-600)", paddingTop: 8 }} />
        {based.map((s) => (
          <Line
            key={s.key}
            type="monotone"
            dataKey={s.key}
            name={s.name}
            stroke={s.color}
            strokeWidth={2}
            dot={{ r: 3, fill: s.color, strokeWidth: 0 }}
            activeDot={{ r: 5 }}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}

export function EvolutionLine({
  years,
  series,
  metric = "inscriptions",
  height = 280,
}: {
  years: number[];
  series: EvolutionSeries[];
  metric?: string;
  height?: number;
}) {
  const pick = (s: EvolutionSeries, i: number): number => {
    if (metric === "inscriptions") return s.inscriptions[i];
    if (metric === "recettes") return s.recettes[i];
    return s.metrics?.[metric]?.[i] ?? 0;
  };
  const data = years.map((y, i) => {
    const row: Record<string, number | string> = { year: y };
    series.forEach((s) => (row[s.code] = pick(s, i)));
    return row;
  });
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={{ top: 16, right: 20, bottom: 8, left: 8 }}>
        <CartesianGrid vertical={false} />
        <XAxis dataKey="year" tickLine={false} axisLine={{ stroke: "var(--neutral-300)" }} />
        <YAxis tickLine={false} axisLine={false} width={48} tickFormatter={(v) => formatInt(v)} />
        <Tooltip contentStyle={tooltipStyle} formatter={(v: number) => formatInt(v)} />
        <Legend
          iconType="plainline"
          wrapperStyle={{ fontSize: 12, color: "var(--neutral-600)", paddingTop: 8 }}
        />
        {series.map((s) => (
          <Line
            key={s.code}
            type="monotone"
            dataKey={s.code}
            name={s.name}
            stroke={s.color}
            strokeWidth={2}
            dot={{ r: 3, fill: s.color, strokeWidth: 0 }}
            activeDot={{ r: 5 }}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}

const PIE_PALETTE = [
  "#3B82F6", "#F97316", "#10B981", "#A855F7", "#EAB308",
  "#06B6D4", "#EC4899", "#14B8A6", "#F59E0B", "#6366F1",
  "#84CC16", "#EF4444",
];

export function Donut({
  data,
  height = 260,
  colors,
}: {
  data: { name: string; value: number }[];
  height?: number;
  colors?: string[];
}) {
  const pal = colors ?? PIE_PALETTE;
  return (
    <ResponsiveContainer width="100%" height={height}>
      <PieChart>
        <Pie data={data} dataKey="value" nameKey="name" innerRadius="55%" outerRadius="80%" paddingAngle={1} stroke="#fff" strokeWidth={1}>
          {data.map((d, i) => (
            <Cell key={d.name} fill={pal[i % pal.length]} />
          ))}
        </Pie>
        <Tooltip contentStyle={tooltipStyle} formatter={(v: number, n) => [formatInt(v), n]} />
        <Legend wrapperStyle={{ fontSize: 12, color: "var(--neutral-600)", paddingTop: 8 }} />
      </PieChart>
    </ResponsiveContainer>
  );
}

/** Grouped bar where each x category has one bar per antenna code. */
export function GroupedAntennaBar({
  data,
  keys,
  height = 280,
}: {
  data: Record<string, number | string>[];
  keys: { code: string; color: string }[];
  height?: number;
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 16, right: 20, bottom: 8, left: 8 }}>
        <CartesianGrid vertical={false} />
        <XAxis dataKey="name" tickLine={false} axisLine={{ stroke: "var(--neutral-300)" }} interval={0} angle={data.length > 6 ? -30 : 0} textAnchor={data.length > 6 ? "end" : "middle"} height={data.length > 6 ? 64 : 30} />
        <YAxis tickLine={false} axisLine={false} width={48} tickFormatter={(v) => formatInt(v)} />
        <Tooltip cursor={{ fill: "var(--accent-50)" }} contentStyle={tooltipStyle} formatter={(v: number) => formatInt(v)} />
        <Legend wrapperStyle={{ fontSize: 12, color: "var(--neutral-600)", paddingTop: 8 }} />
        {keys.map((k) => (
          <Bar key={k.code} dataKey={k.code} fill={k.color} radius={[3, 3, 0, 0]} maxBarSize={28} />
        ))}
      </BarChart>
    </ResponsiveContainer>
  );
}
