"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import { toBlob } from "html-to-image";
import { ChartFsHeight } from "./rc";

/** Déclenche le téléchargement d'un contenu (texte ou blob). */
function triggerDownload(content: string | Blob, filename: string, mime: string) {
  const blob = content instanceof Blob ? content : new Blob(["﻿" + content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

const csvCell = (t: string) => (/[",\n]/.test(t) ? `"${t.replace(/"/g, '""')}"` : t);

/** Extrait un CSV du 1er <table> trouvé dans le panneau (si présent). */
function tableToCsv(root: HTMLElement | null): string | null {
  const table = root?.querySelector("table");
  if (!table) return null;
  const lines = Array.from(table.querySelectorAll("tr"))
    .map((tr) =>
      Array.from(tr.querySelectorAll("th,td"))
        .map((c) => csvCell((c.textContent || "").replace(/\s+/g, " ").trim()))
        .join(","),
    )
    .filter((l) => l.replace(/,/g, "").trim().length > 0);
  return lines.length ? lines.join("\n") : null;
}

const slug = (s?: string) => (s ?? "graphique").replace(/[^\w-]+/g, "_").replace(/^_+|_+$/g, "") || "graphique";

export function Panel({
  title,
  subtitle,
  right,
  children,
  className = "",
  copyable = true,
  csv,
}: {
  title?: string;
  subtitle?: string;
  right?: ReactNode;
  children: ReactNode;
  className?: string;
  copyable?: boolean;
  /** Données CSV explicites (prioritaires sur le scraping d'un <table>). */
  csv?: { filename?: string; rows: (string | number)[][] };
}) {
  const cardRef = useRef<HTMLDivElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const [state, setState] = useState<"idle" | "copied" | "saved" | "error">("idle");
  const [menuOpen, setMenuOpen] = useState(false);
  const [fs, setFs] = useState(false);
  const [csvAvailable, setCsvAvailable] = useState(false);

  // CSV dispo si prop explicite OU si un <table> est présent dans le corps.
  useEffect(() => {
    setCsvAvailable(!!csv?.rows?.length || !!cardRef.current?.querySelector("table"));
  });

  // Échap ferme le menu / le plein écran ; clic hors menu ferme le menu.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setMenuOpen(false);
        setFs(false);
      }
    };
    const onDown = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) setMenuOpen(false);
    };
    window.addEventListener("keydown", onKey);
    window.addEventListener("mousedown", onDown);
    return () => {
      window.removeEventListener("keydown", onKey);
      window.removeEventListener("mousedown", onDown);
    };
  }, []);

  // Bloque le scroll de fond en plein écran + suit la hauteur de la fenêtre
  // (pour dimensionner les graphes en conséquence).
  const [vh, setVh] = useState(0);
  useEffect(() => {
    if (!fs) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const upd = () => setVh(window.innerHeight);
    upd();
    window.addEventListener("resize", upd);
    return () => {
      document.body.style.overflow = prev;
      window.removeEventListener("resize", upd);
    };
  }, [fs]);

  // Hauteur imposée aux graphes en plein écran (≈ hauteur utile de la modale).
  const fsHeight = fs ? Math.round(Math.min(840, (vh || (typeof window !== "undefined" ? window.innerHeight : 900)) * 0.76)) : undefined;

  const capture = () =>
    cardRef.current
      ? toBlob(cardRef.current, {
          pixelRatio: 2,
          backgroundColor: "#ffffff",
          skipFonts: true,
          filter: (node) => !(node instanceof HTMLElement && node.dataset?.noExport === "true"),
        })
      : Promise.resolve(null);

  const copyImage = async () => {
    setMenuOpen(false);
    try {
      const blob = await capture();
      if (!blob) throw new Error("capture vide");
      try {
        await navigator.clipboard.write([new ClipboardItem({ "image/png": blob })]);
        setState("copied");
      } catch {
        triggerDownload(blob, `${slug(title)}.png`, "image/png");
        setState("saved");
      }
    } catch {
      setState("error");
    }
    setTimeout(() => setState("idle"), 1900);
  };

  const exportPng = async () => {
    setMenuOpen(false);
    try {
      const blob = await capture();
      if (!blob) throw new Error("capture vide");
      triggerDownload(blob, `${slug(title)}.png`, "image/png");
      setState("saved");
    } catch {
      setState("error");
    }
    setTimeout(() => setState("idle"), 1900);
  };

  const exportCsv = () => {
    setMenuOpen(false);
    const content = csv?.rows?.length
      ? csv.rows.map((r) => r.map((c) => csvCell(String(c))).join(",")).join("\n")
      : tableToCsv(cardRef.current);
    if (content) triggerDownload(content, `${slug(csv?.filename ?? title)}.csv`, "text/csv;charset=utf-8");
  };

  const showHeader = title || right || copyable;

  return (
    <>
      {/* Fond assombri en plein écran (clic = fermer). */}
      {fs && <div className="fixed inset-0 z-[55] bg-neutral-900/60 backdrop-blur-[2px]" onClick={() => setFs(false)} />}

      <section
        ref={cardRef}
        className={
          fs
            ? "oscar-fs fixed inset-3 z-[60] mx-auto flex max-w-[1600px] flex-col overflow-hidden rounded-xl border border-neutral-200 bg-surface shadow-2xl sm:inset-5"
            : `min-w-0 rounded-lg border border-neutral-200 bg-surface shadow-xs ${className}`
        }
      >
        {showHeader && (
          <header className="flex flex-shrink-0 items-start justify-between gap-3 border-b border-neutral-200 px-5 py-4">
            <div className="min-w-0">
              {title && <h2 className="text-h2 font-semibold text-neutral-900">{title}</h2>}
              {subtitle && <p className="mt-0.5 text-body-sm text-neutral-500">{subtitle}</p>}
            </div>

            <div ref={menuRef} data-no-export="true" className="relative flex flex-shrink-0 items-center gap-2">
              {right}
              {state !== "idle" && (
                <span className={`text-caption font-medium ${state === "error" ? "text-error" : "text-success"}`}>
                  {state === "copied" ? "Copié ✓" : state === "saved" ? "Téléchargé ✓" : "Erreur"}
                </span>
              )}

              {fs && (
                <button
                  onClick={() => setFs(false)}
                  aria-label="Quitter le plein écran"
                  title="Fermer (Échap)"
                  className="grid h-[28px] w-[28px] place-items-center rounded-md border border-neutral-200 text-neutral-500 transition-colors hover:border-neutral-300 hover:text-neutral-900"
                >
                  <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M18 6 6 18M6 6l12 12" />
                  </svg>
                </button>
              )}

              {copyable && (
                <>
                  <button
                    onClick={() => setMenuOpen((v) => !v)}
                    aria-label="Actions du graphique"
                    aria-haspopup="menu"
                    aria-expanded={menuOpen}
                    title="Copier, exporter, plein écran"
                    className={`grid h-[28px] w-[28px] place-items-center rounded-md border transition-colors ${
                      menuOpen ? "border-neutral-300 text-neutral-800" : "border-neutral-200 text-neutral-500 hover:border-neutral-300 hover:text-neutral-800"
                    }`}
                  >
                    <svg className="h-4 w-4" viewBox="0 0 24 24" fill="currentColor">
                      <circle cx="12" cy="5" r="1.7" />
                      <circle cx="12" cy="12" r="1.7" />
                      <circle cx="12" cy="19" r="1.7" />
                    </svg>
                  </button>

                  {menuOpen && (
                    <div role="menu" className="absolute right-0 top-[calc(100%+6px)] z-[70] w-56 overflow-hidden rounded-md border border-neutral-200 bg-surface py-1 shadow-lg">
                      {!fs && (
                        <MenuItem icon="fullscreen" onClick={() => { setMenuOpen(false); setFs(true); }}>
                          Plein écran
                        </MenuItem>
                      )}
                      <MenuItem icon="copy" onClick={copyImage}>Copier l'image</MenuItem>
                      <MenuItem icon="image" onClick={exportPng}>Exporter en PNG</MenuItem>
                      {csvAvailable && <MenuItem icon="csv" onClick={exportCsv}>Exporter en CSV</MenuItem>}
                    </div>
                  )}
                </>
              )}
            </div>
          </header>
        )}

        <div className={fs ? "oscar-fs-body thin-scroll flex-1 overflow-auto p-6" : "bg-surface p-5"}>
          <ChartFsHeight height={fsHeight}>{children}</ChartFsHeight>
        </div>
      </section>
    </>
  );
}

function MenuItem({ children, onClick, icon }: { children: ReactNode; onClick: () => void; icon: "fullscreen" | "copy" | "image" | "csv" }) {
  return (
    <button
      role="menuitem"
      onClick={onClick}
      className="flex w-full items-center gap-2.5 px-3 py-2 text-left text-body-sm text-neutral-700 transition-colors hover:bg-accent-50 hover:text-accent-700"
    >
      <span className="flex-shrink-0 text-neutral-400">
        {icon === "fullscreen" && (
          <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M8 3H5a2 2 0 0 0-2 2v3M21 8V5a2 2 0 0 0-2-2h-3M16 21h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3" />
          </svg>
        )}
        {icon === "copy" && (
          <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <rect x="9" y="9" width="13" height="13" rx="2" />
            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
          </svg>
        )}
        {icon === "image" && (
          <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <rect x="3" y="3" width="18" height="18" rx="2" />
            <circle cx="9" cy="9" r="2" />
            <path d="m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21" />
          </svg>
        )}
        {icon === "csv" && (
          <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <path d="M14 2v6h6M8 13h2M8 17h2M14 13h2M14 17h2" />
          </svg>
        )}
      </span>
      {children}
    </button>
  );
}

export function Eyebrow({ children }: { children: ReactNode }) {
  return (
    <div className="text-eyebrow font-semibold uppercase tracking-[0.1em] text-accent-600">
      {children}
    </div>
  );
}
