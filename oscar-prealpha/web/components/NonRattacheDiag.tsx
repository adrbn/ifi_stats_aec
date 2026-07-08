"use client";

import { useState } from "react";
import type { NonRattacheCourse } from "@/lib/types";

/** Diagnostic « NON RATTACHÉ » : liste les cours du périmètre dont le secteur
 *  n'a pas pu être déterminé (catégorie AEC vide, ou absente du tableau de
 *  correspondances), avec nom du cours, antenne, période et RAISON — pour
 *  comprendre depuis OSCAR l'origine de l'anomalie (souvent une saisie AEC
 *  incomplète) et savoir comment la corriger. */
export function NonRattacheDiag({ rows }: { rows: NonRattacheCourse[] }) {
  const [open, setOpen] = useState(true);
  if (!rows.length) return null;

  return (
    <div className="rounded-md border border-warning/40 bg-warning-soft/50">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left"
      >
        <span className="flex items-center gap-2.5">
          <span className="grid h-6 w-6 flex-shrink-0 place-items-center rounded-full bg-warning text-[13px] font-bold text-white">
            !
          </span>
          <span className="text-body-sm font-semibold text-neutral-800">
            {rows.length} cours « NON RATTACHÉ » sur ce périmètre
          </span>
          <span className="text-caption text-neutral-500">— pourquoi&nbsp;?</span>
        </span>
        <span className="text-caption font-medium text-neutral-500">{open ? "Masquer" : "Détailler"}</span>
      </button>

      {open && (
        <div className="border-t border-warning/30 px-2 pb-2 pt-1">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[640px] border-collapse text-body-sm">
              <thead>
                <tr>
                  {["Cours", "Antenne", "Période", "Catégorie AEC", "Raison"].map((h) => (
                    <th
                      key={h}
                      className="px-3 py-2 text-left text-eyebrow font-semibold uppercase tracking-[0.06em] text-neutral-500"
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map((r, i) => (
                  <tr key={`${r.code}-${i}`} className="border-t border-warning/20 align-top">
                    <td className="px-3 py-2">
                      <span className="block font-medium text-neutral-800">{r.nom || "—"}</span>
                      {r.code && <span className="block text-caption text-neutral-500">{r.code}</span>}
                    </td>
                    <td className="whitespace-nowrap px-3 py-2 text-neutral-700">{r.sede || "—"}</td>
                    <td className="whitespace-nowrap px-3 py-2 text-neutral-700">
                      {r.periode || (r.annee != null ? String(r.annee) : "—")}
                    </td>
                    <td className="px-3 py-2">
                      {r.categorieVide ? (
                        <span className="rounded-xs bg-error-soft px-1.5 py-0.5 text-caption font-medium text-error">
                          (vide)
                        </span>
                      ) : (
                        <span className="text-neutral-700">{r.categorie}</span>
                      )}
                    </td>
                    <td className="px-3 py-2 text-neutral-600">{r.reason}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
