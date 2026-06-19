"use client";

import { useRef, useState, type ReactNode } from "react";
import { toBlob } from "html-to-image";

export function Panel({
  title,
  subtitle,
  right,
  children,
  className = "",
  copyable = true,
}: {
  title?: string;
  subtitle?: string;
  right?: ReactNode;
  children: ReactNode;
  className?: string;
  copyable?: boolean;
}) {
  const bodyRef = useRef<HTMLDivElement>(null);
  const [state, setState] = useState<"idle" | "copied" | "saved" | "error">("idle");

  const copy = async () => {
    if (!bodyRef.current) return;
    try {
      // skipFonts: on n'embarque pas les @font-face (Google Fonts cross-origin →
      // SecurityError + lenteur) ; la police déjà chargée est rendue telle quelle.
      const blob = await toBlob(bodyRef.current, { pixelRatio: 2, backgroundColor: "#ffffff", skipFonts: true });
      if (!blob) throw new Error("capture vide");
      try {
        // Copie dans le presse-papiers (collable dans une présentation / un mail).
        await navigator.clipboard.write([new ClipboardItem({ "image/png": blob })]);
        setState("copied");
      } catch {
        // Repli : téléchargement du PNG (navigateurs sans clipboard image).
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `${(title ?? "graphique").replace(/[^\w-]+/g, "_")}.png`;
        a.click();
        URL.revokeObjectURL(url);
        setState("saved");
      }
    } catch {
      setState("error");
    }
    setTimeout(() => setState("idle"), 1900);
  };

  return (
    <section className={`min-w-0 rounded-lg border border-neutral-200 bg-surface shadow-xs ${className}`}>
      {(title || right || copyable) && (
        <header className="flex items-start justify-between gap-3 border-b border-neutral-200 px-5 py-4">
          <div className="min-w-0">
            {title && <h2 className="text-h2 font-semibold text-neutral-900">{title}</h2>}
            {subtitle && <p className="mt-0.5 text-body-sm text-neutral-500">{subtitle}</p>}
          </div>
          <div className="flex flex-shrink-0 items-center gap-2">
            {right}
            {copyable && (
              <button
                onClick={copy}
                title="Copier le graphique en image (presse-papiers)"
                aria-label="Copier en image"
                className={`inline-flex items-center gap-1.5 rounded-md border px-2 py-1 text-caption font-medium transition-colors ${
                  state === "error"
                    ? "border-error/40 text-error"
                    : state !== "idle"
                      ? "border-success/40 text-success"
                      : "border-neutral-200 text-neutral-500 hover:border-neutral-300 hover:text-neutral-800"
                }`}
              >
                {state === "idle" ? (
                  <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <rect x="9" y="9" width="13" height="13" rx="2" />
                    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
                  </svg>
                ) : null}
                {state === "idle" ? "Copier" : state === "copied" ? "Copié ✓" : state === "saved" ? "Téléchargé ✓" : "Erreur"}
              </button>
            )}
          </div>
        </header>
      )}
      <div ref={bodyRef} className="bg-surface p-5">
        {children}
      </div>
    </section>
  );
}

export function Eyebrow({ children }: { children: ReactNode }) {
  return (
    <div className="text-eyebrow font-semibold uppercase tracking-[0.1em] text-accent-600">
      {children}
    </div>
  );
}
