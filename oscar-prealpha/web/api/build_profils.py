#!/usr/bin/env python3
"""build_profils.py — compute fixtures/profils.json for the OSCAR pre-alpha.

Loads the real clients CSV the same way OSCAR does (pandas, auto-detected
separator), runs oscar_core.process_profils_clients (ported verbatim from
dashboard_aec_v2.py), then aggregates the result into the JSON contract the
web front-end expects.

Run with the project venv:
    .venv/bin/python build_profils.py
"""
from __future__ import annotations

import json
import math
import os
from datetime import datetime, timezone

import pandas as pd

import oscar_core as oc

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
API_DIR = os.path.dirname(os.path.abspath(__file__))
# Prod (Vercel): data bundled at web/api/data ; dev: fall back to repo-root data/.
DATA_DIR = os.path.join(API_DIR, "data")
if not os.path.isdir(DATA_DIR):
    DATA_DIR = os.path.join(API_DIR, "..", "..", "..", "data")
CSV_PATH = os.path.normpath(
    os.path.join(DATA_DIR, "export_417433918_clients_nat_23_24_25_26.csv")
)
FIXTURES_DIR = os.path.join(API_DIR, "fixtures")
OUT_PATH = os.path.join(FIXTURES_DIR, "profils.json")

# Antenna metadata (code -> display name + colour)
SEDE_META = {
    "IFM": ("IFM Milano", "#FF8C00"),
    "IFF": ("IFF Firenze", "#8B5CF6"),
    "IFN": ("IFN Napoli", "#22C55E"),
    "IFP": ("IFP Palermo", "#EF4444"),
}
SEDE_ORDER = ["IFM", "IFF", "IFN", "IFP"]

# ---------------------------------------------------------------------------
# JSON-safe rounding helpers (plain python int / float, never numpy)
# ---------------------------------------------------------------------------

def _is_nan(v) -> bool:
    try:
        return v is None or (isinstance(v, float) and math.isnan(v)) or pd.isna(v)
    except (TypeError, ValueError):
        return False


def to_int(v) -> int:
    if _is_nan(v):
        return 0
    return int(v)


def round1(v) -> float:
    """Round to 1 decimal, returning a plain float (0.0 on NaN)."""
    if _is_nan(v):
        return 0.0
    return round(float(v), 1)


def pct1(part: float, whole: float) -> float:
    if not whole:
        return 0.0
    return round(100.0 * float(part) / float(whole), 1)


# ---------------------------------------------------------------------------
# CSV loading (same approach as OSCAR: pandas read_csv with auto separator)
# ---------------------------------------------------------------------------

def load_clients_csv(path: str) -> pd.DataFrame:
    """Load the clients export. Auto-detect separator, fall back on latin-1."""
    for enc in ("utf-8", "latin-1"):
        try:
            return pd.read_csv(
                path, sep=None, engine="python", encoding=enc, dtype=str
            )
        except (UnicodeDecodeError, pd.errors.ParserError):
            continue
    # Last resort: default comma separator
    return pd.read_csv(path, encoding="latin-1", low_memory=False, dtype=str)


# ---------------------------------------------------------------------------
# Column discovery helpers
# ---------------------------------------------------------------------------

def find_canal_col(df: pd.DataFrame):
    for c in df.columns:
        lc = c.lower()
        if "comment" in lc and "connu" in lc:
            return c
    return None


def find_col(df: pd.DataFrame, *candidates):
    for cand in candidates:
        if cand in df.columns:
            return cand
    return None


# ---------------------------------------------------------------------------
# Section builders
# ---------------------------------------------------------------------------

def _gender_counts(series: pd.Series):
    """Return (F, M, NS) integer counts for a Genre series."""
    f = int((series == "F").sum())
    m = int((series == "M").sum())
    ns = int((~series.isin(["F", "M"])).sum())
    return f, m, ns


def build_kpis(df: pd.DataFrame):
    total = len(df)
    genre = df["Genre"] if "Genre" in df.columns else pd.Series([], dtype=object)
    f, m, ns = _gender_counts(genre)
    antennes = 0
    if "Sede" in df.columns:
        antennes = int(df.loc[df["Sede"] != "???", "Sede"].nunique())
    age_mean = 0.0
    if "Age_Clean" in df.columns:
        age_mean = round1(pd.to_numeric(df["Age_Clean"], errors="coerce").mean())
    return [
        {"key": "clients", "label": "Clients", "value": int(total), "format": "int"},
        {"key": "antennes", "label": "Antennes", "value": antennes, "format": "int"},
        {"key": "femmes", "label": "% Femmes", "value": pct1(f, total), "format": "pct1"},
        {"key": "hommes", "label": "% Hommes", "value": pct1(m, total), "format": "pct1"},
        {"key": "nonspec", "label": "% Non spécifié", "value": pct1(ns, total), "format": "pct1"},
        {"key": "age", "label": "Âge moyen", "value": age_mean, "format": "dec1"},
    ]


def build_by_sede(df: pd.DataFrame):
    rows = []
    if "Sede" not in df.columns:
        return rows
    for code in SEDE_ORDER:
        sub = df[df["Sede"] == code]
        if len(sub) == 0:
            continue
        name, color = SEDE_META[code]
        f, m, ns = _gender_counts(sub["Genre"]) if "Genre" in sub.columns else (0, 0, 0)
        ages = pd.to_numeric(sub.get("Age_Clean"), errors="coerce") if "Age_Clean" in sub.columns else pd.Series([], dtype=float)
        rows.append({
            "code": code,
            "name": name,
            "color": color,
            "clients": int(len(sub)),
            "femmes": f,
            "hommes": m,
            "nonSpec": ns,
            "ageMoyen": round1(ages.mean()),
            "ageMedian": round1(ages.median()),
        })
    return rows


def build_gender_by_sede(df: pd.DataFrame):
    rows = []
    if "Sede" not in df.columns or "Genre" not in df.columns:
        return rows
    for code in SEDE_ORDER:
        sub = df[df["Sede"] == code]
        if len(sub) == 0:
            continue
        f, m, ns = _gender_counts(sub["Genre"])
        rows.append({"code": code, "F": f, "M": m, "NS": ns})
    return rows


def build_tranches(df: pd.DataFrame):
    rows = []
    if "Tranche_Custom" not in df.columns:
        return rows
    total = len(df)
    counts = df["Tranche_Custom"].value_counts()
    for label in oc.CUSTOM_AGE_BRACKET_ORDER:
        c = int(counts.get(label, 0))
        if c == 0:
            continue
        rows.append({"label": label, "count": c, "pct": pct1(c, total)})
    return rows


def build_types_cours(df: pd.DataFrame):
    rows = []
    if "Type_Cours_FR" not in df.columns:
        return rows
    sub = df["Type_Cours_FR"].dropna()
    sub = sub[sub.astype(str).str.strip() != ""]
    total = len(sub)
    for label, c in sub.value_counts().items():
        rows.append({"label": str(label), "count": int(c), "pct": pct1(int(c), total)})
    return rows  # already sorted desc by value_counts


def build_nationalities(df: pd.DataFrame):
    if "Nationalité" not in df.columns:
        return {}
    raw = df["Nationalité"].astype(str).str.strip()
    blank = raw.isin(["", "nan", "None", "NaN"])
    non_specified = int(blank.sum())
    valid = raw[~blank]
    total_valid = len(valid)
    counts = valid.value_counts()
    nb_nat = int(counts.shape[0])
    principal = {"label": "", "pct": 0.0}
    if total_valid > 0:
        top_label = counts.index[0]
        principal = {"label": str(top_label), "pct": pct1(int(counts.iloc[0]), total_valid)}
    top = [
        {"label": str(lbl), "count": int(c), "pct": pct1(int(c), total_valid)}
        for lbl, c in counts.head(20).items()
    ]
    return {
        "nbNationalities": nb_nat,
        "principal": principal,
        "nonSpecified": non_specified,
        "top": top,
    }


def build_simple_breakdown(df: pd.DataFrame, col, top_n=None):
    """Generic count breakdown for a single column (motivation/canal/csp)."""
    rows = []
    if col is None or col not in df.columns:
        return rows
    sub = df[col].astype(str).str.strip()
    sub = sub[~sub.isin(["", "nan", "None", "NaN"])]
    total = len(sub)
    vc = sub.value_counts()
    if top_n is not None:
        vc = vc.head(top_n)
    for lbl, c in vc.items():
        rows.append({"label": str(lbl), "count": int(c), "pct": pct1(int(c), total)})
    return rows


# ---------------------------------------------------------------------------
# Enriched sections (parity with OSCAR Online render_profils_tabs)
# ---------------------------------------------------------------------------

def _ages(df: pd.DataFrame) -> pd.Series:
    """Valid ages as a numeric series (NaN dropped)."""
    if "Age_Clean" not in df.columns:
        return pd.Series([], dtype=float)
    return pd.to_numeric(df["Age_Clean"], errors="coerce").dropna()


def _histogram(ages: pd.Series, lo: int = 3, hi: int = 80, step: int = 2):
    """2-year bins over [lo, hi). Returns list of {bin, count}."""
    rows = []
    if len(ages) == 0:
        return rows
    for start in range(lo, hi, step):
        end = start + step
        c = int(((ages >= start) & (ages < end)).sum())
        rows.append({"bin": f"{start}-{end}", "count": c})
    return rows


def _box_stats(ages: pd.Series):
    """Return {min,q1,median,q3,max} for a box plot (0.0 when empty)."""
    if len(ages) == 0:
        return {"min": 0.0, "q1": 0.0, "median": 0.0, "q3": 0.0, "max": 0.0}
    return {
        "min": round1(ages.min()),
        "q1": round1(ages.quantile(0.25)),
        "median": round1(ages.median()),
        "q3": round1(ages.quantile(0.75)),
        "max": round1(ages.max()),
    }


def build_age_histogram(df: pd.DataFrame):
    """Overall 2-year age histogram over Age_Clean (3..80)."""
    return _histogram(_ages(df))


def build_age_by_sede(df: pd.DataFrame):
    """Per Sede: 2-year age histogram + box-plot stats."""
    rows = []
    if "Sede" not in df.columns or "Age_Clean" not in df.columns:
        return rows
    for code in SEDE_ORDER:
        sub = df[df["Sede"] == code]
        if len(sub) == 0:
            continue
        ages = _ages(sub)
        if len(ages) == 0:
            continue
        name, color = SEDE_META[code]
        rows.append({
            "code": code,
            "name": name,
            "color": color,
            "histogram": _histogram(ages),
            "box": _box_stats(ages),
        })
    return rows


def build_tranches_by_sede(df: pd.DataFrame):
    """Grouped bar: one row per bracket, one column per Sede code."""
    rows = []
    if "Tranche_Custom" not in df.columns or "Sede" not in df.columns:
        return rows
    for label in oc.CUSTOM_AGE_BRACKET_ORDER:
        sub = df[df["Tranche_Custom"] == label]
        if len(sub) == 0:
            continue
        row = {"code": label}
        for code in SEDE_ORDER:
            row[code] = int((sub["Sede"] == code).sum())
        rows.append(row)
    return rows


def build_levels(df: pd.DataFrame):
    """Macro_Niveau counts ordered A0..C2 then Autre."""
    rows = []
    if "Macro_Niveau" not in df.columns:
        return rows
    counts = df["Macro_Niveau"].value_counts()
    order = list(oc.MACRO_LEVEL_ORDER) + ["Autre"]
    for label in order:
        c = int(counts.get(label, 0))
        if c == 0:
            continue
        rows.append({"label": label, "count": c})
    return rows


def build_nationality_by_sede(df: pd.DataFrame):
    """For the top-5 nationalities, per-Sede client counts (grouped bar)."""
    rows = []
    if "Nationalité" not in df.columns or "Sede" not in df.columns:
        return rows
    raw = df["Nationalité"].astype(str).str.strip()
    valid_mask = ~raw.isin(["", "nan", "None", "NaN"])
    valid = raw[valid_mask]
    if len(valid) == 0:
        return rows
    top5 = list(valid.value_counts().head(5).index)
    for nat in top5:
        nat_mask = valid_mask & (raw == nat)
        sub = df[nat_mask]
        row = {"nationality": str(nat)}
        for code in SEDE_ORDER:
            row[code] = int((sub["Sede"] == code).sum())
        rows.append(row)
    return rows


def build_breakdown_by_sede(df: pd.DataFrame, col, top_n=None):
    """Per-Sede % share for a categorical column (motivation/canal).

    Returns [{label, IFM, IFF, IFN, IFP}] where each antenna value is the
    percentage that label represents *within that antenna* (normalized per
    Sede, matching the OSCAR Online grouped %-bars). When top_n is set, only
    the globally most frequent labels are kept (canal -> top 5).
    """
    rows = []
    if col is None or col not in df.columns or "Sede" not in df.columns:
        return rows
    sub = df[[col, "Sede"]].copy()
    sub[col] = sub[col].astype(str).str.strip()
    sub = sub[~sub[col].isin(["", "nan", "None", "NaN"])]
    if len(sub) == 0:
        return rows
    labels = list(sub[col].value_counts().index)
    if top_n is not None:
        labels = labels[:top_n]
    sub = sub[sub[col].isin(labels)]
    # per-Sede totals (over the kept labels, mirroring OSCAR's transform("sum"))
    sede_totals = {code: int((sub["Sede"] == code).sum()) for code in SEDE_ORDER}
    for label in labels:
        lab_rows = sub[sub[col] == label]
        row = {"label": str(label)}
        for code in SEDE_ORDER:
            cnt = int((lab_rows["Sede"] == code).sum())
            row[code] = pct1(cnt, sede_totals[code])
        rows.append(row)
    return rows


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    os.makedirs(FIXTURES_DIR, exist_ok=True)

    if not os.path.exists(CSV_PATH):
        payload = {"available": False, "reason": f"CSV not found at {CSV_PATH}"}
        with open(OUT_PATH, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
        print("UNAVAILABLE:", payload["reason"])
        return

    try:
        df_raw = load_clients_csv(CSV_PATH)
    except Exception as exc:  # noqa: BLE001 — surface any load failure
        payload = {"available": False, "reason": f"Failed to load CSV: {exc}"}
        with open(OUT_PATH, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
        print("UNAVAILABLE:", payload["reason"])
        return

    # Capture the acquisition-channel column name before RGPD filtering.
    canal_col_raw = find_canal_col(df_raw)

    df = oc.process_profils_clients(df_raw)

    canal_col = find_canal_col(df) or canal_col_raw
    motivation_col = find_col(df, "Motivation")
    csp_col = find_col(df, "Catégorie socio-professionnelle")

    fixture = {
        "available": True,
        "meta": {
            "source": "computed",
            "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "total": int(len(df)),
        },
        "kpis": build_kpis(df),
        "bySede": build_by_sede(df),
        "tranches": build_tranches(df),
        "typesCours": build_types_cours(df),
        "genderBySede": build_gender_by_sede(df),
        "nationalities": build_nationalities(df),
        "motivation": build_simple_breakdown(df, motivation_col),
        "canal": build_simple_breakdown(df, canal_col),
        "csp": build_simple_breakdown(df, csp_col, top_n=15),
        # ── Enriched sections (parity with OSCAR Online) ──
        "ageHistogram": build_age_histogram(df),
        "ageBySede": build_age_by_sede(df),
        "tranchesBySede": build_tranches_by_sede(df),
        "levels": build_levels(df),
        "nationalityBySede": build_nationality_by_sede(df),
        "motivationBySede": build_breakdown_by_sede(df, motivation_col),
        "canalBySede": build_breakdown_by_sede(df, canal_col, top_n=5),
    }

    with open(OUT_PATH, "w", encoding="utf-8") as fh:
        json.dump(fixture, fh, ensure_ascii=False, indent=2)

    kpi_sample = ", ".join(f"{k['label']}={k['value']}" for k in fixture["kpis"])
    print(f"Wrote {OUT_PATH}")
    print(f"KPIs: {kpi_sample}")
    print(
        f"Sections: bySede={len(fixture['bySede'])}, tranches={len(fixture['tranches'])}, "
        f"typesCours={len(fixture['typesCours'])}, "
        f"nationalities.top={len(fixture['nationalities'].get('top', []))}, "
        f"motivation={len(fixture['motivation'])}, canal={len(fixture['canal'])}, "
        f"csp={len(fixture['csp'])}"
    )
    print(
        f"Enriched: ageHistogram={len(fixture['ageHistogram'])}, "
        f"ageBySede={len(fixture['ageBySede'])}, tranchesBySede={len(fixture['tranchesBySede'])}, "
        f"levels={len(fixture['levels'])}, nationalityBySede={len(fixture['nationalityBySede'])}, "
        f"motivationBySede={len(fixture['motivationBySede'])}, canalBySede={len(fixture['canalBySede'])}"
    )


if __name__ == "__main__":
    main()
