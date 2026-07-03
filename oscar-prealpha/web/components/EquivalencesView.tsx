"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Panel } from "./Card";
import { PageTitle } from "./PageTitle";

interface MappingRow {
  categorie: string;
  macro: string;
  sousSecteur: string;
  secteur: string;
}
interface MappingPayload {
  rows: MappingRow[];
  sectorOrder: string[];
  count: number;
  present: string[];
  unmapped: string[];
  csvPath?: string;
  editable?: boolean;
}

async function fetchMapping(): Promise<MappingPayload> {
  const res = await fetch("/api/mapping", { headers: { accept: "application/json" }, cache: "no-store" });
  if (!res.ok) throw new Error(`status ${res.status}`);
  return (await res.json()) as MappingPayload;
}

const SECTOR_COLOR: Record<string, string> = {
  "PROGRAMMÉS": "#FF8C00",
  "PLATEFORMES": "#3B82F6",
  "ECOLES": "#22C55E",
  "SUR MESURE": "#8B5CF6",
  "SOCIÉTÉS": "#EF4444",
  "NON RATTACHÉ": "#94A3B8",
};

function toCsv(rows: MappingRow[]): string {
  const head = "Catégorie,Macro-catégorie,Sous-secteur,Secteur";
  const esc = (s: string) => (/[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s);
  const body = rows.map((r) => [r.categorie, r.macro, r.sousSecteur, r.secteur].map(esc).join(","));
  return [head, ...body].join("\n");
}

export function EquivalencesView() {
  const { data, isLoading, isError } = useQuery({ queryKey: ["mapping"], queryFn: fetchMapping, staleTime: 60_000 });
  const [q, setQ] = useState("");
  const [sector, setSector] = useState<string>("");

  const rows = data?.rows ?? [];
  const sectors = data?.sectorOrder ?? [];
  const unmapped = data?.unmapped ?? [];

  const filtered = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return rows.filter((r) => {
      if (sector && r.secteur !== sector) return false;
      if (!needle) return true;
      return [r.categorie, r.macro, r.sousSecteur, r.secteur].some((v) => v.toLowerCase().includes(needle));
    });
  }, [rows, q, sector]);

  const download = () => {
    const blob = new Blob([toCsv(rows)], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "category_mapping.csv";
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-5">
      <PageTitle eyebrow="Paramètres" title="Équivalences catégories → secteurs">
        Correspondance de chaque catégorie de cours AEC vers sa macro-catégorie, son sous-secteur et son secteur OSCAR.
      </PageTitle>

      {/* Consultation seule : rappel du mode d'édition (FS Vercel en lecture seule). */}
      <div className="flex items-start gap-2 rounded-md border border-neutral-200 bg-neutral-50 px-3 py-2.5 text-caption text-neutral-600">
        <span className="mt-0.5 flex-shrink-0 font-semibold text-neutral-500">i</span>
        <span>
          Tableau en <b>lecture seule</b> ici (l'hébergement de production est en lecture seule). Pour <b>modifier</b> une
          équivalence : éditez <code className="rounded-xs bg-neutral-200 px-1 py-0.5">{data?.csvPath ?? "data/category_mapping.csv"}</code>
          {" "}(colonnes <code className="rounded-xs bg-neutral-200 px-1 py-0.5">Catégorie,Macro-catégorie,Sous-secteur,Secteur</code>),
          committez, et redéployez. Le fichier <b>surcharge</b> le mapping par défaut. Bouton « Exporter » ci-dessous pour partir du fichier actuel.
        </span>
      </div>

      {isLoading && <p className="text-body-sm text-neutral-500">Chargement du mapping…</p>}
      {isError && <p className="text-body-sm text-error">Impossible de charger le mapping (serveur indisponible).</p>}

      {!isLoading && !isError && (
        <>
          {unmapped.length > 0 && (
            <Panel title={`À rattacher · ${unmapped.length} catégorie(s) NON RATTACHÉ`} subtitle="Présentes dans les données mais absentes du mapping → à ajouter au CSV">
              <div className="flex flex-wrap gap-1.5">
                {unmapped.map((c) => (
                  <span key={c} className="inline-flex items-center gap-1.5 rounded-pill border border-neutral-300 bg-surface px-2.5 py-[3px] text-caption font-medium text-neutral-700">
                    <span className="h-2 w-2 rounded-full" style={{ background: SECTOR_COLOR["NON RATTACHÉ"] }} />
                    {c}
                  </span>
                ))}
              </div>
            </Panel>
          )}

          <div className="flex flex-wrap items-center gap-2.5">
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Rechercher une catégorie, un secteur…"
              className="min-w-[220px] flex-1 rounded-md border border-neutral-200 bg-surface px-3 py-1.5 text-body-sm text-neutral-800 outline-none focus:border-accent-400"
            />
            <div className="inline-flex flex-wrap gap-1 rounded-pill bg-neutral-100 p-[3px]">
              <button
                onClick={() => setSector("")}
                className={`rounded-pill px-3 py-1.5 text-body-sm font-medium transition-all ${sector === "" ? "bg-accent-500 text-white shadow-sm" : "text-neutral-600 hover:text-neutral-900"}`}
              >
                Tous
              </button>
              {sectors.map((s) => (
                <button
                  key={s}
                  onClick={() => setSector(s === sector ? "" : s)}
                  className={`rounded-pill px-3 py-1.5 text-body-sm font-medium transition-all ${sector === s ? "bg-accent-500 text-white shadow-sm" : "text-neutral-600 hover:text-neutral-900"}`}
                >
                  {s}
                </button>
              ))}
            </div>
            <button
              onClick={download}
              className="rounded-md border border-neutral-200 bg-surface px-3 py-1.5 text-body-sm font-medium text-neutral-600 transition-colors hover:border-accent-400 hover:text-accent-700"
            >
              Exporter CSV
            </button>
          </div>

          <Panel title="Tableau des équivalences" subtitle={`${filtered.length} / ${rows.length} catégories`}>
            <div className="thin-scroll max-h-[600px] overflow-auto rounded-md border border-neutral-200">
              <table className="w-full min-w-[720px] border-collapse text-body-sm">
                <thead>
                  <tr>
                    {["Catégorie (AEC)", "Macro-catégorie", "Sous-secteur", "Secteur"].map((h) => (
                      <th key={h} className="sticky top-0 z-10 border-b border-neutral-200 bg-neutral-50 px-3.5 py-2.5 text-left text-eyebrow font-semibold uppercase tracking-[0.06em] text-neutral-600">
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((r) => {
                    const na = r.secteur === "NON RATTACHÉ";
                    return (
                      <tr key={r.categorie} className={`even:bg-neutral-50 hover:bg-accent-50 ${na ? "bg-error-soft/40" : ""}`}>
                        <td className="px-3.5 py-2 font-medium text-neutral-800">{r.categorie}</td>
                        <td className="px-3.5 py-2 text-neutral-600">{r.macro}</td>
                        <td className="px-3.5 py-2 text-neutral-600">{r.sousSecteur}</td>
                        <td className="px-3.5 py-2">
                          <span className="inline-flex items-center gap-1.5 font-medium text-neutral-800">
                            <span className="h-2 w-2 rounded-full" style={{ background: SECTOR_COLOR[r.secteur] ?? "#94A3B8" }} />
                            {r.secteur}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                  {filtered.length === 0 && (
                    <tr>
                      <td colSpan={4} className="px-3.5 py-6 text-center text-body-sm text-neutral-500">Aucune catégorie ne correspond.</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </Panel>
        </>
      )}
    </div>
  );
}
