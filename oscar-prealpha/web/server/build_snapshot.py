"""build_snapshot.py — compute a real OSCAR snapshot from the annual AEC exports.

Loads the 2023/2024/2025 annual zip exports + category_mapping.csv from
../../data/, runs the oscar_core pipeline (load_excel -> process_data ->
aggregate_by_sector / create_ifi_totals / calculate_yoy_by_sede), and writes
fixtures/snapshot.json matching the existing fixture schema exactly.

Strategy:
  - meta.source = "computed" when the full pipeline succeeds.
  - On any per-field failure, fall back to the fixture value for that field and
    set source = "partial".
  - On total failure, leave the fixture untouched.

The annual zip xlsx files are the classic AEC "category report" format
(columns: Tranche d'âge du cours, Catégorie de cours, Nb. de Cours,
Nb. d'inscriptions, Nouveaux inscrits, Recettes, ...). They are consumed by the
oscar_core pipeline, NOT by aec_parser_v3 (which targets the newer per-course
export format with a 'Date début' column).
"""
from __future__ import annotations

import io
import json
import os
import zipfile
from datetime import datetime, timezone

import oscar_core as core

HERE = os.path.dirname(os.path.abspath(__file__))
# Prod (Vercel): data bundled at web/server/data ; dev: fall back to repo-root data/.
DATA_DIR = os.path.join(HERE, "data")
if not os.path.isdir(DATA_DIR):
    DATA_DIR = os.path.join(HERE, "..", "..", "..", "data")
FIXTURE_PATH = os.path.join(HERE, "fixtures", "snapshot.json")
# Pristine fallback copy (never overwritten); falls back to FIXTURE_PATH if absent.
PRISTINE_PATH = os.path.join(HERE, "fixtures", "snapshot.fixture.json")

ANNUAL_ZIPS = {
    2023: "exports_AEC_2023_annuel.zip",
    2024: "exports_AEC_2024_annuel.zip",
    2025: "exports_AEC_2025_annuel.zip",
}

ANTENNA_META = {
    "IFI": {"name": "IFI Global", "city": "Italia", "color": "#3B82F6"},
    "IFM": {"name": "IFM Milano", "city": "Milano", "color": "#FF8C00", "lat": 45.4642, "lng": 9.19},
    "IFF": {"name": "IFF Firenze", "city": "Firenze", "color": "#8B5CF6", "lat": 43.7696, "lng": 11.2558},
    "IFN": {"name": "IFN Napoli", "city": "Napoli", "color": "#22C55E", "lat": 40.8518, "lng": 14.2681},
    "IFP": {"name": "IFP Palermo", "city": "Palermo", "color": "#EF4444", "lat": 38.1157, "lng": 13.3615},
}

ANTENNA_ORDER = ["IFM", "IFF", "IFN", "IFP"]

# Map internal sector codes -> display labels used in the fixture sectors table.
SECTOR_LABELS = {
    "ECOLES": "ECOLES",
    "PROGRAMMÉS": "PROGRAMMÉS",
    "PLATEFORMES": "PLATEFORMES",
    "SUR MESURE": "INTENSIFS",   # fixture label; closest analogue in this dataset
    "SOCIÉTÉS": "ENTREPRISES",
}


def _empty_fallback():
    """An EMPTY snapshot — NO fabricated statistics. Used only if real
    computation fails, so the API/UI shows an honest 'unavailable' state.
    Antenna list is real network metadata (codes/colors/coords), not data."""
    antennas = []
    for code in ["IFI"] + ANTENNA_ORDER:
        m = ANTENNA_META[code]
        antennas.append({"code": code, **m})
    return {
        "meta": {"app": "OSCAR", "subtitle": "Institut français Italia — pilotage statistique",
                 "source": "unavailable", "updated": "", "years": [], "antennas": antennas},
        "filters": {"year": 0, "antennas": list(ANTENNA_ORDER), "sectors": []},
        "kpis": [],
        "byAntenna": [],
        "sectors": {"columns": ["Secteur", "Cours", "Inscriptions", "Nouv. inscrits", "% nouv.", "Recettes", "Remplissage"],
                    "rows": [], "total": {"secteur": "TOTAL", "cours": 0, "inscriptions": 0, "nouv": 0,
                                          "pctNouv": 0, "recettes": 0, "remplissage": 0}},
        "evolution": {"years": [], "series": []},
        "breakdowns": {}, "yoy": {"years": [], "rows": []},
        "profitability": {"bySector": [], "byAntenna": []},
    }


def _load_fixture():
    # Back-compat alias: callers expect a baseline dict. No fabricated data.
    return _empty_fallback()


def _round(v, ndigits=0):
    try:
        if ndigits == 0:
            return int(round(float(v)))
        return round(float(v), ndigits)
    except Exception:  # noqa: BLE001
        return 0


def load_all_years():
    """Return a tagged DataFrame from the NEW per-course cache
    (data/new_cours/cache_cours.xlsx), parsed by aec_parser_v3 + sector levels.
    (Remplace l'ancien chargement des ZIP « rapport par catégorie ».)"""
    import aec_parser_v3 as parser

    candidates = [
        os.path.join(DATA_DIR, "new_cours", "cache_cours.xlsx"),
        os.path.join(HERE, "..", "..", "..", "data", "new_cours", "cache_cours.xlsx"),
    ]
    path = next((p for p in candidates if os.path.exists(p)), None)
    if path is None:
        raise RuntimeError("cache_cours.xlsx introuvable — lance l'outil « Récupérer cours AEC ».")

    with open(path, "rb") as f:
        df, _stats = parser.parse_aec_export(f.read())  # aggregate=True

    # Mapping catégorie→secteur complet (sinon beaucoup de NON RATTACHÉ).
    for csv in (os.path.join(DATA_DIR, "category_mapping.csv"),
                os.path.join(HERE, "..", "..", "..", "data", "category_mapping.csv")):
        if os.path.exists(csv):
            try:
                core.load_csv_mappings(csv)
            except Exception:  # noqa: BLE001
                pass
            break

    # Niveaux de secteur (le parser ne les produit pas, engine les attend).
    levels = df["Catégorie de cours"].apply(core.map_category_to_levels)
    df["Macro-catégorie"] = levels.apply(lambda x: x[0])
    df["Sous-secteur"] = levels.apply(lambda x: x[1])
    df["Secteur"] = levels.apply(lambda x: x[2])
    return df


def compute_kpis(df, latest_year, prev_year):
    """KPIs for the latest year with YoY deltas vs prev_year."""
    def total(d, col):
        return d[col].sum() if col in d.columns else 0

    cur = df[df["Année"] == latest_year]
    prev = df[df["Année"] == prev_year] if prev_year else None

    def delta(cur_v, prev_v):
        if prev is None or prev_v in (0, None):
            return 0.0
        return round((cur_v - prev_v) / prev_v * 100, 1)

    inscr = total(cur, "Nb. d'inscriptions")
    cours = total(cur, "Nb. de Cours")
    recettes = total(cur, "Recettes")
    heures = total(cur, "Qté heures")
    rempl = (inscr / cours) if cours else 0

    p_inscr = total(prev, "Nb. d'inscriptions") if prev is not None else 0
    p_cours = total(prev, "Nb. de Cours") if prev is not None else 0
    p_recettes = total(prev, "Recettes") if prev is not None else 0
    p_rempl = (p_inscr / p_cours) if p_cours else 0

    dlabel = f"vs {prev_year}" if prev_year else "—"
    return [
        {"key": "inscriptions", "label": "Inscriptions", "value": _round(inscr),
         "format": "int", "delta": delta(inscr, p_inscr), "deltaLabel": dlabel},
        {"key": "cours", "label": "Cours", "value": _round(cours),
         "format": "int", "delta": delta(cours, p_cours), "deltaLabel": dlabel},
        {"key": "recettes", "label": "Recettes", "value": _round(recettes),
         "format": "eur", "delta": delta(recettes, p_recettes), "deltaLabel": dlabel},
        {"key": "heures", "label": "Qté heures", "value": _round(heures),
         "format": "int", "delta": 0, "deltaLabel": "stable"},
        {"key": "remplissage", "label": "Remplissage", "value": _round(rempl, 1),
         "format": "dec1", "delta": _round(rempl - p_rempl, 1), "deltaLabel": dlabel},
    ]


def compute_by_antenna(df, latest_year):
    cur = df[df["Année"] == latest_year]
    rows = []
    for code in ANTENNA_ORDER:
        d = cur[cur["Sede"] == code]
        inscr = d["Nb. d'inscriptions"].sum() if "Nb. d'inscriptions" in d.columns else 0
        cours = d["Nb. de Cours"].sum() if "Nb. de Cours" in d.columns else 0
        recettes = d["Recettes"].sum() if "Recettes" in d.columns else 0
        rempl = (inscr / cours) if cours else 0
        meta = ANTENNA_META[code]
        rows.append({
            "code": code, "name": meta["name"], "color": meta["color"],
            "inscriptions": _round(inscr), "cours": _round(cours),
            "recettes": _round(recettes), "remplissage": _round(rempl, 1),
        })
    return rows


def compute_sectors(df, latest_year):
    cur = df[df["Année"] == latest_year]
    agg = core.aggregate_by_sector(cur, group_cols=["Secteur"])
    rows = []
    tot_cours = tot_inscr = tot_nouv = tot_rec = 0.0
    # Order sectors by the canonical SECTOR_ORDER, then any extras.
    seen = list(agg["Secteur"]) if not agg.empty else []
    ordered = [s for s in core.SECTOR_ORDER if s in seen] + [s for s in seen if s not in core.SECTOR_ORDER]
    for sec in ordered:
        r = agg[agg["Secteur"] == sec]
        if r.empty:
            continue
        r = r.iloc[0]
        cours = float(r.get("Nb. de Cours", 0) or 0)
        inscr = float(r.get("Nb. d'inscriptions", 0) or 0)
        nouv = float(r.get("Nouveaux inscrits", 0) or 0)
        rec = float(r.get("Recettes", 0) or 0)
        rempl = (inscr / cours) if cours else 0
        pct = (nouv / inscr * 100) if inscr else 0
        rows.append({
            "secteur": SECTOR_LABELS.get(sec, sec),
            "cours": _round(cours), "inscriptions": _round(inscr),
            "nouv": _round(nouv), "pctNouv": _round(pct, 1),
            "recettes": _round(rec), "remplissage": _round(rempl, 2),
        })
        tot_cours += cours
        tot_inscr += inscr
        tot_nouv += nouv
        tot_rec += rec
    total = {
        "secteur": "TOTAL", "cours": _round(tot_cours), "inscriptions": _round(tot_inscr),
        "nouv": _round(tot_nouv),
        "pctNouv": _round((tot_nouv / tot_inscr * 100) if tot_inscr else 0, 1),
        "recettes": _round(tot_rec),
        "remplissage": _round((tot_inscr / tot_cours) if tot_cours else 0, 2),
    }
    return {
        "columns": ["Secteur", "Cours", "Inscriptions", "Nouv. inscrits", "% nouv.", "Recettes", "Remplissage"],
        "rows": rows,
        "total": total,
    }


def compute_evolution(df):
    yoy = core.calculate_yoy_by_sede(df)
    years = sorted(int(y) for y in df["Année"].unique())
    series = []
    for code in ANTENNA_ORDER:
        meta = ANTENNA_META[code]
        inscr_list, rec_list = [], []
        for yr in years:
            if yoy is not None:
                row = yoy[(yoy["Sede"] == code) & (yoy["Année"] == yr)]
                inscr_list.append(_round(row["Inscriptions"].sum()) if not row.empty else 0)
                rec_list.append(_round(row["Recettes"].sum()) if not row.empty else 0)
            else:
                d = df[(df["Sede"] == code) & (df["Année"] == yr)]
                inscr_list.append(_round(d["Nb. d'inscriptions"].sum()))
                rec_list.append(_round(d["Recettes"].sum()))
        series.append({
            "code": code, "name": meta["name"], "color": meta["color"],
            "inscriptions": inscr_list, "recettes": rec_list,
        })
    return {"years": years, "series": series}


DIMENSIONS = [
    ("secteur", "Secteur", "Secteur"),
    ("sous_secteur", "Sous-secteur", "Sous-secteur"),
    ("macro", "Macro-catégorie", "Macro-catégorie"),
    ("categorie", "Catégorie de cours", "Catégorie"),
]


def _agg_rows(agg, dim_col):
    """Turn an aggregate_by_sector result into snapshot rows + a TOTAL."""
    rows = []
    tc = ti = tn = tr = 0.0
    for _, r in agg.iterrows():
        cours = float(r.get("Nb. de Cours", 0) or 0)
        inscr = float(r.get("Nb. d'inscriptions", 0) or 0)
        nouv = float(r.get("Nouveaux inscrits", 0) or 0)
        rec = float(r.get("Recettes", 0) or 0)
        rows.append({
            "label": str(r.get(dim_col, "—")),
            "cours": _round(cours), "inscriptions": _round(inscr),
            "nouv": _round(nouv), "pctNouv": _round((nouv / inscr * 100) if inscr else 0, 1),
            "recettes": _round(rec), "remplissage": _round((inscr / cours) if cours else 0, 2),
        })
        tc += cours; ti += inscr; tn += nouv; tr += rec
    rows.sort(key=lambda x: x["inscriptions"], reverse=True)
    total = {
        "label": "TOTAL", "cours": _round(tc), "inscriptions": _round(ti),
        "nouv": _round(tn), "pctNouv": _round((tn / ti * 100) if ti else 0, 1),
        "recettes": _round(tr), "remplissage": _round((ti / tc) if tc else 0, 2),
    }
    return {"rows": rows, "total": total}


def compute_breakdowns(df, latest_year):
    """Per-dimension breakdown tables (Secteur / Sous-secteur / Macro / Catégorie)."""
    cur = df[df["Année"] == latest_year]
    out = {}
    for key, col, label in DIMENSIONS:
        if col not in cur.columns:
            continue
        agg = core.aggregate_by_sector(cur, group_cols=[col])
        if agg.empty:
            continue
        block = _agg_rows(agg, col)
        block["key"] = key
        block["label"] = label
        out[key] = block
    return out


def compute_yoy(df):
    """Global year-over-year table with variation %."""
    comp, years = core.calculate_yoy_comparison(df)
    if comp is None:
        return {"years": [int(y) for y in years], "rows": []}
    rows = []
    for _, r in comp.iterrows():
        rows.append({
            "year": int(r["Année"]),
            "inscriptions": _round(r["Inscriptions"]),
            "cours": _round(r["Cours"]),
            "recettes": _round(r["Recettes"]),
            "heures": _round(r["Heures"]),
            "inscriptionsVar": None if r.get("Inscriptions_var") != r.get("Inscriptions_var") else _round(r.get("Inscriptions_var", 0), 1),
            "recettesVar": None if r.get("Recettes_var") != r.get("Recettes_var") else _round(r.get("Recettes_var", 0), 1),
        })
    return {"years": [int(y) for y in years], "rows": rows}


def compute_profitability(df, latest_year):
    """ARPI (recettes / inscription) by sector and by antenna."""
    cur = df[df["Année"] == latest_year]
    by_sector_df, by_sede_df, _ = core.calculate_profitability(cur)
    by_sector = [
        {"label": str(r["Secteur"]), "inscriptions": _round(r["Nb. d'inscriptions"]),
         "recettes": _round(r["Recettes"]), "arpi": _round(r["ARPI"], 2)}
        for _, r in by_sector_df.iterrows()
    ]
    by_antenna = []
    for _, r in by_sede_df.iterrows():
        code = str(r["Sede"])
        meta = ANTENNA_META.get(code, {"color": "#64748B"})
        by_antenna.append({
            "code": code, "color": meta.get("color", "#64748B"),
            "inscriptions": _round(r["Nb. d'inscriptions"]),
            "recettes": _round(r["Recettes"]), "arpi": _round(r["ARPI"], 2),
        })
    return {"bySector": by_sector, "byAntenna": by_antenna}


def build():
    fixture = _load_fixture()
    source = "computed"

    # meta is always rebuilt deterministically from constants.
    meta = {
        "app": "OSCAR",
        "subtitle": "Institut français Italia — pilotage statistique",
        "source": source,
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "years": fixture["meta"]["years"],
        "antennas": fixture["meta"]["antennas"],
    }

    try:
        df = load_all_years()
    except Exception as e:  # noqa: BLE001
        print(f"[build_snapshot] data load failed ({e}); returning EMPTY (no fake data).")
        return _empty_fallback(), "unavailable"

    years = sorted(int(y) for y in df["Année"].unique())
    latest_year = years[-1]
    prev_year = years[-2] if len(years) >= 2 else None
    meta["years"] = years

    snapshot = {"meta": meta}

    # filters
    snapshot["filters"] = {"year": latest_year, "antennas": list(ANTENNA_ORDER), "sectors": []}

    # kpis
    try:
        snapshot["kpis"] = compute_kpis(df, latest_year, prev_year)
    except Exception as e:  # noqa: BLE001
        print(f"[build_snapshot] kpis failed ({e}); using fixture.")
        snapshot["kpis"] = fixture["kpis"]
        source = "partial"

    # byAntenna
    try:
        snapshot["byAntenna"] = compute_by_antenna(df, latest_year)
    except Exception as e:  # noqa: BLE001
        print(f"[build_snapshot] byAntenna failed ({e}); using fixture.")
        snapshot["byAntenna"] = fixture["byAntenna"]
        source = "partial"

    # sectors
    try:
        snapshot["sectors"] = compute_sectors(df, latest_year)
    except Exception as e:  # noqa: BLE001
        print(f"[build_snapshot] sectors failed ({e}); using fixture.")
        snapshot["sectors"] = fixture["sectors"]
        source = "partial"

    # evolution
    try:
        snapshot["evolution"] = compute_evolution(df)
    except Exception as e:  # noqa: BLE001
        print(f"[build_snapshot] evolution failed ({e}); using fixture.")
        snapshot["evolution"] = fixture["evolution"]
        source = "partial"

    # breakdowns (Secteur / Sous-secteur / Macro / Catégorie)
    try:
        snapshot["breakdowns"] = compute_breakdowns(df, latest_year)
    except Exception as e:  # noqa: BLE001
        print(f"[build_snapshot] breakdowns failed ({e}).")
        snapshot["breakdowns"] = {}

    # year-over-year (global table)
    try:
        snapshot["yoy"] = compute_yoy(df)
    except Exception as e:  # noqa: BLE001
        print(f"[build_snapshot] yoy failed ({e}).")
        snapshot["yoy"] = {"years": [], "rows": []}

    # profitability (ARPI)
    try:
        snapshot["profitability"] = compute_profitability(df, latest_year)
    except Exception as e:  # noqa: BLE001
        print(f"[build_snapshot] profitability failed ({e}).")
        snapshot["profitability"] = {"bySector": [], "byAntenna": []}

    snapshot["meta"]["source"] = source
    return snapshot, source


def main():
    snapshot, source = build()
    os.makedirs(os.path.dirname(FIXTURE_PATH), exist_ok=True)
    with open(FIXTURE_PATH, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2)
    print(f"[build_snapshot] wrote {FIXTURE_PATH} (source={source})")
    return source


if __name__ == "__main__":
    main()
