"use client";

import { create } from "zustand";
import type { AntennaCode } from "./types";

// Dimensions ORTHOGONALES (un cours a à la fois un secteur ET un niveau, une
// tranche d'âge, une période, une matière, un volume d'UE) : elles ne
// participent pas à la cascade secteur→sous-secteur→macro→catégorie.
export type DimKey =
  | "secteurs" | "sousSecteurs" | "macros" | "categories"
  | "niveaux" | "ages" | "periodes" | "matieres" | "ues";
export const ORTHOGONAL_DIMS: DimKey[] = ["niveaux", "ages", "periodes", "matieres", "ues"];
export type YearMode = "civil" | "school";

interface FilterState {
  years: number[]; // empty = all available years
  yearMode: YearMode; // année civile (défaut) ou scolaire
  antennas: AntennaCode[]; // operational antennas (excludes IFI meta)
  dims: Record<DimKey, string[]>;
  aiOpen: boolean;
  confidential: boolean; // mode confidentiel : masque les données de recettes (défaut ON)
  toggleYear: (y: number) => void;
  setAllYears: () => void;
  setYearMode: (m: YearMode) => void;
  toggleAntenna: (c: AntennaCode) => void;
  setAntennas: (a: AntennaCode[]) => void;
  toggleDim: (dim: DimKey, value: string) => void;
  clearDim: (dim: DimKey) => void;
  reset: () => void;
  setAiOpen: (v: boolean) => void;
  setConfidential: (v: boolean) => void;
}

const ALL: AntennaCode[] = ["IFM", "IFF", "IFN", "IFP"];
const EMPTY_DIMS: Record<DimKey, string[]> = {
  secteurs: [], sousSecteurs: [], macros: [], categories: [],
  niveaux: [], ages: [], periodes: [], matieres: [], ues: [],
};

// Selecting a parent dimension resets its descendants (cascade integrity).
// Les dimensions orthogonales sont hors cascade : aucun parent ne les
// réinitialise, et elles n'ont pas de descendant.
const DESCENDANTS: Record<DimKey, DimKey[]> = {
  secteurs: ["sousSecteurs", "macros", "categories"],
  sousSecteurs: ["macros", "categories"],
  macros: ["categories"],
  categories: [],
  niveaux: [],
  ages: [],
  periodes: [],
  matieres: [],
  ues: [],
};

export const useFilters = create<FilterState>((set) => ({
  years: [],
  yearMode: "civil",
  antennas: [...ALL],
  dims: { ...EMPTY_DIMS },
  aiOpen: false,
  confidential: true, // activé par défaut : les recettes sont masquées d'emblée
  toggleYear: (y) =>
    set((s) => {
      const has = s.years.includes(y);
      const next = has ? s.years.filter((x) => x !== y) : [...s.years, y];
      return { years: next.sort((a, b) => a - b) };
    }),
  setAllYears: () => set({ years: [] }),
  // Les valeurs d'années diffèrent entre les deux modes (civile vs scolaire) :
  // on repart sur « Toutes » pour éviter une sélection incohérente.
  setYearMode: (m) =>
    set((s) => (s.yearMode === m ? {} : { yearMode: m, years: [] })),
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
  // reset ne touche PAS au mode confidentiel (garde-fou : il reste actif).
  reset: () => set({ years: [], yearMode: "civil", antennas: [...ALL], dims: { ...EMPTY_DIMS } }),
  setAiOpen: (aiOpen) => set({ aiOpen }),
  setConfidential: (confidential) => set({ confidential }),
}));
