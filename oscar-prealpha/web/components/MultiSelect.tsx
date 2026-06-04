"use client";

import { useEffect, useRef, useState } from "react";
import { IconChevron } from "./icons";

export function MultiSelect({
  label,
  options,
  selected,
  onToggle,
  onClear,
  disabled,
}: {
  label: string;
  options: string[];
  selected: string[];
  onToggle: (v: string) => void;
  onClear: () => void;
  disabled?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const onDoc = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  const count = selected.length;
  const filtered = q ? options.filter((o) => o.toLowerCase().includes(q.toLowerCase())) : options;

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        disabled={disabled}
        onClick={() => setOpen((v) => !v)}
        className={`inline-flex items-center gap-2 rounded-pill border px-3 py-1.5 text-body-sm font-medium transition-colors ${
          count
            ? "border-accent-500 bg-accent-50 text-accent-700"
            : "border-neutral-200 bg-surface text-neutral-700 hover:text-neutral-900"
        } ${disabled ? "cursor-not-allowed opacity-50" : ""}`}
      >
        <span className="text-eyebrow font-semibold uppercase tracking-[0.06em] opacity-70">{label}</span>
        <span>{count ? `${count} sélection${count > 1 ? "s" : ""}` : "Tous"}</span>
        <IconChevron className="h-3 w-3 rotate-90 opacity-60" />
      </button>

      {open && (
        <div className="absolute left-0 z-50 mt-1 w-72 rounded-md border border-neutral-200 bg-surface p-2 shadow-lg">
          <div className="mb-2 flex items-center gap-2">
            <input
              autoFocus
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder={`Filtrer ${label.toLowerCase()}…`}
              className="flex-1 rounded-sm border border-neutral-200 px-2 py-1 text-body-sm outline-none focus:border-accent-500"
            />
            {count > 0 && (
              <button onClick={onClear} className="rounded-sm px-2 py-1 text-caption text-neutral-500 hover:bg-error-soft hover:text-error">
                Effacer
              </button>
            )}
          </div>
          <div className="thin-scroll max-h-64 overflow-auto">
            {filtered.length === 0 && <div className="px-2 py-3 text-caption text-neutral-400">Aucune option</div>}
            {filtered.map((o) => {
              const on = selected.includes(o);
              return (
                <label key={o} className="flex cursor-pointer items-center gap-2 rounded-sm px-2 py-1.5 text-body-sm hover:bg-neutral-100">
                  <input type="checkbox" checked={on} onChange={() => onToggle(o)} className="accent-[var(--accent-500)]" />
                  <span className={on ? "font-medium text-neutral-900" : "text-neutral-700"}>{o}</span>
                </label>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
