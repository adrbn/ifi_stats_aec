"use client";

import { useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Panel } from "./Card";
import { PageTitle } from "./PageTitle";
import { IconArrowUp, IconArrowDown, IconCheck, IconClose, IconTrash } from "./icons";

interface MappingRow {
  categorie: string;
  macro: string;
  sousSecteur: string;
  secteur: string;
  override?: boolean;
}
interface MappingPayload {
  rows: MappingRow[];
  sectorOrder: string[];
  sousSecteurOrder?: string[];
  count: number;
  present: string[];
  unmapped: string[];
  csvPath?: string;
  editable?: boolean;
  storage?: string;
  overridesCount?: number;
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

type SortKey = "categorie" | "macro" | "sousSecteur" | "secteur";
const COLUMNS: { key: SortKey; label: string }[] = [
  { key: "categorie", label: "Catégorie (AEC)" },
  { key: "macro", label: "Macro-catégorie" },
  { key: "sousSecteur", label: "Sous-secteur" },
  { key: "secteur", label: "Secteur" },
];

function toCsv(rows: MappingRow[]): string {
  const head = "Catégorie,Macro-catégorie,Sous-secteur,Secteur";
  const esc = (s: string) => (/[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s);
  const body = rows.map((r) => [r.categorie, r.macro, r.sousSecteur, r.secteur].map(esc).join(","));
  return [head, ...body].join("\n");
}

interface Draft {
  categorie: string;
  macro: string;
  sousSecteur: string;
  secteur: string;
  isNew: boolean;
}

export function EquivalencesView() {
  const qc = useQueryClient();
  const { data, isLoading, isError } = useQuery({ queryKey: ["mapping"], queryFn: fetchMapping, staleTime: 60_000 });
  const [q, setQ] = useState("");
  const [sector, setSector] = useState<string>("");
  const [sortKey, setSortKey] = useState<SortKey>("secteur");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");

  // Édition
  const [draft, setDraft] = useState<Draft | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const rows = data?.rows ?? [];
  const sectors = data?.sectorOrder ?? [];
  const unmapped = data?.unmapped ?? [];
  const editable = !!data?.editable;

  // Suggestions (datalists) pour l'édition.
  const macroOptions = useMemo(() => Array.from(new Set(rows.map((r) => r.macro).filter(Boolean))).sort(), [rows]);
  const sousOptions = useMemo(
    () => Array.from(new Set([...(data?.sousSecteurOrder ?? []), ...rows.map((r) => r.sousSecteur)].filter(Boolean))).sort(),
    [rows, data?.sousSecteurOrder],
  );
  const sectorChoices = useMemo(
    () => sectors.filter((s) => s !== "NON RATTACHÉ"),
    [sectors],
  );

  const filtered = useMemo(() => {
    const needle = q.trim().toLowerCase();
    const out = rows.filter((r) => {
      if (sector && r.secteur !== sector) return false;
      if (!needle) return true;
      return [r.categorie, r.macro, r.sousSecteur, r.secteur].some((v) => v.toLowerCase().includes(needle));
    });
    const dir = sortDir === "asc" ? 1 : -1;
    return out.sort((a, b) =>
      dir * a[sortKey].localeCompare(b[sortKey], "fr", { sensitivity: "base", numeric: true }),
    );
  }, [rows, q, sector, sortKey, sortDir]);

  function toggleSort(key: SortKey) {
    if (key === sortKey) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    else {
      setSortKey(key);
      setSortDir("asc");
    }
  }

  const download = () => {
    const blob = new Blob([toCsv(rows)], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "category_mapping.csv";
    a.click();
    URL.revokeObjectURL(url);
  };

  // --- Mutations (POST /api/mapping) : appliquées en temps réel côté serveur ---
  async function submit(body: Record<string, unknown>): Promise<boolean> {
    setBusy(true);
    setErr(null);
    try {
      const res = await fetch("/api/mapping", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(body),
      });
      const j = await res.json().catch(() => null);
      if (!res.ok || !j?.ok) {
        setErr(j?.message || `Échec (${res.status})`);
        return false;
      }
      // Rafraîchit le mapping ET les données Cours (secteurs recalculés en direct).
      await qc.invalidateQueries({ queryKey: ["mapping"] });
      await qc.invalidateQueries({ queryKey: ["cours"] });
      return true;
    } catch {
      setErr("Erreur réseau");
      return false;
    } finally {
      setBusy(false);
    }
  }

  async function saveDraft() {
    if (!draft) return;
    if (!draft.categorie.trim() || !draft.secteur.trim()) {
      setErr("Catégorie et secteur sont obligatoires.");
      return;
    }
    const ok = await submit({
      action: "upsert",
      categorie: draft.categorie,
      macro: draft.macro,
      sousSecteur: draft.sousSecteur,
      secteur: draft.secteur,
    });
    if (ok) setDraft(null);
  }

  async function resetRow(categorie: string) {
    await submit({ action: "delete", categorie });
  }

  const startEdit = (r: MappingRow) =>
    setDraft({ categorie: r.categorie, macro: r.macro, sousSecteur: r.sousSecteur, secteur: r.secteur, isNew: false });
  const startAdd = (categorie: string) =>
    setDraft({ categorie, macro: "", sousSecteur: "", secteur: sectorChoices[0] ?? "PROGRAMMÉS", isNew: true });

  return (
    <div className="space-y-5">
      <PageTitle eyebrow="Paramètres" title="Équivalences catégories → secteurs">
        Correspondance de chaque catégorie de cours AEC vers sa macro-catégorie, son sous-secteur et son secteur OSCAR.
      </PageTitle>

      {/* Bandeau mode d'édition / persistance. */}
      {editable ? (
        <div className="flex items-start gap-2 rounded-md border border-accent-100 bg-accent-50 px-3 py-2.5 text-caption text-neutral-700">
          <span className="mt-0.5 flex-shrink-0 font-semibold text-accent-600">✎</span>
          <span>
            <b>Édition activée.</b> Les modifications s'appliquent <b>en temps réel</b> (les secteurs sont recalculés
            aussitôt) et sont <b>persistées</b>
            {data?.storage === "kv" ? " sur le magasin KV (durable, survit aux redéploiements)" : " dans un fichier local (dev)"}.
            {typeof data?.overridesCount === "number" && data.overridesCount > 0 && (
              <> {data.overridesCount} correspondance(s) personnalisée(s).</>
            )}
          </span>
        </div>
      ) : (
        <div className="flex items-start gap-2 rounded-md border border-neutral-200 bg-neutral-50 px-3 py-2.5 text-caption text-neutral-600">
          <span className="mt-0.5 flex-shrink-0 font-semibold text-neutral-500">i</span>
          <span>
            Tableau en <b>lecture seule</b> (aucune persistance configurée sur cet hébergement). Pour activer l'édition,
            configurez un magasin KV (variables <code className="rounded-xs bg-neutral-200 px-1 py-0.5">KV_REST_API_URL</code>{" "}
            / <code className="rounded-xs bg-neutral-200 px-1 py-0.5">KV_REST_API_TOKEN</code>). En attendant, éditez{" "}
            <code className="rounded-xs bg-neutral-200 px-1 py-0.5">{data?.csvPath ?? "data/category_mapping.csv"}</code>, committez et redéployez.
          </span>
        </div>
      )}

      {isLoading && <p className="text-body-sm text-neutral-500">Chargement du mapping…</p>}
      {isError && <p className="text-body-sm text-error">Impossible de charger le mapping (serveur indisponible).</p>}
      {err && (
        <div className="flex items-center justify-between rounded-md border border-error/40 bg-error-soft/60 px-3 py-2 text-body-sm text-error">
          <span>{err}</span>
          <button onClick={() => setErr(null)} className="text-error/70 hover:text-error"><IconClose className="h-3.5 w-3.5" /></button>
        </div>
      )}

      {!isLoading && !isError && (
        <>
          {unmapped.length > 0 && (
            <Panel
              title={`À rattacher · ${unmapped.length} catégorie(s) NON RATTACHÉ`}
              subtitle={editable ? "Cliquez une catégorie pour la rattacher à un secteur" : "Présentes dans les données mais absentes du mapping → à ajouter"}
            >
              <div className="flex flex-wrap gap-1.5">
                {unmapped.map((c) =>
                  editable ? (
                    <button
                      key={c}
                      onClick={() => startAdd(c)}
                      className="inline-flex items-center gap-1.5 rounded-pill border border-neutral-300 bg-surface px-2.5 py-[3px] text-caption font-medium text-neutral-700 transition-colors hover:border-accent-500 hover:bg-accent-50 hover:text-accent-700"
                    >
                      <span className="h-2 w-2 rounded-full" style={{ background: SECTOR_COLOR["NON RATTACHÉ"] }} />
                      {c}
                      <span className="text-accent-600">+</span>
                    </button>
                  ) : (
                    <span key={c} className="inline-flex items-center gap-1.5 rounded-pill border border-neutral-300 bg-surface px-2.5 py-[3px] text-caption font-medium text-neutral-700">
                      <span className="h-2 w-2 rounded-full" style={{ background: SECTOR_COLOR["NON RATTACHÉ"] }} />
                      {c}
                    </span>
                  ),
                )}
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

          <Panel title="Tableau des équivalences" subtitle={`${filtered.length} / ${rows.length} catégories · cliquez un en-tête pour trier`}>
            <div className="thin-scroll max-h-[600px] overflow-auto rounded-md border border-neutral-200">
              <table className="w-full min-w-[760px] border-collapse text-body-sm">
                <thead>
                  <tr>
                    {COLUMNS.map((c) => {
                      const active = sortKey === c.key;
                      return (
                        <th key={c.key} className="sticky top-0 z-10 border-b border-neutral-200 bg-neutral-50 px-3.5 py-2.5 text-left text-eyebrow font-semibold uppercase tracking-[0.06em] text-neutral-600">
                          <button
                            onClick={() => toggleSort(c.key)}
                            className={`inline-flex items-center gap-1 transition-colors hover:text-accent-700 ${active ? "text-accent-700" : ""}`}
                          >
                            {c.label}
                            {active ? (
                              sortDir === "asc" ? <IconArrowUp className="h-3 w-3" /> : <IconArrowDown className="h-3 w-3" />
                            ) : (
                              <span className="text-neutral-300">↕</span>
                            )}
                          </button>
                        </th>
                      );
                    })}
                    {editable && (
                      <th className="sticky top-0 z-10 border-b border-neutral-200 bg-neutral-50 px-3.5 py-2.5 text-right text-eyebrow font-semibold uppercase tracking-[0.06em] text-neutral-600">
                        Actions
                      </th>
                    )}
                  </tr>
                </thead>
                <tbody>
                  {/* Éditeur d'ajout (nouvelle correspondance) en tête de tableau. */}
                  {draft?.isNew && (
                    <EditorRow
                      draft={draft}
                      setDraft={setDraft}
                      onSave={saveDraft}
                      onCancel={() => setDraft(null)}
                      busy={busy}
                      sectorChoices={sectorChoices}
                      macroOptions={macroOptions}
                      sousOptions={sousOptions}
                      lockCategorie
                    />
                  )}

                  {filtered.map((r) => {
                    const editing = draft && !draft.isNew && draft.categorie === r.categorie;
                    if (editing) {
                      return (
                        <EditorRow
                          key={r.categorie}
                          draft={draft}
                          setDraft={setDraft}
                          onSave={saveDraft}
                          onCancel={() => setDraft(null)}
                          busy={busy}
                          sectorChoices={sectorChoices}
                          macroOptions={macroOptions}
                          sousOptions={sousOptions}
                          lockCategorie
                        />
                      );
                    }
                    const na = r.secteur === "NON RATTACHÉ";
                    return (
                      <tr key={r.categorie} className={`even:bg-neutral-50 hover:bg-accent-50 ${na ? "bg-error-soft/40" : ""}`}>
                        <td className="px-3.5 py-2 font-medium text-neutral-800">
                          <span className="inline-flex items-center gap-1.5">
                            {r.categorie}
                            {r.override && (
                              <span className="rounded-xs bg-accent-100 px-1 py-0.5 text-[10px] font-semibold uppercase text-accent-700" title="Correspondance personnalisée">
                                perso
                              </span>
                            )}
                          </span>
                        </td>
                        <td className="px-3.5 py-2 text-neutral-600">{r.macro}</td>
                        <td className="px-3.5 py-2 text-neutral-600">{r.sousSecteur}</td>
                        <td className="px-3.5 py-2">
                          <span className="inline-flex items-center gap-1.5 font-medium text-neutral-800">
                            <span className="h-2 w-2 rounded-full" style={{ background: SECTOR_COLOR[r.secteur] ?? "#94A3B8" }} />
                            {r.secteur}
                          </span>
                        </td>
                        {editable && (
                          <td className="px-3.5 py-2 text-right">
                            <div className="inline-flex gap-1">
                              <button
                                onClick={() => startEdit(r)}
                                disabled={busy}
                                className="rounded-sm border border-neutral-200 px-2 py-1 text-caption font-medium text-neutral-600 transition-colors hover:border-accent-400 hover:text-accent-700 disabled:opacity-50"
                              >
                                Éditer
                              </button>
                              {r.override && (
                                <button
                                  onClick={() => resetRow(r.categorie)}
                                  disabled={busy}
                                  title="Réinitialiser (retour au mapping par défaut)"
                                  className="grid h-[26px] w-[26px] place-items-center rounded-sm border border-neutral-200 text-neutral-500 transition-colors hover:border-error/50 hover:text-error disabled:opacity-50"
                                >
                                  <IconTrash className="h-3.5 w-3.5" />
                                </button>
                              )}
                            </div>
                          </td>
                        )}
                      </tr>
                    );
                  })}
                  {filtered.length === 0 && !draft?.isNew && (
                    <tr>
                      <td colSpan={editable ? 5 : 4} className="px-3.5 py-6 text-center text-body-sm text-neutral-500">Aucune catégorie ne correspond.</td>
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

/** Ligne d'édition (ajout ou modification) — inputs macro/sous-secteur (avec
 *  suggestions) + select secteur, boutons Enregistrer / Annuler. */
function EditorRow({
  draft,
  setDraft,
  onSave,
  onCancel,
  busy,
  sectorChoices,
  macroOptions,
  sousOptions,
  lockCategorie,
}: {
  draft: Draft;
  setDraft: (d: Draft) => void;
  onSave: () => void;
  onCancel: () => void;
  busy: boolean;
  sectorChoices: string[];
  macroOptions: string[];
  sousOptions: string[];
  lockCategorie: boolean;
}) {
  const inputCls =
    "w-full rounded-sm border border-neutral-300 bg-surface px-2 py-1 text-body-sm text-neutral-900 outline-none focus:border-accent-500";
  return (
    <tr className="bg-accent-50/60">
      <td className="px-3.5 py-2 font-medium text-neutral-800">
        {lockCategorie ? (
          <span>{draft.categorie}</span>
        ) : (
          <input className={inputCls} value={draft.categorie} onChange={(e) => setDraft({ ...draft, categorie: e.target.value })} />
        )}
      </td>
      <td className="px-3.5 py-2">
        <input list="macro-opts" className={inputCls} value={draft.macro} placeholder="Macro-catégorie" onChange={(e) => setDraft({ ...draft, macro: e.target.value })} />
        <datalist id="macro-opts">{macroOptions.map((m) => <option key={m} value={m} />)}</datalist>
      </td>
      <td className="px-3.5 py-2">
        <input list="sous-opts" className={inputCls} value={draft.sousSecteur} placeholder="Sous-secteur" onChange={(e) => setDraft({ ...draft, sousSecteur: e.target.value })} />
        <datalist id="sous-opts">{sousOptions.map((s) => <option key={s} value={s} />)}</datalist>
      </td>
      <td className="px-3.5 py-2">
        <select className={inputCls} value={draft.secteur} onChange={(e) => setDraft({ ...draft, secteur: e.target.value })}>
          {!sectorChoices.includes(draft.secteur) && draft.secteur && <option value={draft.secteur}>{draft.secteur}</option>}
          {sectorChoices.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
      </td>
      <td className="px-3.5 py-2 text-right">
        <div className="inline-flex gap-1">
          <button
            onClick={onSave}
            disabled={busy}
            className="grid h-[26px] w-[26px] place-items-center rounded-sm bg-accent-500 text-white transition-colors hover:bg-accent-600 disabled:opacity-50"
            title="Enregistrer"
          >
            <IconCheck className="h-3.5 w-3.5" />
          </button>
          <button
            onClick={onCancel}
            disabled={busy}
            className="grid h-[26px] w-[26px] place-items-center rounded-sm border border-neutral-200 text-neutral-500 transition-colors hover:text-neutral-800 disabled:opacity-50"
            title="Annuler"
          >
            <IconClose className="h-3.5 w-3.5" />
          </button>
        </div>
      </td>
    </tr>
  );
}
