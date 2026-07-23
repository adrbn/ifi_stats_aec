#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_cache_ids.py — remplace QUELQUES cours dans le cache, par n° de classe.

Complément de `reexport_ids.py` : celui-ci réexporte des cours précis depuis
AEC (`cours_corriges.xlsx`), celui-là les injecte dans `cache_cours.xlsx`.

Différence avec `update_cache.py` : update_cache remplace des ANNÉES ENTIÈRES
(un fichier d'une ligne y effacerait toute une année). Ici c'est un *upsert*
ligne à ligne sur « Classe N° » : seuls les cours listés bougent, le reste du
cache est strictement inchangé — y compris si la correction fait changer le
cours d'année ou de période.

Usage :
    python patch_cache_ids.py            # applique
    python patch_cache_ids.py --dry-run  # montre ce qui changerait, n'écrit rien
"""
from __future__ import annotations
import re
import sys
import shutil
import argparse

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

from pathlib import Path
import pandas as pd

OUT = Path(__file__).resolve().parent / "data" / "new_cours"
CACHE = OUT / "cache_cours.xlsx"
BACKUP = OUT / "cache_cours.bak_patch.xlsx"
CORRIGES = OUT / "cours_corriges.xlsx"
CLE = "Classe N°"
SUIVI = ["Nom du cours", "Période", "Date début", "Date fin", "Statut", "Lieu du cours"]


def _lire(p: Path) -> pd.DataFrame:
    try:
        df = pd.read_excel(p, sheet_name="AEC")
    except Exception:
        df = pd.read_excel(p)
    df.columns = [str(c).strip() for c in df.columns]
    return df


def _cle(s: pd.Series) -> pd.Series:
    return s.astype(str).str.replace(r"\D", "", regex=True)


def _apercu(r) -> str:
    bouts = []
    for c in SUIVI:
        if c in r.index and pd.notna(r[c]):
            v = str(r[c])
            bouts.append(f"{c}={v[:34]}")
    return " | ".join(bouts)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="affiche les changements sans écrire le cache")
    ap.add_argument("--source", default=str(CORRIGES),
                    help="fichier des cours réexportés (défaut : cours_corriges.xlsx)")
    ap.add_argument("--supprimer", default="",
                    help="n° de classe à RETIRER du cache (cours supprimés dans AEC), "
                         "séparés par des virgules")
    args = ap.parse_args()

    a_supprimer = {re.sub(r"\D", "", x) for x in args.supprimer.split(",") if x.strip()}
    a_supprimer.discard("")

    if not CACHE.exists():
        print(f"❌ {CACHE.name} introuvable — il n'y a rien à corriger.")
        return 1
    cache = _lire(CACHE)
    if CLE not in cache.columns:
        print(f"❌ colonne « {CLE} » absente de {CACHE.name}.")
        return 1

    # Une suppression seule est un usage valable (cours effacé dans AEC) : dans
    # ce cas il n'y a pas de réexport à fusionner.
    src = Path(args.source)
    if src.exists():
        neuf = _lire(src)
        if CLE not in neuf.columns:
            print(f"❌ colonne « {CLE} » absente de {src.name}.")
            return 1
    elif a_supprimer:
        neuf = pd.DataFrame(columns=cache.columns)
    else:
        print(f"❌ {src.name} introuvable — lance d'abord `reexport_ids.py`.")
        return 1
    if neuf.empty and not a_supprimer:
        print(f"❌ {src.name} est vide — rien à faire (cache intact).")
        return 1

    # Colonnes : on aligne le neuf sur le cache (l'export AEC doit avoir les
    # mêmes ; on signale tout écart plutôt que de le masquer).
    manquantes = [c for c in cache.columns if c not in neuf.columns]
    nouvelles = [c for c in neuf.columns if c not in cache.columns]
    if manquantes:
        print(f"⚠ {len(manquantes)} colonne(s) du cache absente(s) de l'export "
              f"→ laissées vides : {manquantes[:6]}{'…' if len(manquantes) > 6 else ''}")
    if nouvelles:
        print(f"⚠ {len(nouvelles)} colonne(s) en trop dans l'export → ignorée(s) : "
              f"{nouvelles[:6]}{'…' if len(nouvelles) > 6 else ''}")
    neuf = neuf.reindex(columns=cache.columns)

    cache["__k"] = _cle(cache[CLE])
    neuf["__k"] = _cle(neuf[CLE])
    neuf = neuf.drop_duplicates("__k", keep="first")

    avant = len(cache)
    print(f"\nCache avant : {avant} cours")
    print(f"Cours réexportés : {len(neuf)}\n")

    # ── détail des changements ────────────────────────────────────────
    remplaces, ajoutes, inchanges = [], [], []
    idx_cache = {k: i for i, k in enumerate(cache["__k"])}
    for _, r in neuf.iterrows():
        k = r["__k"]
        if k in idx_cache:
            old = cache.iloc[idx_cache[k]]
            diffs = []
            for c in SUIVI:
                if c in cache.columns:
                    a, b = old.get(c), r.get(c)
                    if str(a) != str(b):
                        diffs.append(f"{c} : {str(a)[:24]} → {str(b)[:24]}")
            if diffs:
                remplaces.append((k, diffs))
                print(f"  ✏ n° {k}")
                for d in diffs:
                    print(f"      {d}")
            else:
                inchanges.append(k)
        else:
            ajoutes.append(k)
            print(f"  ➕ n° {k} (absent du cache) — {_apercu(r)}")

    # ── suppressions demandées (cours effacés dans AEC) ───────────────
    supprimes, introuvables = [], []
    for k in sorted(a_supprimer):
        if k in idx_cache:
            supprimes.append(k)
            print(f"  🗑 n° {k} RETIRÉ du cache — {_apercu(cache.iloc[idx_cache[k]])}")
        else:
            introuvables.append(k)
    if introuvables:
        print(f"  (à supprimer mais déjà absents du cache : {', '.join(introuvables)})")

    if inchanges:
        print(f"  = {len(inchanges)} cours identiques (aucun changement) : "
              f"{', '.join(inchanges[:12])}{'…' if len(inchanges) > 12 else ''}")
    print(f"\nRésumé : {len(remplaces)} modifié(s), {len(ajoutes)} ajouté(s), "
          f"{len(supprimes)} supprimé(s), {len(inchanges)} inchangé(s)")

    if not remplaces and not ajoutes and not supprimes:
        print("→ Rien à écrire, le cache est déjà à jour.")
        return 0

    # ── fusion ────────────────────────────────────────────────────────
    # Un cours explicitement supprimé ne doit pas être réintroduit par le
    # réexport : on l'écarte des deux côtés.
    neuf = neuf[~neuf["__k"].isin(a_supprimer)]
    garde = cache[~cache["__k"].isin(set(neuf["__k"]) | a_supprimer)]
    fusion = pd.concat([neuf, garde], ignore_index=True).drop(columns="__k")
    apres = len(fusion)

    # garde-fous : hors suppressions explicites, un upsert ne doit RIEN perdre
    attendu = avant + len(ajoutes) - len(supprimes)
    if apres != attendu:
        print(f"❌ incohérence : {apres} lignes après fusion, {attendu} attendues. "
              f"Écriture annulée (cache intact).")
        return 1
    dups = int(fusion[CLE].notna().sum() - fusion[CLE].nunique(dropna=True))
    if dups:
        print(f"❌ {dups} doublons « {CLE} » après fusion — écriture annulée (cache intact).")
        return 1

    print(f"Cache après : {apres} cours  (Δ {apres - avant:+d})")
    an = pd.to_datetime(fusion["Date début"], errors="coerce", dayfirst=True).dt.year
    print("  par année :", {int(a): int(v) for a, v in an.value_counts().sort_index().items()
                            if pd.notna(a)})

    if args.dry_run:
        print("\n🧪 --dry-run : aucun fichier modifié.")
        return 0

    try:
        shutil.copyfile(CACHE, BACKUP)
        print(f"  💾 backup → {BACKUP.name}")
    except Exception as e:  # noqa: BLE001
        print(f"  (backup impossible : {e})")

    fusion.to_excel(CACHE, index=False, sheet_name="AEC")
    print(f"\n→ {CACHE.name} mis à jour ({apres} cours × {fusion.shape[1]} colonnes)")
    print("   Pense à relancer le contrôle qualité, puis « Publier sur OSCAR ».")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
