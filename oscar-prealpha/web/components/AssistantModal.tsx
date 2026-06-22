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

export function AssistantModal() {
  const open = useFilters((s) => s.aiOpen);
  const setOpen = useFilters((s) => s.setAiOpen);
  const { data } = useSnapshot();
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const bodyRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bodyRef.current?.scrollTo({ top: bodyRef.current.scrollHeight, behavior: "smooth" });
  }, [msgs]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [setOpen]);

  function ask(q: string) {
    if (!q.trim()) return;
    setMsgs((m) => [...m, { role: "user", text: q }, { role: "bot", text: answer(q, data) }]);
    setInput("");
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
                  {m.text}
                </div>
              ))}
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
                placeholder="Posez votre question…"
                className="flex-1 rounded-md border border-neutral-200 bg-surface px-3 py-2 text-body-sm text-neutral-900 outline-none transition-shadow focus:border-accent-500 focus:shadow-focus"
              />
              <button
                type="submit"
                aria-label="envoyer"
                className="grid h-[34px] w-[34px] place-items-center rounded-full bg-accent-500 text-white transition-colors hover:bg-accent-600"
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
