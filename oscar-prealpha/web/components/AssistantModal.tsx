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
  "Quelle antenne a le meilleur taux de remplissage ?",
  "Quel secteur est le plus rentable ?",
  "Total des inscriptions cette année ?",
];

/** Lightweight local analyst — answers from the loaded snapshot.
 *  (The real build wires this to the Albert API endpoint on the backend.) */
function answer(q: string, snap: Snapshot): string {
  const ql = q.toLowerCase();
  if (ql.includes("rempliss")) {
    const best = [...snap.byAntenna].sort((a, b) => b.remplissage - a.remplissage)[0];
    return `D'après ${snap.filters.year}, ${best.name} affiche le meilleur taux de remplissage à ${formatDec1(best.remplissage)} élèves/cours.`;
  }
  if (ql.includes("rentab") || ql.includes("secteur")) {
    const best = [...snap.sectors.rows].sort((a, b) => b.recettes - a.recettes)[0];
    return `Le secteur le plus générateur de recettes est ${best.secteur} avec ${formatEur(best.recettes)} (${formatInt(best.inscriptions)} inscriptions).`;
  }
  if (ql.includes("inscription") || ql.includes("total")) {
    const k = snap.kpis.find((x) => x.key === "inscriptions");
    return `Total des inscriptions en ${snap.filters.year} : ${formatInt(k?.value ?? 0)} sur le périmètre filtré.`;
  }
  const top = [...snap.byAntenna].sort((a, b) => b.inscriptions - a.inscriptions)[0];
  return `Sur les données ${snap.filters.year}, ${top.name} mène avec ${formatInt(top.inscriptions)} inscriptions. Posez une question sur le remplissage, la rentabilité ou les inscriptions.`;
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
                      ? "max-w-[85%] self-end rounded-md rounded-br-[2px] bg-accent-50 px-3 py-2.5 text-neutral-900"
                      : "max-w-[85%] self-start rounded-md rounded-bl-[2px] bg-neutral-50 px-3 py-2.5 text-neutral-800"
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
