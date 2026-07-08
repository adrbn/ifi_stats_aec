"use client";

import { useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import type { NonRattacheCourse } from "@/lib/types";
import { IconCheck } from "./icons";

interface MappingLite {
  rows?: { categorie: string }[];
  editable?: boolean;
}

async function fetchMappingLite(): Promise<MappingLite> {
  const res = await fetch("/api/mapping", { headers: { accept: "application/json" }, cache: "no-store" });
  if (!res.ok) throw new Error(`status ${res.status}`);
  return (await res.json()) as MappingLite;
}

/** Diagnostic « NON RATTACHÉ » : liste les cours du périmètre dont le secteur
 *  n'a pas pu être déterminé (catégorie AEC vide, ou absente du tableau de
 *  correspondances), avec nom du cours, antenne, période et RAISON. Quand
 *  l'édition est possible, on peut rattacher chaque cours à une catégorie
 *  (assignation Code cours → catégorie, appliquée en temps réel). */
export function NonRattacheDiag({ rows }: { rows: NonRattacheCourse[] }) {
  const qc = useQueryClient();
  const [open, setOpen] = useState(true);
  const { data: mapping } = useQuery({ queryKey: ["mapping"], queryFn: fetchMappingLite, staleTime: 60_000 });
  const editable = !!mapping?.editable;
  const categories = useMemo(
    () => Array.from(new Set((mapping?.rows ?? []).map((r) => r.categorie))).sort((a, b) => a.localeCompare(b, "fr")),
    [mapping?.rows],
  );

  const [sel, setSel] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState<string | null>(null); // code en cours
  const [err, setErr] = useState<string | null>(null);

  if (!rows.length) return null;

  async function attach(code: string) {
    const categorie = (sel[code] ?? "").trim();
    if (!categorie) {
      setErr("Choisissez une catégorie.");
      return;
    }
    setBusy(code);
    setErr(null);
    try {
      const res = await fetch("/api/course-mapping", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ action: "upsert", code, categorie }),
      });
      const j = await res.json().catch(() => null);
      if (!res.ok || !j?.ok) {
        setErr(j?.message || `Échec (${res.status})`);
        return;
      }
      // Le cours change de secteur et quitte le diagnostic → on rafraîchit tout.
      await qc.invalidateQueries({ queryKey: ["cours"] });
      await qc.invalidateQueries({ queryKey: ["mapping"] });
    } catch {
      setErr("Erreur réseau");
    } finally {
      setBusy(null);
    }
  }

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
          {err && <p className="px-2 py-1.5 text-caption text-error">{err}</p>}
          <div className="overflow-x-auto">
            <table className="w-full min-w-[640px] border-collapse text-body-sm">
              <thead>
                <tr>
                  {["Cours", "Antenne", "Période", "Catégorie AEC", "Raison", ...(editable ? ["Rattacher à…"] : [])].map((h) => (
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
                    {editable && (
                      <td className="px-3 py-2">
                        <div className="flex items-center gap-1.5">
                          <input
                            list="nr-cat-opts"
                            value={sel[r.code] ?? ""}
                            onChange={(e) => setSel((s) => ({ ...s, [r.code]: e.target.value }))}
                            placeholder="Catégorie…"
                            className="w-[190px] rounded-sm border border-neutral-300 bg-surface px-2 py-1 text-body-sm text-neutral-900 outline-none focus:border-accent-500"
                          />
                          <button
                            onClick={() => attach(r.code)}
                            disabled={busy === r.code || !(sel[r.code] ?? "").trim()}
                            title="Rattacher ce cours à cette catégorie"
                            className="grid h-[28px] w-[28px] place-items-center rounded-sm bg-accent-500 text-white transition-colors hover:bg-accent-600 disabled:opacity-40"
                          >
                            <IconCheck className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {editable && (
            <>
              <datalist id="nr-cat-opts">
                {categories.map((c) => (
                  <option key={c} value={c} />
                ))}
              </datalist>
              <p className="px-3 py-2 text-caption text-neutral-500">
                Rattacher assigne la catégorie au cours (par code) — effet immédiat, réversible. À privilégier en dépannage&nbsp;;
                la correction pérenne se fait sur la fiche du cours dans AEC.
              </p>
            </>
          )}
        </div>
      )}
    </div>
  );
}
