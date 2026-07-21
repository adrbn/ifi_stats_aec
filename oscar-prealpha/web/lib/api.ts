import type { Snapshot, AntennaCode } from "./types";
import type { DimKey } from "./store";
import { EMPTY_SNAPSHOT } from "./fixture";

/** Toutes les dimensions filtrables envoyées au backend. */
const DIM_KEYS: DimKey[] = [
  "secteurs", "sousSecteurs", "macros", "categories",
  "niveaux", "ages", "periodes", "matieres", "ues",
];

export interface SnapshotQuery {
  years?: number[];
  antennas?: AntennaCode[];
  dims?: Partial<Record<DimKey, string[]>>;
  mode?: "civil" | "school" | "trimester";
}

/**
 * Fetch the live, filter-aware Cours payload from the backend (proxied via
 * /api). Computed on demand for the selected years/antennas — same granularity
 * as OSCAR Online. Returns an EMPTY snapshot if the backend is unreachable.
 */
export async function fetchSnapshot(q: SnapshotQuery = {}): Promise<Snapshot> {
  const params = new URLSearchParams();
  if (q.years?.length) params.set("years", q.years.join(","));
  if (q.antennas?.length) params.set("antennas", q.antennas.join(","));
  if (q.dims) {
    // repeated params (?secteurs=A&secteurs=B) — safe for values containing commas
    DIM_KEYS.forEach((k) => {
      (q.dims?.[k] ?? []).forEach((v) => params.append(k, v));
    });
  }
  if (q.mode && q.mode !== "civil") params.set("mode", q.mode);
  const qs = params.toString();
  try {
    const res = await fetch(`/api/cours${qs ? `?${qs}` : ""}`, {
      headers: { accept: "application/json" },
      cache: "no-store",
    });
    if (!res.ok) throw new Error(`status ${res.status}`);
    return (await res.json()) as Snapshot;
  } catch {
    // Backend offline — return an EMPTY snapshot (no fabricated data).
    return EMPTY_SNAPSHOT;
  }
}
