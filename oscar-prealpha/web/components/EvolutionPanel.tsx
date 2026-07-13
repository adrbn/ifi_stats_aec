"use client";

import { useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { ResponsiveContainer } from "./rc";
import type { EvolutionSeries } from "@/lib/types";
import { formatInt } from "@/lib/format";
import { useFilters } from "@/lib/store";
import { yearLabel } from "./Filters";
import { Panel } from "./Card";

const tooltipStyle = {
  background: "#fff",
  border: "1px solid var(--neutral-200)",
  borderRadius: 6,
  boxShadow: "0 1px 3px rgba(15,23,42,0.06), 0 1px 2px rgba(15,23,42,0.04)",
  fontSize: 12,
  fontFamily: "var(--font-sans)",
  color: "var(--neutral-900)",
};

type View = "line" | "bar";
type Scale = "linear" | "log";

function Seg<T extends string>({
  value,
  onChange,
  options,
}: {
  value: T;
  onChange: (v: T) => void;
  options: { value: T; label: string }[];
}) {
  return (
    <div className="inline-flex gap-1 rounded-pill bg-neutral-100 p-[3px]">
      {options.map((o) => (
        <button
          key={o.value}
          onClick={() => onChange(o.value)}
          className={`rounded-pill px-2.5 py-1 text-caption font-semibold transition-all duration-150 ease-out-soft ${
            value === o.value ? "bg-accent-500 text-white shadow-sm" : "text-neutral-500 hover:bg-surface hover:text-neutral-900"
          }`}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

/**
 * Panneau d'évolution avec bascules en haut à droite :
 *  - Courbe ⇄ Histogramme,
 *  - échelle Linéaire ⇄ Log (utile quand une antenne écrase les autres),
 * et passage forcé en histogramme quand une seule période est sélectionnée
 * (une courbe à un point n'a aucun intérêt).
 */
export function EvolutionPanel({
  title,
  subtitle,
  years,
  series,
  metric = "inscriptions",
}: {
  title: string;
  subtitle?: string;
  years: number[];
  series: EvolutionSeries[];
  metric?: string;
}) {
  const yearMode = useFilters((s) => s.yearMode);
  const single = years.length < 2;
  const [view, setView] = useState<View>("line");
  const [scale, setScale] = useState<Scale>("linear");
  const effView: View = single ? "bar" : view; // 1 période → histogramme

  const pick = (s: EvolutionSeries, i: number): number => {
    if (metric === "inscriptions") return s.inscriptions[i];
    if (metric === "recettes") return s.recettes[i];
    return s.metrics?.[metric]?.[i] ?? 0;
  };
  const data = years.map((y, i) => {
    const row: Record<string, number | string> = { x: yearLabel(y, yearMode) };
    series.forEach((s) => (row[s.code] = pick(s, i)));
    return row;
  });

  const controls = (
    <div className="flex flex-wrap items-center gap-1.5">
      {!single && (
        <Seg
          value={view}
          onChange={setView}
          options={[
            { value: "line", label: "Courbe" },
            { value: "bar", label: "Histo." },
          ]}
        />
      )}
      {effView === "line" && (
        <Seg
          value={scale}
          onChange={setScale}
          options={[
            { value: "linear", label: "Lin." },
            { value: "log", label: "Log" },
          ]}
        />
      )}
    </div>
  );

  const axisX = (
    <XAxis dataKey="x" tickLine={false} axisLine={{ stroke: "var(--neutral-300)" }} />
  );
  const legend = (
    <Legend iconType="plainline" wrapperStyle={{ fontSize: 12, color: "var(--neutral-600)", paddingTop: 8 }} />
  );
  const tooltip = <Tooltip contentStyle={tooltipStyle} formatter={(v: number) => formatInt(v)} />;

  return (
    <Panel title={title} subtitle={subtitle} right={controls}>
      <ResponsiveContainer width="100%" height={300}>
        {effView === "line" ? (
          <LineChart data={data} margin={{ top: 16, right: 20, bottom: 8, left: 8 }}>
            <CartesianGrid vertical={false} />
            {axisX}
            <YAxis
              tickLine={false}
              axisLine={false}
              width={52}
              scale={scale === "log" ? "log" : "auto"}
              domain={scale === "log" ? [1, "auto"] : [0, "auto"]}
              allowDataOverflow={scale === "log"}
              tickFormatter={(v) => formatInt(v)}
            />
            {tooltip}
            {legend}
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
                connectNulls
              />
            ))}
          </LineChart>
        ) : (
          <BarChart data={data} margin={{ top: 16, right: 20, bottom: 8, left: 8 }}>
            <CartesianGrid vertical={false} />
            {axisX}
            <YAxis tickLine={false} axisLine={false} width={52} tickFormatter={(v) => formatInt(v)} />
            <Tooltip cursor={{ fill: "var(--accent-50)" }} contentStyle={tooltipStyle} formatter={(v: number) => formatInt(v)} />
            {legend}
            {series.map((s) => (
              <Bar key={s.code} dataKey={s.code} name={s.name} fill={s.color} radius={[3, 3, 0, 0]} maxBarSize={28} />
            ))}
          </BarChart>
        )}
      </ResponsiveContainer>
    </Panel>
  );
}
