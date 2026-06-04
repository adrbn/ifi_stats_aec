"""build_produits.py — compute a real OSCAR "Produits" data file.

Loads the 4 real produits xlsx exports from ../../data/ exactly the way OSCAR
does (extract_sede_from_filename + process_produits in oscar_core), then writes
fixtures/produits.json matching the agreed contract.

On total failure (no files load), writes {"available": false, "reason": ...}.
Every aggregation is guarded with `if col in df.columns` so missing columns are
omitted gracefully rather than crashing.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

import pandas as pd

import oscar_core as core

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "..", "..", "data")
FIXTURE_PATH = os.path.join(HERE, "fixtures", "produits.json")

PRODUIT_FILES = [
    "export_1272524851_produits_IFM.xlsx",
    "export_1337622529_produits_IFF.xlsx",
    "export_274802696_produits_IFN.xlsx",
    "export_762105081_produits_IFP.xlsx",
]

ANTENNA_META = {
    "IFM": {"name": "IFM Milano", "color": "#FF8C00"},
    "IFF": {"name": "IFF Firenze", "color": "#8B5CF6"},
    "IFN": {"name": "IFN Napoli", "color": "#22C55E"},
    "IFP": {"name": "IFP Palermo", "color": "#EF4444"},
}
ANTENNA_ORDER = ["IFM", "IFF", "IFN", "IFP"]

CATALOGUE_CAP = 1000

# Column name constants
COL_TYPE = "Type de produit"
COL_NOM = "Nom du produit"
COL_PRIX = "Prix"
COL_HEURES = "Heures"
COL_PLACES = "Nombre maximum de places"
COL_ACTIF = "Actif"
COL_SEDE = "Sede"
COL_TARIF_REDUIT = "Tarif réduit"
COL_PRIX_MEMBRE = "Prix membre"

PRIX_HISTOGRAM_BINS = 30
BOX_MIN_ROWS = 5  # only build a box for types with enough priced rows
REDUCED_SCATTER_CAP = 600


# ---- numpy/pandas -> plain python helpers -------------------------------

def _py(value):
    """Convert a numpy/pandas scalar to a plain python int/float/None."""
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if hasattr(value, "item"):
        value = value.item()
    return value


def _f(value, ndigits=None):
    """Coerce to plain float (optionally rounded), or None if not finite."""
    v = _py(value)
    if v is None:
        return None
    try:
        fv = float(v)
    except (TypeError, ValueError):
        return None
    if fv != fv:  # NaN
        return None
    return round(fv, ndigits) if ndigits is not None else fv


def _i(value):
    """Coerce to plain int, or None."""
    v = _f(value)
    return int(v) if v is not None else None


# ---- loading ------------------------------------------------------------

def load_all():
    """Load + process all available produits files. Returns (df, loaded_names)."""
    frames = []
    loaded = []
    for fn in PRODUIT_FILES:
        path = os.path.join(DATA_DIR, fn)
        if not os.path.exists(path):
            continue
        try:
            raw = pd.read_excel(path, engine="openpyxl")
        except Exception as exc:  # noqa: BLE001
            print(f"[build_produits] failed to read {fn}: {exc}")
            continue
        sede = core.extract_sede_from_filename(fn)
        frames.append(core.process_produits(raw, sede))
        loaded.append(fn)
    if not frames:
        return None, []
    df = pd.concat(frames, ignore_index=True)
    return df, loaded


# ---- aggregations -------------------------------------------------------

def build_kpis(df):
    kpis = []
    kpis.append({"key": "produits", "label": "Produits", "value": int(len(df)), "format": "int"})
    if COL_TYPE in df.columns:
        kpis.append({"key": "types", "label": "Types",
                     "value": int(df[COL_TYPE].nunique()), "format": "int"})
    if COL_ACTIF in df.columns:
        kpis.append({"key": "actifs", "label": "Produits actifs",
                     "value": int(df[COL_ACTIF].sum()), "format": "int"})
    if COL_PRIX in df.columns:
        kpis.append({"key": "prixMoyen", "label": "Prix moyen",
                     "value": _f(df[COL_PRIX].mean(), 2), "format": "eur0"})
    if COL_HEURES in df.columns:
        kpis.append({"key": "heures", "label": "Total heures",
                     "value": _f(df[COL_HEURES].sum(), 2), "format": "int"})
    if COL_PLACES in df.columns:
        kpis.append({"key": "capacite", "label": "Capacité totale",
                     "value": _f(df[COL_PLACES].sum(), 2), "format": "int"})
    return kpis


def build_by_sede(df):
    if COL_SEDE not in df.columns:
        return []
    out = []
    for code in ANTENNA_ORDER:
        sub = df[df[COL_SEDE] == code]
        if len(sub) == 0:
            continue
        meta = ANTENNA_META[code]
        row = {
            "code": code,
            "name": meta["name"],
            "color": meta["color"],
            "nbProduits": int(len(sub)),
        }
        if COL_PRIX in sub.columns:
            row["prixMoyen"] = _f(sub[COL_PRIX].mean(), 1)
        if COL_HEURES in sub.columns:
            row["totalHeures"] = _f(sub[COL_HEURES].sum(), 1)
        out.append(row)
    return out


def build_by_type(df):
    if COL_TYPE not in df.columns:
        return []
    out = []
    for type_name, sub in df.groupby(COL_TYPE):
        row = {"type": str(type_name), "nbProduits": int(len(sub))}
        if COL_PRIX in sub.columns:
            row["prixMoyen"] = _f(sub[COL_PRIX].mean(), 2)
            row["prixMin"] = _f(sub[COL_PRIX].min(), 2)
            row["prixMax"] = _f(sub[COL_PRIX].max(), 2)
        if COL_HEURES in sub.columns:
            row["heuresTotal"] = _f(sub[COL_HEURES].sum(), 1)
            row["heuresMoy"] = _f(sub[COL_HEURES].mean(), 1)
        out.append(row)
    out.sort(key=lambda r: r["nbProduits"], reverse=True)
    return out


def build_catalogue(df):
    out = []
    for _, r in df.head(CATALOGUE_CAP).iterrows():
        item = {
            "sede": str(r[COL_SEDE]) if COL_SEDE in df.columns else "???",
            "type": str(r[COL_TYPE]) if COL_TYPE in df.columns else "",
            "nom": str(r[COL_NOM]) if COL_NOM in df.columns else "",
            "prix": _f(r[COL_PRIX]) if COL_PRIX in df.columns else None,
            "heures": _f(r[COL_HEURES]) if COL_HEURES in df.columns else None,
            "places": _f(r[COL_PLACES]) if COL_PLACES in df.columns else None,
            "actif": bool(r[COL_ACTIF]) if COL_ACTIF in df.columns else False,
        }
        out.append(item)
    return out


def build_prix_stats_by_sede(df):
    if COL_SEDE not in df.columns or COL_PRIX not in df.columns:
        return []
    out = []
    for code in ANTENNA_ORDER:
        sub = df[df[COL_SEDE] == code]
        if len(sub) == 0:
            continue
        prix = sub[COL_PRIX]
        out.append({
            "code": code,
            "nbProduits": int(len(sub)),
            "prixMoyen": _f(prix.mean(), 1),
            "prixMedian": _f(prix.median(), 1),
            "prixMin": _f(prix.min(), 1),
            "prixMax": _f(prix.max(), 1),
            "ecartType": _f(prix.std(), 1),
        })
    return out


def build_prix_par_heure_by_type(df):
    if COL_TYPE not in df.columns or COL_PRIX not in df.columns or COL_HEURES not in df.columns:
        return []
    out = []
    for type_name, sub in df.groupby(COL_TYPE):
        sub = sub[sub[COL_HEURES] > 0]
        if len(sub) == 0:
            continue
        ratio = (sub[COL_PRIX] / sub[COL_HEURES]).mean()
        out.append({
            "type": str(type_name),
            "prixParHeure": _f(ratio, 1),
            "nbProduits": int(len(sub)),
        })
    out.sort(key=lambda r: (r["prixParHeure"] if r["prixParHeure"] is not None else -1),
             reverse=True)
    return out


def build_prix_histogram(df):
    """Histogram of Prix>0 over ~30 fixed-width bins → [{bin, count}]."""
    if COL_PRIX not in df.columns:
        return []
    prix = df[df[COL_PRIX] > 0][COL_PRIX].dropna()
    if len(prix) == 0:
        return []
    lo = float(prix.min())
    hi = float(prix.max())
    if hi <= lo:  # all the same value → single bin
        return [{"bin": _f(lo, 0), "count": int(len(prix))}]
    counts, edges = _histogram(prix, lo, hi)
    out = []
    for i, c in enumerate(counts):
        center = (edges[i] + edges[i + 1]) / 2.0
        out.append({"bin": _f(center, 0), "count": int(c)})
    return out


def _histogram(series, lo, hi):
    """Pure-python fixed-width histogram (avoids numpy import surface)."""
    width = (hi - lo) / PRIX_HISTOGRAM_BINS
    edges = [lo + i * width for i in range(PRIX_HISTOGRAM_BINS + 1)]
    counts = [0] * PRIX_HISTOGRAM_BINS
    for v in series:
        idx = int((v - lo) / width)
        if idx >= PRIX_HISTOGRAM_BINS:
            idx = PRIX_HISTOGRAM_BINS - 1
        if idx < 0:
            idx = 0
        counts[idx] += 1
    return counts, edges


def build_prix_box_by_type(df):
    """Five-number summary of Prix per type (only types with enough rows)."""
    if COL_TYPE not in df.columns or COL_PRIX not in df.columns:
        return []
    out = []
    for type_name, sub in df.groupby(COL_TYPE):
        prix = sub[COL_PRIX].dropna()
        if len(prix) < BOX_MIN_ROWS:
            continue
        out.append({
            "type": str(type_name),
            "min": _f(prix.min(), 1),
            "q1": _f(prix.quantile(0.25), 1),
            "median": _f(prix.median(), 1),
            "q3": _f(prix.quantile(0.75), 1),
            "max": _f(prix.max(), 1),
        })
    out.sort(key=lambda r: (r["median"] if r["median"] is not None else -1), reverse=True)
    return out


def build_type_by_sede(df):
    """Counts per type × antenna → [{type, IFM, IFF, IFN, IFP}] for grouped bar."""
    if COL_TYPE not in df.columns or COL_SEDE not in df.columns:
        return []
    out = []
    for type_name, sub in df.groupby(COL_TYPE):
        row = {"type": str(type_name)}
        for code in ANTENNA_ORDER:
            row[code] = int((sub[COL_SEDE] == code).sum())
        out.append(row)
    out.sort(key=lambda r: sum(r[c] for c in ANTENNA_ORDER), reverse=True)
    return out


def build_reduced(df):
    """Scatter Prix vs Tarif réduit (capped) + reduction KPIs."""
    if COL_TARIF_REDUIT not in df.columns or COL_PRIX not in df.columns:
        return [], {"nb": 0, "avgPct": None, "maxPct": None}
    sub = df[(df[COL_TARIF_REDUIT] > 0) & (df[COL_PRIX] > 0)].copy()
    if len(sub) == 0:
        return [], {"nb": 0, "avgPct": None, "maxPct": None}
    sub["__pct"] = (sub[COL_PRIX] - sub[COL_TARIF_REDUIT]) / sub[COL_PRIX] * 100.0
    kpis = {
        "nb": int(len(sub)),
        "avgPct": _f(sub["__pct"].mean(), 1),
        "maxPct": _f(sub["__pct"].max(), 1),
    }
    scatter = []
    for _, r in sub.head(REDUCED_SCATTER_CAP).iterrows():
        scatter.append({
            "prix": _f(r[COL_PRIX], 1),
            "tarifReduit": _f(r[COL_TARIF_REDUIT], 1),
            "sede": str(r[COL_SEDE]) if COL_SEDE in df.columns else "???",
            "nom": str(r[COL_NOM]) if COL_NOM in df.columns else "",
            "type": str(r[COL_TYPE]) if COL_TYPE in df.columns else "",
        })
    return scatter, kpis


def build_member_kpis(df):
    """KPIs for rows with Prix membre>0 & Prix>0 → {nb, avgPct}."""
    if COL_PRIX_MEMBRE not in df.columns or COL_PRIX not in df.columns:
        return {"nb": 0, "avgPct": None}
    sub = df[(df[COL_PRIX_MEMBRE] > 0) & (df[COL_PRIX] > 0)].copy()
    if len(sub) == 0:
        return {"nb": 0, "avgPct": None}
    pct = (sub[COL_PRIX] - sub[COL_PRIX_MEMBRE]) / sub[COL_PRIX] * 100.0
    return {"nb": int(len(sub)), "avgPct": _f(pct.mean(), 1)}


def build():
    df, loaded = load_all()
    if df is None:
        return {"available": False,
                "reason": f"no produits xlsx could be loaded from {DATA_DIR}"}

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    reduced_scatter, reduced_kpis = build_reduced(df)
    return {
        "available": True,
        "meta": {"source": "computed", "updated": now},
        "kpis": build_kpis(df),
        "bySede": build_by_sede(df),
        "byType": build_by_type(df),
        "catalogue": build_catalogue(df),
        "prixStatsBySede": build_prix_stats_by_sede(df),
        "prixParHeureByType": build_prix_par_heure_by_type(df),
        "prixHistogram": build_prix_histogram(df),
        "prixBoxByType": build_prix_box_by_type(df),
        "typeBySede": build_type_by_sede(df),
        "reducedScatter": reduced_scatter,
        "reducedKpis": reduced_kpis,
        "memberKpis": build_member_kpis(df),
    }


def main():
    result = build()
    os.makedirs(os.path.dirname(FIXTURE_PATH), exist_ok=True)
    with open(FIXTURE_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    status = "available" if result.get("available") else f"unavailable: {result.get('reason')}"
    print(f"[build_produits] wrote {FIXTURE_PATH} ({status})")
    return result


if __name__ == "__main__":
    main()
