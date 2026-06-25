"""engine.py — on-demand OSCAR computation (matches OSCAR Online's live recompute).

Loads the combined Cours dataframe ONCE, then computes the full payload for any
filter combination (multiple years, multiple antennas). Same pandas functions as
the original dashboard → same results. Real sector names (no relabeling).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

import oscar_core as core
import build_snapshot as bs

_DF = None
_ELEVES = None


def get_df():
    """Combined, tagged Cours dataframe across all annual exports (cached)."""
    global _DF
    if _DF is None:
        _DF = bs.load_all_years()
    return _DF


def get_eleves():
    """Cache d'enrôlements (Code Client × Code cours) — chargé une fois."""
    global _ELEVES
    if _ELEVES is None:
        _ELEVES = bs.load_eleves()
    return _ELEVES


def _distinct_students(df_scope) -> Optional[int]:
    """Nombre d'élèves différents (Code Client distincts) parmi les enrôlements
    dont le « Code cours » appartient au périmètre df_scope. Renvoie None si le
    cache élèves est absent (l'indicateur est alors masqué côté UI)."""
    el = get_eleves()
    if el is None or not len(el) or "Code cours" not in df_scope.columns:
        return None
    codes = set(df_scope["Code cours"].dropna().astype(str))
    if not codes:
        return 0
    return int(el[el["Code cours"].isin(codes)]["Code Client"].nunique())


def _year_col(mode: str) -> str:
    """Colonne d'année selon le mode : civile (défaut) ou scolaire."""
    return "Année scolaire" if mode == "school" else "Année"


def available_years(mode: str = "civil") -> List[int]:
    df = get_df()
    col = _year_col(mode)
    if col not in df.columns:
        col = "Année"
    return sorted(int(y) for y in df[col].unique())


def meta(mode: str = "civil") -> dict:
    antennas = []
    for code in ["IFI"] + bs.ANTENNA_ORDER:
        antennas.append({"code": code, **bs.ANTENNA_META[code]})
    return {
        "app": "OSCAR",
        "subtitle": "Institut français Italia — pilotage statistique",
        "source": "computed",
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "years": available_years(mode),
        "yearMode": mode,
        "antennas": antennas,
    }


def _sum(d, col):
    return float(d[col].sum()) if col in d.columns and len(d) else 0.0


def _year_text(y: int, mode: str) -> str:
    """Libellé d'année : civile « 2024 » / scolaire « 2024-25 »."""
    return f"{y}-{(y + 1) % 100:02d}" if mode == "school" else str(y)


def _kpis(df_sel, years: List[int], antennas: List[str], df_all=None, year_mode: str = "civil"):
    """Totals over the selected years. Delta vs previous year only when a single
    year is selected (and the prior year exists for the same antennas).

    df_all : référentiel complet (déjà aligné sur le mode d'année actif) pour le
    calcul du delta N-1. Fourni par compute() afin que le mode scolaire compare
    bien à l'année scolaire précédente. year_mode sert au libellé du delta
    (« vs 2024 » en civil, « vs 2024-25 » en scolaire)."""
    if df_all is None:
        df_all = get_df()
    inscr = _sum(df_sel, "Nb. d'inscriptions")
    cours = _sum(df_sel, "Nb. de Cours")
    recettes = _sum(df_sel, "Recettes")
    heures = _sum(df_sel, "Qté heures")
    heures_eleves = _sum(df_sel, "Nombre total d'heures vendues (heures-étudiants)")
    eleves_diff = _distinct_students(df_sel)  # None si cache élèves absent
    rempl = (inscr / cours) if cours else 0
    panier_inscr = (recettes / inscr) if inscr else 0
    panier_pers = (recettes / eleves_diff) if eleves_diff else None  # None si pas de cache élèves

    delta = {"inscr": None, "cours": None, "recettes": None, "rempl": None,
             "heures": None, "heures_eleves": None, "eleves": None,
             "panier_inscr": None, "panier_pers": None}
    dlabel = ""
    if len(years) == 1:
        prev = years[0] - 1
        prev_sel = df_all[(df_all["Année"] == prev) & (df_all["Sede"].isin(antennas))]
        if len(prev_sel):
            # Comparaison à l'année (civile ou scolaire) précédente — df_all est
            # déjà aligné sur le mode actif, donc « prev » est la bonne année.
            dlabel = f"vs {_year_text(prev, year_mode)}"
            p_inscr = _sum(prev_sel, "Nb. d'inscriptions")
            p_cours = _sum(prev_sel, "Nb. de Cours")
            p_rec = _sum(prev_sel, "Recettes")
            p_heures = _sum(prev_sel, "Qté heures")
            p_heures_el = _sum(prev_sel, "Nombre total d'heures vendues (heures-étudiants)")
            p_eleves = _distinct_students(prev_sel)
            p_rempl = (p_inscr / p_cours) if p_cours else 0
            p_panier_inscr = (p_rec / p_inscr) if p_inscr else 0
            p_panier_pers = (p_rec / p_eleves) if p_eleves else 0
            pct = lambda c, p: round((c - p) / p * 100, 1) if p else None
            delta = {
                "inscr": pct(inscr, p_inscr),
                "cours": pct(cours, p_cours),
                "recettes": pct(recettes, p_rec),
                "heures": pct(heures, p_heures),
                "heures_eleves": pct(heures_eleves, p_heures_el),
                "eleves": pct(eleves_diff, p_eleves) if (eleves_diff is not None and p_eleves) else None,
                "rempl": round(rempl - p_rempl, 1) if p_rempl else None,
                "panier_inscr": pct(panier_inscr, p_panier_inscr),
                "panier_pers": pct(panier_pers, p_panier_pers) if (panier_pers is not None and p_panier_pers) else None,
            }

    # Ordre métier : Inscriptions · (Élèves différents) · Cours · Qté heures ·
    # Remplissage · Recettes · Heures-élèves. « Élèves différents » n'apparaît
    # que si le cache élèves est présent (sinon l'indicateur est masqué).
    out = [
        {"key": "inscriptions", "label": "Inscriptions", "value": bs._round(inscr), "format": "int", "delta": delta["inscr"], "deltaLabel": dlabel},
    ]
    if eleves_diff is not None:
        out.append({"key": "eleves_differents", "label": "Élèves différents", "value": int(eleves_diff), "format": "int", "delta": delta["eleves"], "deltaLabel": dlabel})
    out += [
        {"key": "cours", "label": "Cours", "value": bs._round(cours), "format": "int", "delta": delta["cours"], "deltaLabel": dlabel},
        {"key": "heures", "label": "Qté heures", "value": bs._round(heures), "format": "int", "delta": delta["heures"], "deltaLabel": dlabel},
        {"key": "remplissage", "label": "Élèves / cours", "value": bs._round(rempl, 1), "format": "dec1", "delta": delta["rempl"], "deltaLabel": dlabel},
        {"key": "heures_eleves", "label": "Heures-élèves", "value": bs._round(heures_eleves), "format": "int", "delta": delta["heures_eleves"], "deltaLabel": dlabel},
        {"key": "recettes", "label": "Recettes", "value": bs._round(recettes), "format": "eur", "delta": delta["recettes"], "deltaLabel": dlabel},
        {"key": "panier_inscr", "label": "Panier / inscr.", "value": bs._round(panier_inscr), "format": "eur", "delta": delta["panier_inscr"], "deltaLabel": dlabel},
    ]
    # Panier par personne distincte : seulement si le cache élèves est présent.
    if panier_pers is not None:
        out.append({"key": "panier_pers", "label": "Panier / personne", "value": bs._round(panier_pers), "format": "eur", "delta": delta["panier_pers"], "deltaLabel": dlabel})
    return out


def _by_antenna(df_sel, antennas: List[str]):
    rows = []
    for code in bs.ANTENNA_ORDER:
        if code not in antennas:
            continue
        d = df_sel[df_sel["Sede"] == code]
        inscr = _sum(d, "Nb. d'inscriptions")
        cours = _sum(d, "Nb. de Cours")
        rows.append({
            "code": code, "name": bs.ANTENNA_META[code]["name"], "color": bs.ANTENNA_META[code]["color"],
            "inscriptions": bs._round(inscr), "cours": bs._round(cours),
            "recettes": bs._round(_sum(d, "Recettes")),
            "remplissage": bs._round((inscr / cours) if cours else 0, 1),
        })
    return rows


def _sectors(df_sel):
    agg = core.aggregate_by_sector(df_sel, group_cols=["Secteur"])
    seen = list(agg["Secteur"]) if not agg.empty else []
    ordered = [s for s in core.SECTOR_ORDER if s in seen] + [s for s in seen if s not in core.SECTOR_ORDER]
    rows, tc, ti, tn, tr = [], 0.0, 0.0, 0.0, 0.0
    for sec in ordered:
        r = agg[agg["Secteur"] == sec]
        if r.empty:
            continue
        r = r.iloc[0]
        cours = float(r.get("Nb. de Cours", 0) or 0)
        inscr = float(r.get("Nb. d'inscriptions", 0) or 0)
        nouv = float(r.get("Nouveaux inscrits", 0) or 0)
        rec = float(r.get("Recettes", 0) or 0)
        rows.append({
            "secteur": sec,  # REAL sector name (no relabeling)
            "cours": bs._round(cours), "inscriptions": bs._round(inscr), "nouv": bs._round(nouv),
            "pctNouv": bs._round((nouv / inscr * 100) if inscr else 0, 1),
            "recettes": bs._round(rec), "remplissage": bs._round((inscr / cours) if cours else 0, 2),
        })
        tc += cours; ti += inscr; tn += nouv; tr += rec
    total = {"secteur": "TOTAL", "cours": bs._round(tc), "inscriptions": bs._round(ti), "nouv": bs._round(tn),
             "pctNouv": bs._round((tn / ti * 100) if ti else 0, 1), "recettes": bs._round(tr),
             "remplissage": bs._round((ti / tc) if tc else 0, 2)}
    return {"columns": ["Secteur", "Cours", "Inscriptions", "Nouv. inscrits", "% nouv.", "Recettes", "Remplissage"],
            "rows": rows, "total": total}


def _breakdowns(df_sel):
    out = {}
    for key, col, label in bs.DIMENSIONS:
        if col not in df_sel.columns:
            continue
        agg = core.aggregate_by_sector(df_sel, group_cols=[col])
        if agg.empty:
            continue
        block = bs._agg_rows(agg, col)
        block["key"] = key
        block["label"] = label
        out[key] = block
    return out


def _evolution(df_sel, years: List[int], antennas: List[str]):
    yrs = sorted(years)
    series = []
    for code in bs.ANTENNA_ORDER:
        if code not in antennas:
            continue
        metrics = {k: [] for k, _l, _c, _f in INDICATORS}
        inscr_list, rec_list = [], []
        for yr in yrs:
            d = df_sel[(df_sel["Sede"] == code) & (df_sel["Année"] == yr)]
            for key, _l, col, _f in INDICATORS:
                metrics[key].append(_indic_value(d, key, col))
            inscr_list.append(bs._round(_sum(d, "Nb. d'inscriptions")))
            rec_list.append(bs._round(_sum(d, "Recettes")))
        series.append({"code": code, "name": bs.ANTENNA_META[code]["name"], "color": bs.ANTENNA_META[code]["color"],
                       "inscriptions": inscr_list, "recettes": rec_list, "metrics": metrics})
    return {"years": yrs, "series": series}


def _yoy(df_sel, years: List[int]):
    rows = []
    yrs = sorted(years)
    prev_vals = None
    for yr in yrs:
        d = df_sel[df_sel["Année"] == yr]
        inscr = _sum(d, "Nb. d'inscriptions")
        cours = _sum(d, "Nb. de Cours")
        rec = _sum(d, "Recettes")
        heures = _sum(d, "Nombre total d'heures vendues (heures-étudiants)")
        iv = rv = None
        if prev_vals:
            iv = round((inscr - prev_vals[0]) / prev_vals[0] * 100, 1) if prev_vals[0] else None
            rv = round((rec - prev_vals[1]) / prev_vals[1] * 100, 1) if prev_vals[1] else None
        rows.append({"year": yr, "inscriptions": bs._round(inscr), "cours": bs._round(cours),
                     "recettes": bs._round(rec), "heures": bs._round(heures),
                     "inscriptionsVar": iv, "recettesVar": rv})
        prev_vals = (inscr, rec)
    return {"years": yrs, "rows": rows}


def _profitability(df_sel):
    if df_sel.empty:
        return {"bySector": [], "byAntenna": []}
    by_sector_df, by_sede_df, _ = core.calculate_profitability(df_sel)
    by_sector = [{"label": str(r["Secteur"]), "inscriptions": bs._round(r["Nb. d'inscriptions"]),
                  "recettes": bs._round(r["Recettes"]), "arpi": bs._round(r["ARPI"], 2)}
                 for _, r in by_sector_df.iterrows()]
    by_antenna = []
    for _, r in by_sede_df.iterrows():
        code = str(r["Sede"])
        m = bs.ANTENNA_META.get(code, {"color": "#64748B"})
        by_antenna.append({"code": code, "color": m.get("color", "#64748B"),
                           "inscriptions": bs._round(r["Nb. d'inscriptions"]),
                           "recettes": bs._round(r["Recettes"]), "arpi": bs._round(r["ARPI"], 2)})
    return {"bySector": by_sector, "byAntenna": by_antenna}


_DIM_COL = {
    "secteurs": "Secteur",
    "sousSecteurs": "Sous-secteur",
    "macros": "Macro-catégorie",
    "categories": "Catégorie de cours",
}

# Indicators shared by the per-sector / per-antenna analytical charts.
# « eleves_differents » est un COMPTE DISTINCT (non additif) : col=None, calculé
# spécialement dans _indic_value via _distinct_students.
INDICATORS = [
    ("inscriptions", "Inscriptions", "Nb. d'inscriptions", "int"),
    ("eleves_differents", "Élèves différents", None, "int"),
    ("cours", "Cours", "Nb. de Cours", "int"),
    ("nouveaux", "Nouveaux inscrits", "Nouveaux inscrits", "int"),
    ("reinscrits", "Réinscrits", "Réinscrits", "int"),
    ("heures", "Qté heures", "Qté heures", "int"),
    ("heures_eleves", "Heures-élèves", "Nombre total d'heures vendues (heures-étudiants)", "int"),
    ("recettes", "Recettes", "Recettes", "eur"),
    ("remplissage", "Élèves / cours", None, "dec1"),
    # Paniers moyens (ratios non additifs, col=None → calcul spécial _indic_value).
    # panier_inscr = Recettes / inscriptions ; panier_pers = Recettes / élèves
    # différents (dépend du cache élèves, sinon 0).
    ("panier_inscr", "Panier / inscr.", None, "eur"),
    ("panier_pers", "Panier / personne", None, "eur"),
]
INDICATOR_META = [{"key": k, "label": l, "format": f} for k, l, _c, f in INDICATORS]


def _ordered_sectors(df_sel):
    if "Secteur" not in df_sel.columns:
        return []
    present = list(df_sel["Secteur"].dropna().unique())
    return [s for s in core.SECTOR_ORDER if s in present] + [s for s in present if s not in core.SECTOR_ORDER]


def _indic_value(d, key, col):
    if key == "remplissage":
        inscr = _sum(d, "Nb. d'inscriptions")
        cours = _sum(d, "Nb. de Cours")
        return round(inscr / cours, 2) if cours else 0
    if key == "panier_inscr":
        inscr = _sum(d, "Nb. d'inscriptions")
        return bs._round(_sum(d, "Recettes") / inscr) if inscr else 0
    if key == "panier_pers":
        pers = _distinct_students(d)
        return bs._round(_sum(d, "Recettes") / pers) if pers else 0
    if key == "eleves_differents":
        v = _distinct_students(d)
        return int(v) if v is not None else 0
    return bs._round(_sum(d, col))


def _by_sector_indicators(df_sel):
    out = {}
    secteurs = _ordered_sectors(df_sel)
    for key, _l, col, _f in INDICATORS:
        out[key] = [{"label": sec, "value": _indic_value(df_sel[df_sel["Secteur"] == sec], key, col)} for sec in secteurs]
    return out


def _by_antenna_indicators(df_sel, antennas):
    out = {}
    for key, _l, col, _f in INDICATORS:
        rows = []
        for code in bs.ANTENNA_ORDER:
            if code not in antennas:
                continue
            d = df_sel[df_sel["Sede"] == code]
            rows.append({"code": code, "color": bs.ANTENNA_META[code]["color"], "value": _indic_value(d, key, col)})
        out[key] = rows
    return out


def _sector_antenna_matrix(df_sel, antennas):
    """Matrice secteur × antenne pour CHAQUE indicateur (matrices[key][sec][ant]).
    La heatmap peut ainsi suivre l'indicateur sélectionné."""
    secteurs = _ordered_sectors(df_sel)
    ants = [a for a in bs.ANTENNA_ORDER if a in antennas]
    matrices = {key: [] for key, _l, _c, _f in INDICATORS}
    for sec in secteurs:
        row_by_key = {key: [] for key, _l, _c, _f in INDICATORS}
        for a in ants:
            d = df_sel[(df_sel["Secteur"] == sec) & (df_sel["Sede"] == a)]
            for key, _l, col, _f in INDICATORS:
                row_by_key[key].append(_indic_value(d, key, col))
        for key in matrices:
            matrices[key].append(row_by_key[key])
    return {
        "sectors": secteurs, "antennas": ants,
        "matrices": matrices,
        # rétro-compat (anciens clients) :
        "inscriptions": matrices.get("inscriptions", []),
        "remplissage": matrices.get("remplissage", []),
    }


def _flows(df_sel, antennas):
    """Flux antenne → secteur, avec la valeur de CHAQUE indicateur par flux
    (values[key]). `value` reste les inscriptions (rétro-compat / défaut)."""
    out = []
    if "Secteur" not in df_sel.columns:
        return out
    for a in [x for x in bs.ANTENNA_ORDER if x in antennas]:
        da = df_sel[df_sel["Sede"] == a]
        for sec in _ordered_sectors(da):
            d = da[da["Secteur"] == sec]
            values = {key: _indic_value(d, key, col) for key, _l, col, _f in INDICATORS}
            if values.get("inscriptions", 0) > 0:
                out.append({"source": a, "target": str(sec),
                            "value": values["inscriptions"], "values": values})
    return out


def compute(
    years: Optional[List[int]] = None,
    antennas: Optional[List[str]] = None,
    secteurs: Optional[List[str]] = None,
    sousSecteurs: Optional[List[str]] = None,
    macros: Optional[List[str]] = None,
    categories: Optional[List[str]] = None,
    year_mode: str = "civil",
) -> dict:
    """Full snapshot-shaped payload for the given filters, computed live.

    Dimension filters (secteurs/sousSecteurs/macros/categories) cascade: each
    narrows df_sel, so the returned breakdowns only contain matching children —
    which in turn narrows the child dropdown options on the client.

    year_mode : "civil" (année civile, défaut) ou "school" (année scolaire,
    sep N → août N+1). En mode scolaire on remplace la colonne « Année » par
    « Année scolaire » : tout le pipeline aval (filtres, KPI, évolution, YoY,
    ventilations) regroupe alors par année scolaire sans autre changement.
    """
    year_mode = "school" if year_mode == "school" else "civil"
    df = get_df()
    if year_mode == "school" and "Année scolaire" in df.columns:
        df = df.assign(**{"Année": df["Année scolaire"]})
    all_years = sorted(int(y) for y in df["Année"].unique())
    years = [y for y in (years or all_years) if y in all_years] or all_years
    antennas = [a for a in (antennas or bs.ANTENNA_ORDER) if a in bs.ANTENNA_ORDER] or list(bs.ANTENNA_ORDER)

    base = df[df["Année"].isin(years) & df["Sede"].isin(antennas)]

    sel = {"secteurs": secteurs or [], "sousSecteurs": sousSecteurs or [],
           "macros": macros or [], "categories": categories or []}

    # Cascade dropdown options: each level reflects the parent selection only.
    def _uniq(d, col):
        return sorted(d[col].dropna().astype(str).unique().tolist()) if col in d.columns else []
    b = base
    dim_options = {"secteurs": _uniq(b, "Secteur")}
    if sel["secteurs"]:
        b = b[b["Secteur"].isin(sel["secteurs"])]
    dim_options["sousSecteurs"] = _uniq(b, "Sous-secteur")
    if sel["sousSecteurs"]:
        b = b[b["Sous-secteur"].isin(sel["sousSecteurs"])]
    dim_options["macros"] = _uniq(b, "Macro-catégorie")
    if sel["macros"]:
        b = b[b["Macro-catégorie"].isin(sel["macros"])]
    dim_options["categories"] = _uniq(b, "Catégorie de cours")

    # Analytics dataframe: apply ALL active dimension filters.
    df_sel = base
    for key in ("secteurs", "sousSecteurs", "macros", "categories"):
        vals = sel[key]
        col = _DIM_COL[key]
        if vals and col in df_sel.columns:
            df_sel = df_sel[df_sel[col].isin(vals)]

    # Référentiel pour le delta N-1 : MÊMES filtres dimension + antennes, mais
    # TOUTES les années → la comparaison N-1 porte sur le même périmètre filtré
    # (sinon on compare une valeur filtrée à un total non filtré → delta faux).
    df_scope = df[df["Sede"].isin(antennas)]
    for key in ("secteurs", "sousSecteurs", "macros", "categories"):
        vals = sel[key]
        col = _DIM_COL[key]
        if vals and col in df_scope.columns:
            df_scope = df_scope[df_scope[col].isin(vals)]

    m = meta(year_mode)
    return {
        "meta": m,
        "filters": {
            "years": years, "year": years[-1] if years else 0, "antennas": antennas,
            "yearMode": year_mode,
            "secteurs": sel["secteurs"], "sousSecteurs": sel["sousSecteurs"],
            "macros": sel["macros"], "categories": sel["categories"], "sectors": [],
        },
        "dimOptions": dim_options,
        "indicators": INDICATOR_META,
        "kpis": _kpis(df_sel, years, antennas, df_scope, year_mode),
        "byAntenna": _by_antenna(df_sel, antennas),
        "sectors": _sectors(df_sel),
        "evolution": _evolution(df_sel, years, antennas),
        "breakdowns": _breakdowns(df_sel),
        "yoy": _yoy(df_sel, years),
        "profitability": _profitability(df_sel),
        "bySectorIndicator": _by_sector_indicators(df_sel),
        "byAntennaIndicator": _by_antenna_indicators(df_sel, antennas),
        "sectorAntenna": _sector_antenna_matrix(df_sel, antennas),
        "flows": _flows(df_sel, antennas),
    }
