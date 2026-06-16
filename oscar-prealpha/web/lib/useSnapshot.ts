"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchSnapshot } from "./api";
import { useFilters } from "./store";
import type { Snapshot } from "./types";
import { EMPTY_SNAPSHOT } from "./fixture";

export function useSnapshot(): { data: Snapshot; isLoading: boolean; isOffline: boolean } {
  const years = useFilters((s) => s.years);
  const yearMode = useFilters((s) => s.yearMode);
  const antennas = useFilters((s) => s.antennas);
  const dims = useFilters((s) => s.dims);
  const q = useQuery({
    queryKey: [
      "cours",
      yearMode,
      [...years].sort().join(","),
      [...antennas].sort().join(","),
      JSON.stringify(dims),
    ],
    queryFn: () => fetchSnapshot({ years, antennas, dims, mode: yearMode }),
    placeholderData: (prev) => prev,
    staleTime: 15_000,
  });
  const data = q.data ?? EMPTY_SNAPSHOT;
  // « Hors-ligne » UNIQUEMENT si un fetch a abouti et a échoué — pas pendant le
  // tout premier chargement (cold start serverless ~10-15 s), sinon le bandeau
  // d'erreur s'affiche alors que les données arrivent juste après.
  const unavailable = data.meta.source === "unavailable";
  return { data, isLoading: q.isLoading, isOffline: !q.isLoading && unavailable };
}
