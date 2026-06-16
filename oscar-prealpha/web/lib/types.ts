export type AntennaCode = "IFI" | "IFM" | "IFF" | "IFN" | "IFP";

export interface Antenna {
  code: AntennaCode;
  name: string;
  city?: string;
  color: string;
  lat?: number;
  lng?: number;
}

export type KpiFormat = "int" | "eur" | "dec1";

export interface Kpi {
  key: string;
  label: string;
  value: number;
  format: KpiFormat;
  delta: number | null;
  deltaLabel?: string;
}

export interface AntennaRow {
  code: AntennaCode;
  name: string;
  color: string;
  inscriptions: number;
  cours: number;
  recettes: number;
  remplissage: number;
}

export interface SectorRow {
  secteur: string;
  cours: number;
  inscriptions: number;
  nouv: number;
  pctNouv: number;
  recettes: number;
  remplissage: number;
}

export interface EvolutionSeries {
  code: AntennaCode;
  name: string;
  color: string;
  inscriptions: number[];
  recettes: number[];
  metrics?: Record<string, number[]>;
}

export interface BreakdownRow {
  label: string;
  cours: number;
  inscriptions: number;
  nouv: number;
  pctNouv: number;
  recettes: number;
  remplissage: number;
}

export interface BreakdownBlock {
  key: string;
  label: string;
  rows: BreakdownRow[];
  total: BreakdownRow;
}

export interface YoyRow {
  year: number;
  inscriptions: number;
  cours: number;
  recettes: number;
  heures: number;
  inscriptionsVar: number | null;
  recettesVar: number | null;
}

export interface ProfitabilityRow {
  label?: string;
  code?: string;
  color?: string;
  inscriptions: number;
  recettes: number;
  arpi: number;
}

export interface Snapshot {
  meta: {
    app: string;
    subtitle: string;
    source: "computed" | "partial" | "unavailable";
    updated: string;
    years: number[];
    antennas: Antenna[];
  };
  filters: {
    year: number;
    years?: number[];
    antennas: AntennaCode[];
    secteurs?: string[];
    sousSecteurs?: string[];
    macros?: string[];
    categories?: string[];
    sectors: string[];
  };
  dimOptions?: { secteurs: string[]; sousSecteurs: string[]; macros: string[]; categories: string[] };
  kpis: Kpi[];
  byAntenna: AntennaRow[];
  sectors: {
    columns: string[];
    rows: SectorRow[];
    total: SectorRow;
  };
  evolution: {
    years: number[];
    series: EvolutionSeries[];
  };
  breakdowns?: Record<string, BreakdownBlock>;
  yoy?: { years: number[]; rows: YoyRow[] };
  profitability?: { bySector: ProfitabilityRow[]; byAntenna: ProfitabilityRow[] };
  indicators?: { key: string; label: string; format: "int" | "eur" | "dec1" }[];
  bySectorIndicator?: Record<string, { label: string; value: number }[]>;
  byAntennaIndicator?: Record<string, { code: AntennaCode; color: string; value: number }[]>;
  sectorAntenna?: {
    sectors: string[];
    antennas: AntennaCode[];
    inscriptions: number[][];
    remplissage: number[][];
    matrices?: Record<string, number[][]>;
  };
  flows?: { source: string; target: string; value: number; values?: Record<string, number> }[];
}
