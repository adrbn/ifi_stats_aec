#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""update_oscar_prod.py — met à jour les données OSCAR de bout en bout et publie
en PRODUCTION (Vercel), en UNE commande.

Pipeline (correctifs du 2026-07-03 intégrés) :
  1. Export AEC « Tous les cours » COMPLET : sélectionne les nœuds de période
     N-2..N+1 ENSEMBLE (corrige la fuite janv–avr — les sessions AEC sont
     rangées par année de création, pas par date de cours) + export « Par
     Classe » (élèves).
  2. Reconstruction NON DESTRUCTIVE des caches : strip des noms de colonnes
     (fix « Quantité d'inscriptions » avec espace final), périmètre de l'année
     scolaire courante 100 % re-tiré + historique conservé, asserts zéro perte.
  3. Régénération du snapshot (build_snapshot, code de main).
  4. Commit + push sur main → Vercel redéploie la prod automatiquement.

Usage :
  double-clic « Mettre à jour OSCAR.command »
  ou : .venv/bin/python update_oscar_prod.py            (interactif)
       .venv/bin/python update_oscar_prod.py --yes      (publie sans confirmer)
       .venv/bin/python update_oscar_prod.py --no-export (rejoue depuis les
                       fichiers déjà exportés — utile pour re-tester)
       .venv/bin/python update_oscar_prod.py --dry-run  (tout SAUF git/deploy)

⚠️ Ne sois pas connecté à AEC ailleurs pendant l'export (AEC = une seule session).
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "new_cours"
WEB = ROOT / "oscar-prealpha" / "web" / "server"
WEB_DATA = WEB / "data" / "new_cours"
VENV = ROOT / ".venv" / "bin" / "python"
SRV_VENV = WEB / ".venv" / "bin" / "python"
FRESH_COURS = DATA / "cours_frais.xlsx"
CACHE_COURS = WEB_DATA / "cache_cours.xlsx"
VERCEL_DASH = "https://vercel.com/adrien-robinos-projects/ifi-stats-aec"


def log(msg: str) -> None:
    print(f"  {msg}", flush=True)


def step(n: int, title: str) -> None:
    print(f"\n\033[1m[{n}/6] {title}\033[0m", flush=True)


def fail(msg: str) -> "None":
    print(f"\n❌ {msg}", flush=True)
    sys.exit(1)


# --- Fenêtre temporelle (année scolaire courante) ----------------------------
def school_year_start(today: date | None = None) -> int:
    today = today or date.today()
    # année scolaire = sep N → août N+1 : un mois >= 9 démarre l'année N.
    return today.year if today.month >= 9 else today.year - 1


def period_year_nodes(today: date | None = None) -> list[str]:
    """Nœuds de période AEC à cocher ENSEMBLE (large fenêtre pour ne rien rater :
    les sessions « 2025-2026 » peuvent être classées sous 2024/2025/2026)."""
    y = (today or date.today()).year
    return [str(y - 2), str(y - 1), str(y), str(y + 1)]


# --- Étape 1 : exports Playwright --------------------------------------------
def export_cours(years_nodes: list[str]) -> None:
    """Un SEUL export « Tous les cours » avec tous les nœuds d'années cochés
    ensemble (réutilise le harnais export_cours_aec)."""
    import aec_login  # noqa: F401  (présence vérifiée)
    import export_cours_aec as exp
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        ctx = pw.chromium.launch_persistent_context(
            user_data_dir=str(exp.PROFIL.resolve()), headless=False,
            accept_downloads=True, args=["--start-maximized"], no_viewport=True)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(exp.BASE + exp.ROUTE)
        page = aec_login.assurer_connexion(ctx, page, log=log)
        if not page:
            ctx.close(); fail("Pas connecté à AEC (vérifie le Trousseau / la session).")
        exp.aller_all_courses(page)
        exp.select_all_centres(page)
        if not exp.set_periods(page, years_nodes):
            ctx.close(); fail(f"Sélection des périodes {years_nodes} échouée.")
        exp.attendre_preload(page); time.sleep(2)
        res = exp.exporter(page, FRESH_COURS)
        if res:
            exp.verifier(FRESH_COURS)
        time.sleep(1)
        ctx.close()
    if not FRESH_COURS.exists():
        fail("L'export des cours n'a produit aucun fichier.")


def export_eleves(sy: int) -> None:
    """Export « Par Classe » pour l'année scolaire courante (années civiles
    sy et sy+1), puis merge (merge_eleves fusionne tous les fichiers présents)."""
    annees = f"{sy},{sy + 1}"
    env = {"OSCAR_ANNEES": annees}
    _run([str(VENV), "export_eleves_par_classe.py"], env=env,
         err="Export élèves (Par Classe) échoué.")
    _run([str(VENV), "merge_eleves.py"], err="Fusion des élèves (merge_eleves) échouée.")


# --- Étape 2 : reconstruction non destructive du cache cours -----------------
def rebuild_cache_cours(today: date | None = None) -> None:
    import pandas as pd

    base = pd.read_excel(CACHE_COURS, sheet_name="AEC")
    fresh = pd.read_excel(FRESH_COURS, sheet_name="AEC")
    base.columns = [str(c).strip() for c in base.columns]
    fresh.columns = [str(c).strip() for c in fresh.columns]  # fix « inscriptions » espace final
    cols = list(base.columns)
    fresh = fresh.loc[:, ~fresh.columns.duplicated()].reindex(columns=cols)

    bd = pd.to_datetime(base["Date début"], errors="coerce", dayfirst=True)
    fd = pd.to_datetime(fresh["Date début"], errors="coerce", dayfirst=True)
    cut = pd.Timestamp(f"{school_year_start(today)}-09-01")

    history = base[(bd < cut) | bd.isna()]                 # historique + cours sans date
    fresh_win = fresh[fd >= cut]                           # année scolaire courante, fraîche
    sF = set(fresh_win["Classe N°"].dropna().astype(str))
    missing = base[(bd >= cut) & (~base["Classe N°"].astype(str).isin(sF))]  # préservés

    new = pd.concat([fresh_win, missing, history], ignore_index=True)
    k = new["Classe N°"].astype("object")
    dupe = k.where(k.notna(), pd.Series([f"__NA_{i}" for i in range(len(new))], index=new.index)).duplicated(keep="first")
    new = new.loc[~dupe]

    lost = set(base["Classe N°"].dropna().astype(str)) - set(new["Classe N°"].dropna().astype(str))
    if lost:
        fail(f"Reconstruction refusée : {len(lost)} cours de la prod seraient perdus.")
    if new.shape[1] != base.shape[1]:
        fail("Reconstruction refusée : nombre de colonnes incohérent.")

    ny = pd.to_datetime(new["Date début"], errors="coerce", dayfirst=True)
    log(f"cache_cours : {len(base)} → {len(new)} cours (0 perte)")
    log("par année : " + str({int(a): int(v) for a, v in ny.dt.year.value_counts(dropna=True).sort_index().items()}))
    new.to_excel(CACHE_COURS, index=False, sheet_name="AEC")


# --- Étape 3 : snapshot -------------------------------------------------------
def build_snapshot() -> None:
    _run([str(SRV_VENV), "build_snapshot.py"], cwd=WEB, err="build_snapshot a échoué.")
    _sanity_snapshot()


def _sanity_snapshot() -> None:
    import json
    snap = json.loads((WEB / "fixtures" / "snapshot.json").read_text(encoding="utf-8"))
    if snap.get("meta", {}).get("source") != "computed":
        fail("Snapshot invalide (source != computed) — publication annulée.")
    kpis = {k["key"]: k["value"] for k in snap.get("kpis", [])}
    ins = kpis.get("inscriptions", 0)
    if not (100 < ins < 200000):
        fail(f"Snapshot suspect (inscriptions={ins}) — publication annulée.")
    log(f"snapshot OK · maj={snap['meta'].get('updated')} · inscriptions={ins}")


# --- Étape 4 : git + push (→ Vercel auto-deploy) -----------------------------
FILES = [
    "oscar-prealpha/web/server/data/new_cours/cache_cours.xlsx",
    "oscar-prealpha/web/server/data/new_cours/cache_eleves.xlsx",
    "oscar-prealpha/web/server/fixtures/snapshot.json",
]


def publish(auto_yes: bool) -> None:
    branch = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"],
                            cwd=ROOT, capture_output=True, text=True).stdout.strip()
    if branch != "main":
        log(f"⚠ Tu n'es pas sur main (branche « {branch} »).")
        if not auto_yes and not _confirm(f"Publier quand même depuis « {branch} » sur main ?"):
            fail("Publication annulée.")
    diff = subprocess.run(["git", "status", "--short"] + FILES, cwd=ROOT,
                          capture_output=True, text=True).stdout.strip()
    if not diff:
        log("Aucun changement de données à publier (déjà à jour).")
        return
    if not auto_yes and not _confirm("Publier ces données en PRODUCTION (push main → deploy Vercel) ?"):
        fail("Publication annulée (les fichiers locaux sont à jour, rien n'a été poussé).")
    _run(["git", "add"] + FILES, cwd=ROOT, err="git add a échoué.")
    msg = f"data(oscar): mise à jour des données au {date.today():%Y-%m-%d}"
    _run(["git", "commit", "-m", msg], cwd=ROOT, err="git commit a échoué.")
    # main peut avoir avancé côté distant : on rebase avant de pousser.
    subprocess.run(["git", "pull", "--rebase", "origin", "main"], cwd=ROOT)
    _run(["git", "push", "origin", "HEAD:main"], cwd=ROOT, err="git push a échoué.")
    print(f"\n✅ Poussé sur main → Vercel redéploie la prod.\n   Suivi : {VERCEL_DASH}", flush=True)


# --- Utilitaires --------------------------------------------------------------
def _run(cmd: list[str], cwd: Path | None = None, env: dict | None = None, err: str = "") -> None:
    import os
    e = {**os.environ, **(env or {})}
    r = subprocess.run(cmd, cwd=str(cwd or ROOT), env=e)
    if r.returncode != 0:
        fail(err or f"Commande échouée : {' '.join(cmd)}")


def _confirm(q: str) -> bool:
    try:
        return input(f"\n❓ {q} [o/N] ").strip().lower() in ("o", "oui", "y", "yes")
    except EOFError:
        return False


def _check_env() -> None:
    if not VENV.exists():
        fail(f"venv d'export absent ({VENV}). Crée-le : "
             "python3.13 -m venv .venv && .venv/bin/pip install playwright pandas openpyxl "
             "&& .venv/bin/python -m playwright install chromium")
    if not SRV_VENV.exists():
        fail(f"venv serveur absent ({SRV_VENV}).")
    if not CACHE_COURS.exists():
        fail(f"cache_cours introuvable ({CACHE_COURS}). Es-tu bien à la racine du repo ?")


def main() -> None:
    ap = argparse.ArgumentParser(description="Met à jour les données OSCAR et publie en prod.")
    ap.add_argument("--yes", action="store_true", help="publie sans demander confirmation")
    ap.add_argument("--no-export", action="store_true", help="réutilise les exports déjà présents")
    ap.add_argument("--dry-run", action="store_true", help="tout sauf git/deploy")
    args = ap.parse_args()

    print("\033[1m═══ Mise à jour OSCAR → production ═══\033[0m")
    _check_env()
    today = date.today()
    sy = school_year_start(today)
    nodes = period_year_nodes(today)
    log(f"Année scolaire courante : {sy}-{sy + 1} · nœuds période : {nodes}")

    if not args.no_export:
        step(1, "Export AEC des cours (complet)")
        log("⚠ Ne sois pas connecté à AEC ailleurs. Une fenêtre Chrome va s'ouvrir.")
        export_cours(nodes)
        step(2, "Export AEC des élèves (Par Classe)")
        export_eleves(sy)
    else:
        step(1, "Export cours — SAUTÉ (--no-export)"); log("réutilise " + FRESH_COURS.name)
        step(2, "Export élèves — SAUTÉ (--no-export)")

    step(3, "Reconstruction des caches (non destructive)")
    rebuild_cache_cours(today)

    step(4, "Régénération du snapshot")
    build_snapshot()

    step(5, "Vérification")
    log("caches + snapshot à jour localement.")

    step(6, "Publication en production")
    if args.dry_run:
        log("--dry-run : rien n'est poussé ni déployé.")
    else:
        publish(args.yes)
    print("\n\033[1m✔ Terminé.\033[0m")


if __name__ == "__main__":
    main()
