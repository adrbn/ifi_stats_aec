"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { useSnapshot } from "@/lib/useSnapshot";
import { useFilters } from "@/lib/store";
import { AntennaBar, HBar, EvolutionLine, GroupedYearBar } from "@/components/Charts";
import { formatInt, formatEur, formatEurCompact, formatDec1 } from "@/lib/format";

// ── Couleurs Système de design de l'État (DSFR) ──
const BLEU = "#000091"; // Bleu France
const ROUGE = "#e1000f"; // Rouge Marianne

function yLabel(y: number, mode: string) {
  return mode === "school" ? `${y}-${String((y + 1) % 100).padStart(2, "0")}` : String(y);
}

// ── Briques de présentation (style DSFR) ──
function Eyebrow({ children, color = "#6b7280" }: { children: ReactNode; color?: string }) {
  return (
    <div className="text-[11px] font-bold uppercase tracking-[0.18em]" style={{ color }}>
      {children}
    </div>
  );
}

function SectionTitle({ children }: { children: ReactNode }) {
  return (
    <h2
      className="mb-4 flex items-center gap-3 break-after-avoid text-[20px] font-bold leading-tight"
      style={{ color: BLEU }}
    >
      <span className="inline-block h-6 w-[5px] flex-shrink-0 rounded-sm" style={{ background: BLEU }} />
      {children}
    </h2>
  );
}

function Insight({ children, tone = "info" }: { children: ReactNode; tone?: "info" | "warn" }) {
  const c = tone === "warn" ? "#b45309" : BLEU;
  const bg = tone === "warn" ? "#fffbeb" : "#f5f6ff";
  return (
    <div
      className="break-inside-avoid rounded-sm border-l-[3px] px-4 py-3 text-[13.5px] leading-relaxed"
      style={{ borderColor: c, background: bg }}
    >
      {children}
    </div>
  );
}

function ChartCard({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="break-inside-avoid rounded-sm border border-neutral-200 p-4">
      <div className="mb-2 text-[11px] font-semibold uppercase tracking-[0.08em] text-neutral-500">{title}</div>
      {children}
    </div>
  );
}

type Col = { k: string; label: string; right?: boolean };
function DataTable({ cols, rows, title }: { cols: Col[]; rows: Record<string, ReactNode>[]; title?: string }) {
  return (
    <div className="break-inside-avoid">
      {title && <div className="mb-1.5 text-[12px] font-semibold uppercase tracking-[0.06em] text-neutral-500">{title}</div>}
      <table className="w-full border-collapse text-[12.5px]">
        <thead>
          <tr style={{ background: BLEU }} className="text-left text-white">
            {cols.map((c) => (
              <th key={c.k} className={`px-3 py-2 font-semibold ${c.right ? "text-right" : ""}`}>{c.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i} className={i % 2 ? "bg-neutral-50" : ""}>
              {cols.map((c) => (
                <td key={c.k} className={`border-b border-neutral-200 px-3 py-2 ${c.right ? "tnum text-right" : "font-medium text-neutral-800"}`}>{r[c.k]}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

const fmtBy = (v: number, f?: string) =>
  f === "eur" ? formatEur(v) : f === "dec1" ? formatDec1(v) : formatInt(v);

function deltaText(d: number | null, fmt: string) {
  if (d == null) return "—";
  if (fmt === "dec1") return `${d > 0 ? "+" : ""}${formatDec1(d)}`;
  return `${d > 0 ? "+" : ""}${formatDec1(d)} %`;
}

export default function RapportPage() {
  const { data } = useSnapshot();
  const yearMode = useFilters((s) => s.yearMode);

  const years = data.filters.years ?? data.meta.years ?? [];
  const allYears = data.meta.years ?? [];
  const isAllYears = years.length === 0 || years.length === allYears.length;
  const sortedYears = [...years].sort((a, b) => a - b);
  const periodLabel = (() => {
    const ys = sortedYears.length ? sortedYears : allYears;
    if (!ys.length) return "—";
    if (ys.length === 1) return `Année ${yLabel(ys[0], yearMode)}`;
    return `${yLabel(ys[0], yearMode)} → ${yLabel(ys[ys.length - 1], yearMode)}`;
  })();
  const ants = data.filters.antennas ?? [];
  const antLabel = ants.length >= 4 ? "Réseau complet (IFM · IFF · IFN · IFP)" : ants.join(" · ") || "—";
  const modeLabel = yearMode === "school" ? "Année scolaire" : "Année civile";

  // ── Indicateurs ──
  const kpi = (k: string) => data.kpis.find((x) => x.key === k);
  const v = (k: string) => kpi(k)?.value ?? 0;
  const inscriptions = v("inscriptions");
  const recettes = v("recettes");
  const cours = v("cours");
  const eleves = kpi("eleves_differents");
  const panierI = kpi("panier_inscr");
  const panierP = kpi("panier_pers");
  const remplKpi = kpi("remplissage");

  const sumInd = (k: string) => (data.byAntennaIndicator?.[k] ?? []).reduce((s, r) => s + r.value, 0);
  const nouveaux = sumInd("nouveaux") || (data.sectors?.total?.nouv ?? 0);
  const reinscrits = sumInd("reinscrits");
  const pctNouveaux = inscriptions ? (nouveaux / inscriptions) * 100 : 0;

  // ── Croissance par antenne — sur les deux dernières années COMPLÈTES ──
  // L'année courante (en cours) est partielle → la comparer à une année pleine
  // ferait apparaître un faux effondrement. On l'exclut des variations textuelles
  // (les graphes, eux, montrent honnêtement la courbe).
  const evo = data.evolution;
  const eyears = evo?.years ?? [];
  const multiYear = eyears.length >= 2;
  const nowY = new Date().getFullYear();
  const latestYear = eyears.length ? Math.max(...eyears) : null;
  const partialLatest =
    latestYear != null && (yearMode === "school" ? latestYear >= nowY - 1 : latestYear >= nowY);
  const latestLabel = latestYear != null ? yLabel(latestYear, yearMode) : "";
  // Index de l'année complète la plus récente (on saute la dernière si partielle).
  const curIdx = eyears.length - 1 - (partialLatest ? 1 : 0);
  const canGrow = curIdx >= 1;
  const growYearsLabel = canGrow ? `${yLabel(eyears[curIdx], yearMode)} vs ${yLabel(eyears[curIdx - 1], yearMode)}` : "";
  const antGrowth = canGrow
    ? ((evo.series ?? [])
        .map((s) => {
          const a = s.inscriptions ?? [];
          const cur = a[curIdx];
          const prev = a[curIdx - 1];
          return prev != null && prev !== 0 && cur != null
            ? { code: s.code, name: s.name, g: ((cur - prev) / prev) * 100 }
            : null;
        })
        .filter(Boolean) as { code: string; name: string; g: number }[])
    : [];
  const topGrow = antGrowth.length ? [...antGrowth].sort((a, b) => b.g - a.g)[0] : null;
  const lowGrow = antGrowth.length ? [...antGrowth].sort((a, b) => a.g - b.g)[0] : null;
  const signed = (g: number) => `${g > 0 ? "+" : g < 0 ? "−" : ""}${formatDec1(Math.abs(g))} %`;

  // ── Secteurs ──
  const sectorRows = [...(data.sectors?.rows ?? [])].sort((a, b) => b.recettes - a.recettes);
  const topSector = sectorRows[0];
  const topSectorShare = topSector && recettes ? (topSector.recettes / recettes) * 100 : 0;

  // ── Antennes (tableau) ──
  const byAnt = data.byAntenna ?? [];
  const topAnt = [...byAnt].sort((a, b) => b.inscriptions - a.inscriptions)[0];

  const updated = (() => {
    try {
      return new Date(data.meta.updated).toLocaleDateString("fr-FR", { day: "2-digit", month: "long", year: "numeric" });
    } catch {
      return data.meta.updated;
    }
  })();

  const evoSpanLabel =
    evo?.years?.length >= 2 ? `${yLabel(evo.years[0], yearMode)} → ${yLabel(evo.years.at(-1)!, yearMode)}` : periodLabel;

  return (
    <div className="min-h-screen bg-neutral-100 py-6 print:bg-white print:py-0">
      {/* Barre d'actions — masquée à l'impression */}
      <div className="mx-auto mb-5 flex max-w-[820px] items-center justify-between px-4 print:hidden">
        <Link href="/cours/synthese" className="text-body-sm font-medium text-neutral-600 hover:text-neutral-900">
          ← Retour au tableau de bord
        </Link>
        <div className="flex items-center gap-3">
          <Link
            href="/presentation"
            className="inline-flex items-center gap-2 rounded-md border px-4 py-2 text-body-sm font-semibold transition-colors hover:bg-neutral-50"
            style={{ borderColor: BLEU, color: BLEU }}
          >
            ▶ Mode présentation
          </Link>
          <button
            onClick={() => window.print()}
            className="inline-flex items-center gap-2 rounded-md px-4 py-2 text-body-sm font-semibold text-white shadow-sm transition-opacity hover:opacity-90"
            style={{ background: BLEU }}
          >
            📄 Télécharger le PDF
          </button>
        </div>
      </div>

      {/* Document A4 */}
      <article
        className="mx-auto max-w-[820px] bg-white px-12 py-10 text-neutral-800 shadow-lg print:max-w-none print:px-0 print:py-0 print:shadow-none"
        style={{ fontFeatureSettings: '"tnum"' }}
      >
        {/* ====================== COUVERTURE ====================== */}
        <header className="break-inside-avoid">
          <div className="flex items-start justify-between">
            {/* Logos officiels repris du modèle CR IFI (extraits du PDF). */}
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/rf-logo.png" alt="République française" className="h-[78px] w-auto" />
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/ifi-logo.png" alt="Institut français Italia" className="h-[64px] w-auto" />
          </div>

          <div className="mt-5 border-b border-neutral-200 pb-2 text-[12px] text-neutral-600">
            <strong className="text-neutral-800">Ambassade de France en Italie</strong> · Service de Coopération et d'Action Culturelle
          </div>
          <div className="mt-2 h-[3px] w-full" style={{ background: BLEU }} />

          <div className="mt-10">
            <Eyebrow color={ROUGE}>Document interne</Eyebrow>
            <h1 className="mt-3 text-[44px] font-extrabold leading-none" style={{ color: BLEU }}>
              Rapport d'activité
            </h1>
            <div className="mt-5 h-[3px] w-full" style={{ background: BLEU }} />
            <p className="mt-5 text-[19px] text-neutral-500">Réseau de l'Institut français Italia</p>
            <p className="text-[22px] font-bold" style={{ color: BLEU }}>
              {periodLabel} · Cours
            </p>
          </div>

          {/* Métadonnées */}
          <div className="mt-12 grid grid-cols-2 gap-x-10 gap-y-5 border-t border-neutral-200 pt-6 text-[13px]">
            <div>
              <Eyebrow>Périmètre</Eyebrow>
              <div className="mt-1 font-semibold text-neutral-900">{periodLabel}</div>
              <div className="text-neutral-600">{modeLabel}</div>
            </div>
            <div>
              <Eyebrow>Antennes</Eyebrow>
              <div className="mt-1 font-semibold text-neutral-900">{antLabel}</div>
            </div>
            <div>
              <Eyebrow>Source des données</Eyebrow>
              <div className="mt-1 font-semibold text-neutral-900">Export AEC « Tous les cours »</div>
              <div className="text-neutral-600">Données au {updated}</div>
            </div>
            <div>
              <Eyebrow>Indicateurs couverts</Eyebrow>
              <div className="mt-1 font-semibold text-neutral-900">{data.kpis.length} KPI · {byAnt.length} antennes · {sectorRows.length} secteurs</div>
            </div>
          </div>

          <div className="mt-12 border-t border-neutral-200 pt-3 text-center text-[11px] tracking-[0.04em] text-neutral-500">
            Document interne · <span className="font-semibold" style={{ color: BLEU }}>OSCAR / RAPPORT D'ACTIVITÉ</span> · Diffusion restreinte équipe IFI
          </div>
        </header>

        {/* ====================== SYNTHÈSE EXÉCUTIVE ====================== */}
        <section className="break-before-page pt-2">
          <SectionTitle>Synthèse exécutive</SectionTitle>
          {partialLatest && (
            <div className="mb-4">
              <Insight tone="warn">
                <strong>Note méthodologique.</strong> L'année <strong>{latestLabel}</strong> est en cours : ses totaux et ses variations N-1 sont partiels et ne sont pas comparables à une année pleine. Les variations par antenne portent donc sur les dernières années <strong>complètes</strong>{growYearsLabel ? <> ({growYearsLabel})</> : null}.
              </Insight>
            </div>
          )}
          <p className="mb-5 text-[14px] leading-relaxed">
            Sur le périmètre <strong>{periodLabel}</strong> — {antLabel} —, le réseau enregistre{" "}
            <strong>{formatInt(inscriptions)} inscriptions</strong>
            {kpi("inscriptions")?.delta != null && (
              <> ({deltaText(kpi("inscriptions")!.delta, "int")} {kpi("inscriptions")!.deltaLabel})</>
            )}{" "}
            réparties sur <strong>{formatInt(cours)} cours</strong>, pour{" "}
            <strong>{formatEur(recettes)}</strong> de recettes
            {kpi("recettes")?.delta != null && <> ({deltaText(kpi("recettes")!.delta, "int")})</>}.{" "}
            Le panier moyen s'établit à <strong>{panierI ? formatEur(panierI.value) : "—"}</strong> par inscription
            {panierP && <> et <strong>{formatEur(panierP.value)}</strong> par personne</>}.
          </p>

          {/* Bandeau chiffres-clés */}
          <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
            {[
              { l: "Inscriptions", val: formatInt(inscriptions), k: kpi("inscriptions") },
              { l: "Recettes", val: formatEurCompact(recettes), k: kpi("recettes") },
              { l: eleves ? "Élèves différents" : "Cours", val: eleves ? formatInt(eleves.value) : formatInt(cours), k: eleves ?? kpi("cours") },
              { l: "Panier / inscr.", val: panierI ? formatEur(panierI.value) : "—", k: panierI },
            ].map((c) => (
              <div key={c.l} className="break-inside-avoid rounded-sm border border-neutral-200 p-3">
                <div className="text-[10px] font-semibold uppercase tracking-[0.08em] text-neutral-500">{c.l}</div>
                <div className="mt-1 text-[26px] font-extrabold leading-none tnum" style={{ color: BLEU }}>{c.val}</div>
                {c.k?.delta != null && (
                  <div className={`mt-1 text-[11px] font-semibold ${c.k.delta >= 0 ? "text-green-700" : "text-red-600"}`}>
                    {deltaText(c.k.delta, c.k.format)} {c.k.deltaLabel}
                  </div>
                )}
              </div>
            ))}
          </div>

          <Insight>
            <strong>Faits marquants.</strong>{" "}
            {topAnt && <>Première antenne : <strong>{topAnt.name}</strong> ({formatInt(topAnt.inscriptions)} inscriptions). </>}
            {topSector && <>Secteur le plus contributeur : <strong>{topSector.secteur}</strong> ({formatDec1(topSectorShare)} % des recettes). </>}
            {topGrow && lowGrow && topGrow.code !== lowGrow.code && (
              <>Variations {growYearsLabel} : <strong>{topGrow.name}</strong> {signed(topGrow.g)}, <strong>{lowGrow.name}</strong> {signed(lowGrow.g)}. </>
            )}
            {pctNouveaux > 0 && <>Nouveaux inscrits : <strong>{formatDec1(pctNouveaux)} %</strong>.</>}
          </Insight>
        </section>

        {/* ====================== INDICATEURS CLÉS ====================== */}
        <section className="mt-10">
          <SectionTitle>Indicateurs clés</SectionTitle>
          <table className="w-full break-inside-avoid border-collapse text-[13px]">
            <thead>
              <tr style={{ background: BLEU }} className="text-left text-white">
                <th className="px-3 py-2 font-semibold">Indicateur</th>
                <th className="px-3 py-2 text-right font-semibold">Valeur</th>
                <th className="px-3 py-2 text-right font-semibold">Variation {kpi("inscriptions")?.deltaLabel ?? ""}</th>
              </tr>
            </thead>
            <tbody>
              {data.kpis.map((k, i) => (
                <tr key={k.key} className={i % 2 ? "bg-neutral-50" : ""}>
                  <td className="border-b border-neutral-200 px-3 py-2 font-medium text-neutral-800">{k.label}</td>
                  <td className="border-b border-neutral-200 px-3 py-2 text-right tnum font-semibold" style={{ color: BLEU }}>
                    {fmtBy(k.value, k.format)}
                  </td>
                  <td className={`border-b border-neutral-200 px-3 py-2 text-right tnum ${k.delta == null ? "text-neutral-400" : k.delta >= 0 ? "text-green-700" : "text-red-600"}`}>
                    {deltaText(k.delta, k.format)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>

        {/* ====================== ÉVOLUTION ====================== */}
        {multiYear && (
          <section className="break-before-page pt-2">
            <SectionTitle>Évolution pluriannuelle</SectionTitle>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <ChartCard title={`Inscriptions par antenne · ${evoSpanLabel}`}>
                <EvolutionLine years={evo.years} series={evo.series} metric="inscriptions" />
              </ChartCard>
              {data.yoy && (
                <ChartCard title={`Recettes du réseau · ${evoSpanLabel}`}>
                  <GroupedYearBar rows={data.yoy.rows} metric="recettes" />
                </ChartCard>
              )}
            </div>
            <div className="mt-4">
              <Insight>
                {kpi("inscriptions")?.delta != null && (
                  <>Les inscriptions évoluent de <strong>{deltaText(kpi("inscriptions")!.delta, "int")}</strong> {kpi("inscriptions")!.deltaLabel}. </>
                )}
                {kpi("recettes")?.delta != null && (
                  <>Les recettes varient de <strong>{deltaText(kpi("recettes")!.delta, "int")}</strong> sur la même base. </>
                )}
                Lecture pluriannuelle sur {evo.years.length} exercices ({evoSpanLabel}).
              </Insight>
            </div>
          </section>
        )}

        {/* ====================== PAR ANTENNE ====================== */}
        <section className="mt-10">
          <SectionTitle>Performance par antenne</SectionTitle>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <ChartCard title="Inscriptions par antenne (IFI = réseau)">
              <AntennaBar
                rows={byAnt.map((a) => ({ code: a.code, color: a.color, value: a.inscriptions }))}
                label="Inscriptions"
              />
            </ChartCard>
            <div className="break-inside-avoid">
              <table className="w-full border-collapse text-[13px]">
                <thead>
                  <tr style={{ background: BLEU }} className="text-left text-white">
                    <th className="px-3 py-2 font-semibold">Antenne</th>
                    <th className="px-3 py-2 text-right font-semibold">Inscr.</th>
                    <th className="px-3 py-2 text-right font-semibold">Cours</th>
                    <th className="px-3 py-2 text-right font-semibold">Recettes</th>
                    <th className="px-3 py-2 text-right font-semibold">Rempl.</th>
                  </tr>
                </thead>
                <tbody>
                  {byAnt.map((a, i) => (
                    <tr key={a.code} className={i % 2 ? "bg-neutral-50" : ""}>
                      <td className="border-b border-neutral-200 px-3 py-2 font-medium">{a.code}</td>
                      <td className="border-b border-neutral-200 px-3 py-2 text-right tnum">{formatInt(a.inscriptions)}</td>
                      <td className="border-b border-neutral-200 px-3 py-2 text-right tnum">{formatInt(a.cours)}</td>
                      <td className="border-b border-neutral-200 px-3 py-2 text-right tnum">{formatEurCompact(a.recettes)}</td>
                      <td className="border-b border-neutral-200 px-3 py-2 text-right tnum">{formatDec1(a.remplissage)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
          <div className="mt-4">
            <Insight tone={lowGrow && lowGrow.g < -2 ? "warn" : "info"}>
              {topAnt && <><strong>{topAnt.name}</strong> est la première antenne du réseau ({formatInt(topAnt.inscriptions)} inscriptions). </>}
              {topGrow && lowGrow && topGrow.code !== lowGrow.code && (
                <>Sur {growYearsLabel} (années complètes), <strong>{topGrow.name}</strong> affiche {signed(topGrow.g)} et <strong>{lowGrow.name}</strong> {signed(lowGrow.g)}. </>
              )}
            </Insight>
          </div>
        </section>

        {/* ====================== PAR SECTEUR ====================== */}
        <section className="break-before-page pt-2">
          <SectionTitle>Analyse par secteur</SectionTitle>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <ChartCard title="Recettes par secteur (top)">
              <HBar
                data={sectorRows.slice(0, 8).map((s) => ({ name: s.secteur, value: s.recettes }))}
                unit="eur"
                color={BLEU}
                height={300}
              />
            </ChartCard>
            <div className="break-inside-avoid">
              <table className="w-full border-collapse text-[13px]">
                <thead>
                  <tr style={{ background: BLEU }} className="text-left text-white">
                    <th className="px-3 py-2 font-semibold">Secteur</th>
                    <th className="px-3 py-2 text-right font-semibold">Inscr.</th>
                    <th className="px-3 py-2 text-right font-semibold">Recettes</th>
                    <th className="px-3 py-2 text-right font-semibold">% rec.</th>
                  </tr>
                </thead>
                <tbody>
                  {sectorRows.map((s, i) => (
                    <tr key={s.secteur} className={i % 2 ? "bg-neutral-50" : ""}>
                      <td className="border-b border-neutral-200 px-3 py-2 font-medium">{s.secteur}</td>
                      <td className="border-b border-neutral-200 px-3 py-2 text-right tnum">{formatInt(s.inscriptions)}</td>
                      <td className="border-b border-neutral-200 px-3 py-2 text-right tnum">{formatEurCompact(s.recettes)}</td>
                      <td className="border-b border-neutral-200 px-3 py-2 text-right tnum">{recettes ? formatDec1((s.recettes / recettes) * 100) : "0"} %</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
          {topSector && (
            <div className="mt-4">
              <Insight>
                Secteur le plus contributeur : <strong>{topSector.secteur}</strong> — <strong>{formatEur(topSector.recettes)}</strong> de recettes (<strong>{formatDec1(topSectorShare)} %</strong> du total), {formatInt(topSector.inscriptions)} inscriptions.
              </Insight>
            </div>
          )}
        </section>

        {/* ====================== ACQUISITION & PANIER ====================== */}
        <section className="mt-10">
          <SectionTitle>Acquisition, fidélisation & panier moyen</SectionTitle>
          <div className="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
            {[
              { l: "Nouveaux inscrits", val: formatInt(nouveaux) },
              { l: "% nouveaux", val: `${formatDec1(pctNouveaux)} %` },
              ...(reinscrits ? [{ l: "Réinscrits", val: formatInt(reinscrits) }] : []),
              { l: "Panier / inscr.", val: panierI ? formatEur(panierI.value) : "—" },
              ...(panierP ? [{ l: "Panier / personne", val: formatEur(panierP.value) }] : []),
            ].slice(0, 4).map((c) => (
              <div key={c.l} className="break-inside-avoid rounded-sm border border-neutral-200 p-3">
                <div className="text-[10px] font-semibold uppercase tracking-[0.08em] text-neutral-500">{c.l}</div>
                <div className="mt-1 text-[22px] font-extrabold leading-none tnum" style={{ color: BLEU }}>{c.val}</div>
              </div>
            ))}
          </div>
          <Insight>
            Nouveaux inscrits : <strong>{formatDec1(pctNouveaux)} %</strong> des inscriptions{reinscrits ? <>, dont <strong>{formatInt(reinscrits)}</strong> réinscriptions</> : null}. Panier moyen : <strong>{panierI ? formatEur(panierI.value) : "—"}</strong>/inscription{panierP && <>, <strong>{formatEur(panierP.value)}</strong>/personne</>}.
          </Insight>
        </section>

        {/* ====================== ÉVOLUTION ANNÉE PAR ANNÉE ====================== */}
        {data.yoy && data.yoy.rows.length > 0 && (
          <section className="break-before-page pt-2">
            <SectionTitle>Évolution année par année</SectionTitle>
            <DataTable
              cols={[
                { k: "an", label: "Année" },
                { k: "ins", label: "Inscriptions", right: true },
                { k: "co", label: "Cours", right: true },
                { k: "re", label: "Recettes", right: true },
                { k: "he", label: "Heures-élèves", right: true },
                { k: "vi", label: "Δ inscr.", right: true },
                { k: "vr", label: "Δ recettes", right: true },
              ]}
              rows={data.yoy.rows.map((r) => ({
                an: yLabel(r.year, yearMode),
                ins: formatInt(r.inscriptions),
                co: formatInt(r.cours),
                re: formatEur(r.recettes),
                he: formatInt(r.heures),
                vi: deltaText(r.inscriptionsVar, "int") ?? "—",
                vr: deltaText(r.recettesVar, "int") ?? "—",
              }))}
            />
          </section>
        )}

        {/* ====================== RÉPARTITIONS ====================== */}
        {data.breakdowns && Object.keys(data.breakdowns).length > 0 && (
          <section className="mt-10">
            <SectionTitle>Répartitions</SectionTitle>
            <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
              {Object.values(data.breakdowns).map((bd) => (
                <DataTable
                  key={bd.key}
                  title={bd.label}
                  cols={[
                    { k: "l", label: bd.label },
                    { k: "ins", label: "Inscr.", right: true },
                    { k: "co", label: "Cours", right: true },
                    { k: "re", label: "Recettes", right: true },
                    { k: "rp", label: "Rempl.", right: true },
                  ]}
                  rows={bd.rows.map((r) => ({
                    l: r.label,
                    ins: formatInt(r.inscriptions),
                    co: formatInt(r.cours),
                    re: formatEurCompact(r.recettes),
                    rp: formatDec1(r.remplissage),
                  }))}
                />
              ))}
            </div>
          </section>
        )}

        {/* ====================== RENTABILITÉ ====================== */}
        {data.profitability && (data.profitability.byAntenna.length > 0 || data.profitability.bySector.length > 0) && (
          <section className="break-before-page pt-2">
            <SectionTitle>Rentabilité — recette moyenne par inscription (ARPI)</SectionTitle>
            <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
              {data.profitability.byAntenna.length > 0 && (
                <DataTable
                  title="Par antenne"
                  cols={[
                    { k: "c", label: "Antenne" },
                    { k: "ins", label: "Inscr.", right: true },
                    { k: "re", label: "Recettes", right: true },
                    { k: "ar", label: "ARPI", right: true },
                  ]}
                  rows={data.profitability.byAntenna.map((r) => ({
                    c: r.code,
                    ins: formatInt(r.inscriptions),
                    re: formatEurCompact(r.recettes),
                    ar: formatEur(r.arpi),
                  }))}
                />
              )}
              {data.profitability.bySector.length > 0 && (
                <DataTable
                  title="Par secteur"
                  cols={[
                    { k: "l", label: "Secteur" },
                    { k: "ins", label: "Inscr.", right: true },
                    { k: "re", label: "Recettes", right: true },
                    { k: "ar", label: "ARPI", right: true },
                  ]}
                  rows={data.profitability.bySector.map((r) => ({
                    l: r.label,
                    ins: formatInt(r.inscriptions),
                    re: formatEurCompact(r.recettes),
                    ar: formatEur(r.arpi),
                  }))}
                />
              )}
            </div>
          </section>
        )}

        <div className="mt-12 border-t border-neutral-200 pt-3 text-center text-[11px] tracking-[0.04em] text-neutral-500">
          Institut français Italia · <span className="font-semibold" style={{ color: BLEU }}>OSCAR — Rapport d'activité</span> · Données AEC au {updated} · Diffusion restreinte
        </div>
      </article>
    </div>
  );
}
