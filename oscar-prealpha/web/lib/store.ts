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
// Mode d'INTERVALLE du sélecteur : année civile, année scolaire, ou trimestre.
export type YearMode = "civil" | "school" | "trimester";

interface FilterState {
  years: number[]; // empty = all available years (mode civil / scolaire)
  yearMode: YearMode; // année civile (défaut) / scolaire / trimestre
  // Mode TRIMESTRE : sélection à 2 axes (plus lisible qu'une longue liste de
  // « 2025-26 T1 »). Vides = tout. Le périmètre = produit croisé (années × T).
  triYears: number[]; // années scolaires sélectionnées
  triQuarters: number[]; // trimestres sélectionnés (1, 2, 3)
  antennas: AntennaCode[]; // operational antennas (excludes IFI meta)
  dims: Record<DimKey, string[]>;
  aiOpen: boolean;
  confidential: boolean; // mode confidentiel : masque les données de recettes (défaut ON)
  toggleYear: (y: number) => void;
  setAllYears: () => void;
  toggleTriYear: (y: number) => void;
  setAllTriYears: () => void;
  toggleTriQuarter: (q: number) => void;
  setAllTriQuarters: () => void;
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
  triYears: [],
  triQuarters: [],
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
  toggleTriYear: (y) =>
    set((s) => {
      const has = s.triYears.includes(y);
      const next = has ? s.triYears.filter((x) => x !== y) : [...s.triYears, y];
      return { triYears: next.sort((a, b) => a - b) };
    }),
  setAllTriYears: () => set({ triYears: [] }),
  toggleTriQuarter: (q) =>
    set((s) => {
      const has = s.triQuarters.includes(q);
      const next = has ? s.triQuarters.filter((x) => x !== q) : [...s.triQuarters, q];
      return { triQuarters: next.sort((a, b) => a - b) };
    }),
  setAllTriQuarters: () => set({ triQuarters: [] }),
  // Les valeurs d'intervalle diffèrent entre les modes : on repart sur « Tout »
  // (years + sélection trimestre) pour éviter une sélection incohérente.
  setYearMode: (m) =>
    set((s) => (s.yearMode === m ? {} : { yearMode: m, years: [], triYears: [], triQuarters: [] })),
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
  reset: () => set({ years: [], yearMode: "civil", triYears: [], triQuarters: [], antennas: [...ALL], dims: { ...EMPTY_DIMS } }),
  setAiOpen: (aiOpen) => set({ aiOpen }),
  setConfidential: (confidential) => set({ confidential }),
}));
