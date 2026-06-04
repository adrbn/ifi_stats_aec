import type { Snapshot, AntennaCode } from "./types";
import { EMPTY_SNAPSHOT } from "./fixture";

export interface SnapshotQuery {
  years?: number[];
  antennas?: AntennaCode[];
  dims?: { secteurs: string[]; sousSecteurs: string[]; macros: string[]; categories: string[] };
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
    (["secteurs", "sousSecteurs", "macros", "categories"] as const).forEach((k) => {
      q.dims![k].forEach((v) => params.append(k, v));
    });
  }
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
