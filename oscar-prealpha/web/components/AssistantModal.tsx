"use client";

import { useState, useRef, useEffect } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { useFilters } from "@/lib/store";
import { useSnapshot } from "@/lib/useSnapshot";
import { IconClose, IconHistory, IconTrash, IconSend } from "./icons";
import { formatDec1, formatEur, formatInt } from "@/lib/format";
import type { Snapshot } from "@/lib/types";

interface Msg {
  role: "bot" | "user";
  text: string;
}

/** Rendu léger du markdown renvoyé par le LLM : **gras** (le reste — listes,
 *  sauts de ligne — passe via whitespace-pre-line). */
function renderRich(text: string) {
  return text.split(/(\*\*[^*]+\*\*)/g).map((seg, i) =>
    seg.startsWith("**") && seg.endsWith("**") ? (
      <strong key={i} className="font-semibold text-neutral-900">{seg.slice(2, -2)}</strong>
    ) : (
      <span key={i}>{seg}</span>
    ),
  );
}

const SUGGESTIONS = [
  "Classement des antennes par inscriptions",
  "Quel secteur génère le plus de recettes ?",
  "Combien d'élèves différents au total ?",
  "Taux de remplissage par antenne",
];

type Fmt = "int" | "eur" | "dec1";
const strip = (s: string) => s.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);
const fmtVal = (v: number, f: Fmt) => (f === "eur" ? formatEur(v) : f === "dec1" ? formatDec1(v) : formatInt(v));

// Indicateurs reconnus (ordre = priorité de détection : les libellés composés
// d'abord, ex. « heures-élèves » avant « heures »).
const INDICATORS: { match: string[]; key: string; label: string; fmt: Fmt }[] = [
  { match: ["heures-eleves", "heures eleves", "heures vendues", "heures etudiant"], key: "heures_eleves", label: "heures-élèves", fmt: "int" },
  { match: ["remplissage", "rempliss", "taux de rempl"], key: "remplissage", label: "taux de remplissage", fmt: "dec1" },
  { match: ["eleves differents", "eleve different", "etudiants differents", "distinct"], key: "eleves_differents", label: "élèves différents", fmt: "int" },
  { match: ["reinscr"], key: "reinscrits", label: "réinscrits", fmt: "int" },
  { match: ["nouveau", "nouvel inscrit", "nouvelle inscrit"], key: "nouveaux", label: "nouveaux inscrits", fmt: "int" },
  { match: ["heure", "qte heure"], key: "heures", label: "quantité d'heures", fmt: "int" },
  { match: ["recette", "chiffre", "revenu", "rentab"], key: "recettes", label: "recettes", fmt: "eur" },
  { match: ["cours"], key: "cours", label: "nombre de cours", fmt: "int" },
  { match: ["inscription", "inscrit"], key: "inscriptions", label: "inscriptions", fmt: "int" },
];

// Métriques que l'on n'a PAS dans les données Cours — refusées honnêtement.
const UNKNOWN: [string, string][] = [
  ["abandon", "taux d'abandon"], ["decroch", "décrochage"], ["retention", "rétention"],
  ["churn", "churn"], ["satisfaction", "satisfaction"], ["absent", "absentéisme"],
  ["reussite", "réussite"], ["echec", "échec"], ["note", "notes/résultats"],
  ["age moyen", "âge"], ["nationalit", "nationalité"], ["sexe", "sexe"], ["genre", "genre"],
];

const DISPO = "Indicateurs disponibles : inscriptions, élèves différents, cours, quantité d'heures, heures-élèves, recettes, taux de remplissage, nouveaux & réinscrits.";

/** Analyste local : répond à partir du snapshot chargé (périmètre filtré actuel).
 *  Détecte l'indicateur + la dimension (antenne/secteur) + l'agrégation, et
 *  refuse honnêtement les métriques absentes des données. */
function answer(q: string, snap: Snapshot): string {
  const ql = strip(q);
  // Match sur une limite de mot (évite « classe » dans « classement », etc.).
  const hit = (term: string) => new RegExp("\\b" + term.replace(/[.*+?^${}()|[\]\\-]/g, "\\$&")).test(ql);
  const hasIndicator = INDICATORS.some((d) => d.match.some((m) => hit(strip(m))));

  // Métrique inconnue (et pas d'indicateur valide détecté à côté).
  if (!hasIndicator) {
    const unk = UNKNOWN.find(([k]) => ql.includes(k));
    if (unk) {
      const profil = ["age moyen", "nationalit", "sexe", "genre"].some((k) => ql.includes(k));
      return `Je n'ai pas d'indicateur « ${unk[1]} » dans les données Cours. ${DISPO}${profil ? " Pour l'âge / la nationalité, voir les onglets « Profils »." : ""}`;
    }
  }

  const ind = INDICATORS.find((d) => d.match.some((m) => hit(strip(m)))) ?? INDICATORS[INDICATORS.length - 1];

  const yearTxt = (snap.filters.years && snap.filters.years.length ? snap.filters.years.join(", ") : String(snap.filters.year || "")) || "période filtrée";
  const scope = `(périmètre : ${yearTxt})`;

  const wantSector = ql.includes("secteur");
  const dimWord = wantSector ? "secteur" : "antenne";
  const rows = wantSector
    ? (snap.bySectorIndicator?.[ind.key] ?? []).map((r) => ({ name: r.label, value: r.value }))
    : (snap.byAntennaIndicator?.[ind.key] ?? []).map((r) => ({ name: r.code, value: r.value }));

  const wantList = /\bpar\b|chaque|classement|repartition|liste|toutes|tous|ventil/.test(ql);
  const wantWorst = /pire|moins|plus faible|plus bas|derniere?\b|au plus bas/.test(ql);
  const wantBest = /meilleur|top|plus haut|plus eleve|plus fort|premiere?\b|plus de|plus grand|le plus/.test(ql);
  const wantTotal = /total|combien|somme|au total|nombre total/.test(ql);

  const kpi = snap.kpis.find((k) => k.key === ind.key);
  const totalVal = kpi
    ? kpi.value
    : ind.key === "remplissage" || ind.key === "eleves_differents"
      ? null // non sommable sans le distinct global
      : rows.reduce((s, r) => s + r.value, 0);

  // Total demandé (et pas de classement/best/worst).
  if (wantTotal && !wantList && !wantBest && !wantWorst && totalVal != null) {
    return `${cap(ind.label)} ${scope} : ${fmtVal(totalVal, ind.fmt)}.`;
  }

  if (!rows.length) {
    if (totalVal != null) return `${cap(ind.label)} ${scope} : ${fmtVal(totalVal, ind.fmt)}.`;
    return `Pas de donnée « ${ind.label} » par ${dimWord} sur ce périmètre. ${DISPO}`;
  }

  const sorted = [...rows].sort((a, b) => b.value - a.value);

  if (wantList) {
    const lines = sorted.map((r, i) => `${i + 1}. ${r.name} — ${fmtVal(r.value, ind.fmt)}`).join("\n");
    const tot = totalVal != null ? `\nTotal IFI : ${fmtVal(totalVal, ind.fmt)}` : "";
    return `${cap(ind.label)} par ${dimWord} ${scope} :\n${lines}${tot}`;
  }
  if (wantWorst) {
    const w = sorted[sorted.length - 1];
    return `Plus faible ${ind.label} par ${dimWord} ${scope} : ${w.name} (${fmtVal(w.value, ind.fmt)}).`;
  }
  // Par défaut : le meilleur (« quelle antenne a le plus… »).
  const b = sorted[0];
  void wantBest;
  return `${cap(ind.label)} — en tête par ${dimWord} ${scope} : ${b.name} (${fmtVal(b.value, ind.fmt)}).`;
}

// Dictionnaire des indicateurs — donné au LLM pour qu'il sache CE QU'IL REGARDE
// (définition + unité), au lieu de deviner à partir des seuls libellés.
const DICTIONNAIRE: Record<string, string> = {
  inscriptions: "Nombre d'inscriptions à des cours (un élève peut compter plusieurs fois).",
  eleves_differents: "Élèves distincts (Code Client uniques) — non additif entre périmètres.",
  cours: "Nombre de cours (sessions) ouverts.",
  heures: "Qté d'heures enseignées.",
  heures_eleves: "Heures-élèves = heures vendues (heures × élèves).",
  remplissage: "Taux de remplissage = inscriptions / cours (élèves par cours).",
  recettes: "Recettes en euros.",
  nouveaux: "Nouveaux inscrits (première inscription).",
  reinscrits: "Réinscrits (déjà venus).",
  panier_inscr: "Panier moyen par inscription (recettes / inscriptions), en €.",
  panier_pers: "Panier moyen par personne (recettes / élèves différents), en €.",
};

/** Contexte data envoyé au LLM. Contient (1) le PÉRIMÈTRE exact filtré + les
 *  années disponibles, (2) un dictionnaire des indicateurs, (3) les totaux +
 *  ventilations, (4) le diagnostic des cours NON RATTACHÉ — pour que l'assistant
 *  comprenne précisément ce qu'il regarde. */
function buildContext(d: Snapshot) {
  const f = d.filters ?? ({} as Snapshot["filters"]);
  const nr = d.diagnostics?.nonRattache ?? [];
  return {
    perimetre: {
      annees: f.years ?? (f.year ? [f.year] : []),
      mode_annee: d.meta?.yearMode === "school" ? "scolaire (sept→août)" : "civil (année civile)",
      antennes: f.antennas,
      filtres_dimension: {
        secteurs: f.secteurs ?? [],
        sous_secteurs: f.sousSecteurs ?? [],
        macros: f.macros ?? [],
        categories: f.categories ?? [],
        niveaux: f.niveaux ?? [],
      },
      annees_disponibles: d.meta?.years ?? [],
    },
    dictionnaire: (d.indicators ?? [])
      .map((i) => ({ cle: i.key, libelle: i.label, definition: DICTIONNAIRE[i.key] ?? "" })),
    totaux_IFI: d.kpis.map((k) => ({ cle: k.key, libelle: k.label, valeur: k.value, variation: k.delta, variation_libelle: k.deltaLabel })),
    par_antenne: d.byAntennaIndicator,
    par_secteur: d.bySectorIndicator,
    evolution_par_annee: {
      annees: d.evolution.years,
      series: d.evolution.series.map((s) => ({ code: s.code, nom: s.name, metriques: s.metrics })),
    },
    // Ventilation fine du périmètre filtré : secteur, sous_secteur, macro,
    // categorie, niveau, format, tranche d'âge (avec recettes par ligne).
    ventilation_par_dimension: Object.fromEntries(
      Object.entries(d.breakdowns ?? {}).map(([dim, block]) => [
        dim,
        (block?.rows ?? []).map((r) => ({
          libelle: r.label,
          inscriptions: r.inscriptions,
          cours: r.cours,
          recettes: r.recettes,
          remplissage: r.remplissage,
        })),
      ]),
    ),
    // Cours non rattachés (catégorie vide/inconnue) présents dans le périmètre.
    diagnostics: {
      non_rattache: nr.map((c) => ({
        cours: c.nom, code: c.code, antenne: c.sede,
        annee: c.annee, periode: c.periode, categorie: c.categorie, raison: c.reason,
      })),
    },
  };
}

export function AssistantModal() {
  const open = useFilters((s) => s.aiOpen);
  const setOpen = useFilters((s) => s.setAiOpen);
  const { data } = useSnapshot();
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [pending, setPending] = useState(false);
  const bodyRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bodyRef.current?.scrollTo({ top: bodyRef.current.scrollHeight, behavior: "smooth" });
  }, [msgs, pending]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [setOpen]);

  async function ask(q: string) {
    if (!q.trim() || pending) return;
    // Historique de la conversation (avant ce message) pour les questions de
    // suivi (« en %age », « et pour 2023 ? »…).
    const history = msgs.slice(-10).map((m) => ({ role: m.role, content: m.text }));
    setMsgs((m) => [...m, { role: "user", text: q }]);
    setInput("");
    setPending(true);
    try {
      // 1) On tente le LLM (API Albert) avec le contexte data + l'historique.
      const res = await fetch("/api/assistant", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ question: q, context: buildContext(data), history }),
      });
      const j = await res.json().catch(() => null);
      const text = j?.ok && j.answer ? j.answer : answer(q, data); // 2) repli déterministe
      setMsgs((m) => [...m, { role: "bot", text }]);
    } catch {
      setMsgs((m) => [...m, { role: "bot", text: answer(q, data) }]);
    } finally {
      setPending(false);
    }
  }

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="fixed inset-0 z-[100] flex items-center justify-center bg-neutral-900/30 p-4 backdrop-blur-sm"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={() => setOpen(false)}
        >
          <motion.div
            className="flex max-h-[80vh] w-full max-w-[480px] flex-col overflow-hidden rounded-lg border border-neutral-200 bg-surface shadow-lg"
            initial={{ opacity: 0, scale: 0.96, y: 8 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: 8 }}
            transition={{ duration: 0.18, ease: [0.16, 1, 0.3, 1] }}
            onClick={(e) => e.stopPropagation()}
          >
            <header className="flex items-center justify-between border-b border-neutral-200 bg-neutral-50 px-4 py-3">
              <div className="flex items-center gap-3">
                <span className="grid h-8 w-8 place-items-center rounded-full bg-accent-500 text-[11px] font-semibold text-white">
                  AI
                </span>
                <div>
                  <b className="block text-body font-semibold leading-tight text-neutral-900">OSCAR AI</b>
                  <span className="text-[11px] text-neutral-500">Assistant data analyst</span>
                </div>
              </div>
              <div className="flex gap-0.5">
                <IconBtn label="historique"><IconHistory className="h-3.5 w-3.5" /></IconBtn>
                <IconBtn label="effacer" onClick={() => setMsgs([])}><IconTrash className="h-3.5 w-3.5" /></IconBtn>
                <IconBtn label="fermer" onClick={() => setOpen(false)}><IconClose className="h-3.5 w-3.5" /></IconBtn>
              </div>
            </header>

            <div ref={bodyRef} className="thin-scroll flex min-h-[220px] flex-1 flex-col gap-3 overflow-y-auto p-4 text-body-sm">
              <div className="max-w-[85%] self-start rounded-md rounded-bl-[2px] bg-neutral-50 px-3 py-2.5 text-neutral-800">
                Bonjour ! Posez-moi vos questions sur vos données. Par exemple :
              </div>
              {msgs.length === 0 && (
                <div className="flex max-w-[90%] flex-col gap-1.5 self-start">
                  {SUGGESTIONS.map((s) => (
                    <button
                      key={s}
                      onClick={() => ask(s)}
                      className="rounded-md border border-neutral-200 bg-surface px-2.5 py-1.5 text-left text-caption text-neutral-700 transition-colors hover:border-accent-500 hover:bg-accent-50 hover:text-accent-700"
                    >
                      {s}
                    </button>
                  ))}
                </div>
              )}
              {msgs.map((m, i) => (
                <div
                  key={i}
                  className={
                    m.role === "user"
                      ? "max-w-[85%] self-end whitespace-pre-line rounded-md rounded-br-[2px] bg-accent-50 px-3 py-2.5 text-neutral-900"
                      : "max-w-[85%] self-start whitespace-pre-line rounded-md rounded-bl-[2px] bg-neutral-50 px-3 py-2.5 text-neutral-800"
                  }
                >
                  {m.role === "bot" ? renderRich(m.text) : m.text}
                </div>
              ))}
              {pending && (
                <div className="max-w-[85%] self-start rounded-md rounded-bl-[2px] bg-neutral-50 px-3 py-2.5 text-neutral-500">
                  <span className="inline-flex gap-1">
                    <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-neutral-400 [animation-delay:-0.2s]" />
                    <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-neutral-400 [animation-delay:-0.1s]" />
                    <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-neutral-400" />
                  </span>
                </div>
              )}
            </div>

            <form
              onSubmit={(e) => {
                e.preventDefault();
                ask(input);
              }}
              className="flex gap-1.5 border-t border-neutral-200 bg-neutral-50 px-4 py-3"
            >
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                disabled={pending}
                placeholder={pending ? "OSCAR réfléchit…" : "Posez votre question…"}
                className="flex-1 rounded-md border border-neutral-200 bg-surface px-3 py-2 text-body-sm text-neutral-900 outline-none transition-shadow focus:border-accent-500 focus:shadow-focus disabled:opacity-60"
              />
              <button
                type="submit"
                aria-label="envoyer"
                disabled={pending}
                className="grid h-[34px] w-[34px] place-items-center rounded-full bg-accent-500 text-white transition-colors hover:bg-accent-600 disabled:opacity-50"
              >
                <IconSend className="h-3.5 w-3.5" />
              </button>
            </form>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

function IconBtn({
  children,
  label,
  onClick,
}: {
  children: React.ReactNode;
  label: string;
  onClick?: () => void;
}) {
  return (
    <button
      aria-label={label}
      onClick={onClick}
      className="grid h-[30px] w-[30px] place-items-center rounded-sm text-neutral-500 transition-colors hover:bg-neutral-100 hover:text-neutral-800"
    >
      {children}
    </button>
  );
}
