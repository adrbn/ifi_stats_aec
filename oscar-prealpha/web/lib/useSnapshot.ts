"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchSnapshot } from "./api";
import { useFilters } from "./store";
import type { Snapshot } from "./types";
import { EMPTY_SNAPSHOT } from "./fixture";

export function useSnapshot(): { data: Snapshot; isLoading: boolean; isOffline: boolean } {
  const years = useFilters((s) => s.years);
  const antennas = useFilters((s) => s.antennas);
  const dims = useFilters((s) => s.dims);
  const q = useQuery({
    queryKey: [
      "cours",
      [...years].sort().join(","),
      [...antennas].sort().join(","),
      JSON.stringify(dims),
    ],
    queryFn: () => fetchSnapshot({ years, antennas, dims }),
    placeholderData: (prev) => prev,
    staleTime: 15_000,
  });
  const data = q.data ?? EMPTY_SNAPSHOT;
  return { data, isLoading: q.isLoading, isOffline: data.meta.source === "unavailable" };
}
