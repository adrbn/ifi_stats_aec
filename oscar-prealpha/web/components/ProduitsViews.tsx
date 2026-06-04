"use client";

import { useDomain, type DomainKpi } from "@/lib/domain";
import { Panel } from "./Card";
import { PageTitle } from "./PageTitle";
import { StatCards, DomainUnavailable } from "./StatCards";
import { HBar } from "./Charts";
import {
  PrixHistogram,
  PrixBoxByType,
  ReducedScatter,
  TypeBySedeBar,
  SedeBar,
} from "./ProduitsCharts";
import { formatInt, formatEur, formatDec1, formatPct } from "@/lib/format";

interface BySedeRow {
  code: string;
  name: string;
  color: string;
  nbProduits: number;
  prixMoyen: number;
  totalHeures: number;
}
interface ByTypeRow {
  type: string;
  nbProduits: number;
  prixMoyen: number;
  prixMin: number;
  prixMax: number;
  heuresTotal: number;
  heuresMoy: number;
}
interface CatalogueRow {
  sede: string;
  type: string;
  nom: string;
  prix: number | null;
  heures: number | null;
  places: number | null;
  actif: boolean;
}
interface PrixStatsRow {
  code: string;
  nbProduits: number;
  prixMoyen: number;
  prixMedian: number;
  prixMin: number;
  prixMax: number;
  ecartType: number;
}
interface PrixParHeureRow {
  type: string;
  prixParHeure: number;
  nbProduits: number;
}

interface ProduitsData {
  kpis: DomainKpi[];
  bySede: BySedeRow[];
  byType: ByTypeRow[];
  catalogue: CatalogueRow[];
  prixStatsBySede: PrixStatsRow[];
  prixParHeureByType: PrixParHeureRow[];
  prixHistogram: { bin: number; count: number }[];
  prixBoxByType: { type: string; min: number; q1: number; median: number; q3: number; max: number }[];
  typeBySede: { type: string; IFM: number; IFF: number; IFN: number; IFP: number }[];
  reducedScatter: { prix: number; tarifReduit: number; sede: string; nom: string; type: string }[];
  reducedKpis: { nb: number; avgPct: number | null; maxPct: number | null };
  memberKpis: { nb: number; avgPct: number | null };
}

function useProduits() {
  return useDomain<ProduitsData>("produits");
}

function Shell({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="space-y-5">
      <PageTitle eyebrow="Produits" title={title} />
      {children}
    </div>
  );
}
function Loading() {
  return <div className="h-40 animate-pulse rounded-md border border-neutral-200 bg-neutral-50" />;
}

function eur0(n: number | null) {
  return n == null ? "—" : formatEur(n);
}
function pct1(n: number | null) {
  return n == null ? "—" : formatPct(n);
}

/** Small inline metric tiles for sub-blocks that aren't the top-level KPI strip. */
function MiniStats({ items }: { items: { label: string; value: string }[] }) {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
      {items.map((m) => (
        <div key={m.label} className="flex flex-col gap-1 rounded-md border border-neutral-200 bg-surface p-3.5">
          <div className="text-eyebrow font-semibold uppercase text-neutral-500">{m.label}</div>
          <div className="tnum text-[20px] font-bold leading-none text-neutral-900">{m.value}</div>
        </div>
      ))}
    </div>
  );
}

const TH = (h: string, alignLeft: boolean, sticky = true) =>
  `${sticky ? "sticky top-0 z-10 " : ""}border-b border-neutral-200 bg-neutral-50 px-3.5 py-2 text-eyebrow font-semibold uppercase text-neutral-600 ${alignLeft ? "text-left" : "text-right"}`;

// =====================================================
// TAB PR1 — CATALOGUE
// =====================================================
export function ProduitsCatalogue() {
  const { data, available, isLoading, reason } = useProduits();
  return (
    <Shell title="Catalogue">
      {isLoading ? (
        <Loading />
      ) : !available || !data ? (
        <DomainUnavailable title="Produits" reason={reason} />
      ) : (
        <>
          <StatCards kpis={data.kpis} />

          <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
            <Panel title="Produits par antenne" subtitle="Nb produits · prix moyen · total heures">
              <div className="overflow-hidden rounded-md border border-neutral-200">
                <table className="w-full border-collapse text-body-sm">
                  <thead>
                    <tr>
                      <th className={TH("Antenne", true, false)}>Antenne</th>
                      <th className={TH("Nb produits", false, false)}>Nb produits</th>
                      <th className={TH("Prix moyen", false, false)}>Prix moyen</th>
                      <th className={TH("Total heures", false, false)}>Total heures</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.bySede.map((s) => (
                      <tr key={s.code} className="even:bg-neutral-50 hover:bg-accent-50">
                        <td className="px-3.5 py-2 font-medium text-neutral-800">
                          <span className="mr-2 inline-block h-2.5 w-2.5 rounded-full align-middle" style={{ background: s.color }} />
                          {s.code}
                        </td>
                        <td className="tnum px-3.5 py-2 text-right">{formatInt(s.nbProduits)}</td>
                        <td className="tnum px-3.5 py-2 text-right">{eur0(s.prixMoyen)}</td>
                        <td className="tnum px-3.5 py-2 text-right">{formatDec1(s.totalHeures)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Panel>

            <Panel title="Nb produits par antenne">
              <SedeBar data={data.bySede.map((s) => ({ code: s.code, value: s.nbProduits }))} />
            </Panel>
          </div>

          <Panel title="Catalogue complet" subtitle={`${data.catalogue.length} produits`}>
            <div className="thin-scroll max-h-[520px] overflow-auto rounded-md border border-neutral-200">
              <table className="w-full border-collapse text-body-sm">
                <thead>
                  <tr>
                    {["Antenne", "Type", "Produit", "Prix", "Heures", "Places", "Actif"].map((h, i) => (
                      <th key={h} className={TH(h, i < 3)}>
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {data.catalogue.map((p, i) => (
                    <tr key={i} className="even:bg-neutral-50 hover:bg-accent-50">
                      <td className="px-3.5 py-2 text-neutral-700">{p.sede}</td>
                      <td className="px-3.5 py-2 text-neutral-700">{p.type}</td>
                      <td className="px-3.5 py-2 font-medium text-neutral-800">{p.nom}</td>
                      <td className="tnum px-3.5 py-2 text-right">{eur0(p.prix)}</td>
                      <td className="tnum px-3.5 py-2 text-right">{p.heures == null ? "—" : formatDec1(p.heures)}</td>
                      <td className="tnum px-3.5 py-2 text-right">{p.places == null ? "—" : formatInt(p.places)}</td>
                      <td className="px-3.5 py-2 text-right">
                        {p.actif ? (
                          <span className="rounded-xs bg-success-soft px-1.5 py-0.5 text-caption font-semibold text-success">actif</span>
                        ) : (
                          <span className="text-caption text-neutral-400">inactif</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Panel>
        </>
      )}
    </Shell>
  );
}

// =====================================================
// TAB PR2 — PAR TYPE DE PRODUIT
// =====================================================
export function ProduitsTypes() {
  const { data, available, isLoading, reason } = useProduits();
  return (
    <Shell title="Par type">
      {isLoading ? (
        <Loading />
      ) : !available || !data ? (
        <DomainUnavailable title="Produits" reason={reason} />
      ) : (
        <>
          <Panel title="Analyse par type de produit" subtitle="Nb · prix moyen / min / max · heures total / moyen">
            <div className="thin-scroll max-h-[480px] overflow-auto rounded-md border border-neutral-200">
              <table className="w-full border-collapse text-body-sm">
                <thead>
                  <tr>
                    {["Type", "Nb", "Prix moy.", "Prix min", "Prix max", "Heures tot.", "Heures moy."].map((h, i) => (
                      <th key={h} className={TH(h, i === 0)}>
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {data.byType.map((t) => (
                    <tr key={t.type} className="even:bg-neutral-50 hover:bg-accent-50">
                      <td className="px-3.5 py-2 font-medium text-neutral-800">{t.type}</td>
                      <td className="tnum px-3.5 py-2 text-right">{formatInt(t.nbProduits)}</td>
                      <td className="tnum px-3.5 py-2 text-right">{eur0(t.prixMoyen)}</td>
                      <td className="tnum px-3.5 py-2 text-right">{eur0(t.prixMin)}</td>
                      <td className="tnum px-3.5 py-2 text-right">{eur0(t.prixMax)}</td>
                      <td className="tnum px-3.5 py-2 text-right">{formatDec1(t.heuresTotal)}</td>
                      <td className="tnum px-3.5 py-2 text-right">{formatDec1(t.heuresMoy)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Panel>

          <Panel title="Nb produits par type">
            <HBar
              data={data.byType.map((t) => ({ name: t.type, value: t.nbProduits }))}
              height={Math.max(220, data.byType.length * 28)}
            />
          </Panel>

          <Panel title="Nb produits par type et par antenne">
            <TypeBySedeBar data={data.typeBySede} />
          </Panel>

          {data.prixBoxByType.length > 0 && (
            <Panel title="Distribution des prix par type" subtitle="Boîte à moustaches (Q1 · médiane · Q3 · min–max)">
              <PrixBoxByType data={data.prixBoxByType} />
            </Panel>
          )}
        </>
      )}
    </Shell>
  );
}

// =====================================================
// TAB PR3 — ANALYSE TARIFAIRE
// =====================================================
export function ProduitsTarifs() {
  const { data, available, isLoading, reason } = useProduits();
  return (
    <Shell title="Tarifs">
      {isLoading ? (
        <Loading />
      ) : !available || !data ? (
        <DomainUnavailable title="Produits" reason={reason} />
      ) : (
        <>
          <Panel title="Distribution des prix" subtitle="Produits avec prix > 0">
            <PrixHistogram data={data.prixHistogram} />
          </Panel>

          <Panel title="Statistiques de prix par antenne">
            <div className="overflow-hidden rounded-md border border-neutral-200">
              <table className="w-full border-collapse text-body-sm">
                <thead>
                  <tr>
                    {["Antenne", "Nb", "Moyen", "Médian", "Min", "Max", "Écart-type"].map((h, i) => (
                      <th key={h} className={TH(h, i === 0, false)}>
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {data.prixStatsBySede.map((s) => (
                    <tr key={s.code} className="even:bg-neutral-50 hover:bg-accent-50">
                      <td className="px-3.5 py-2 font-medium text-neutral-800">{s.code}</td>
                      <td className="tnum px-3.5 py-2 text-right">{formatInt(s.nbProduits)}</td>
                      <td className="tnum px-3.5 py-2 text-right">{eur0(s.prixMoyen)}</td>
                      <td className="tnum px-3.5 py-2 text-right">{eur0(s.prixMedian)}</td>
                      <td className="tnum px-3.5 py-2 text-right">{eur0(s.prixMin)}</td>
                      <td className="tnum px-3.5 py-2 text-right">{eur0(s.prixMax)}</td>
                      <td className="tnum px-3.5 py-2 text-right">{formatDec1(s.ecartType)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Panel>

          {data.reducedKpis.nb > 0 && (
            <Panel title="Tarifs réduits" subtitle="Prix vs tarif réduit (référence y = x)">
              <div className="space-y-4">
                <MiniStats
                  items={[
                    { label: "Produits avec réduction", value: formatInt(data.reducedKpis.nb) },
                    { label: "Réduction moyenne", value: pct1(data.reducedKpis.avgPct) },
                    { label: "Réduction max", value: pct1(data.reducedKpis.maxPct) },
                  ]}
                />
                <ReducedScatter data={data.reducedScatter} />
              </div>
            </Panel>
          )}

          {data.memberKpis.nb > 0 && (
            <Panel title="Prix membre">
              <MiniStats
                items={[
                  { label: "Produits avec prix membre", value: formatInt(data.memberKpis.nb) },
                  { label: "Avantage moyen membre", value: pct1(data.memberKpis.avgPct) },
                ]}
              />
            </Panel>
          )}

          <Panel title="Prix moyen par heure et par type">
            <HBar
              data={data.prixParHeureByType.map((t) => ({ name: t.type, value: Math.round(t.prixParHeure) }))}
              height={Math.max(220, data.prixParHeureByType.length * 28)}
              color="#F59E0B"
              unit="eur"
            />
            <div className="thin-scroll mt-4 max-h-[360px] overflow-auto rounded-md border border-neutral-200">
              <table className="w-full border-collapse text-body-sm">
                <thead>
                  <tr>
                    {["Type", "Prix moyen / heure", "Nb produits"].map((h, i) => (
                      <th key={h} className={TH(h, i === 0)}>
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {data.prixParHeureByType.map((t) => (
                    <tr key={t.type} className="even:bg-neutral-50 hover:bg-accent-50">
                      <td className="px-3.5 py-2 font-medium text-neutral-800">{t.type}</td>
                      <td className="tnum px-3.5 py-2 text-right">{eur0(t.prixParHeure)}/h</td>
                      <td className="tnum px-3.5 py-2 text-right">{formatInt(t.nbProduits)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Panel>
        </>
      )}
    </Shell>
  );
}
