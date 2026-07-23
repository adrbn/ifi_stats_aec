#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""publier_oscar_pr.py — publie le cache COURS frais vers OSCAR via une PULL REQUEST.

Au lieu de pousser directement en production (ce qui court-circuiterait la
relecture), on propose les données à Adrien par une PR :

  1. vérifie le cache frais local (data/new_cours/cache_cours.xlsx)
  2. se resynchronise sur adrbn/main (règle : toujours partir de la base à jour)
  3. crée une branche dédiée  data/maj-cours-<horodatage>
  4. copie le cache dans le dépôt OSCAR + régénère fixtures/snapshot.json
  5. commit + push sur le fork, puis ouvre la PR vers adrbn/main
  6. remet le dépôt sur la branche où il était (aucune perturbation)

Sécurités : refuse de tourner si le dépôt a des modifications non commitées,
vérifie le snapshot régénéré, et restaure toujours la branche d'origine.

Usage :
    python publier_oscar_pr.py --dry-run   # tout SAUF push/PR (test à blanc)
    python publier_oscar_pr.py             # publie et ouvre la PR
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

ICI = Path(__file__).resolve().parent
SRC_CACHE = ICI / "data" / "new_cours" / "cache_cours.xlsx"

# Dépôt OSCAR (surchargeable : set OSCAR_REPO=...)
REPO = Path(os.environ.get(
    "OSCAR_REPO",
    r"G:\Drive condivisi\IFI - Marketing des cours\STATS & INDICATEURS\OSCAR\ifi_stats_aec",
))
WEB_SERVER = REPO / "oscar-prealpha" / "web" / "server"
DEST_CACHE = WEB_SERVER / "data" / "new_cours" / "cache_cours.xlsx"
SNAPSHOT = WEB_SERVER / "fixtures" / "snapshot.json"

UPSTREAM = "upstream"          # adrbn/ifi_stats_aec
ORIGIN = "origin"              # le fork
BASE = "main"
UPSTREAM_REPO = "adrbn/ifi_stats_aec"

# Identité des commits de données. Par défaut on laisse Git utiliser la config
# du poste (user.name / user.email) : surcharger seulement si elle est absente,
# via OSCAR_GIT_NAME / OSCAR_GIT_EMAIL. Sans ça, le script imposerait l'identité
# de son auteur à quiconque l'utilise.
GIT_NAME = os.environ.get("OSCAR_GIT_NAME", "")
GIT_EMAIL = os.environ.get("OSCAR_GIT_EMAIL", "")

# Fichiers publiés par la PR (uniquement les données cours)
FICHIERS_PR = [
    "oscar-prealpha/web/server/data/new_cours/cache_cours.xlsx",
    "oscar-prealpha/web/server/fixtures/snapshot.json",
]


def log(m: str) -> None:
    print(m, flush=True)


def fail(m: str) -> "None":
    log(f"\n❌ {m}")
    sys.exit(1)


def proprietaire_fork() -> str:
    """Compte GitHub propriétaire de `origin`, pour le « --head owner:branche ».

    Déduit de l'URL du remote (https://github.com/<owner>/<repo>.git ou
    git@github.com:<owner>/<repo>.git) plutôt que codé en dur : chaque personne
    publie ainsi depuis SON fork."""
    url = git("remote", "get-url", ORIGIN, check=False)
    m = re.search(r"[/:]([^/:]+)/[^/]+?(?:\.git)?$", url.strip())
    if not m:
        fail(f"impossible de déduire le propriétaire du fork depuis « {url} ».")
    return m.group(1)


def gh_exe() -> str:
    p = Path(r"C:\Program Files\GitHub CLI\gh.exe")
    return str(p) if p.exists() else "gh"


def srv_python() -> str:
    win = WEB_SERVER / ".venv" / "Scripts" / "python.exe"
    nix = WEB_SERVER / ".venv" / "bin" / "python"
    if win.exists():
        return str(win)
    if nix.exists():
        return str(nix)
    return sys.executable


def git(*args: str, check: bool = True, capture: bool = True) -> str:
    """git -C <repo> …

    L'identité n'est forcée que si OSCAR_GIT_NAME / OSCAR_GIT_EMAIL sont
    définis : sinon on laisse la configuration Git du poste décider (passer un
    `user.name` vide ferait échouer le commit)."""
    ident = []
    if GIT_NAME:
        ident += ["-c", f"user.name={GIT_NAME}"]
    if GIT_EMAIL:
        ident += ["-c", f"user.email={GIT_EMAIL}"]
    cmd = ["git", "-C", str(REPO), *ident, *args]
    r = subprocess.run(cmd, capture_output=capture, text=True, encoding="utf-8", errors="replace")
    if check and r.returncode != 0:
        fail(f"git {' '.join(args)} a échoué :\n{(r.stderr or r.stdout or '').strip()[:600]}")
    return (r.stdout or "").strip()


def resume_donnees() -> str:
    """Petit résumé du cache (nb de cours, années) pour le corps de la PR."""
    try:
        import pandas as pd
        df = pd.read_excel(SRC_CACHE)
        df.columns = [str(c).strip() for c in df.columns]
        n = len(df)
        d = pd.to_datetime(df.get("Date début"), errors="coerce", dayfirst=True)
        par_an = d.dt.year.value_counts().sort_index()
        detail = " · ".join(f"{int(a)} : {int(v)}" for a, v in par_an.items() if a == a)
        return f"**{n} cours** — {detail}"
    except Exception:  # noqa: BLE001
        return "(résumé indisponible)"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="tout sauf push et PR")
    args = ap.parse_args()

    log("=" * 60)
    log("  Publier les données COURS sur OSCAR (Pull Request)")
    log("=" * 60)

    # 1) cache frais présent ?
    if not SRC_CACHE.exists():
        fail(f"Cache introuvable : {SRC_CACHE}\n   Lance d'abord « Recuperer cours AEC » (mise à jour des données).")
    maj = datetime.fromtimestamp(SRC_CACHE.stat().st_mtime).strftime("%d/%m/%Y à %H:%M")
    log(f"✓ Cache local : {SRC_CACHE.name} (maj {maj})")
    if not REPO.exists():
        fail(f"Dépôt OSCAR introuvable : {REPO}\n   (définis la variable OSCAR_REPO si besoin)")
    log(f"✓ Dépôt OSCAR : {REPO}")

    # 2) le dépôt doit être propre (on ne touche pas au travail en cours)
    sale = git("status", "--porcelain")
    if sale:
        fail("Le dépôt OSCAR a des modifications non commitées.\n"
             "   Commit/annule-les avant de publier :\n   " + sale[:400])
    branche_origine = git("rev-parse", "--abbrev-ref", "HEAD")
    log(f"✓ Dépôt propre (branche actuelle : {branche_origine})")

    # 3) base à jour
    log("\n▶ Resynchronisation sur adrbn/main…")
    git("fetch", UPSTREAM)
    base_sha = git("rev-parse", f"{UPSTREAM}/{BASE}")
    log(f"  {UPSTREAM}/{BASE} = {base_sha[:8]}")

    branche = f"data/maj-cours-{datetime.now():%Y%m%d-%H%M}"
    ok = False
    try:
        git("checkout", "-b", branche, f"{UPSTREAM}/{BASE}")
        log(f"✓ Branche créée : {branche}")

        # 4) copie du cache + régénération du snapshot
        log("\n▶ Copie du cache et régénération du snapshot…")
        DEST_CACHE.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(SRC_CACHE, DEST_CACHE)
        log(f"  cache → {DEST_CACHE.relative_to(REPO)}")

        env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
        r = subprocess.run([srv_python(), "build_snapshot.py"], cwd=str(WEB_SERVER),
                           capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
        if r.returncode != 0:
            fail("build_snapshot a échoué :\n" + (r.stderr or r.stdout or "")[-800:])
        log("  snapshot.json régénéré")

        # vérif snapshot
        try:
            import json
            snap = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
            ins = next((k.get("value") for k in snap.get("kpis", []) if k.get("key") == "inscriptions"), None)
            log(f"  ✓ snapshot OK (maj={snap.get('meta', {}).get('updated')}, inscriptions={ins})")
            if not ins:
                fail("Snapshot suspect (0 inscription) — publication annulée.")
        except Exception as e:  # noqa: BLE001
            fail(f"Snapshot illisible : {e}")

        # 5) commit
        git("add", "--", *FICHIERS_PR)
        if not git("status", "--porcelain"):
            log("\nℹ️  Aucune différence : les données du dépôt sont déjà à jour. Rien à publier.")
            return 0
        resume = resume_donnees()
        msg = (f"data: mise à jour du cache cours (export AEC du {maj})\n\n"
               f"{resume}\n\n"
               f"Régénère aussi fixtures/snapshot.json à partir de ce cache.\n")
        git("commit", "-m", msg)
        log(f"✓ Commit créé\n  {resume}")

        if args.dry_run:
            log("\n🧪 DRY-RUN : on s'arrête avant le push et la PR.")
            log(f"   Auraient été poussés : {', '.join(FICHIERS_PR)}")
            log(f"   Branche : {branche} → PR vers {UPSTREAM_REPO}:{BASE}")
            return 0

        # 6) push + PR
        log("\n▶ Push sur le fork…")
        git("push", "-u", ORIGIN, branche)
        log("✓ Poussé")

        log("\n▶ Ouverture de la Pull Request…")
        corps = (
            "## Mise à jour des données Cours\n\n"
            f"Export AEC du **{maj}** — {resume}\n\n"
            "Contenu :\n"
            "- `cache_cours.xlsx` (cache des cours, tous centres)\n"
            "- `fixtures/snapshot.json` régénéré à partir de ce cache\n\n"
            "_Données uniquement — aucun changement de code._\n\n"
            "🤖 Publié depuis l'outil AEC (bouton « Publier sur OSCAR »)\n"
        )
        pr = subprocess.run(
            [gh_exe(), "pr", "create", "--repo", UPSTREAM_REPO, "--base", BASE,
             "--head", f"{proprietaire_fork()}:{branche}",
             "--title", f"data: mise à jour du cache cours (export AEC du {maj})",
             "--body", corps],
            capture_output=True, text=True, encoding="utf-8", errors="replace")
        if pr.returncode != 0:
            fail("Création de la PR échouée :\n" + (pr.stderr or pr.stdout or "")[-600:])
        url = (pr.stdout or "").strip().splitlines()[-1]
        log(f"\n🎉 PR ouverte : {url}")
        ok = True
        return 0
    finally:
        # 7) toujours revenir à la branche d'origine
        try:
            git("checkout", branche_origine, check=False)
            log(f"\n↩ Dépôt remis sur « {branche_origine} »")
            if not ok and not args.dry_run:
                log("   (la branche de publication reste disponible en local)")
        except Exception:  # noqa: BLE001
            pass


if __name__ == "__main__":
    raise SystemExit(main())
