"use client";

import { motion } from "framer-motion";
import type { Kpi } from "@/lib/types";
import { formatKpi, formatDelta } from "@/lib/format";
import { IconArrowUp, IconArrowDown } from "./icons";

export function KpiCard({ kpi, index = 0 }: { kpi: Kpi; index?: number }) {
  const value = formatKpi(kpi.value, kpi.format);
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
      <div className="text-eyebrow font-semibold uppercase text-neutral-500">{kpi.label}</div>
      <div className="tnum text-display font-bold leading-none text-neutral-900">{value}</div>
      {kpi.delta != null && (
        <div className={`tnum inline-flex w-max items-center gap-1 rounded-xs px-2 py-0.5 text-caption font-semibold ${deltaStyles}`}>
          {dir === "up" && <IconArrowUp className="h-2.5 w-2.5" />}
          {dir === "down" && <IconArrowDown className="h-2.5 w-2.5" />}
          {dir === "flat" ? "— " : ""}
          {formatDelta(kpi.delta, kpi.format)}
          {kpi.deltaLabel && dir !== "flat" && (
            <span className="font-medium opacity-70">{kpi.deltaLabel}</span>
          )}
        </div>
      )}
    </motion.div>
  );
}

export function KpiRow({ kpis }: { kpis: Kpi[] }) {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-7">
      {kpis.map((k, i) => (
        <KpiCard key={k.key} kpi={k} index={i} />
      ))}
    </div>
  );
}
