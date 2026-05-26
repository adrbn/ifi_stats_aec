"""
OSCAR v3 — AEC export parser (new format).

This module reads the new "Cours > Tous les cours" AEC export (one row per
course) and converts it into a v2-compatible dataframe expected by the
OSCAR dashboard. It performs:

1. Reading from .xlsx (with 'AEC' sheet preferred)
2. Status filtering (Ouvert / Fermé à l'inscription / En attente by default)
3. Date floor filtering (default: 2022-09-01)
4. Sede derivation from "Lieu du cours" (IFM/IFF/IFN/IFP)
5. Année + Semestre derivation from "Date début"
   - Jan–Aug → S1
   - Sep–Dec → S2
6. Column renaming to match OSCAR v2's internal schema
7. Aggregation by (Année, Semestre, Sede, Catégorie de cours)

The resulting dataframe has the same column shape as `process_data()` output
in dashboard_aec_v2.py, so the existing dashboard UI works without changes
once `Macro-catégorie/Sous-secteur/Secteur` are added via CATEGORY_MAPPING.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from typing import Iterable, Optional

import pandas as pd


# ────────────────────────────────────────────────────────────────────────────
# Configuration
# ────────────────────────────────────────────────────────────────────────────

DEFAULT_ALLOWED_STATUSES: tuple[str, ...] = (
    "Ouvert",
    "Fermé à l'inscription",
    "En attente",
)

DEFAULT_DATE_FLOOR: datetime = datetime(2022, 9, 1)

# Map "Lieu du cours" / "Centre" full string → Sede code.
SEDE_FROM_LIEU_KEYWORDS: dict[str, str] = {
    "milano": "IFM",
    "firenze": "IFF",
    "florence": "IFF",
    "napoli": "IFN",
    "naples": "IFN",
    "palermo": "IFP",
    "palerme": "IFP",
}

# Column name mapping: new AEC export → OSCAR v2 internal schema.
# (trailing space on "Quantité d'inscriptions" is intentional — that's the real header)
COLUMN_RENAME_MAP: dict[str, str] = {
    "Quantité d'inscriptions ": "Nb. d'inscriptions",
    "Total des ventes": "Recettes",
    "Qté heures vendues": "Nombre total d'heures vendues (heures-étudiants)",
    "Qté synchrones heures vendues": "Heures synchrones vendues (heures-étudiants)",
    "Nombre total d'heures": "Nombre d'heures prévues",
    # If "Qté heures" is present instead (the AEC "heures enseignées" field),
    # we promote it to planned-hours.
    "Qté heures": "Nombre d'heures prévues",
    "Catégorie": "Catégorie de cours",
    "Tranche d'âge": "Tranche d'âge du cours",
    # Pass-throughs (same name): Nouveaux inscrits, Réinscrits, Niveau,
    # Période, Statut, Format, Localisation, Matière, Type, Date début, Date fin
}

# Metrics summed during groupby aggregation.
# Each key is an OSCAR v2 column name; value is the aggregation rule.
AGG_RULES: dict[str, str] = {
    "Nb. d'inscriptions": "sum",
    "Recettes": "sum",
    "Nombre d'heures prévues": "sum",
    "Nombre total d'heures vendues (heures-étudiants)": "sum",
    "Heures synchrones vendues (heures-étudiants)": "sum",
    "Heures de cours asynchrones": "sum",
    "Nouveaux inscrits": "sum",
    "Réinscrits": "sum",
}


@dataclass(frozen=True)
class ParseStats:
    """Diagnostic counters returned alongside the parsed dataframe."""
    rows_raw: int
    rows_after_status_filter: int
    rows_after_date_filter: int
    rows_after_dropna: int
    rows_aggregated: int
    statuses_kept: tuple[str, ...]
    date_floor: datetime
    unknown_sedes: tuple[str, ...]


# ────────────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────────────

def _derive_sede(lieu: object) -> Optional[str]:
    """Extract Sede code (IFM/IFF/IFN/IFP) from 'Lieu du cours' free text."""
    if not isinstance(lieu, str):
        return None
    low = lieu.lower()
    for keyword, code in SEDE_FROM_LIEU_KEYWORDS.items():
        if keyword in low:
            return code
    return None


def _semester_from_month(month: int) -> str:
    """Jan–Aug → S1, Sep–Dec → S2."""
    return "S1" if month <= 8 else "S2"


def _read_raw(file_content: bytes | BytesIO | object) -> pd.DataFrame:
    """Read the AEC sheet, falling back to sheet 0."""
    if isinstance(file_content, bytes):
        data: BytesIO | object = BytesIO(file_content)
    elif hasattr(file_content, "getvalue"):
        data = BytesIO(file_content.getvalue())
    elif hasattr(file_content, "read"):
        file_content.seek(0)
        data = BytesIO(file_content.read())
    else:
        data = file_content
    try:
        return pd.read_excel(data, sheet_name="AEC")
    except Exception:
        if hasattr(data, "seek"):
            data.seek(0)
        return pd.read_excel(data, sheet_name=0)


def _rename_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Apply the new-export → OSCAR v2 column renames, resolving collisions.

    Some AEC exports include both 'Qté heures' (granular hours definition) and
    'Nombre total d'heures' (legacy/aggregate). Both would map to 'Nombre
    d'heures prévues' and create a duplicate column. We prefer 'Qté heures'
    when present (richer, used by the recent AEC schema).
    """
    df = df.copy()
    # Disambiguate planned-hours column: prefer 'Qté heures' over 'Nombre total d'heures'
    if "Qté heures" in df.columns and "Nombre total d'heures" in df.columns:
        df = df.drop(columns=["Nombre total d'heures"])

    rename_dict = {old: new for old, new in COLUMN_RENAME_MAP.items() if old in df.columns}
    return df.rename(columns=rename_dict)


# ────────────────────────────────────────────────────────────────────────────
# Public API
# ────────────────────────────────────────────────────────────────────────────

def parse_aec_export(
    file_content: bytes | BytesIO | object,
    *,
    allowed_statuses: Iterable[str] = DEFAULT_ALLOWED_STATUSES,
    date_floor: datetime = DEFAULT_DATE_FLOOR,
    aggregate: bool = True,
) -> tuple[pd.DataFrame, ParseStats]:
    """Parse a new-format AEC export.

    Args:
        file_content: bytes, BytesIO, or file-like object pointing to a .xlsx
        allowed_statuses: rows whose 'Statut' is NOT in this set are dropped
        date_floor: rows whose 'Date début' is earlier are dropped
        aggregate: if True (default), return a v2-shaped aggregated dataframe.
            If False, return per-course rows with renamed columns + derived
            Sede/Année/Semestre/Période (richer; useful for future v3 features
            like daily inscriptions).

    Returns:
        (df, stats) — df is OSCAR v2-compatible if aggregate=True.
    """
    raw = _read_raw(file_content)
    rows_raw = len(raw)

    df = _rename_columns(raw)

    # Status filter
    allowed = set(allowed_statuses)
    if "Statut" in df.columns:
        df = df[df["Statut"].astype(str).str.strip().isin(allowed)]
    rows_after_status = len(df)

    # Date floor (skip rows with no Date début)
    if "Date début" in df.columns:
        df["Date début"] = pd.to_datetime(df["Date début"], errors="coerce")
        df = df[df["Date début"].notna() & (df["Date début"] >= pd.Timestamp(date_floor))]
    rows_after_date = len(df)

    # Derive Sede
    lieu_col = "Lieu du cours" if "Lieu du cours" in df.columns else (
        "Centre" if "Centre" in df.columns else None
    )
    if lieu_col is not None:
        df = df.copy()
        df["Sede"] = df[lieu_col].apply(_derive_sede)
    else:
        df["Sede"] = None

    unknown_sedes_series = df.loc[df["Sede"].isna() & df.get(lieu_col).notna(), lieu_col] if lieu_col else pd.Series(dtype=str)
    unknown_sedes = tuple(sorted(set(unknown_sedes_series.astype(str).tolist()))) if not unknown_sedes_series.empty else ()

    # Drop rows we couldn't tag with a Sede (they'd skew totals silently)
    df = df[df["Sede"].notna()].copy()
    rows_after_dropna = len(df)

    # Derive Année + Semestre + Période
    df["Année"] = df["Date début"].dt.year.astype(int)
    df["Mois début"] = df["Date début"].dt.month.astype(int)
    df["Semestre"] = df["Mois début"].apply(_semester_from_month)
    df["Période"] = df["Année"].astype(str) + " " + df["Semestre"]

    # Ensure the v2 categorical columns exist
    for c in ("Catégorie de cours", "Niveau", "Tranche d'âge du cours",
              "Matière", "Format", "Localisation", "Type"):
        if c not in df.columns:
            df[c] = None

    # Ensure numeric metric columns exist
    for c, _ in AGG_RULES.items():
        if c not in df.columns:
            df[c] = 0

    # Coerce metrics to numeric
    for c in AGG_RULES:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    if not aggregate:
        # Per-course view (richer)
        return df.reset_index(drop=True), ParseStats(
            rows_raw=rows_raw,
            rows_after_status_filter=rows_after_status,
            rows_after_date_filter=rows_after_date,
            rows_after_dropna=rows_after_dropna,
            rows_aggregated=len(df),
            statuses_kept=tuple(allowed),
            date_floor=date_floor,
            unknown_sedes=unknown_sedes,
        )

    # Aggregate by (Année, Semestre, Sede, Catégorie de cours)
    group_cols = ["Année", "Semestre", "Période", "Sede", "Catégorie de cours"]
    agg_with_count = dict(AGG_RULES)

    # Count of courses per group
    grouped = (
        df.groupby(group_cols, dropna=False)
          .agg({**agg_with_count, "Date début": "size"})
          .rename(columns={"Date début": "Nb. de Cours"})
          .reset_index()
    )

    return grouped, ParseStats(
        rows_raw=rows_raw,
        rows_after_status_filter=rows_after_status,
        rows_after_date_filter=rows_after_date,
        rows_after_dropna=rows_after_dropna,
        rows_aggregated=len(grouped),
        statuses_kept=tuple(allowed),
        date_floor=date_floor,
        unknown_sedes=unknown_sedes,
    )


__all__ = [
    "parse_aec_export",
    "ParseStats",
    "DEFAULT_ALLOWED_STATUSES",
    "DEFAULT_DATE_FLOOR",
    "COLUMN_RENAME_MAP",
    "AGG_RULES",
]
