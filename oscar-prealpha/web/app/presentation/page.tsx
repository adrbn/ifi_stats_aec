"use client";

import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import Link from "next/link";
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
  return <div className="text-[14px] font-bold uppercase tracking-[0.2em]" style={{ color }}>{children}</div>;
}
function SlideHead({ title, sub }: { title: string; sub?: string }) {
  return (
    <div className="mb-8">
      <h2 className="flex items-center gap-3 text-[40px] font-extrabold leading-tight" style={{ color: BLEU }}>
        <span className="inline-block h-10 w-[7px] rounded-sm" style={{ background: BLEU }} />
        {title}
      </h2>
      {sub && <p className="mt-1 pl-[20px] text-[18px] text-neutral-500">{sub}</p>}
    </div>
  );
}

const PRINT_CSS = `
@media print {
  @page { size: A4 landscape; margin: 8mm; }
  html, body { background: #fff !important; }
  .pres-chrome, .pres-arrow { display: none !important; }
  .pres-root { position: static !important; height: auto !important; overflow: visible !important; display: block !important; z-index: auto !important; }
  .pres-scene { display: block !important; position: static !important; overflow: visible !important; height: auto !important; padding: 0 !important; }
  .pres-slide { position: relative !important; inset: auto !important; opacity: 1 !important; z-index: auto !important;
    height: 185mm !important; max-height: 185mm !important; overflow: hidden !important;
    display: flex !important; padding: 4mm !important; }
  /* saut AVANT chaque slide sauf la première (les flèches suivent les slides dans
     le DOM, donc :last-child ne cible pas la dernière slide → pas de page vide). */
  .pres-slide + .pres-slide { page-break-before: always !important; break-before: page !important; }
  * { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }
}`;

function buildDeckHtml(images: string[], title: string) {
  const sections = images
    .map((src, i) => `<section class="s${i === 0 ? " on" : ""}"><img alt="slide ${i + 1}" src="${src}"></section>`)
    .join("\n");
  return `<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>${title}</title>
<style>
  *{box-sizing:border-box;margin:0;padding:0}
  body{background:#1b1b1f;font-family:system-ui,Segoe UI,Roboto,sans-serif;height:100vh;overflow:hidden}
  #deck{height:100vh;display:flex;align-items:center;justify-content:center}
  section{display:none;width:100%;height:100%;align-items:center;justify-content:center;padding:24px}
  section.on{display:flex}
  img{max-width:100%;max-height:100%;object-fit:contain;background:#fff;box-shadow:0 10px 40px rgba(0,0,0,.4);border-radius:6px}
  .bar{position:fixed;left:0;right:0;bottom:0;display:flex;align-items:center;justify-content:center;gap:18px;padding:12px;color:#fff;font-size:14px;background:rgba(0,0,0,.35)}
  .bar button{background:#fff;color:#000091;border:0;border-radius:6px;padding:8px 14px;font-weight:700;cursor:pointer}
  .ct{min-width:56px;text-align:center;font-variant-numeric:tabular-nums}
  @media print{ @page{size:A4 landscape;margin:0} body{background:#fff;height:auto;overflow:visible} #deck{display:block;height:auto} section{display:flex !important;page-break-after:always;height:100vh;padding:0} .bar{display:none} img{box-shadow:none;border-radius:0} }
</style></head><body>
<div id="deck">${sections}</div>
<div class="bar">
  <button onclick="go(-1)">‹ Précédent</button>
  <span class="ct"><span id="i">1</span> / ${images.length}</span>
  <button onclick="go(1)">Suivant ›</button>
  <button onclick="if(document.fullscreenElement){document.exitFullscreen()}else{document.documentElement.requestFullscreen()}">Plein écran</button>
  <button onclick="window.print()">Imprimer / PDF</button>
</div>
<script>
  var n=${images.length},c=0,S=document.querySelectorAll('#deck section');
  function show(){S.forEach(function(e,k){e.classList.toggle('on',k===c)});document.getElementById('i').textContent=c+1}
  function go(d){c=Math.max(0,Math.min(n-1,c+d));show()}
  document.addEventListener('keydown',function(e){if(e.key==='ArrowRight'||e.key===' '){go(1)}else if(e.key==='ArrowLeft'){go(-1)}});
</script>
</body></html>`;
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

  // ── Slides ──
  const slides: { key: string; node: ReactNode }[] = [];
  slides.push({
    key: "cover",
    node: (
      <div className="text-center">
        <div className="mb-12 flex items-center justify-center gap-14">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/rf-logo.png" alt="République française" className="h-28 w-auto" />
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/ifi-logo.png" alt="Institut français Italia" className="h-24 w-auto" />
        </div>
        <Eyebrow color={ROUGE}>Document interne</Eyebrow>
        <h1 className="mt-4 text-[84px] font-extrabold leading-none" style={{ color: BLEU }}>Rapport d'activité</h1>
        <div className="mx-auto mt-7 h-[5px] w-[300px]" style={{ background: BLEU }} />
        <p className="mt-7 text-[28px] text-neutral-500">Réseau de l'Institut français Italia</p>
        <p className="mt-1 text-[36px] font-bold" style={{ color: BLEU }}>{periodLabel} · Cours</p>
        <p className="mt-10 text-[16px] text-neutral-400">{antLabel}</p>
      </div>
    ),
  });
  slides.push({
    key: "kpis",
    node: (
      <div className="w-full">
        <SlideHead title="Les chiffres clés" sub={periodLabel} />
        <div className="grid grid-cols-2 gap-6 md:grid-cols-3">
          {data.kpis.map((k) => (
            <div key={k.key} className="rounded-lg border border-neutral-200 px-7 py-6">
              <div className="text-[13px] font-semibold uppercase tracking-[0.08em] text-neutral-500">{k.label}</div>
              <div className="mt-2 text-[46px] font-extrabold leading-none tnum" style={{ color: BLEU }}>
                {k.key === "recettes" || k.key.startsWith("panier") ? formatEurCompact(k.value) : fmtBy(k.value, k.format)}
              </div>
              {k.delta != null && (
                <div className={`mt-2 text-[14px] font-semibold ${k.delta >= 0 ? "text-green-700" : "text-red-600"}`}>
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
          <EvolutionLine years={evo.years} series={evo.series} metric="inscriptions" height={470} />
          {partialLatest && (
            <p className="mt-3 text-[15px] text-neutral-500">
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
        <AntennaBar rows={byAnt.map((a) => ({ code: a.code, color: a.color, value: a.inscriptions }))} label="Inscriptions" height={440} />
        <p className="mt-3 text-[18px] text-neutral-700">
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
        <HBar data={sectorRows.slice(0, 8).map((s) => ({ name: s.secteur, value: s.recettes }))} unit="eur" color={BLEU} height={460} />
        {topSector && (
          <p className="mt-3 text-[18px] text-neutral-700">
            <strong style={{ color: BLEU }}>{topSector.secteur}</strong> pèse {formatDec1(topSectorShare)} % des recettes ({formatEur(topSector.recettes)}).
          </p>
        )}
      </div>
    ),
  });
  if (data.yoy && data.yoy.rows.length > 0)
    slides.push({
      key: "yoy",
      node: (
        <div className="w-full">
          <SlideHead title="Évolution année par année" />
          <table className="w-full border-collapse text-[18px]">
            <thead>
              <tr style={{ background: BLEU }} className="text-left text-white">
                <th className="px-4 py-2.5 font-semibold">Année</th>
                <th className="px-4 py-2.5 text-right font-semibold">Inscriptions</th>
                <th className="px-4 py-2.5 text-right font-semibold">Cours</th>
                <th className="px-4 py-2.5 text-right font-semibold">Recettes</th>
                <th className="px-4 py-2.5 text-right font-semibold">Δ inscr.</th>
                <th className="px-4 py-2.5 text-right font-semibold">Δ recettes</th>
              </tr>
            </thead>
            <tbody>
              {data.yoy!.rows.map((r, k) => (
                <tr key={r.year} className={k % 2 ? "bg-neutral-50" : ""}>
                  <td className="border-b border-neutral-200 px-4 py-2.5 font-semibold">{yLabel(r.year, yearMode)}</td>
                  <td className="border-b border-neutral-200 px-4 py-2.5 text-right tnum">{formatInt(r.inscriptions)}</td>
                  <td className="border-b border-neutral-200 px-4 py-2.5 text-right tnum">{formatInt(r.cours)}</td>
                  <td className="border-b border-neutral-200 px-4 py-2.5 text-right tnum">{formatEurCompact(r.recettes)}</td>
                  <td className="border-b border-neutral-200 px-4 py-2.5 text-right tnum">{deltaText(r.inscriptionsVar, "int") ?? "—"}</td>
                  <td className="border-b border-neutral-200 px-4 py-2.5 text-right tnum">{deltaText(r.recettesVar, "int") ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ),
    });
  slides.push({
    key: "acq",
    node: (
      <div className="w-full">
        <SlideHead title="Acquisition, fidélisation & panier" sub={periodLabel} />
        <div className="grid grid-cols-2 gap-7 md:grid-cols-4">
          {[
            { l: "Nouveaux inscrits", val: formatInt(nouveaux) },
            { l: "% nouveaux", val: `${formatDec1(pctNouveaux)} %` },
            ...(reinscrits ? [{ l: "Réinscrits", val: formatInt(reinscrits) }] : []),
            { l: "Panier / inscr.", val: panierI ? formatEur(panierI.value) : "—" },
            ...(panierP ? [{ l: "Panier / personne", val: formatEur(panierP.value) }] : []),
          ]
            .slice(0, 4)
            .map((c) => (
              <div key={c.l} className="rounded-lg border border-neutral-200 px-6 py-7 text-center">
                <div className="text-[13px] font-semibold uppercase tracking-[0.08em] text-neutral-500">{c.l}</div>
                <div className="mt-2 text-[44px] font-extrabold leading-none tnum" style={{ color: BLEU }}>{c.val}</div>
              </div>
            ))}
        </div>
        <p className="mt-9 text-[20px] leading-relaxed text-neutral-700">
          Nouveaux inscrits : <strong>{formatDec1(pctNouveaux)} %</strong> des inscriptions{reinscrits ? <>, dont <strong>{formatInt(reinscrits)}</strong> réinscriptions</> : null}. Panier moyen :{" "}
          <strong style={{ color: BLEU }}>{panierI ? formatEur(panierI.value) : "—"}</strong>/inscription{panierP ? <>, {formatEur(panierP.value)}/personne</> : null}.
        </p>
      </div>
    ),
  });
  if (data.profitability && data.profitability.byAntenna.length > 0)
    slides.push({
      key: "renta",
      node: (
        <div className="w-full">
          <SlideHead title="Rentabilité — recette par inscription" sub="ARPI par antenne" />
          <table className="w-full border-collapse text-[19px]">
            <thead>
              <tr style={{ background: BLEU }} className="text-left text-white">
                <th className="px-4 py-3 font-semibold">Antenne</th>
                <th className="px-4 py-3 text-right font-semibold">Inscriptions</th>
                <th className="px-4 py-3 text-right font-semibold">Recettes</th>
                <th className="px-4 py-3 text-right font-semibold">ARPI</th>
              </tr>
            </thead>
            <tbody>
              {data.profitability!.byAntenna.map((r, k) => (
                <tr key={r.code} className={k % 2 ? "bg-neutral-50" : ""}>
                  <td className="border-b border-neutral-200 px-4 py-3 font-semibold">{r.code}</td>
                  <td className="border-b border-neutral-200 px-4 py-3 text-right tnum">{formatInt(r.inscriptions)}</td>
                  <td className="border-b border-neutral-200 px-4 py-3 text-right tnum">{formatEurCompact(r.recettes)}</td>
                  <td className="border-b border-neutral-200 px-4 py-3 text-right tnum">{formatEur(r.arpi)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ),
    });
  slides.push({
    key: "faits",
    node: (
      <div className="w-full">
        <SlideHead title="Faits marquants" sub="Chiffres clés du périmètre" />
        <ul className="space-y-4 text-[21px] leading-relaxed text-neutral-800">
          {topAnt && (
            <li>Première antenne : <strong style={{ color: BLEU }}>{topAnt.name}</strong> — {formatInt(topAnt.inscriptions)} inscriptions{inscriptions ? <> ({formatDec1((topAnt.inscriptions / inscriptions) * 100)} % du réseau)</> : null}.</li>
          )}
          {topSector && (
            <li>Secteur le plus contributeur : <strong style={{ color: BLEU }}>{topSector.secteur}</strong> — {formatDec1(topSectorShare)} % des recettes.</li>
          )}
          {topGrow && lowGrow && topGrow.code !== lowGrow.code && (
            <li>Variations {growYearsLabel} : {topGrow.name} {signed(topGrow.g)} · {lowGrow.name} {signed(lowGrow.g)}.</li>
          )}
          <li>Nouveaux inscrits : <strong>{formatDec1(pctNouveaux)} %</strong>{reinscrits ? <> · {formatInt(reinscrits)} réinscriptions</> : null}.</li>
          {panierI && <li>Panier moyen : <strong>{formatEur(panierI.value)}</strong>/inscription{panierP ? <> · {formatEur(panierP.value)}/personne</> : null}.</li>}
          {remplKpi && <li>Remplissage moyen : <strong>{formatDec1(remplKpi.value)}</strong> élèves/cours.</li>}
        </ul>
      </div>
    ),
  });
  slides.push({
    key: "end",
    node: (
      <div className="text-center">
        <div className="text-[72px] font-extrabold" style={{ color: BLEU }}>Merci.</div>
        <p className="mt-4 text-[20px] text-neutral-500">Institut français Italia · OSCAR — Rapport d'activité</p>
        <p className="mt-1 text-[15px] text-neutral-400">Diffusion restreinte · données AEC « Tous les cours »</p>
      </div>
    ),
  });

  // ── Navigation / état ──
  const n = slides.length;
  const [i, setI] = useState(0);
  const [busy, setBusy] = useState(false);
  const idx = Math.min(i, n - 1);
  const go = useCallback((d: number) => setI((p) => Math.max(0, Math.min(n - 1, p + d))), [n]);
  const sceneRef = useRef<HTMLDivElement>(null);

  const toggleFs = useCallback(() => {
    try {
      if (!document.fullscreenElement) document.documentElement.requestFullscreen();
      else document.exitFullscreen();
    } catch {
      /* no-op */
    }
  }, []);

  const exportHtml = useCallback(async () => {
    setBusy(true);
    try {
      const { toPng } = await import("html-to-image");
      const els = Array.from(sceneRef.current?.querySelectorAll<HTMLElement>(".pres-capture") ?? []);
      const imgs: string[] = [];
      for (const el of els) {
        // eslint-disable-next-line no-await-in-loop
        imgs.push(await toPng(el, { pixelRatio: 2, backgroundColor: "#ffffff", skipFonts: true }));
      }
      const html = buildDeckHtml(imgs, `OSCAR — Rapport d'activité ${periodLabel}`);
      const blob = new Blob([html], { type: "text/html" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `presentation-oscar-${periodLabel.replace(/[^\w-]+/g, "_")}.html`;
      a.click();
      URL.revokeObjectURL(url);
    } finally {
      setBusy(false);
    }
  }, [periodLabel]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "ArrowRight" || e.key === " " || e.key === "PageDown") { e.preventDefault(); go(1); }
      else if (e.key === "ArrowLeft" || e.key === "PageUp") { e.preventDefault(); go(-1); }
      else if (e.key.toLowerCase() === "f") toggleFs();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [go, toggleFs]);

  const btn = "rounded-md border border-neutral-200 px-3 py-1.5 text-[13px] font-medium text-neutral-600 transition hover:border-neutral-300 hover:text-neutral-900 disabled:opacity-40";

  return (
    <div className="pres-root fixed inset-0 z-50 flex flex-col bg-white">
      <style dangerouslySetInnerHTML={{ __html: PRINT_CSS }} />

      {/* En-tête */}
      <div className="pres-chrome flex items-center justify-between border-b border-neutral-200 px-6 py-3">
        <span className="text-[12px] font-bold uppercase tracking-[0.16em]" style={{ color: BLEU }}>OSCAR · Présentation</span>
        <div className="flex items-center gap-2.5">
          <button onClick={exportHtml} disabled={busy} className={btn}>{busy ? "Export…" : "⬇ HTML"}</button>
          <button onClick={() => window.print()} className={btn}>⬇ PDF</button>
          <button onClick={toggleFs} className={btn}>⛶ Plein écran</button>
          <Link href="/rapport" className={btn}>↩ Rapport</Link>
          <Link href="/cours/synthese" className={btn}>✕ Quitter</Link>
        </div>
      </div>

      {/* Scène : toutes les slides montées (active visible) → permet impression + export */}
      <div ref={sceneRef} className="pres-scene relative flex flex-1 items-center justify-center overflow-hidden">
        {slides.map((s, k) => (
          <div
            key={s.key}
            className={`pres-slide absolute inset-0 flex items-center justify-center overflow-y-auto px-12 py-6 transition-opacity duration-300 ${
              k === idx ? "z-10 opacity-100" : "pointer-events-none opacity-0"
            }`}
          >
            <div className="pres-capture mx-auto w-full max-w-[1240px] bg-white">
              {s.node}
            </div>
          </div>
        ))}
        <button aria-label="Précédent" onClick={() => go(-1)} disabled={idx === 0}
          className="pres-arrow absolute left-3 top-1/2 z-20 -translate-y-1/2 rounded-full border border-neutral-200 bg-white/80 px-3 py-2 text-neutral-600 shadow-sm transition hover:text-neutral-900 disabled:opacity-30">‹</button>
        <button aria-label="Suivant" onClick={() => go(1)} disabled={idx === n - 1}
          className="pres-arrow absolute right-3 top-1/2 z-20 -translate-y-1/2 rounded-full border border-neutral-200 bg-white/80 px-3 py-2 text-neutral-600 shadow-sm transition hover:text-neutral-900 disabled:opacity-30">›</button>
      </div>

      {/* Pied */}
      <div className="pres-chrome flex items-center justify-between border-t border-neutral-200 px-6 py-3">
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
