#!/usr/bin/env python3
"""
merge_eleves.py — fusionne les exports « Par Classe » (eleves_par_classe_*.xlsx)
en un cache d'enrôlements (Code Client × Code cours) pour l'indicateur
« nombre d'élèves différents ».

Le backend joint ensuite ce cache au cache cours sur « Code cours » : le nombre
d'élèves différents d'un périmètre = Code Client distincts parmi les enrôlements
dont le Code cours appartient au périmètre filtré.

Sortie : data/new_cours/cache_eleves.xlsx (+ copie dans web/server/data/new_cours
pour la prod Vercel).
"""
from __future__ import annotations
import glob
import re
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).parent
SRC = ROOT / "data" / "new_cours"
OUT = SRC / "cache_eleves.xlsx"
PROD = ROOT / "oscar-prealpha" / "web" / "server" / "data" / "new_cours" / "cache_eleves.xlsx"

KEEP = ["Code Client", "Code cours", "Nom du cours"]


def main():
    files = sorted(glob.glob(str(SRC / "eleves_par_classe_*.xlsx")))
    if not files:
        raise SystemExit("Aucun fichier eleves_par_classe_*.xlsx — lance export_eleves_par_classe.py")

    parts = []
    for f in files:
        year = int(re.search(r"(\d{4})", Path(f).name).group(1))
        d = pd.read_excel(f, sheet_name=0)
        d.columns = [str(c).strip() for c in d.columns]
        d = d[[c for c in KEEP if c in d.columns]].copy()
        d["Année"] = year
        parts.append(d)
        print(f"  {Path(f).name}: {len(d)} enrôlements")

    e = pd.concat(parts, ignore_index=True)
    e = e.dropna(subset=["Code Client", "Code cours"])
    e["Code Client"] = e["Code Client"].astype(str).str.strip()
    e["Code cours"] = e["Code cours"].astype(str).str.strip()

    # Grain = 1 ligne par (Code Client, Code cours) : un élève inscrit à un cours.
    # (Un même couple peut apparaître plusieurs fois si plusieurs inscriptions ;
    # on garde l'année la plus récente pour info.)
    before = len(e)
    e = e.sort_values("Année").drop_duplicates(subset=["Code Client", "Code cours"], keep="last")
    print(f"\nenrôlements: {before} → {len(e)} couples (Code Client × Code cours) uniques")
    print(f"élèves DISTINCTS (Code Client) global : {e['Code Client'].nunique()}")
    print(f"cours distincts (Code cours)          : {e['Code cours'].nunique()}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    e.to_excel(OUT, index=False)
    print(f"\n✅ {OUT}")
    try:
        PROD.parent.mkdir(parents=True, exist_ok=True)
        e.to_excel(PROD, index=False)
        print(f"✅ {PROD} (prod Vercel)")
    except Exception as ex:  # noqa: BLE001
        print(f"⚠ copie prod ratée: {ex}")


if __name__ == "__main__":
    main()
