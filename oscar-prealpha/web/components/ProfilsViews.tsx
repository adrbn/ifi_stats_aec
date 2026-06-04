"use client";

import { useState } from "react";
import { useDomain, type DomainKpi } from "@/lib/domain";
import { Panel } from "./Card";
import { PageTitle } from "./PageTitle";
import { StatCards, DomainUnavailable } from "./StatCards";
import { CountTable } from "./CountTable";
import { Donut, HBar } from "./Charts";
import {
  AgeHistogram,
  AgeBoxBySede,
  MacroLevelBar,
  GroupedSedeBar,
  GroupedPaletteBar,
  type SedeSeries,
} from "./ProfilsCharts";
import { formatInt, formatDec1 } from "@/lib/format";

// Antenna palette (matches OSCAR / build_profils.py SEDE_META)
const SEDE_KEYS = [
  { code: "IFM", name: "IFM Milano", color: "#FF8C00" },
  { code: "IFF", name: "IFF Firenze", color: "#8B5CF6" },
  { code: "IFN", name: "IFN Napoli", color: "#22C55E" },
  { code: "IFP", name: "IFP Palermo", color: "#EF4444" },
];

interface BreakdownRow {
  label: string;
  count: number;
  pct: number;
}

interface ProfilsData {
  meta: { total: number };
  kpis: DomainKpi[];
  bySede: { code: string; name: string; color: string; clients: number; femmes: number; hommes: number; nonSpec: number; ageMoyen: number; ageMedian: number }[];
  tranches: BreakdownRow[];
  typesCours: BreakdownRow[];
  genderBySede: { code: string; F: number; M: number; NS: number }[];
  nationalities: { nbNationalities: number; principal: { label: string; pct: number }; nonSpecified: number; top: BreakdownRow[] };
  motivation: BreakdownRow[];
  canal: BreakdownRow[];
  csp: BreakdownRow[];
  // enriched
  ageHistogram: { bin: string; count: number }[];
  ageBySede: SedeSeries[];
  tranchesBySede: ({ code: string } & Record<string, number | string>)[];
  levels: { label: string; count: number }[];
  nationalityBySede: ({ nationality: string } & Record<string, number | string>)[];
  motivationBySede: ({ label: string } & Record<string, number | string>)[];
  canalBySede: ({ label: string } & Record<string, number | string>)[];
}

function useProfils() {
  return useDomain<ProfilsData>("profils");
}

function Shell({ title, eyebrow, children }: { title: string; eyebrow: string; children: React.ReactNode }) {
  return (
    <div className="space-y-5">
      <PageTitle eyebrow={eyebrow} title={title} />
      {children}
    </div>
  );
}

function Loading() {
  return <div className="h-40 animate-pulse rounded-md border border-neutral-200 bg-neutral-50" />;
}

/** Compact count/pct table mirroring the OSCAR st.dataframe blocks. */
function MiniTable({ label, rows, max }: { label: string; rows: BreakdownRow[]; max?: number }) {
  return <CountTable label={label} rows={rows} max={max} />;
}

// ════════════════════════════════════════════════════════════════════════
// TAB P1 — SYNTHÈSE
// ════════════════════════════════════════════════════════════════════════
export function ProfilsSynthese() {
  const { data, available, isLoading, reason } = useProfils();
  return (
    <Shell eyebrow="Profils" title="Synthèse">
      {isLoading ? (
        <Loading />
      ) : !available || !data ? (
        <DomainUnavailable title="Profils" reason={reason} />
      ) : (
        <>
          <StatCards kpis={data.kpis} />

          <Panel title="Détail par antenne" subtitle="Clients, genre et âge par sede">
            <div className="overflow-hidden rounded-md border border-neutral-200">
              <table className="w-full border-collapse text-body-sm">
                <thead>
                  <tr>
                    {["Antenne", "Clients", "Femmes", "Hommes", "Non spéc.", "Âge moyen", "Âge médian"].map((h, i) => (
                      <th key={h} className={`border-b border-neutral-200 bg-neutral-50 px-3.5 py-2 text-eyebrow font-semibold uppercase text-neutral-600 ${i === 0 ? "text-left" : "text-right"}`}>
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {data.bySede.map((s) => (
                    <tr key={s.code} className="even:bg-neutral-50 hover:bg-accent-50">
                      <td className="px-3.5 py-2">
                        <span className="inline-flex items-center gap-2 font-medium text-neutral-800">
                          <span className="h-2 w-2 rounded-full" style={{ background: s.color }} />
                          {s.name}
                        </span>
                      </td>
                      <td className="tnum px-3.5 py-2 text-right">{formatInt(s.clients)}</td>
                      <td className="tnum px-3.5 py-2 text-right">{formatInt(s.femmes)}</td>
                      <td className="tnum px-3.5 py-2 text-right">{formatInt(s.hommes)}</td>
                      <td className="tnum px-3.5 py-2 text-right">{formatInt(s.nonSpec)}</td>
                      <td className="tnum px-3.5 py-2 text-right">{formatDec1(s.ageMoyen)}</td>
                      <td className="tnum px-3.5 py-2 text-right">{formatDec1(s.ageMedian)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Panel>

          <Panel title="Clients par antenne">
            <HBar data={data.bySede.map((s) => ({ name: s.name, value: s.clients }))} height={220} />
          </Panel>

          <div className="grid grid-cols-1 gap-5 xl:grid-cols-2">
            <Panel title="Tranches d'âge" subtitle="Répartition par tranche">
              <MiniTable label="Tranche d'âge" rows={data.tranches} />
            </Panel>
            <Panel title="Tranches d'âge">
              <Donut data={data.tranches.map((t) => ({ name: t.label, value: t.count }))} height={300} />
            </Panel>
          </div>

          <div className="grid grid-cols-1 gap-5 xl:grid-cols-2">
            <Panel title="Type de cours" subtitle="Répartition par type">
              <MiniTable label="Type de cours" rows={data.typesCours} />
            </Panel>
            <Panel title="Type de cours">
              <Donut data={data.typesCours.map((t) => ({ name: t.label, value: t.count }))} height={300} />
            </Panel>
          </div>
        </>
      )}
    </Shell>
  );
}

// ════════════════════════════════════════════════════════════════════════
// TAB P2 — DÉMOGRAPHIE
// ════════════════════════════════════════════════════════════════════════
export function ProfilsDemographie() {
  const { data, available, isLoading, reason } = useProfils();
  const [ageMode, setAgeMode] = useState<"sum" | "compare">("sum");

  // Age KPIs (moyen/médian/min/max) computed from the enriched box stats
  const ageKpis: DomainKpi[] = data
    ? (() => {
        const boxes = data.ageBySede.map((s) => s.box);
        const moyen = data.kpis.find((k) => k.key === "age")?.value ?? 0;
        const median = boxes.length ? medianOf(boxes.map((b) => b.median)) : 0;
        const min = boxes.length ? Math.min(...boxes.map((b) => b.min)) : 0;
        const max = boxes.length ? Math.max(...boxes.map((b) => b.max)) : 0;
        return [
          { key: "age_moyen", label: "Âge moyen", value: moyen, format: "dec1" },
          { key: "age_median", label: "Âge médian", value: median, format: "dec1" },
          { key: "age_min", label: "Âge min", value: min, format: "dec1" },
          { key: "age_max", label: "Âge max", value: max, format: "dec1" },
        ];
      })()
    : [];

  return (
    <Shell eyebrow="Profils" title="Démographie">
      {isLoading ? (
        <Loading />
      ) : !available || !data ? (
        <DomainUnavailable title="Profils" reason={reason} />
      ) : (
        <>
          <StatCards kpis={ageKpis} />

          <Panel
            title="Distribution des âges"
            subtitle={ageMode === "sum" ? "Distribution globale (bins de 2 ans)" : "Superposition par antenne"}
            right={
              <div className="inline-flex rounded-md border border-neutral-200 p-0.5 text-caption">
                {(["sum", "compare"] as const).map((m) => (
                  <button
                    key={m}
                    onClick={() => setAgeMode(m)}
                    className={`rounded-sm px-2.5 py-1 font-medium transition-colors ${ageMode === m ? "bg-accent-600 text-white" : "text-neutral-600 hover:text-neutral-900"}`}
                  >
                    {m === "sum" ? "Cumulé" : "Comparaison"}
                  </button>
                ))}
              </div>
            }
          >
            <AgeHistogram overall={data.ageHistogram} bySede={data.ageBySede} mode={ageMode} height={380} />
          </Panel>

          <Panel title="Âge par antenne" subtitle="Boîte à moustaches (min · Q1 · médiane · Q3 · max)">
            <AgeBoxBySede rows={data.ageBySede} height={340} />
          </Panel>

          <div className="grid grid-cols-1 gap-5 xl:grid-cols-2">
            <Panel title="Genre par antenne">
              <GroupedSedeBar
                data={data.genderBySede.map((r) => ({ name: r.code, F: r.F, M: r.M, NS: r.NS }))}
                xKey="name"
                keys={[
                  { code: "F", name: "Femmes", color: "#ec4899" },
                  { code: "M", name: "Hommes", color: "#3b82f6" },
                  { code: "NS", name: "Non spéc.", color: "#a855f7" },
                ]}
                height={320}
              />
            </Panel>
            <Panel title="Niveaux CEFR" subtitle="Macro-niveaux A0 → C2">
              <MacroLevelBar rows={data.levels} height={320} />
            </Panel>
          </div>

          <Panel title="Tranches d'âge par antenne">
            <GroupedPaletteBar data={data.tranchesBySede} xKey="code" keys={SEDE_KEYS.map((s) => s.code)} height={380} />
          </Panel>
        </>
      )}
    </Shell>
  );
}

function medianOf(values: number[]): number {
  if (!values.length) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
}

// ════════════════════════════════════════════════════════════════════════
// TAB P3 — NATIONALITÉS
// ════════════════════════════════════════════════════════════════════════
export function ProfilsNationalites() {
  const { data, available, isLoading, reason } = useProfils();
  return (
    <Shell eyebrow="Profils" title="Nationalités">
      {isLoading ? (
        <Loading />
      ) : !available || !data ? (
        <DomainUnavailable title="Profils" reason={reason} />
      ) : (
        <>
          <StatCards
            kpis={[
              { key: "nb", label: "Nb nationalités", value: data.nationalities.nbNationalities, format: "int" },
              { key: "principal", label: `Principale (${data.nationalities.principal?.label ?? "—"})`, value: data.nationalities.principal?.pct ?? 0, format: "pct1" },
              { key: "ns", label: "Non indiquée", value: data.nationalities.nonSpecified, format: "int" },
            ]}
          />

          <div className="grid grid-cols-1 gap-5 xl:grid-cols-2">
            <Panel title="Top 20 nationalités">
              <CountTable label="Nationalité" rows={data.nationalities.top} max={20} />
            </Panel>
            <Panel title="Répartition (Top 10 + Autres + Non indiquée)">
              <Donut data={buildNatPie(data)} height={320} />
            </Panel>
          </div>

          <Panel title="Nationalités par antenne" subtitle="Top 5 nationalités, ventilées par sede">
            <GroupedSedeBar
              data={data.nationalityBySede.map((r) => ({ name: r.nationality, ...r }))}
              xKey="name"
              keys={SEDE_KEYS}
              unit="int"
              height={360}
            />
          </Panel>
        </>
      )}
    </Shell>
  );
}

function buildNatPie(data: ProfilsData): { name: string; value: number }[] {
  const top10 = data.nationalities.top.slice(0, 10);
  const slices = top10.map((n) => ({ name: n.label, value: n.count }));
  const othersCount = data.nationalities.top.slice(10).reduce((acc, n) => acc + n.count, 0);
  if (othersCount > 0) slices.push({ name: "Autres", value: othersCount });
  if (data.nationalities.nonSpecified > 0) slices.push({ name: "Non indiquée", value: data.nationalities.nonSpecified });
  return slices;
}

// ════════════════════════════════════════════════════════════════════════
// TAB P4 — MOTIVATION & ACQUISITION
// ════════════════════════════════════════════════════════════════════════
export function ProfilsMotivation() {
  const { data, available, isLoading, reason } = useProfils();
  return (
    <Shell eyebrow="Profils" title="Motivation & acquisition">
      {isLoading ? (
        <Loading />
      ) : !available || !data ? (
        <DomainUnavailable title="Profils" reason={reason} />
      ) : (
        <>
          {/* Motivation */}
          <div className="grid grid-cols-1 gap-5 xl:grid-cols-2">
            <Panel title="Motivation">
              <CountTable label="Motivation" rows={data.motivation} max={15} />
            </Panel>
            <Panel title="Motivation">
              <Donut data={data.motivation.map((m) => ({ name: m.label, value: m.count }))} height={320} />
            </Panel>
          </div>
          {data.motivationBySede.length > 0 && (
            <Panel title="Motivation par antenne" subtitle="Part (%) au sein de chaque antenne">
              <GroupedSedeBar data={data.motivationBySede} xKey="label" keys={SEDE_KEYS} unit="pct" height={360} />
            </Panel>
          )}

          {/* Canal d'acquisition */}
          <div className="grid grid-cols-1 gap-5 xl:grid-cols-2">
            <Panel title="Canal d'acquisition" subtitle="Comment l'élève a connu l'IFI">
              <CountTable label="Canal" rows={data.canal} max={15} />
            </Panel>
            <Panel title="Canal d'acquisition">
              <Donut data={data.canal.map((c) => ({ name: c.label, value: c.count }))} height={320} />
            </Panel>
          </div>
          {data.canalBySede.length > 0 && (
            <Panel title="Canal par antenne" subtitle="Top 5 canaux, part (%) au sein de chaque antenne">
              <GroupedSedeBar data={data.canalBySede} xKey="label" keys={SEDE_KEYS} unit="pct" height={360} />
            </Panel>
          )}

          {/* CSP */}
          <div className="grid grid-cols-1 gap-5 xl:grid-cols-2">
            <Panel title="Catégorie socio-professionnelle" subtitle="Top 15">
              <CountTable label="CSP" rows={data.csp} max={15} />
            </Panel>
            <Panel title="CSP — Top 10">
              <HBar
                data={data.csp.slice(0, 10).map((c) => ({ name: c.label, value: c.count }))}
                height={Math.max(220, Math.min(10, data.csp.length) * 32)}
                color="#8B5CF6"
              />
            </Panel>
          </div>
        </>
      )}
    </Shell>
  );
}
