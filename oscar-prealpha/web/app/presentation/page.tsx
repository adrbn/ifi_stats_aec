"use client";

import { useCallback, useEffect, useState, type ReactNode } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import { useSnapshot } from "@/lib/useSnapshot";
import { useFilters } from "@/lib/store";
import { AntennaBar, HBar, EvolutionLine } from "@/components/Charts";
import { formatInt, formatEur, formatEurCompact, formatDec1 } from "@/lib/format";

const BLEU = "#000091";
const ROUGE = "#e1000f";

function yLabel(y: number, mode: string) {
  return mode === "school" ? `${y}-${String((y + 1) % 100).padStart(2, "0")}` : String(y);
}
const fmtBy = (v: number, f?: string) =>
  f === "eur" ? formatEur(v) : f === "dec1" ? formatDec1(v) : formatInt(v);
const deltaText = (d: number | null, fmt?: string) =>
  d == null ? null : `${d > 0 ? "+" : d < 0 ? "−" : ""}${formatDec1(Math.abs(d))}${fmt === "dec1" ? "" : " %"}`;

function Eyebrow({ children, color = "#6b7280" }: { children: ReactNode; color?: string }) {
  return <div className="text-[13px] font-bold uppercase tracking-[0.2em]" style={{ color }}>{children}</div>;
}
function SlideHead({ title, sub }: { title: string; sub?: string }) {
  return (
    <div className="mb-8">
      <h2 className="flex items-center gap-3 text-[34px] font-extrabold leading-tight" style={{ color: BLEU }}>
        <span className="inline-block h-9 w-[6px] rounded-sm" style={{ background: BLEU }} />
        {title}
      </h2>
      {sub && <p className="mt-1 pl-[18px] text-[16px] text-neutral-500">{sub}</p>}
    </div>
  );
}

export default function PresentationPage() {
  const { data } = useSnapshot();
  const yearMode = useFilters((s) => s.yearMode);

  // ── Dérivations (mêmes règles que le rapport) ──
  const years = data.filters.years ?? [];
  const allYears = data.meta.years ?? [];
  const sortedYears = [...years].sort((a, b) => a - b);
  const periodLabel = (() => {
    const ys = sortedYears.length ? sortedYears : allYears;
    if (!ys.length) return "—";
    if (ys.length === 1) return `Année ${yLabel(ys[0], yearMode)}`;
    return `${yLabel(ys[0], yearMode)} → ${yLabel(ys[ys.length - 1], yearMode)}`;
  })();
  const ants = data.filters.antennas ?? [];
  const antLabel = ants.length >= 4 ? "Réseau complet (IFM · IFF · IFN · IFP)" : ants.join(" · ") || "—";

  const kpi = (k: string) => data.kpis.find((x) => x.key === k);
  const v = (k: string) => kpi(k)?.value ?? 0;
  const inscriptions = v("inscriptions");
  const recettes = v("recettes");
  const panierI = kpi("panier_inscr");
  const panierP = kpi("panier_pers");
  const remplKpi = kpi("remplissage");

  const sumInd = (k: string) => (data.byAntennaIndicator?.[k] ?? []).reduce((s, r) => s + r.value, 0);
  const nouveaux = sumInd("nouveaux") || (data.sectors?.total?.nouv ?? 0);
  const reinscrits = sumInd("reinscrits");
  const pctNouveaux = inscriptions ? (nouveaux / inscriptions) * 100 : 0;

  const evo = data.evolution;
  const eyears = evo?.years ?? [];
  const multiYear = eyears.length >= 2;
  const nowY = new Date().getFullYear();
  const latestYear = eyears.length ? Math.max(...eyears) : null;
  const partialLatest = latestYear != null && (yearMode === "school" ? latestYear >= nowY - 1 : latestYear >= nowY);
  const latestLabel = latestYear != null ? yLabel(latestYear, yearMode) : "";
  const curIdx = eyears.length - 1 - (partialLatest ? 1 : 0);
  const canGrow = curIdx >= 1;
  const growYearsLabel = canGrow ? `${yLabel(eyears[curIdx], yearMode)} vs ${yLabel(eyears[curIdx - 1], yearMode)}` : "";
  const antGrowth = canGrow
    ? ((evo.series ?? [])
        .map((s) => {
          const a = s.inscriptions ?? [];
          const cur = a[curIdx];
          const prev = a[curIdx - 1];
          return prev != null && prev !== 0 && cur != null ? { code: s.code, name: s.name, g: ((cur - prev) / prev) * 100 } : null;
        })
        .filter(Boolean) as { code: string; name: string; g: number }[])
    : [];
  const topGrow = antGrowth.length ? [...antGrowth].sort((a, b) => b.g - a.g)[0] : null;
  const lowGrow = antGrowth.length ? [...antGrowth].sort((a, b) => a.g - b.g)[0] : null;
  const signed = (g: number) => `${g > 0 ? "+" : g < 0 ? "−" : ""}${formatDec1(Math.abs(g))} %`;

  const sectorRows = [...(data.sectors?.rows ?? [])].sort((a, b) => b.recettes - a.recettes);
  const topSector = sectorRows[0];
  const topSectorShare = topSector && recettes ? (topSector.recettes / recettes) * 100 : 0;
  const byAnt = data.byAntenna ?? [];
  const topAnt = [...byAnt].sort((a, b) => b.inscriptions - a.inscriptions)[0];

  const reco: string[] = [];
  if (lowGrow && lowGrow.g < -2) reco.push(`Prioriser l'antenne ${lowGrow.name} (repli de ${signed(lowGrow.g)} sur ${growYearsLabel}) : acquisition ciblée.`);
  if (topGrow && topGrow.g > 2) reco.push(`Diffuser au réseau les leviers de ${topGrow.name} (${signed(topGrow.g)} sur ${growYearsLabel}).`);
  if (pctNouveaux < 35) reco.push(`Renforcer l'acquisition : ${formatDec1(pctNouveaux)} % de nouveaux inscrits seulement.`);
  else reco.push(`Structurer la fidélisation : ${formatDec1(pctNouveaux)} % de nouveaux — sécuriser la réinscription.`);
  if (remplKpi && remplKpi.value < 12) reco.push(`Optimiser le remplissage (${formatDec1(remplKpi.value)} élèves/cours).`);
  if (topSector) reco.push(`Consolider le secteur « ${topSector.secteur} » (${formatDec1(topSectorShare)} % des recettes).`);
  if (panierI) reco.push(`Activer des leviers de panier moyen (${formatEur(panierI.value)}/inscription).`);

  // ── Slides ──
  const slides: { key: string; node: ReactNode }[] = [];

  slides.push({
    key: "cover",
    node: (
      <div className="text-center">
        <div className="mb-12 flex items-center justify-center gap-12">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/rf-logo.png" alt="République française" className="h-24 w-auto" />
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/ifi-logo.png" alt="Institut français Italia" className="h-20 w-auto" />
        </div>
        <Eyebrow color={ROUGE}>Document interne</Eyebrow>
        <h1 className="mt-4 text-[72px] font-extrabold leading-none" style={{ color: BLEU }}>Rapport d'activité</h1>
        <div className="mx-auto mt-6 h-[4px] w-[260px]" style={{ background: BLEU }} />
        <p className="mt-6 text-[24px] text-neutral-500">Réseau de l'Institut français Italia</p>
        <p className="mt-1 text-[30px] font-bold" style={{ color: BLEU }}>{periodLabel} · Cours</p>
        <p className="mt-10 text-[14px] text-neutral-400">{antLabel}</p>
      </div>
    ),
  });

  slides.push({
    key: "kpis",
    node: (
      <div className="w-full">
        <SlideHead title="Les chiffres clés" sub={periodLabel} />
        <div className="grid grid-cols-2 gap-5 md:grid-cols-3">
          {data.kpis.map((k) => (
            <div key={k.key} className="rounded-lg border border-neutral-200 px-6 py-5">
              <div className="text-[12px] font-semibold uppercase tracking-[0.08em] text-neutral-500">{k.label}</div>
              <div className="mt-2 text-[40px] font-extrabold leading-none tnum" style={{ color: BLEU }}>
                {k.key === "recettes" || k.key.startsWith("panier") ? formatEurCompact(k.value) : fmtBy(k.value, k.format)}
              </div>
              {k.delta != null && (
                <div className={`mt-2 text-[13px] font-semibold ${k.delta >= 0 ? "text-green-700" : "text-red-600"}`}>
                  {deltaText(k.delta, k.format)} {k.deltaLabel}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    ),
  });

  if (multiYear)
    slides.push({
      key: "evo",
      node: (
        <div className="w-full">
          <SlideHead title="Évolution pluriannuelle" sub={`Inscriptions par antenne · ${yLabel(eyears[0], yearMode)} → ${latestLabel}`} />
          <div className="h-[440px] w-full">
            <EvolutionLine years={evo.years} series={evo.series} metric="inscriptions" />
          </div>
          {partialLatest && (
            <p className="mt-4 text-[14px] text-neutral-500">
              ⚠️ L'année {latestLabel} est en cours (données partielles) — les variations citées portent sur les années complètes.
            </p>
          )}
        </div>
      ),
    });

  slides.push({
    key: "antennes",
    node: (
      <div className="w-full">
        <SlideHead title="Performance par antenne" sub="IFI = total réseau" />
        <div className="h-[400px] w-full">
          <AntennaBar rows={byAnt.map((a) => ({ code: a.code, color: a.color, value: a.inscriptions }))} label="Inscriptions" />
        </div>
        <p className="mt-3 text-[16px] text-neutral-700">
          {topAnt && <><strong style={{ color: BLEU }}>{topAnt.name}</strong> est la première antenne ({formatInt(topAnt.inscriptions)} inscriptions). </>}
          {topGrow && lowGrow && topGrow.code !== lowGrow.code && <>Sur {growYearsLabel} : {topGrow.name} {signed(topGrow.g)} · {lowGrow.name} {signed(lowGrow.g)}.</>}
        </p>
      </div>
    ),
  });

  slides.push({
    key: "secteurs",
    node: (
      <div className="w-full">
        <SlideHead title="Analyse par secteur" sub="Recettes par secteur" />
        <div className="h-[420px] w-full">
          <HBar data={sectorRows.slice(0, 8).map((s) => ({ name: s.secteur, value: s.recettes }))} unit="eur" color={BLEU} height={420} />
        </div>
        {topSector && (
          <p className="mt-3 text-[16px] text-neutral-700">
            <strong style={{ color: BLEU }}>{topSector.secteur}</strong> pèse {formatDec1(topSectorShare)} % des recettes ({formatEur(topSector.recettes)}).
          </p>
        )}
      </div>
    ),
  });

  slides.push({
    key: "acq",
    node: (
      <div className="w-full">
        <SlideHead title="Acquisition, fidélisation & panier" sub={periodLabel} />
        <div className="grid grid-cols-2 gap-6 md:grid-cols-4">
          {[
            { l: "Nouveaux inscrits", val: formatInt(nouveaux) },
            { l: "% nouveaux", val: `${formatDec1(pctNouveaux)} %` },
            ...(reinscrits ? [{ l: "Réinscrits", val: formatInt(reinscrits) }] : []),
            { l: "Panier / inscr.", val: panierI ? formatEur(panierI.value) : "—" },
            ...(panierP ? [{ l: "Panier / personne", val: formatEur(panierP.value) }] : []),
          ]
            .slice(0, 4)
            .map((c) => (
              <div key={c.l} className="rounded-lg border border-neutral-200 px-6 py-6 text-center">
                <div className="text-[12px] font-semibold uppercase tracking-[0.08em] text-neutral-500">{c.l}</div>
                <div className="mt-2 text-[38px] font-extrabold leading-none tnum" style={{ color: BLEU }}>{c.val}</div>
              </div>
            ))}
        </div>
        <p className="mt-8 text-[18px] leading-relaxed text-neutral-700">
          <strong>{formatDec1(pctNouveaux)} %</strong> des inscriptions proviennent de nouveaux publics. Le panier moyen de{" "}
          <strong style={{ color: BLEU }}>{panierI ? formatEur(panierI.value) : "—"}</strong>/inscription est un levier direct sur les recettes.
        </p>
      </div>
    ),
  });

  slides.push({
    key: "reco",
    node: (
      <div className="w-full">
        <SlideHead title="Recommandations" sub="Pistes d'action prioritaires" />
        <ul className="space-y-4">
          {reco.map((r, idx) => (
            <li key={idx} className="flex items-start gap-4 text-[19px] leading-relaxed text-neutral-800">
              <span className="mt-0.5 flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full text-[15px] font-bold text-white" style={{ background: BLEU }}>{idx + 1}</span>
              <span>{r}</span>
            </li>
          ))}
        </ul>
      </div>
    ),
  });

  slides.push({
    key: "end",
    node: (
      <div className="text-center">
        <div className="text-[64px] font-extrabold" style={{ color: BLEU }}>Merci.</div>
        <p className="mt-4 text-[18px] text-neutral-500">Institut français Italia · OSCAR — Rapport d'activité</p>
        <p className="mt-1 text-[14px] text-neutral-400">Diffusion restreinte · données AEC « Tous les cours »</p>
      </div>
    ),
  });

  // ── Navigation ──
  const n = slides.length;
  const [i, setI] = useState(0);
  const idx = Math.min(i, n - 1);
  const go = useCallback((d: number) => setI((p) => Math.max(0, Math.min(n - 1, p + d))), [n]);

  const toggleFs = useCallback(() => {
    try {
      if (!document.fullscreenElement) document.documentElement.requestFullscreen();
      else document.exitFullscreen();
    } catch {
      /* no-op */
    }
  }, []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "ArrowRight" || e.key === " " || e.key === "PageDown") { e.preventDefault(); go(1); }
      else if (e.key === "ArrowLeft" || e.key === "PageUp") { e.preventDefault(); go(-1); }
      else if (e.key.toLowerCase() === "f") toggleFs();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [go, toggleFs]);

  return (
    <div className="fixed inset-0 z-50 flex flex-col bg-white">
      {/* En-tête fin */}
      <div className="flex items-center justify-between border-b border-neutral-200 px-6 py-3">
        <span className="text-[12px] font-bold uppercase tracking-[0.16em]" style={{ color: BLEU }}>OSCAR · Présentation</span>
        <div className="flex items-center gap-4">
          <button onClick={toggleFs} className="text-[13px] font-medium text-neutral-500 hover:text-neutral-900">⛶ Plein écran</button>
          <Link href="/cours/synthese" className="text-[13px] font-medium text-neutral-500 hover:text-neutral-900">✕ Quitter</Link>
        </div>
      </div>

      {/* Scène */}
      <div className="relative flex flex-1 items-center justify-center overflow-hidden px-10 py-8">
        <AnimatePresence mode="wait">
          <motion.div
            key={slides[idx].key}
            initial={{ opacity: 0, x: 28 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -28 }}
            transition={{ duration: 0.28, ease: [0.16, 1, 0.3, 1] }}
            className="mx-auto w-full max-w-[1080px]"
          >
            {slides[idx].node}
          </motion.div>
        </AnimatePresence>

        {/* Zones de clic préc/suiv */}
        <button aria-label="Précédent" onClick={() => go(-1)} disabled={idx === 0}
          className="absolute left-3 top-1/2 -translate-y-1/2 rounded-full border border-neutral-200 bg-white/80 px-3 py-2 text-neutral-600 shadow-sm transition hover:text-neutral-900 disabled:opacity-30">‹</button>
        <button aria-label="Suivant" onClick={() => go(1)} disabled={idx === n - 1}
          className="absolute right-3 top-1/2 -translate-y-1/2 rounded-full border border-neutral-200 bg-white/80 px-3 py-2 text-neutral-600 shadow-sm transition hover:text-neutral-900 disabled:opacity-30">›</button>
      </div>

      {/* Pied : progression + points */}
      <div className="flex items-center justify-between border-t border-neutral-200 px-6 py-3">
        <div className="flex gap-1.5">
          {slides.map((s, k) => (
            <button key={s.key} aria-label={`Diapo ${k + 1}`} onClick={() => setI(k)}
              className="h-2 rounded-full transition-all" style={{ width: k === idx ? 22 : 8, background: k === idx ? BLEU : "#cbd5e1" }} />
          ))}
        </div>
        <div className="tnum text-[13px] font-semibold text-neutral-500">{idx + 1} / {n}</div>
      </div>
    </div>
  );
}
