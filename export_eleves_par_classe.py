#!/usr/bin/env python3
"""
export_eleves_par_classe.py — exporte le rapport AEC « Cours > Rapports > Par
Classe » (1 ligne = 1 élève × 1 cours, avec Code Client), un fichier par année.
Sert de base à l'indicateur « nombre d'élèves différents ».

Réutilise tout le harnais de export_cours_aec.py (login, filtres période/centre,
export Kendo « toutes colonnes »). Même contraintes : AEC = session unique,
export par année (limite de volume).

    OSCAR_ANNEES="2025" python export_eleves_par_classe.py   # une année (test)
    python export_eleves_par_classe.py                        # 2023→année courante
"""
from __future__ import annotations
import time
from pathlib import Path
from playwright.sync_api import sync_playwright
import aec_login
import export_cours_aec as exp

BASE = exp.BASE
OUT = exp.OUT
PROFIL = exp.PROFIL
ANNEES = exp.ANNEES
log = exp.log

REPORTS_ROUTE = "#/course/course-reports"


def aller_par_classe(page):
    """Ouvre la bibliothèque de rapports Cours puis la carte « Par Classe »,
    et attend que la grille (+ bouton export) soit prête."""
    if "course-reports" not in (page.url or ""):
        try:
            page.goto(BASE + REPORTS_ROUTE)
        except Exception:
            pass
    exp.attendre_preload(page)
    exp.pause("moyen")
    ouvert = False
    for loc in (page.get_by_role("heading", name="Par Classe"),
                page.get_by_text("Par Classe", exact=True),
                page.locator('text="Par Classe"')):
        try:
            if loc.count():
                loc.first.click(timeout=6000)
                ouvert = True
                log("   ↳ carte « Par Classe » ouverte")
                break
        except Exception:
            continue
    if not ouvert:
        log("   ⚠ carte « Par Classe » introuvable")
    exp.attendre_preload(page)
    page.wait_for_selector('button[test="export"]', timeout=45000)
    exp.pause("page")


def select_all_centres_report(page):
    """Coche le master « Tous les centres » (aria-labelledby='0') du rapport, qui
    cascade vers toutes les antennes. Le rapport est scopé à une seule sede par
    défaut (celle de l'utilisateur)."""
    log("🏛  Établissement → Tous les centres (master)")
    if not exp.ouvrir_filtre(page, '[test="IDETABLISHMENT_BRANCHs"]', "etab",
                             '.k-animation-container .k-treeview-leaf, kendo-popup .k-treeview-leaf'):
        log("   ⚠ popup établissement introuvable")
        return
    try:
        vf = page.locator('[test="expand_closed_etablishment_branch"]')
        if vf.count() and vf.first.is_visible():
            vf.first.click(); exp.pause("moyen"); log("   ✓ centres fermés affichés")
    except Exception:
        pass
    res = page.evaluate("""()=>{
        const cb = document.querySelector('.k-animation-container input.k-checkbox[aria-labelledby="0"], kendo-popup input.k-checkbox[aria-labelledby="0"]');
        if(!cb) return 'absent';
        const cls = cb.className || '';
        if(!cls.includes('k-checked')){ cb.click(); return 'coché'; }
        return 'déjà coché';
    }""")
    log(f"   Tous les centres: {res}")
    exp.pause("moyen")
    exp.fermer_popup(page)


def fermer_avertissement_1000(page):
    """Ferme l'éventuel modal « Ce rapport contient plus de 1000 résultats » en
    cliquant OK. L'export, lui, contient TOUTES les lignes (pas la limite 1000)."""
    try:
        for sel in ('button:has-text("OK")', '.k-dialog button:has-text("OK")',
                    'kendo-dialog button:has-text("OK")'):
            b = page.locator(sel)
            if b.count() and b.first.is_visible():
                b.first.click(timeout=2000)
                log("   ✓ avertissement « +1000 résultats » fermé (OK)")
                exp.pause("court")
                return
    except Exception:
        pass


def exporter_report(page, chemin: Path, timeout_ms: int = 240000):
    """Export Excel du rapport. On GARDE « colonnes visibles » coché : seules les
    7 colonnes utiles (dont Code Client / Nom du cours / Code cours) sont
    exportées → génération serveur rapide même pour des milliers de lignes
    (décocher = 100+ colonnes = timeout)."""
    log("📥 Export du rapport (colonnes visibles)…")
    fermer_avertissement_1000(page)
    exp.attendre_preload(page)
    try:
        page.locator('button[test="export"]').first.click()
        page.wait_for_selector("kendo-window", timeout=15000)
        exp.pause("moyen")
        with page.expect_download(timeout=timeout_ms) as di:
            page.locator('kendo-window button[test="export"]').first.click()
            log("   ⏳ génération serveur en cours…")
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


def _clear_all_checked_periods(page):
    """Décoche TOUTES les périodes cochées (années ET mois orphelins comme
    2026-JUIN), sans jamais toucher le maître « Toutes les périodes » (aria sans
    underscore). Corrige le bug où un mois pré-coché restait sélectionné."""
    dec = 0
    for _ in range(80):
        ay = page.evaluate("""()=>{
            const cbs=Array.from(document.querySelectorAll('.k-animation-container input.k-checkbox.k-checked, kendo-popup input.k-checkbox.k-checked'));
            for(const c of cbs){ const a=c.getAttribute('aria-labelledby')||''; if((a.match(/_/g)||[]).length>=1) return a; }
            return null;
        }""")
        if not ay:
            break
        try:
            page.locator(f'.k-animation-container input.k-checkbox[aria-labelledby="{ay}"], kendo-popup input.k-checkbox[aria-labelledby="{ay}"]').first.click()
            exp.pause("court")
            dec += 1
        except Exception:
            break
    return dec


def set_periods_report(page, year: str):
    """Sélectionne UNIQUEMENT l'année demandée dans le rapport (toutes périodes
    précédentes décochées, mois orphelins inclus). Renvoie True si ok."""
    log(f"📅 Période → {year} uniquement (rapport)")
    fermer_avertissement_1000(page)  # le modal « +1000 » bloquerait le filtre
    if not exp.ouvrir_filtre(page, '[test="IDPERIODs"]', "periode",
                             '.k-animation-container .k-treeview-leaf, kendo-popup .k-treeview-leaf'):
        log("   ⚠ popup période introuvable")
        return False
    for _ in range(14):
        if exp._annee_presente(page, year):
            break
        try:
            link = page.get_by_text("Voir les périodes les plus anciennes")
            if link.count() and link.first.is_visible():
                link.first.click(); exp.pause("moyen")
            else:
                exp.pause("court")
        except Exception:
            exp.pause("court")
    dec = _clear_all_checked_periods(page)
    log(f"   {dec} période(s) décochée(s) (remise à zéro complète)")
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
    }""", year)
    log(f"   année {year}: {res}")
    exp.fermer_popup(page)
    return res in ('coché', 'déjà')


def verifier(chemin: Path):
    try:
        import pandas as pd
        try:
            df = pd.read_excel(chemin, sheet_name=0)
        except Exception:
            df = pd.read_excel(chemin)
    except Exception as e:
        log(f"   (lecture impossible: {e})")
        return
    cols = list(df.columns)
    has_cc = any("code client" in str(c).lower() for c in cols)
    log(f"   lignes={len(df)} colonnes={df.shape[1]} | Code Client présent: {has_cc}")
    log(f"   colonnes: {cols[:12]}")
    cc = next((c for c in cols if "code client" in str(c).lower()), None)
    if cc:
        log(f"   élèves distincts (Code Client) dans ce fichier: {df[cc].nunique()}")


def main():
    files = []
    with sync_playwright() as pw:
        ctx = pw.chromium.launch_persistent_context(
            user_data_dir=str(PROFIL.resolve()), headless=False,
            accept_downloads=True, args=["--start-maximized"], no_viewport=True)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        try:
            page.bring_to_front()
        except Exception:
            pass
        try:
            page.goto(BASE + "#/course/all-courses")
        except Exception:
            pass

        page = aec_login.assurer_connexion(ctx, page, log=log)
        if not page:
            log("✗ pas connecté — abandon.")
            ctx.close()
            return

        # Ouvrir le rapport + sélectionner tous les centres UNE SEULE FOIS : le
        # rapport reste ouvert entre les années, ses filtres persistent. On évite
        # le reload (qui referme la carte) et on se contente de changer la période.
        try:
            aller_par_classe(page)
        except Exception as e:
            log(f"   ⚠ navigation Par Classe: {e}")
            ctx.close()
            return
        try:
            select_all_centres_report(page)
        except Exception as e:
            log(f"   ⚠ centres: {e}")
        exp.attendre_preload(page)
        fermer_avertissement_1000(page)  # « tous centres » → grille volumineuse

        for year in ANNEES:
            log("=" * 44)
            log(f"📆 Élèves par classe — année {year}")
            try:
                if not set_periods_report(page, str(year)):
                    log(f"   ⚠ année {year} non sélectionnée — sautée")
                    continue
            except Exception as e:
                log(f"   ⚠ période {year}: {e}")
                continue
            exp.attendre_preload(page)
            fermer_avertissement_1000(page)
            exp.pause("long")
            cible = OUT / f"eleves_par_classe_{year}.xlsx"
            if exporter_report(page, cible):
                verifier(cible)
                files.append(cible)

        try:
            aec_login.sauver_session(ctx, log) if hasattr(aec_login, "sauver_session") else None
        except Exception:
            pass
        ctx.close()

    log("=" * 44)
    log(f"✅ {len(files)} fichier(s) exporté(s) : {[f.name for f in files]}")


if __name__ == "__main__":
    main()
