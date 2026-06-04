import type { Snapshot } from "./types";

/**
 * EMPTY snapshot — used ONLY when the FastAPI backend is unreachable.
 * Contains NO fabricated statistics: all metrics are empty and source is
 * "unavailable", so the UI shows an explicit "backend hors-ligne" state
 * rather than fake numbers. The antenna list is real network metadata
 * (codes/colors/geo-coordinates), not data.
 */
export const EMPTY_SNAPSHOT: Snapshot = {
  meta: {
    app: "OSCAR",
    subtitle: "Institut français Italia — pilotage statistique",
    source: "unavailable",
    updated: "",
    years: [],
    antennas: [
      { code: "IFI", name: "IFI Global", city: "Italia", color: "#3B82F6" },
      { code: "IFM", name: "IFM Milano", city: "Milano", color: "#FF8C00", lat: 45.4642, lng: 9.19 },
      { code: "IFF", name: "IFF Firenze", city: "Firenze", color: "#8B5CF6", lat: 43.7696, lng: 11.2558 },
      { code: "IFN", name: "IFN Napoli", city: "Napoli", color: "#22C55E", lat: 40.8518, lng: 14.2681 },
      { code: "IFP", name: "IFP Palermo", city: "Palermo", color: "#EF4444", lat: 38.1157, lng: 13.3615 },
    ],
  },
  filters: { year: 0, antennas: ["IFM", "IFF", "IFN", "IFP"], sectors: [] },
  kpis: [],
  byAntenna: [],
  sectors: {
    columns: ["Secteur", "Cours", "Inscriptions", "Nouv. inscrits", "% nouv.", "Recettes", "Remplissage"],
    rows: [],
    total: { secteur: "TOTAL", cours: 0, inscriptions: 0, nouv: 0, pctNouv: 0, recettes: 0, remplissage: 0 },
  },
  evolution: { years: [], series: [] },
  breakdowns: {},
  yoy: { years: [], rows: [] },
  profitability: { bySector: [], byAntenna: [] },
};
