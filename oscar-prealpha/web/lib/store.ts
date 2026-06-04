"use client";

import { create } from "zustand";
import type { AntennaCode } from "./types";

export type DimKey = "secteurs" | "sousSecteurs" | "macros" | "categories";

interface FilterState {
  years: number[]; // empty = all available years
  antennas: AntennaCode[]; // operational antennas (excludes IFI meta)
  dims: Record<DimKey, string[]>;
  aiOpen: boolean;
  toggleYear: (y: number) => void;
  setAllYears: () => void;
  toggleAntenna: (c: AntennaCode) => void;
  setAntennas: (a: AntennaCode[]) => void;
  toggleDim: (dim: DimKey, value: string) => void;
  clearDim: (dim: DimKey) => void;
  reset: () => void;
  setAiOpen: (v: boolean) => void;
}

const ALL: AntennaCode[] = ["IFM", "IFF", "IFN", "IFP"];
const EMPTY_DIMS: Record<DimKey, string[]> = { secteurs: [], sousSecteurs: [], macros: [], categories: [] };

// Selecting a parent dimension resets its descendants (cascade integrity).
const DESCENDANTS: Record<DimKey, DimKey[]> = {
  secteurs: ["sousSecteurs", "macros", "categories"],
  sousSecteurs: ["macros", "categories"],
  macros: ["categories"],
  categories: [],
};

export const useFilters = create<FilterState>((set) => ({
  years: [],
  antennas: [...ALL],
  dims: { ...EMPTY_DIMS },
  aiOpen: false,
  toggleYear: (y) =>
    set((s) => {
      const has = s.years.includes(y);
      const next = has ? s.years.filter((x) => x !== y) : [...s.years, y];
      return { years: next.sort((a, b) => a - b) };
    }),
  setAllYears: () => set({ years: [] }),
  toggleAntenna: (c) =>
    set((s) => {
      const has = s.antennas.includes(c);
      const next = has ? s.antennas.filter((x) => x !== c) : [...s.antennas, c];
      return { antennas: next.length ? next : s.antennas };
    }),
  setAntennas: (antennas) => set({ antennas }),
  toggleDim: (dim, value) =>
    set((s) => {
      const cur = s.dims[dim];
      const has = cur.includes(value);
      const nextDimVals = has ? cur.filter((x) => x !== value) : [...cur, value];
      const dims = { ...s.dims, [dim]: nextDimVals };
      for (const d of DESCENDANTS[dim]) dims[d] = []; // reset children
      return { dims };
    }),
  clearDim: (dim) =>
    set((s) => {
      const dims = { ...s.dims, [dim]: [] };
      for (const d of DESCENDANTS[dim]) dims[d] = [];
      return { dims };
    }),
  reset: () => set({ years: [], antennas: [...ALL], dims: { ...EMPTY_DIMS } }),
  setAiOpen: (aiOpen) => set({ aiOpen }),
}));
