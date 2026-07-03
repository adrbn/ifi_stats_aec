#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
update_cache.py — fusion INCRÉMENTALE dans un cache blindé.

Lit les fichiers fraîchement exportés `cours_<année>_centres.xlsx` (les années
fraîches = variable d'env OSCAR_ANNEES, sinon toutes celles présentes) et met à
jour `cache_cours.xlsx` :
  • les années fraîchement re-tirées sont REMPLACÉES dans le cache
    (→ gère ajouts / modifs / suppressions DANS ces années) ;
  • les autres années restent telles quelles dans le cache (pas de re-DL).
Dédup par « Classe N° » (le frais gagne). Backup + vérifications avant d'écrire.

Sorties : cache_cours.xlsx (le cache) + cours_TOUS_dedup.xlsx (consommé par oscar_cours.py).
"""
from __future__ import annotations
import os
import re
import shutil
from pathlib import Path
import pandas as pd

OUT = Path(__file__).resolve().parent / "data" / "new_cours"
CACHE = OUT / "cache_cours.xlsx"
CACHE_BAK = OUT / "cache_cours.bak.xlsx"
CLE = "Classe N°"
COLS_MIN = ["Classe N°", "Lieu du cours", "Catégorie", "Statut", "Date début"]


def _annee(df):
    return pd.to_datetime(df["Date début"], errors="coerce", dayfirst=True).dt.year


def main() -> int:
    # 1) quelles années sont "fraîches" ?
    env = os.environ.get("OSCAR_ANNEES", "").strip()
    voulues = [a.strip() for a in env.split(",") if a.strip()]
    fichiers = {}
    for f in OUT.glob("cours_*_centres.xlsx"):
        m = re.search(r"cours_(\d{4})_centres", f.name)
        if m:
            fichiers[m.group(1)] = f
    if not fichiers:
        print("❌ Aucun fichier cours_<année>_centres.xlsx — lance d'abord l'export.")
        return 1
    fresh_years = [y for y in (voulues or sorted(fichiers)) if y in fichiers]
    if not fresh_years:
        print("❌ Les années demandées n'ont pas de fichier export.")
        return 1
    print(f"Années fraîchement exportées : {fresh_years}")

    # 2) charger les frais + VÉRIFS
    frames = []
    for y in fresh_years:
        d = pd.read_excel(fichiers[y], sheet_name="AEC")
        d.columns = [str(c).strip() for c in d.columns]
        manque = [c for c in COLS_MIN if c not in d.columns]
        if manque:
            print(f"❌ {fichiers[y].name} : colonnes manquantes {manque}. Abandon (cache intact).")
            return 1
        if len(d) == 0:
            print(f"⚠️ {fichiers[y].name} est VIDE — année {y} ignorée (sécurité, on ne vide pas le cache).")
            continue
        print(f"  frais {y} : {len(d)} lignes")
        frames.append(d)
    if not frames:
        print("❌ Aucun export frais exploitable. Cache intact.")
        return 1
    fresh = pd.concat(frames, ignore_index=True)
    fresh_set = {int(y) for y in fresh_years}

    # 3) charger le cache existant
    if CACHE.exists():
        cache = pd.read_excel(CACHE, sheet_name="AEC")
        cache.columns = [str(c).strip() for c in cache.columns]
    else:
        cache = pd.DataFrame(columns=list(fresh.columns))
    before = len(cache)
    print(f"\nCache avant : {before} cours")

    # 4) backup (jamais sans filet)
    if CACHE.exists():
        try:
            shutil.copyfile(CACHE, CACHE_BAK)
            print(f"  💾 backup → {CACHE_BAK.name}")
        except Exception as e:  # noqa: BLE001
            print(f"  (backup impossible : {e})")

    # 5) fusion : on retire du cache les années fraîches, on garde le reste, on ajoute le frais
    if before:
        cy = _annee(cache)
        cache_garde = cache[~cy.isin(fresh_set)].copy()
    else:
        cache_garde = cache
    combine = pd.concat([fresh, cache_garde], ignore_index=True)  # frais d'abord = prioritaire
    k = combine[CLE].astype("object")
    na = k.isna()
    k = k.where(~na, pd.Series([f"__NA_{i}" for i in range(len(combine))], index=combine.index))
    combine["__k"] = k
    new_cache = combine.drop_duplicates("__k", keep="first").drop(columns="__k")
    after = len(new_cache)

    # 6) VÉRIFS post-fusion
    print(f"Cache après : {after} cours  (Δ {after - before:+d})")
    ny = _annee(new_cache)
    print("  par année :", {int(a): int(v) for a, v in ny.value_counts(dropna=False).sort_index().items()
                            if pd.notna(a)})
    dups = int(new_cache[CLE].notna().sum() - new_cache[CLE].nunique(dropna=True))
    if dups:
        print(f"❌ {dups} doublons « Classe N° » dans le cache fusionné — écriture annulée (backup gardé).")
        return 1
    # garde-fou anti perte massive (sauf 1er remplissage)
    if before and after < before * 0.8:
        print(f"❌ ALERTE : le cache chuterait de {before} à {after} (>20% perdu). "
              f"Écriture ANNULÉE par sécurité — restaure {CACHE_BAK.name} si besoin.")
        return 1
    # années NON re-tirées : doivent rester identiques au cache
    if before:
        cy = _annee(cache)
        for a in sorted({int(x) for x in cy.dropna().unique()} - fresh_set):
            av = int((cy == a).sum())
            ap = int((ny == a).sum())
            flag = "" if av == ap else "  ⚠ écart"
            print(f"    année {a} (non re-tirée) : {av} → {ap}{flag}")

    # 7) écrire
    new_cache.to_excel(CACHE, index=False, sheet_name="AEC")
    print(f"\n→ {CACHE.name}  ({after} cours × {new_cache.shape[1]} colonnes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
