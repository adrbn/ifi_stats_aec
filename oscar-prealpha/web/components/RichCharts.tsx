"use client";

import { useEffect, useRef, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { ResponsiveContainer } from "./rc";
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
  unit?: "int" | "dec1" | "eur";
}) {
  const cell = (v: number) => (unit === "eur" ? formatEur(v) : unit === "dec1" ? formatDec1(v) : formatInt(v));
  // Le remplissage (ratio) ne se totalise pas par ligne : on masque la colonne Total.
  const showTotal = unit !== "dec1";
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
      <table className="w-full border-separate border-spacing-1 text-body-sm">
        <thead>
          <tr>
            <th className="px-3 py-2 text-left text-eyebrow font-semibold uppercase text-neutral-500"></th>
            {cols.map((c) => (
              <th key={c} className="min-w-[88px] px-4 py-2 text-center text-eyebrow font-semibold uppercase text-neutral-600">{c}</th>
            ))}
            {showTotal && <th className="min-w-[88px] px-4 py-2 text-center text-eyebrow font-semibold uppercase text-neutral-600">Total</th>}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, ri) => (
            <tr key={r}>
              <td className="w-[150px] whitespace-nowrap py-3 pr-4 font-medium text-neutral-800">{r}</td>
              {cols.map((c, ci) => {
                const v = values[ri][ci];
                const t = Math.min(1, v / max);
                return (
                  <td key={c} className="tnum rounded-sm px-4 py-3 text-center" style={{ background: color(v), color: t > 0.6 ? "#fff" : "var(--neutral-800)" }}>
                    {cell(v)}
                  </td>
                );
              })}
              {showTotal && <td className="tnum rounded-sm bg-neutral-50 px-4 py-3 text-center font-semibold text-neutral-900">{cell(rowTotals[ri])}</td>}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/**
 * Treemap hiérarchique antenne › secteur (inscriptions). Colonnes = antennes
 * (largeur ∝ total), segments = secteurs (hauteur ∝ valeur). SVG maison (le
 * Treemap Recharts imbriqué rendait des labels « undefined »). Largeur mesurée
 * → remplit sans déformer le texte. Survol + tooltip natif ; clic = filtre
 * secteur (si onSelect fourni).
 */
export function FlowTreemap({
  flows,
  height = 320,
  onSelect,
  unit = "int",
  label = "inscriptions",
}: {
  flows: { source: string; target: string; value: number }[];
  height?: number;
  onSelect?: (secteur: string) => void;
  unit?: "int" | "eur";
  label?: string;
}) {
  const fmtVal = (v: number) => (unit === "eur" ? formatEur(v) : formatInt(v));
  const ref = useRef<HTMLDivElement>(null);
  const [w, setW] = useState(640);
  useEffect(() => {
    const el = ref.current;
    if (!el || typeof ResizeObserver === "undefined") return;
    const ro = new ResizeObserver((entries) => {
      const cw = entries[0]?.contentRect.width;
      if (cw && cw > 0) setW(cw);
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const TOP = 20;
  const PAD = 2.5;
  const innerH = Math.max(0, height - TOP);

  // Regroupement par antenne (source) + couleur stable par secteur.
  const bySource = new Map<string, { value: number; cells: { target: string; value: number }[] }>();
  for (const f of flows) {
    if (!f.value || f.value <= 0) continue;
    if (!bySource.has(f.source)) bySource.set(f.source, { value: 0, cells: [] });
    const g = bySource.get(f.source)!;
    g.value += f.value;
    g.cells.push({ target: f.target, value: f.value });
  }
  const sources = [...bySource.entries()].sort((a, b) => b[1].value - a[1].value);
  const total = sources.reduce((s, [, g]) => s + g.value, 0) || 1;
  const sectors = [...new Set(flows.map((f) => f.target))];
  const colorOf = (t: string) => SECTOR_PALETTE[Math.max(0, sectors.indexOf(t)) % SECTOR_PALETTE.length];

  type Node = { key: string; x: number; y: number; cw: number; ch: number; source: string; target: string; value: number; big: boolean };
  const nodes: Node[] = [];
  const headers: { source: string; x: number; show: boolean }[] = [];
  let x = 0;
  for (const [source, g] of sources) {
    const cw = (g.value / total) * w;
    headers.push({ source, x, show: cw > 38 });
    let y = TOP;
    for (const c of [...g.cells].sort((a, b) => b.value - a.value)) {
      const ch = (c.value / g.value) * innerH;
      nodes.push({
        key: `${source}-${c.target}`, x, y, cw, ch,
        source, target: c.target, value: c.value,
        big: cw > 48 && ch > 26,
      });
      y += ch;
    }
    x += cw;
  }

  return (
    <div ref={ref} className="w-full min-w-0 overflow-hidden">
      <svg width={w} height={height} role="img" aria-label="Répartition antenne par secteur">
        {headers.map((h) =>
          h.show ? (
            <text key={`h-${h.source}`} x={h.x + 5} y={13} fontSize={11} fontWeight={700} fill="var(--neutral-600)" fontFamily="var(--font-sans)">
              {h.source}
            </text>
          ) : null
        )}
        {nodes.map((n) => (
          <g
            key={n.key}
            onClick={() => onSelect?.(n.target)}
            className={onSelect ? "cursor-pointer transition-opacity hover:opacity-80" : ""}
          >
            <rect
              x={n.x + PAD}
              y={n.y + PAD}
              width={Math.max(0, n.cw - PAD * 2)}
              height={Math.max(0, n.ch - PAD * 2)}
              rx={2.5}
              fill={colorOf(n.target)}
            >
              <title>{`${n.source} · ${n.target}\n${fmtVal(n.value)} ${label} · ${Math.round((n.value / total) * 100)}% du total`}</title>
            </rect>
            {n.big && (
              <>
                <text x={n.x + PAD + 6} y={n.y + 17} fontSize={10.5} fontWeight={600} fill="#fff" fontFamily="var(--font-sans)">
                  {n.target}
                </text>
                <text x={n.x + PAD + 6} y={n.y + 31} fontSize={10} fill="rgba(255,255,255,0.85)" fontFamily="var(--font-sans)" className="tnum">
                  {fmtVal(n.value)}
                </text>
              </>
            )}
          </g>
        ))}
      </svg>
    </div>
  );
}

/** Sankey SVG antenne → secteur : interactif (survol = met en valeur les flux du
 *  nœud, atténue le reste), valeurs chiffrées par nœud, couleurs secteur. */
export function Sankey({
  flows,
  height = 360,
  sedeColors,
  unit = "int",
  label = "inscriptions",
}: {
  flows: { source: string; target: string; value: number }[];
  height?: number;
  sedeColors: Record<string, string>;
  unit?: "int" | "eur" | "dec1";
  label?: string;
}) {
  const [hover, setHover] = useState<string | null>(null);
  const W = 760;
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

  const secColor = (t: string) => SECTOR_PALETTE[Math.max(0, targets.indexOf(t)) % SECTOR_PALETTE.length];
  const x0 = 130;
  const x1 = W - 215;
  const mid = (x0 + x1) / 2;

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
          const col = sedeColors[f.source] ?? "#94A3B8";
          const dimmed = hover != null && f.source !== hover && f.target !== hover;
          return (
            <path
              key={i}
              d={`M${x0},${y0 + sh / 2} C${mid},${y0 + sh / 2} ${mid},${y1 + sh / 2} ${x1},${y1 + sh / 2}`}
              stroke={col}
              strokeWidth={Math.max(1.5, sh)}
              fill="none"
              opacity={dimmed ? 0.07 : hover ? 0.6 : 0.42}
              className="transition-opacity duration-150"
            >
              <title>{`${f.source} → ${f.target}\n${fmt(f.value, unit)} ${label} · ${Math.round((f.value / total) * 100)}%`}</title>
            </path>
          );
        })}
        {sources.map((s) => (
          <g key={s} onMouseEnter={() => setHover(s)} onMouseLeave={() => setHover(null)}>
            <rect x={x0 - 12} y={sy[s].y} width={12} height={sy[s].h} rx={2} fill={sedeColors[s] ?? "#94A3B8"} opacity={hover && hover !== s ? 0.4 : 1} />
            <text x={x0 - 18} y={sy[s].y + sy[s].h / 2 + (sy[s].h > 16 ? -2 : 4)} textAnchor="end" fontSize={12} fontWeight={600} fill="var(--neutral-800)">{s}</text>
            {sy[s].h > 16 && (
              <text x={x0 - 18} y={sy[s].y + sy[s].h / 2 + 11} textAnchor="end" fontSize={10} className="tnum" fill="var(--neutral-400)">{fmt(sourceTot[s], unit)}</text>
            )}
          </g>
        ))}
        {targets.map((t) => (
          <g key={t} onMouseEnter={() => setHover(t)} onMouseLeave={() => setHover(null)}>
            <rect x={x1} y={ty[t].y} width={12} height={ty[t].h} rx={2} fill={secColor(t)} opacity={hover && hover !== t ? 0.4 : 1} />
            <text x={x1 + 18} y={ty[t].y + ty[t].h / 2 + (ty[t].h > 16 ? -2 : 4)} textAnchor="start" fontSize={11} fontWeight={600} fill="var(--neutral-800)">{t}</text>
            {ty[t].h > 16 && (
              <text x={x1 + 18} y={ty[t].y + ty[t].h / 2 + 11} textAnchor="start" fontSize={10} className="tnum" fill="var(--neutral-400)">{fmt(targetTot[t], unit)}</text>
            )}
          </g>
        ))}
      </svg>
    </ResponsiveContainer>
  );
}

/** Acquisition vs fidélisation : part nouveaux (vert) / réinscrits (bleu) par
 *  antenne, avec le % de réinscrits (taux de fidélisation). */
export function AcquisitionRetention({
  rows,
}: {
  rows: { name: string; nouveaux: number; reinscrits: number; highlight?: boolean }[];
}) {
  const REINS = "#3B82F6"; // fidélisation
  const NOUV = "#10B981"; // acquisition
  const max = Math.max(...rows.map((r) => r.nouveaux + r.reinscrits), 1);
  return (
    <div className="space-y-4">
      <div className="mb-1 flex flex-wrap items-center gap-x-4 gap-y-1 text-caption text-neutral-500">
        <span className="inline-flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-sm" style={{ background: REINS }} />Réinscrits (fidélisation)</span>
        <span className="inline-flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-sm" style={{ background: NOUV }} />Nouveaux (acquisition)</span>
      </div>
      {rows.map((r) => {
        const tot = r.nouveaux + r.reinscrits;
        const pct = tot ? Math.round((r.reinscrits / tot) * 100) : 0;
        const w = (tot / max) * 100;
        const reinsW = tot ? (r.reinscrits / tot) * 100 : 0;
        return (
          <div key={r.name} className="flex items-center gap-3">
            <span className={`w-9 flex-shrink-0 text-caption font-semibold ${r.highlight ? "text-accent-700" : "text-neutral-700"}`}>{r.name}</span>
            <div className="flex h-6 flex-1 items-center">
              <div
                className="flex h-full overflow-hidden rounded-sm"
                style={{ width: `${Math.max(w, 1)}%` }}
                title={`${r.name} : ${formatInt(r.reinscrits)} réinscrits (${pct}%) + ${formatInt(r.nouveaux)} nouveaux = ${formatInt(tot)}`}
              >
                <div className="h-full" style={{ width: `${reinsW}%`, background: REINS }} />
                <div className="h-full flex-1" style={{ background: NOUV }} />
              </div>
            </div>
            <span className="tnum w-[88px] flex-shrink-0 text-right text-caption text-neutral-600">
              <b className="text-neutral-900">{pct}%</b> réinscr.
            </span>
          </div>
        );
      })}
    </div>
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
