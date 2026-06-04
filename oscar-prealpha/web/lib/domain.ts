"use client";

import { useQuery } from "@tanstack/react-query";
import { formatInt, formatEur, formatDec1, formatPct } from "./format";

export interface DomainKpi {
  key: string;
  label: string;
  value: number;
  format: "int" | "eur" | "eur0" | "dec1" | "pct1";
}

export function fmtKpi(value: number, format: DomainKpi["format"]): string {
  switch (format) {
    case "eur":
    case "eur0":
      return formatEur(value);
    case "dec1":
      return formatDec1(value);
    case "pct1":
      return formatPct(value);
    default:
      return formatInt(value);
  }
}

interface DomainResult<T> {
  available: boolean;
  data: T | null;
  isLoading: boolean;
  reason?: string;
}

/** Fetch /api/data/{name}.json. Returns {available:false} when no source file. */
export function useDomain<T = any>(name: string): DomainResult<T> {
  const q = useQuery({
    queryKey: ["domain", name],
    queryFn: async () => {
      const res = await fetch(`/api/data/${name}`, { cache: "no-store" });
      if (!res.ok) throw new Error(String(res.status));
      return res.json();
    },
    retry: 1,
    staleTime: 60_000,
  });
  const payload = q.data;
  const available = !!payload && payload.available !== false;
  return {
    available,
    data: available ? (payload as T) : null,
    isLoading: q.isLoading,
    reason: payload?.reason,
  };
}
