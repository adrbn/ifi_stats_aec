"use client";

import { motion } from "framer-motion";
import { type DomainKpi, fmtKpi } from "@/lib/domain";

export function StatCards({ kpis }: { kpis: DomainKpi[] }) {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-6">
      {kpis.map((k, i) => (
        <motion.div
          key={k.key}
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.24, delay: i * 0.03, ease: [0.16, 1, 0.3, 1] }}
          className="flex flex-col gap-1.5 rounded-md border border-neutral-200 bg-surface p-4 transition-[border-color,box-shadow] hover:border-neutral-300 hover:shadow-md"
        >
          <div className="text-eyebrow font-semibold uppercase text-neutral-500">{k.label}</div>
          <div className="tnum text-[22px] font-bold leading-none text-neutral-900">
            {fmtKpi(k.value, k.format)}
          </div>
        </motion.div>
      ))}
    </div>
  );
}

export function DomainUnavailable({ title, reason }: { title: string; reason?: string }) {
  return (
    <div className="flex items-start gap-3 rounded-md border-l-[3px] border-warning bg-warning-soft px-4 py-3 text-body-sm">
      <svg viewBox="0 0 16 16" className="mt-0.5 h-[18px] w-[18px] flex-shrink-0 text-warning" fill="none" stroke="currentColor" strokeWidth={1.5}>
        <path d="M8 2l7 12H1z" strokeLinejoin="round" />
        <path d="M8 7v3M8 12v.5" strokeWidth={2} strokeLinecap="round" />
      </svg>
      <div>
        <b className="block font-semibold text-neutral-900">{title} — export non chargé</b>
        <span className="text-neutral-700">
          Cette vue a besoin de son fichier source (comme OSCAR Online). {reason ? `(${reason})` : ""} Déposez l'export
          correspondant dans <code className="rounded-xs bg-neutral-100 px-1">data/</code> puis relancez le backend.
        </span>
      </div>
    </div>
  );
}
