"use client";

import { motion } from "framer-motion";
import type { Kpi } from "@/lib/types";
import { formatKpi, formatDelta, formatEurCompact } from "@/lib/format";
import { useConfidential } from "@/lib/confidential";
import { IconArrowUp, IconArrowDown } from "./icons";

export function KpiCard({ kpi, index = 0 }: { kpi: Kpi; index?: number }) {
  // Euros en format compact (k€/M€) sur les cartes : évite le débordement du « € »
  // dans les cartes étroites quand le montant a 6 chiffres (ex. recettes < 1 M€).
  const value = kpi.format === "eur" ? formatEurCompact(kpi.value) : formatKpi(kpi.value, kpi.format);
  const dir = kpi.delta == null ? "flat" : kpi.delta > 0 ? "up" : kpi.delta < 0 ? "down" : "flat";

  const deltaStyles =
    dir === "up"
      ? "text-success bg-success-soft"
      : dir === "down"
        ? "text-error bg-error-soft"
        : "text-neutral-500 bg-neutral-100";

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.24, delay: index * 0.04, ease: [0.16, 1, 0.3, 1] }}
      className="group flex flex-col gap-2 rounded-md border border-neutral-200 bg-surface p-4 transition-[border-color,box-shadow] duration-150 ease-out-soft hover:border-neutral-300 hover:shadow-md"
    >
      <div className="min-h-[2.4em] text-eyebrow font-semibold uppercase leading-tight text-neutral-500">{kpi.label}</div>
      <div className="tnum text-display font-bold leading-none text-neutral-900">{value}</div>
      {kpi.delta != null && (
        <div className="mt-auto flex flex-col gap-1">
          <span className={`tnum inline-flex w-max items-center gap-1 rounded-xs px-2 py-0.5 text-caption font-semibold ${deltaStyles}`}>
            {dir === "up" && <IconArrowUp className="h-2.5 w-2.5" />}
            {dir === "down" && <IconArrowDown className="h-2.5 w-2.5" />}
            {dir === "flat" ? "— " : ""}
            {formatDelta(kpi.delta, kpi.format)}
          </span>
          {kpi.deltaLabel && dir !== "flat" && (
            <span className="text-caption font-medium text-neutral-400">{kpi.deltaLabel}</span>
          )}
        </div>
      )}
    </motion.div>
  );
}

// Nombre de colonnes (à lg/xl) selon le nombre de tuiles VISIBLES, pour que les
// tuiles restantes remplissent la ligne quand des KPI sont masqués (mode
// confidentiel) — au lieu de laisser des trous dans une grille figée à 9.
// Classes écrites en toutes lettres (pas d'interpolation) → conservées par Tailwind.
const COLS_BY_COUNT: Record<number, string> = {
  1: "sm:grid-cols-1 lg:grid-cols-1",
  2: "sm:grid-cols-2 lg:grid-cols-2",
  3: "sm:grid-cols-3 lg:grid-cols-3",
  4: "sm:grid-cols-2 lg:grid-cols-4",
  5: "sm:grid-cols-3 lg:grid-cols-5",
  6: "sm:grid-cols-3 lg:grid-cols-6",
  7: "sm:grid-cols-4 lg:grid-cols-4 xl:grid-cols-7",
  8: "sm:grid-cols-4 lg:grid-cols-4 xl:grid-cols-8",
  9: "sm:grid-cols-3 lg:grid-cols-5 xl:grid-cols-9",
};

export function KpiRow({ kpis }: { kpis: Kpi[] }) {
  // Mode confidentiel : on retire les KPI de recettes (recettes + paniers).
  const { filterKeyed } = useConfidential();
  const visible = filterKeyed(kpis);
  const cols = COLS_BY_COUNT[visible.length] ?? COLS_BY_COUNT[9];
  return (
    <div className={`grid grid-cols-2 gap-3 ${cols}`}>
      {visible.map((k, i) => (
        <KpiCard key={k.key} kpi={k} index={i} />
      ))}
    </div>
  );
}
