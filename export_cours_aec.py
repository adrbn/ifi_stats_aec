#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
export_cours_aec.py — exporte « Cours > Tous les cours » (grille brute, 1 ligne
= 1 cours) pour TOUS les centres et TOUTES les périodes → data/new_cours/.

Login ROBUSTE & persistant :
  • Profil Chrome persistant (login mémorisé d'un run à l'autre).
  • Détection « connecté » fiable : présence du sélecteur de centre
    [test="change_etablishment_branch_and_point_sale"] sur N'IMPORTE quel onglet
    (corrige le bug de l'onglet surveillé).
  • Sur la page de login : coche « Rester connecté » (sans jamais cliquer
    « Connexion » ni taper) → la session persiste.
  • Après connexion : sauvegarde aussi storage_state (cookies) dans
    data/new_cours/aec_state.json (filet de sécurité anti-retape).

Filtres auto : Établissement=tous, Période=toutes, Statut laissé sur « Tous ».
Après export : vérification (lignes, centres, plage de dates).
"""
from __future__ import annotations
import os, time, json
from pathlib import Path
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
import aec_login

BASE = "https://ifitalie.aec.app/"
ROUTE = "#/course/all-courses"
PROFIL = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "aec_exporter_profil_chrome"
OUT = Path(__file__).parent / "data" / "new_cours"
OUT.mkdir(parents=True, exist_ok=True)
LOG = OUT / "_export.log"
STATE = OUT / "aec_state.json"
APP_MARKER = '[test="change_etablishment_branch_and_point_sale"]'
DL = {"court": 0.5, "moyen": 1.2, "long": 2.0, "page": 3.0}


def log(m: str) -> None:
    line = f"[{datetime.now():%H:%M:%S}] {m}"
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def pause(t="court"):
    time.sleep(DL.get(t, 0.5))


def attendre_preload(page, t=90):
    fin = time.time() + t
    while time.time() < fin:
        try:
            n = page.evaluate("""() => {let nb=0;document.querySelectorAll('atl-preload').forEach(p=>{const s=getComputedStyle(p);if(s.display!=='none'&&s.visibility!=='hidden'&&p.offsetParent!==null)nb++;});return nb;}""")
            if n == 0:
                return
        except Exception:
            pass
        time.sleep(0.5)


def page_connectee(ctx):
    """Renvoie le 1er onglet où l'appli (header centre) est présente, sinon None."""
    for pg in list(ctx.pages):
        try:
            if pg.locator(APP_MARKER).count() > 0:
                return pg
        except Exception:
            continue
    return None


def cocher_rester_connecte(ctx):
    for pg in list(ctx.pages):
        try:
            if "/login" not in (pg.url or ""):
                continue
            for sel in ('label:has-text("Rester connecté") input[type="checkbox"]',
                        'input[type="checkbox"]'):
                loc = pg.locator(sel)
                if loc.count() > 0:
                    try:
                        if not loc.first.is_checked():
                            loc.first.check(timeout=1500)
                            return True
                    except Exception:
                        continue
        except Exception:
            continue
    return False


def attendre_login(ctx, t=600):
    fin = time.time() + t
    coche = False
    averti = False
    while time.time() < fin:
        pg = page_connectee(ctx)
        if pg:
            return pg
        if not coche:
            coche = cocher_rester_connecte(ctx)
            if coche:
                log("  ✓ « Rester connecté » coché — login mémorisé après ce coup-ci.")
        if not averti:
            averti = True
            log("  👉 CONNECTE-TOI dans la fenêtre (Alt+Tab si cachée). Je ne touche pas au formulaire.")
        time.sleep(2)
    return None


def sauver_session(ctx):
    try:
        ctx.storage_state(path=str(STATE))
        log(f"  💾 session sauvegardée → {STATE.name} (filet anti-retape)")
    except Exception as e:
        log(f"  (sauvegarde session impossible: {e})")


def aller_all_courses(page):
    if "all-courses" not in (page.url or ""):
        try:
            page.locator('a[test="menu_bar_classe_all"]').first.click()
        except Exception:
            page.goto(BASE + ROUTE)
    attendre_preload(page)
    page.wait_for_selector('button[test="export"]', timeout=40000)
    pause("page")


def dump_popup(page, nom):
    try:
        items = page.evaluate("""() => {
            const out=[];
            document.querySelectorAll('kendo-popup,.k-animation-container,.k-popup').forEach(c=>{
                const s=getComputedStyle(c); if(s.display==='none') return;
                c.querySelectorAll('li,[role=option],input[type=checkbox],a,button,span').forEach(e=>{
                    const t=(e.innerText||'').replace(/\\s+/g,' ').trim();
                    if(!t && e.getAttribute('type')!=='checkbox') return;
                    out.push({tag:e.tagName.toLowerCase(),test:e.getAttribute('test')||'',type:e.getAttribute('type')||'',
                              aria:e.getAttribute('aria-labelledby')||'',cls:(e.className||'').toString().slice(0,24),txt:t.slice(0,40)});
                });
            });
            const seen=new Set();
            return out.filter(o=>{const k=o.tag+o.txt+o.aria; if(seen.has(k))return false; seen.add(k); return true;}).slice(0,90);
        }""")
        log(f"   POPUP[{nom}] : {json.dumps(items, ensure_ascii=False)}")
        page.screenshot(path=str(OUT / f"_popup_{nom}.png"))
    except Exception as e:
        log(f"   (dump {nom} ko: {e})")


def fermer_popup(page):
    try:
        page.keyboard.press("Escape")
    except Exception:
        pass
    pause("moyen")


POPUP = '.k-animation-container, kendo-popup, .k-popup'


def popup_ouvert(page) -> bool:
    """Un popup kendo visible avec du contenu est-il présent ?"""
    try:
        return page.evaluate("""() => {
            let ok=false;
            document.querySelectorAll('.k-animation-container, kendo-popup, .k-popup').forEach(c=>{
                if(getComputedStyle(c).display!=='none' && (c.innerText||'').trim().length>0) ok=true;
            });
            return ok;
        }""")
    except Exception:
        return False


def ouvrir_filtre(page, sel, nom, verif_sel):
    """Clique le bouton de filtre et vérifie que SON popup (contenu attendu
    `verif_sel`) est bien ouvert — évite de confondre avec un autre popup."""
    for essai in range(3):
        try:
            page.keyboard.press("Escape")  # fermer tout autre popup ouvert
        except Exception:
            pass
        pause("court")
        try:
            b = page.locator(sel).first
            b.scroll_into_view_if_needed(timeout=2000)
            b.click()
        except Exception as e:
            log(f"   clic {nom} ko: {e}")
        pause("long")
        if page.locator(verif_sel).count() > 0:
            return True
        log(f"   (popup {nom} pas encore ouvert, essai {essai+1})")
    return page.locator(verif_sel).count() > 0


def cocher_tout_checkboxes_popup(page):
    """Sélectionne TOUT dans le popup kendo, quel que soit son type
    (multiselect li[role=option], cases input, cases kendo .k-checkbox, arbre)."""
    n = 0
    # 1) items de liste déroulante / multiselect
    opts = page.locator('.k-animation-container li[role="option"], kendo-popup li[role="option"], .k-popup li[role="option"], .k-animation-container .k-list-item')
    for i in range(opts.count()):
        try:
            o = opts.nth(i)
            if (o.get_attribute("aria-selected") or "") == "true":
                continue
            o.scroll_into_view_if_needed(timeout=1500)
            o.click(force=True); n += 1; pause("court")
        except Exception:
            continue
    if n:
        return n
    # 2) vraies cases à cocher
    cbs = page.locator('.k-animation-container input[type=checkbox], kendo-popup input[type=checkbox]')
    for i in range(cbs.count()):
        try:
            c = cbs.nth(i)
            if "k-checked" in (c.get_attribute("class") or "") or c.is_checked():
                continue
            c.click(force=True); n += 1; pause("court")
        except Exception:
            continue
    # 3) cases kendo rendues en span
    if n == 0:
        chk = page.locator('.k-animation-container .k-checkbox:not(.k-checked), kendo-popup .k-checkbox:not(.k-checked)')
        for i in range(chk.count()):
            try:
                chk.nth(i).click(force=True); n += 1; pause("court")
            except Exception:
                continue
    return n


def select_all_centres(page):
    log("🏛  Établissement → tous les centres")
    if not ouvrir_filtre(page, '[test="IDETABLISHMENT_BRANCHs"]', "etab",
                         '.k-animation-container .k-treeview-leaf, kendo-popup .k-treeview-leaf'):
        log("   ⚠ popup établissement introuvable")
        return
    # afficher aussi les centres fermés (historique)
    try:
        vf = page.locator('[test="expand_closed_etablishment_branch"]')
        if vf.count() > 0 and vf.first.is_visible():
            vf.first.click(); pause("moyen"); log("   ✓ centres fermés affichés")
    except Exception:
        pass
    dump_popup(page, "etab")
    clic = cocher_tout_checkboxes_popup(page)
    log(f"   {clic} sélection(s) centre")
    fermer_popup(page)


def _nb_cases_periode(page):
    return page.locator('.k-animation-container input.k-checkbox, kendo-popup input.k-checkbox').count()


# Années à exporter : 2023 → année courante (recalculé à chaque run pour rester
# à jour), surchargeable via la variable d'env OSCAR_ANNEES="2023,2024,...".
# (Un export par année : AEC plante si on prend tout l'historique d'un coup.)
def _annees_defaut():
    from datetime import date
    return [str(y) for y in range(2023, date.today().year + 1)]


_env_annees = os.environ.get("OSCAR_ANNEES", "").strip()
ANNEES = ([a.strip() for a in _env_annees.split(",") if a.strip()]
          if _env_annees else _annees_defaut())


def _annee_presente(page, y):
    return page.evaluate(
        """(y)=>!!Array.from(document.querySelectorAll('.k-animation-container .k-treeview-leaf, kendo-popup .k-treeview-leaf')).find(l=>(l.innerText||'').trim()===y)""",
        y)


def _decocher_une_annee(page):
    """Décoche UNE année cochée (aria '0_N', un seul underscore). Renvoie son
    aria, ou None s'il n'y en a plus. NE TOUCHE JAMAIS le maître (aria '0')."""
    ay = page.evaluate("""()=>{
        const cbs=Array.from(document.querySelectorAll('.k-animation-container input.k-checkbox.k-checked, kendo-popup input.k-checkbox.k-checked'));
        for(const c of cbs){ const a=c.getAttribute('aria-labelledby')||''; if((a.match(/_/g)||[]).length===1) return a; }
        return null;
    }""")
    if not ay:
        return None
    try:
        page.locator(f'.k-animation-container input.k-checkbox[aria-labelledby="{ay}"], kendo-popup input.k-checkbox[aria-labelledby="{ay}"]').first.click()
        pause("court")
    except Exception:
        return None
    return ay


def set_periods(page, years):
    """Sélectionne UNIQUEMENT la/les année(s) demandée(s). On travaille au
    niveau ANNÉE (jamais le maître « Toutes les périodes », qui en Kendo
    recoche TOUT)."""
    log(f"📅 Période → {years} (uniquement)")
    if not ouvrir_filtre(page, '[test="IDPERIODs"]', "periode",
                         '.k-animation-container .k-treeview-leaf, kendo-popup .k-treeview-leaf'):
        log("   ⚠ popup période introuvable")
        return False
    # 1) charger jusqu'à voir l'année la plus ancienne voulue
    oldest = min(years)
    for _ in range(14):
        if _annee_presente(page, oldest):
            break
        try:
            link = page.get_by_text("Voir les périodes les plus anciennes")
            if link.count() > 0 and link.first.is_visible():
                link.first.click(); pause("moyen")
            else:
                pause("court")
        except Exception:
            pause("court")
    if not _annee_presente(page, oldest):
        log(f"   ⚠ année {oldest} pas chargée après tentatives")
    # 2) décocher toutes les ANNÉES cochées (jamais le maître) → repart de zéro
    dec = 0
    for _ in range(30):
        if _decocher_une_annee(page) is None:
            break
        dec += 1
    log(f"   {dec} année(s) décochée(s) (remise à zéro)")
    # 3) cocher uniquement la/les année(s) voulue(s) (cascade vers ses mois)
    n = 0
    for y in years:
        res = page.evaluate("""(y)=>{
            const leaves=Array.from(document.querySelectorAll('.k-animation-container .k-treeview-leaf, kendo-popup .k-treeview-leaf'));
            for(const lf of leaves){
                if((lf.innerText||'').trim()===y){
                    const li=lf.closest('li.k-treeview-item'); if(!li) continue;
                    const cb=li.querySelector('input.k-checkbox');
                    if(cb){ if(!((cb.className||'').includes('k-checked'))){ cb.click(); return 'coché'; } return 'déjà'; }
                }
            }
            return 'absent';
        }""", y)
        log(f"   année {y}: {res}")
        if res in ('coché', 'déjà'):
            n += 1
        pause("court")
    fermer_popup(page)
    return n > 0


def exporter(page, chemin: Path):
    log("📥 Export de la grille…")
    attendre_preload(page)
    try:
        page.locator('button[test="export"]').first.click()
        page.wait_for_selector("kendo-window", timeout=15000)
        pause("moyen")
        cbs = page.locator('kendo-window input[type="checkbox"]')
        for i in range(cbs.count()):
            c = cbs.nth(i)
            lid = c.get_attribute("id") or ""
            txt = ""
            if lid:
                lab = page.locator(f'kendo-window label[for="{lid}"]')
                if lab.count() > 0:
                    txt = lab.first.inner_text() or ""
            if "visib" in txt.lower() and c.is_checked():
                c.uncheck(); log("   ✓ « colonnes visibles » décoché")
        with page.expect_download(timeout=180000) as di:
            page.locator('kendo-window button[test="export"]').first.click()
        di.value.save_as(str(chemin))
        log(f"✅ FICHIER → {chemin}")
        return chemin
    except Exception as e:
        log(f"✗ export raté : {e}")
        try:
            page.keyboard.press("Escape")
        except Exception:
            pass
        return None


def verifier(chemin: Path):
    log("🔎 Vérification du fichier exporté…")
    try:
        import pandas as pd
        df = pd.read_excel(chemin, sheet_name="AEC")
    except Exception as e:
        log(f"   (lecture impossible: {e})"); return
    log(f"   lignes={len(df)}  colonnes={df.shape[1]}")
    col = "Lieu du cours" if "Lieu du cours" in df.columns else ("Centre" if "Centre" in df.columns else None)
    if col:
        log(f"   centres ({col}) : {dict(list(df[col].value_counts(dropna=False).items())[:8])}")
    if "Statut" in df.columns:
        log(f"   statuts : {dict(df['Statut'].value_counts(dropna=False))}")
    if "Date début" in df.columns:
        import pandas as pd
        dd = pd.to_datetime(df["Date début"], errors="coerce", dayfirst=True)
        log(f"   Date début : {dd.min()} → {dd.max()}")
        log(f"   par année : {dict(dd.dt.year.value_counts(dropna=False).sort_index())}")


def main():
    horod = datetime.now().strftime("%Y%m%d_%H%M%S")
    cible = OUT / f"tous_les_cours_TOUS_{horod}.xlsx"
    with sync_playwright() as pw:
        ctx = pw.chromium.launch_persistent_context(
            user_data_dir=str(PROFIL.resolve()), headless=False,
            accept_downloads=True, args=["--start-maximized"], no_viewport=True)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        try: page.bring_to_front()
        except Exception: pass
        log("🚀 Navigateur ouvert (profil persistant).")
        try:
            page.goto(BASE + ROUTE)
        except Exception:
            pass

        page = aec_login.assurer_connexion(ctx, page, log=log)
        if not page:
            log("✗ pas connecté — abandon."); ctx.close(); return
        try:
            aller_all_courses(page)
            log(f"   page = {page.url}")
            # UN export par année, avec ÉTAT FRAIS à chaque fois (reload → reset des
            # filtres) → aucune accumulation de périodes d'une année sur l'autre.
            for idx, year in enumerate(ANNEES):
                log("=" * 40)
                log(f"📆 Année {year}")
                if idx > 0:
                    try:
                        page.reload(wait_until="domcontentloaded")
                    except Exception as e:
                        log(f"   ⚠ reload: {e}")
                    aller_all_courses(page)
                try:
                    select_all_centres(page)
                except Exception as e:
                    log(f"   ⚠ centres: {e}")
                try:
                    if not set_periods(page, [year]):
                        log(f"   ⚠ année {year} non sélectionnée — sautée"); continue
                except Exception as e:
                    log(f"   ⚠ période {year}: {e}"); continue
                attendre_preload(page); pause("long")
                cible_y = OUT / f"cours_{year}_centres.xlsx"   # nom fixe (pas d'accumulation)
                if exporter(page, cible_y):
                    verifier(cible_y)
        except Exception as e:
            log(f"💥 erreur: {e}")
        log("🎉 Terminé — tu peux fermer la fenêtre.")
        pause("long")
        try:
            ctx.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
