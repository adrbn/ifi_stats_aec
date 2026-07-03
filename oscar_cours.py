#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
oscar_cours.py — (1) vérifie l'intégrité du fichier brut « Tous les cours »
puis (2) le traite « légitimement » selon le mapping OSCAR :
  - dérive Sede (IFM/IFF/IFN/IFP) depuis « Lieu du cours »
  - dérive Année scolaire + Période (P1 sep→déc / P2 janv→août) depuis Date début
  - filtre les statuts (garde Ouvert / Fermé à l'inscription / En attente ; jette Annulé)
  - renomme les colonnes vers les indicateurs OSCAR
  - agrège les indicateurs et sort des listes propres par année scolaire.

Entrée : data/new_cours/cours_FINAL_2023-2026.xlsx
Sorties : data/new_cours/oscar_indicateurs_cours.xlsx (+ feuilles listes)
"""
from __future__ import annotations
import sys
from pathlib import Path
import pandas as pd
import numpy as np

# Réutilise le mapping catégorie→secteur d'OSCAR (légitime, pas de réinvention)
sys.path.insert(0, str(Path(__file__).resolve().parent / "oscar-prealpha" / "web" / "server"))
try:
    import oscar_core as _oc
    try:
        _oc.load_csv_mappings(str(Path(__file__).resolve().parent / "data" / "category_mapping.csv"))
    except Exception:
        pass
    _MAP_SECT = _oc.map_category_to_levels
except Exception:
    _MAP_SECT = None

OUT = Path(__file__).resolve().parent / "data" / "new_cours"
SRC = OUT / "cache_cours.xlsx"        # entrée = le cache (toutes années, dédupliqué)

# Mapping colonne brute (AEC) -> indicateur OSCAR
MAP = {
    "Quantité d'inscriptions": "Inscriptions",
    "Qté heures": "Qté heures",
    "Qté heures vendues": "Heures-élèves",
    "Qté synchrones heures vendues": "Heures synchrones",
    "Qté asynchrones heures vendues": "Heures asynchrones",
    "Total des ventes": "Recettes",
    "Total dépenses": "Dépenses",
}
STATUTS_OK = {"Ouvert", "Fermé à l'inscription", "En attente"}


def sede(x):
    s = str(x).lower()
    if "milano" in s:
        return "IFM"
    if "firenze" in s or "florence" in s:
        return "IFF"
    if "napoli" in s or "naples" in s:
        return "IFN"
    if "palermo" in s or "palerme" in s:
        return "IFP"
    return "?"


def main():
    df = pd.read_excel(SRC, sheet_name="AEC")
    df.columns = [str(c).strip() for c in df.columns]   # vire les espaces finaux

    # ---- périmètre : 2023-01 → (mois courant + N mois) ; toujours à jour ----
    import os
    from datetime import date
    n_mois = int(os.environ.get("OSCAR_CUTOFF_MONTHS", "1"))
    lo = pd.Timestamp("2023-01-01")
    hi = (pd.Timestamp(date.today()) + pd.DateOffset(months=n_mois)).to_period("M").to_timestamp("M")
    dd0 = pd.to_datetime(df["Date début"], errors="coerce", dayfirst=True)
    df = df[(dd0 >= lo) & (dd0 <= hi)].copy()
    df.to_excel(OUT / "cours_FINAL.xlsx", index=False, sheet_name="AEC")
    print(f"PÉRIMÈTRE : {lo.date()} → {hi.date()} (mois courant + {n_mois}) "
          f"→ {len(df)} cours  (→ cours_FINAL.xlsx)\n")

    # ====================== 1) INTÉGRITÉ ======================
    print("=" * 60)
    print("INTÉGRITÉ —", SRC.name)
    print("=" * 60)
    print(f"lignes={len(df)}  colonnes={df.shape[1]}")
    attendues = ["Lieu du cours", "Catégorie", "Statut", "Date début", "Classe N°",
                 "Quantité d'inscriptions", "Nouveaux inscrits", "Réinscrits",
                 "Qté heures", "Qté heures vendues", "Qté synchrones heures vendues",
                 "Total des ventes", "Total dépenses", "Taux de remplissage",
                 "Niveau", "Tranche d'âge"]
    manquantes = [c for c in attendues if c not in df.columns]
    print("colonnes clés manquantes :", manquantes or "AUCUNE ✅")

    n_classes = df["Classe N°"].nunique(dropna=True)
    print(f"Classe N° uniques : {n_classes} / {len(df)} lignes  → doublons résiduels : {len(df) - n_classes}")

    dd = pd.to_datetime(df["Date début"], errors="coerce", dayfirst=True)
    print(f"Date début : NaT={int(dd.isna().sum())}  plage {dd.min()} → {dd.max()}")
    print("statuts :", {k: int(v) for k, v in df["Statut"].value_counts(dropna=False).items()})
    print("centres :", {sede(k): int(v) for k, v in df["Lieu du cours"].value_counts().items()})

    print("\nsanité numérique (min / max / NaN) :")
    for c in ["Quantité d'inscriptions", "Qté heures", "Qté heures vendues",
              "Total des ventes", "Total dépenses"]:
        if c in df.columns:
            s = pd.to_numeric(df[c], errors="coerce")
            neg = int((s < 0).sum())
            print(f"  {c:32s} min={s.min():>10.1f} max={s.max():>10.1f} NaN={int(s.isna().sum())} négatifs={neg}")

    # ====================== 2) TRAITEMENT OSCAR ======================
    df["Sede"] = df["Lieu du cours"].map(sede)
    mois = dd.dt.month
    annee = dd.dt.year
    df["Mois"] = mois
    df["Période"] = np.where(mois >= 9, "P1 (sep–déc)", "P2 (janv–août)")
    sy = annee - (mois < 9).astype("Int64")          # année scolaire = année de début
    df["Année scolaire"] = sy.astype("Int64").astype(str) + "–" + (sy + 1).astype("Int64").astype(str)

    # filtre statut
    avant = len(df)
    work = df[df["Statut"].isin(STATUTS_OK)].copy()
    print(f"\nfiltre statut (Ouvert/Fermé à l'inscr./En attente) : {len(work)} cours gardés "
          f"({avant - len(work)} jetés — Annulé/autres)")

    # renomme + numérise les indicateurs
    for brut, oscar in MAP.items():
        work[oscar] = pd.to_numeric(work.get(brut), errors="coerce").fillna(0) if brut in work else 0
    for c in ["Nouveaux inscrits", "Réinscrits"]:
        work[c] = pd.to_numeric(work.get(c), errors="coerce").fillna(0)

    # secteur / sous-secteur / macro via le mapping OSCAR
    sect = None
    if _MAP_SECT is not None:
        lv = work["Catégorie"].apply(_MAP_SECT)
        work["Macro-catégorie"] = lv.apply(lambda x: x[0])
        work["Sous-secteur"] = lv.apply(lambda x: x[1])
        work["Secteur"] = lv.apply(lambda x: x[2])
        nr = int((work["Secteur"] == "NON RATTACHÉ").sum())
        print(f"\nmapping secteur OSCAR : {len(work) - nr}/{len(work)} cours rattachés "
              f"({nr} NON RATTACHÉ = catégories à compléter dans data/category_mapping.csv)")
        top_nr = work.loc[work["Secteur"] == "NON RATTACHÉ", "Catégorie"].value_counts().head(8)
        if len(top_nr):
            print("  top catégories non rattachées :", {k: int(v) for k, v in top_nr.items()})
        sect = work.groupby(["Année scolaire", "Secteur"], dropna=False).agg(
            Nb_cours=("Classe N°", "count"),
            Inscriptions=("Inscriptions", "sum"),
            Heures_élèves=("Heures-élèves", "sum"),
            Recettes=("Recettes", "sum"),
        ).reset_index()
        print("\n=== par (année scolaire × secteur) ===")
        print(sect.to_string(index=False))

    # agrégat indicateurs par (année scolaire, période, sede)
    g = work.groupby(["Année scolaire", "Période", "Sede"], dropna=False).agg(
        Nb_cours=("Classe N°", "count"),
        Inscriptions=("Inscriptions", "sum"),
        Nouveaux=("Nouveaux inscrits", "sum"),
        Réinscrits=("Réinscrits", "sum"),
        Qté_heures=("Qté heures", "sum"),
        Heures_élèves=("Heures-élèves", "sum"),
        Heures_synchrones=("Heures synchrones", "sum"),
        Recettes=("Recettes", "sum"),
        Dépenses=("Dépenses", "sum"),
    ).reset_index()
    g["Taux_remplissage"] = (g["Inscriptions"] / g["Nb_cours"].replace(0, np.nan)).round(2)
    g["%_nouveaux"] = (g["Nouveaux"] / g["Inscriptions"].replace(0, np.nan) * 100).round(1)
    g["ARPI"] = (g["Recettes"] / g["Inscriptions"].replace(0, np.nan)).round(0)

    print("\n" + "=" * 60)
    print("INDICATEURS OSCAR — par (année scolaire, période, sede)")
    print("=" * 60)
    print(g.to_string(index=False))

    # totaux par année scolaire
    tot = work.groupby("Année scolaire").agg(
        Nb_cours=("Classe N°", "count"),
        Inscriptions=("Inscriptions", "sum"),
        Heures_élèves=("Heures-élèves", "sum"),
        Recettes=("Recettes", "sum"),
    ).reset_index()
    print("\nTOTAux par année scolaire :")
    print(tot.to_string(index=False))

    # ====================== SORTIES ======================
    cols_liste = ["Sede", "Année scolaire", "Période", "Date début", "Classe N°", "Code cours",
                  "Nom du cours", "Catégorie", "Secteur", "Sous-secteur", "Niveau", "Tranche d'âge",
                  "Format", "Statut", "Inscriptions", "Nouveaux inscrits", "Réinscrits",
                  "Qté heures", "Heures-élèves", "Heures synchrones", "Recettes", "Dépenses"]
    cols_liste = [c for c in cols_liste if c in work.columns]
    dest = OUT / "oscar_indicateurs_cours.xlsx"
    with pd.ExcelWriter(dest) as w:
        g.to_excel(w, sheet_name="Indicateurs", index=False)
        tot.to_excel(w, sheet_name="Totaux_année_scolaire", index=False)
        if sect is not None:
            sect.to_excel(w, sheet_name="Par_secteur", index=False)
        for ysc in sorted(work["Année scolaire"].dropna().unique()):
            sub = work[work["Année scolaire"] == ysc][cols_liste].sort_values(["Sede", "Date début"])
            sheet = ("AS_" + ysc).replace("–", "-")[:31]
            sub.to_excel(w, sheet_name=sheet, index=False)
    print(f"\n→ ÉCRIT : {dest.name}  (Indicateurs + Totaux + 1 feuille liste / année scolaire)")


if __name__ == "__main__":
    main()
