#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""controle_incoherences.py — contrôle qualité des dates AEC.

Repère les cours dont la DATE DE DÉBUT ne colle pas avec l'année de leur
PÉRIODE AEC (« 2026-MARS » → 2026), et écrit une liste EXPORTABLE :
    data/new_cours/incoherences_dates.xlsx

Deux niveaux :
  • « erreur probable » : début ET fin hors de l'année de période
    (ex. cours daté 2025 mais rangé/nommé 2026 → saisie erronée).
  • « à vérifier (cours long) » : début hors année de période mais la fin y
    retombe (cours qui chevauche deux années — souvent légitime).

Usage : .venv\\Scripts\\python.exe controle_incoherences.py
"""
from __future__ import annotations
import re
import sys
from pathlib import Path
import pandas as pd

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

OUT = Path(__file__).resolve().parent / "data" / "new_cours"
CACHE = OUT / "cache_cours.xlsx"
RESULT = OUT / "incoherences_dates.xlsx"


def _year_from_period(p) -> int | None:
    m = re.match(r"\s*(\d{4})", str(p))
    return int(m.group(1)) if m else None


def _year_from_code(c) -> int | None:
    m = re.search(r"(20\d{2})", str(c))
    return int(m.group(1)) if m else None


def main() -> int:
    if not CACHE.exists():
        print(f"❌ Cache introuvable : {CACHE} — lance d'abord l'export.")
        return 1
    df = pd.read_excel(CACHE)
    df.columns = [str(c).strip() for c in df.columns]

    deb = pd.to_datetime(df.get("Date début"), errors="coerce", dayfirst=True)
    fin = pd.to_datetime(df.get("Date fin"), errors="coerce", dayfirst=True)
    py = df.get("Période").map(_year_from_period) if "Période" in df.columns else pd.Series([None] * len(df))
    cy = df.get("Code cours").map(_year_from_code) if "Code cours" in df.columns else pd.Series([None] * len(df))

    valid = deb.dt.year.notna() & py.notna()
    debut_hors = valid & (deb.dt.year != py)
    fin_hors = fin.dt.year.isna() | (fin.dt.year != py)
    erreur = debut_hors & fin_hors                       # début ET fin hors période
    long_ = debut_hors & ~fin_hors                       # début hors, fin dans la période

    def _g(r, *names):
        """1ʳᵉ colonne existante parmi `names` (tolère les variantes AEC)."""
        for n in names:
            if n in df.columns and pd.notna(r.get(n)) and str(r.get(n)).strip():
                return r.get(n)
        return None

    rows = []
    for idx in df.index[debut_hors]:
        r = df.loc[idx]
        rows.append({
            "Gravité": "⚠ erreur probable" if erreur[idx] else "à vérifier (cours long)",
            # Identification (ordre demandé : période · intitulé · n° · prof · dates)
            "Période AEC": r.get("Période"),
            "Intitulé (Nom du cours)": _g(r, "Nom du cours", "Nom du cours.1"),
            "N° classe (id)": r.get("Classe N°"),
            "Code cours": r.get("Code cours"),
            "Professeur(s)": _g(r, "Enseignant", "Professeur", "Enseignants"),
            "Date début": deb[idx].date() if pd.notna(deb[idx]) else None,
            "Date fin": fin[idx].date() if pd.notna(fin[idx]) else None,
            # Contexte / diagnostic
            "Année période": py[idx],
            "Année code": cy[idx],
            "Année date début": int(deb[idx].year) if pd.notna(deb[idx]) else None,
            "Écart (ans)": (int(py[idx]) - int(deb[idx].year)) if pd.notna(deb[idx]) else None,
            "Catégorie": r.get("Catégorie"),
            "Niveau": _g(r, "Niveau"),
            "Tranche d'âge": _g(r, "Tranche d'âge", "Tranche d'âge du cours"),
            "Antenne (Lieu)": r.get("Lieu du cours"),
            "Statut": r.get("Statut"),
            "Nb inscriptions": _g(r, "Quantité d'inscriptions", "Nb. d'inscriptions", "Inscrits à ce jour"),
        })

    res = pd.DataFrame(rows)
    if not res.empty:
        res = res.sort_values(["Gravité", "Antenne (Lieu)", "Date début"]).reset_index(drop=True)
    res.to_excel(RESULT, index=False)

    n_err = int(erreur.sum())
    n_long = int(long_.sum())
    print(f"Cours contrôlés          : {int(valid.sum())}")
    print(f"⚠ Erreurs probables      : {n_err}")
    print(f"À vérifier (cours longs) : {n_long}")
    print(f"→ Liste exportée         : {RESULT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
