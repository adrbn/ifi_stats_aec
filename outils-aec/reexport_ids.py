#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
reexport_ids.py — réexport CIBLÉ de quelques cours, par n° de classe.

Pourquoi : quand on corrige un cours dans AEC, sa PÉRIODE change (parfois d'un
an ou de six mois) → impossible de savoir quelle période réexporter. La
recherche générale d'AEC, elle, retrouve le cours par son n° quelle que soit sa
période — à condition que TOUTES les périodes soient cochées (y compris les
anciennes, masquées derrière « Voir les périodes les plus anciennes »).

Déroulé :
  1. toutes les périodes + tous les centres sont sélectionnés (une seule fois) ;
  2. pour chaque n° de classe : recherche → export de la grille filtrée ;
  3. les lignes obtenues sont regroupées dans `cours_corriges.xlsx`.

Ensuite, `patch_cache_ids.py` remplace ces cours dans `cache_cours.xlsx`
(upsert par « Classe N° »), sans toucher au reste du cache.

Usage :
    python reexport_ids.py                 # IDs = ceux d'incoherences_dates.xlsx
    python reexport_ids.py --ids 4592,9128 # IDs choisis
"""
from __future__ import annotations
import os
import re
import sys
import argparse

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

from pathlib import Path
import pandas as pd
from playwright.sync_api import sync_playwright
import aec_login
from export_cours_aec import (BASE, ROUTE, PROFIL, OUT, aller_all_courses,
                              attendre_preload, pause, log, select_all_centres,
                              ouvrir_filtre, fermer_popup, exporter)

CLE = "Classe N°"
DOSSIER = OUT / "corrections"
FUSION = OUT / "cours_corriges.xlsx"
INCOHERENCES = OUT / "incoherences_dates.xlsx"

_LIBELLES_VOIR_PLUS = (
    "Voir les périodes les plus anciennes",
    "Voir les périodes antérieures",
    "Voir les périodes précédentes",
    "périodes antérieures",
    "périodes précédentes",
    "Voir plus",
)


# ─────────────────────────── liste des IDs ────────────────────────────
def ids_depuis_incoherences() -> list[str]:
    if not INCOHERENCES.exists():
        return []
    df = pd.read_excel(INCOHERENCES)
    col = next((c for c in df.columns if "classe" in str(c).lower()), None)
    if not col:
        return []
    out = []
    for v in df[col].dropna():
        s = re.sub(r"\D", "", str(v))
        if s:
            out.append(s)
    return sorted(set(out), key=int)


# ─────────────────────── toutes les périodes ──────────────────────────
def _clic_voir_plus(page) -> bool:
    for txt in _LIBELLES_VOIR_PLUS:
        try:
            l = page.get_by_text(txt, exact=False)
            if l.count() > 0 and l.first.is_visible():
                l.first.click(timeout=4000)
                return True
        except Exception:
            continue
    return False


def _annees_du_popup(page) -> list[str]:
    """Libellés des nœuds ANNÉE (« 2022 », « 2023 »…) actuellement chargés."""
    return page.evaluate("""()=>{
        const ls=Array.from(document.querySelectorAll('.k-animation-container .k-treeview-leaf, kendo-popup .k-treeview-leaf'));
        const ys=new Set();
        ls.forEach(l=>{const t=(l.innerText||'').trim(); if(/^\\d{4}$/.test(t)) ys.add(t);});
        return Array.from(ys).sort();
    }""")


def set_all_periods(page) -> bool:
    """Charge TOUT l'historique des périodes puis coche chaque année.

    On coche année par année (jamais le maître « Toutes les périodes » : en
    Kendo il recoche tout l'arbre y compris ce qui n'est pas chargé, avec des
    effets de bord)."""
    log("📅 Sélection de TOUTES les périodes (historique complet)…")
    if not ouvrir_filtre(page, '[test="IDPERIODs"]', "periode",
                         '.k-animation-container .k-treeview-leaf, kendo-popup .k-treeview-leaf'):
        log("   ⚠ popup période introuvable")
        return False

    # 1) déplier jusqu'à épuisement du lien « voir les plus anciennes »
    clics = 0
    for _ in range(60):
        if not _clic_voir_plus(page):
            break
        clics += 1
        pause("moyen")
    annees = _annees_du_popup(page)
    log(f"   historique déplié ({clics} clic(s)) → années visibles : {annees}")
    if not annees:
        log("   ⚠ aucune année détectée")
        fermer_popup(page)
        return False

    # 2) cocher toutes les années non cochées
    n = 0
    for y in annees:
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
        if res in ("coché", "déjà"):
            n += 1
        pause("court")
    log(f"   {n}/{len(annees)} année(s) sélectionnée(s)")
    fermer_popup(page)
    pause("long")
    return n > 0


# ──────────────────────────── recherche ───────────────────────────────
def chercher(page, terme: str) -> None:
    champ = page.locator('input[test="general_search"]').first
    champ.click()
    champ.fill("")
    pause("court")
    champ.fill(terme)
    pause("court")
    champ.press("Enter")
    pause("moyen")
    try:
        attendre_preload(page, t=60)
    except Exception:
        pass
    pause("long")


def verifier_export(chemin: Path, cid: str):
    """Renvoie la ligne du cours si l'export la contient bien, sinon None."""
    try:
        df = pd.read_excel(chemin, sheet_name="AEC")
    except Exception as e:
        log(f"   ✗ lecture impossible : {e}")
        return None
    df.columns = [str(c).strip() for c in df.columns]
    if CLE not in df.columns:
        log(f"   ✗ colonne « {CLE} » absente")
        return None
    m = df[df[CLE].astype(str).str.replace(r"\D", "", regex=True) == cid]
    log(f"   export : {len(df)} ligne(s) — dont {len(m)} pour le n° {cid}")
    if m.empty:
        log(f"   ⚠ le n° {cid} n'est PAS dans l'export (cours supprimé ? n° inexistant ?)")
        return None
    r = m.iloc[0]
    log(f"   ✓ {str(r.get('Nom du cours', ''))[:45]} | période={r.get('Période')} "
        f"| {r.get('Date début')} → {r.get('Date fin')}")
    return m


# ──────────────────────────────── main ────────────────────────────────
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", default=os.environ.get("OSCAR_IDS", ""),
                    help="n° de classe séparés par des virgules (défaut : incoherences_dates.xlsx)")
    args = ap.parse_args()

    ids = [re.sub(r"\D", "", x) for x in args.ids.split(",") if x.strip()] if args.ids \
        else ids_depuis_incoherences()
    ids = [i for i in ids if i]
    if not ids:
        print("❌ Aucun n° de classe à réexporter "
              "(ni --ids, ni incoherences_dates.xlsx exploitable).")
        return 1

    DOSSIER.mkdir(parents=True, exist_ok=True)
    log(f"🎯 Réexport ciblé de {len(ids)} cours : {', '.join(ids)}")

    recoltes, manquants = [], []
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

        page = aec_login.assurer_connexion(ctx, page, log=log, t_manuel=1200)
        if not page:
            log("✗ pas connecté — abandon.")
            ctx.close()
            return 1

        try:
            aller_all_courses(page)
            # La recherche d'abord : la grille reste légère pendant qu'on coche
            # tout l'historique des périodes (sinon AEC recharge des milliers
            # de lignes à chaque clic).
            log(f"🔍 Recherche « {ids[0]} » (avant d'ouvrir tout l'historique)")
            chercher(page, ids[0])
            select_all_centres(page)
            if not set_all_periods(page):
                log("✗ impossible de sélectionner toutes les périodes — abandon.")
                ctx.close()
                return 1

            for i, cid in enumerate(ids, 1):
                log("=" * 46)
                log(f"🔍 [{i}/{len(ids)}] n° de classe {cid}")
                try:
                    if i > 1:  # le 1er terme est déjà dans le champ
                        chercher(page, cid)
                    else:
                        chercher(page, cid)  # relancé : les filtres ont changé depuis
                    cible = DOSSIER / f"cours_id_{cid}.xlsx"
                    if exporter(page, cible):
                        m = verifier_export(cible, cid)
                        if m is not None:
                            recoltes.append(m)
                        else:
                            manquants.append(cid)
                    else:
                        manquants.append(cid)
                except Exception as e:
                    log(f"   💥 {cid} : {e}")
                    manquants.append(cid)
        except Exception as e:
            log(f"💥 erreur : {e}")
        finally:
            pause("moyen")
            try:
                ctx.close()
            except Exception:
                pass

    log("=" * 46)
    if recoltes:
        fusion = pd.concat(recoltes, ignore_index=True)
        fusion = fusion.drop_duplicates(subset=[CLE], keep="first")
        fusion.to_excel(FUSION, index=False, sheet_name="AEC")
        log(f"✅ {len(fusion)} cours récupérés → {FUSION.name}")
        log("   Étape suivante : python patch_cache_ids.py  (remplace ces cours dans le cache)")
    else:
        log("⚠ aucun cours récupéré.")
    if manquants:
        log(f"⚠ non récupérés : {', '.join(manquants)}")
    return 0 if recoltes else 1


if __name__ == "__main__":
    sys.exit(main())
