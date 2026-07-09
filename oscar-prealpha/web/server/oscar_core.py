"""oscar_core — pure pandas functions extracted from dashboard_aec_v2.py.

This module contains the data-processing core of the OSCAR dashboard with NO
Streamlit dependency. Every function is pure (DataFrame in, DataFrame out) and
the module imports cleanly with `python3 -c "import oscar_core"`.

Extracted functions:
  detect_from_filename, load_excel, load_csv_file, load_file_auto,
  map_category_to_levels, map_category_to_sector, process_data,
  aggregate_by_sector, create_prova_stats_format, create_ifi_totals,
  calculate_profitability, calculate_yoy_comparison, calculate_yoy_by_sede,
  detect_export_type, parse_french_number, extract_sede_from_centre,
  parse_periode_field, assign_semester_from_month, get_age_group,
  format_number, load_csv_mappings

st.session_state-based tracking (unknown categories) has been replaced with a
module-level dict so the functions stay pure and side-effect-light.
"""
from __future__ import annotations

import os
import re
from io import BytesIO

import pandas as pd

# ---------------------------------------------------------------------------
# Constants (copied verbatim from dashboard_aec_v2.py)
# ---------------------------------------------------------------------------

CATEGORY_MAPPING = {
    # PLATEFORMES
    "ABC DELF AUTONOMIE": ("PLATEFORME AbcDelf - Autonomie", "PLATEFORME - Autonomie", "PLATEFORMES"),
    "ABC DELF SCUOLE": ("PLATEFORME AbcDelf - Ecoles", "PLATEFORME - Autonomie", "PLATEFORMES"),
    "ABCDELFB2-4": ("PLATEFORME AbcDelf - Tuteur", "PLATEFORME - Tuteur", "PLATEFORMES"),
    "Cours en ligne Apolearn": ("PLATEFORME - Autres", "PLATEFORME - Autonomie", "PLATEFORMES"),
    "MCEL-12": ("PLATEFORME Madrid -  Tuteur", "PLATEFORME - Tuteur", "PLATEFORMES"),
    "MCEL-12-DUO": ("PLATEFORME Madrid -  Tuteur", "PLATEFORME - Tuteur", "PLATEFORMES"),
    "MCEL-8": ("PLATEFORME Madrid -  Tuteur", "PLATEFORME - Tuteur", "PLATEFORMES"),
    "MCEL-AUTONOMIE": ("PLATEFORME Madrid - Autonomie", "PLATEFORME - Autonomie", "PLATEFORMES"),
    "PLAT-ABCDELFB1+3": ("PLATEFORME AbcDelf - Tuteur", "PLATEFORME - Tuteur", "PLATEFORMES"),
    "PLAT-ABCDELFB2+4": ("PLATEFORME AbcDelf - Tuteur", "PLATEFORME - Tuteur", "PLATEFORMES"),
    "PLAT-MCEL-AUTONOMIE": ("PLATEFORME Madrid - Autonomie", "PLATEFORME - Autonomie", "PLATEFORMES"),
    "PLAT-MCEL-DUO": ("PLATEFORME AbcDelf - Tuteur", "PLATEFORME - Tuteur", "PLATEFORMES"),
    "PLAT-MCEL-INDIV": ("PLATEFORME Madrid -  Tuteur", "PLATEFORME - Tuteur", "PLATEFORMES"),
    "PLAT-RIPASSO-GRAM": ("PLATEFORME - Autres", "PLATEFORME - Autonomie", "PLATEFORMES"),

    # PROGRAMMÉS - COLLECTIFS ADOS/ENFANTS
    "ADOS  16H": ("COLL- ADOS", "COLLECTIFS ADOS/ENFANTS", "PROGRAMMÉS"),
    "ADOS-CAMP": ("COLL- ADOS", "COLLECTIFS ADOS/ENFANTS", "PROGRAMMÉS"),
    "ADOS-EXT": ("COLL- ADOS", "COLLECTIFS ADOS/ENFANTS", "PROGRAMMÉS"),
    "ADOS-EXT-IFM": ("COLL- ADOS", "COLLECTIFS ADOS/ENFANTS", "PROGRAMMÉS"),
    "ADOS-EXT-IFN": ("COLL- ADOS", "COLLECTIFS ADOS/ENFANTS", "PROGRAMMÉS"),
    "ADOS-EXT-IFP": ("COLL- ADOS", "COLLECTIFS ADOS/ENFANTS", "PROGRAMMÉS"),
    "ADOS-INT": ("COLL- ADOS", "COLLECTIFS ADOS/ENFANTS", "PROGRAMMÉS"),
    "ADOS/ENFANTS ATELIERS": ("ATELIERS ADOS/ ENFANTS", "COLLECTIFS ADOS/ENFANTS", "PROGRAMMÉS"),
    "ADOS/ENFANTS CAMPUS 15H": ("CAMPUS JEUNES", "COLLECTIFS ADOS/ENFANTS", "PROGRAMMÉS"),
    "ADOS/ENFANTS CAMPUS 20H": ("CAMPUS JEUNES", "COLLECTIFS ADOS/ENFANTS", "PROGRAMMÉS"),
    "ADOS/ENFANTS CAMPUS 30H": ("CAMPUS JEUNES", "COLLECTIFS ADOS/ENFANTS", "PROGRAMMÉS"),
    "ENFANTS": ("COURS COLL ENFANTS", "COLLECTIFS ADOS/ENFANTS", "PROGRAMMÉS"),
    "ENFANTS 18H": ("COURS COLL ENFANTS", "COLLECTIFS ADOS/ENFANTS", "PROGRAMMÉS"),
    "ENFANTS 25H": ("COURS COLL ENFANTS", "COLLECTIFS ADOS/ENFANTS", "PROGRAMMÉS"),

    # PROGRAMMÉS - Ateliers thématiques
    "Ateliers thématiques": ("ATELIERS ADULTES", "Ateliers thématiques", "PROGRAMMÉS"),

    # PROGRAMMÉS - COLL ADULTES - SPE
    "CONVERSATION": ("COURS COLL CONV", "COLL ADULTES - SPE", "PROGRAMMÉS"),
    "DALF EXPRESS (10+10)": ("PREP EXAMENS", "COLL ADULTES - SPE", "PROGRAMMÉS"),
    "DALF EXT": ("PREP EXAMENS", "COLL ADULTES - SPE", "PROGRAMMÉS"),
    "DELF B2 EXPRESS (6+10)": ("PREP EXAMENS", "COLL ADULTES - SPE", "PROGRAMMÉS"),
    "DELF B2 EXT": ("PREP EXAMENS", "COLL ADULTES - SPE", "PROGRAMMÉS"),
    "SPE-CONV-15H": ("COLL- CONV", "COLL ADULTES - SPE", "PROGRAMMÉS"),
    "SPE-CONV-15H ": ("COLL- CONV", "COLL ADULTES - SPE", "PROGRAMMÉS"),
    "SPE-CONV-21H (D)": ("COLL- CONV", "COLL ADULTES - SPE", "PROGRAMMÉS"),
    "SPE-CONV-21H (P)": ("COLL- CONV", "COLL ADULTES - SPE", "PROGRAMMÉS"),
    "SPE-CONV-28H": ("COLL- CONV", "COLL ADULTES - SPE", "PROGRAMMÉS"),
    "SPE-CONV-30H": ("COLL- CONV", "COLL ADULTES - SPE", "PROGRAMMÉS"),
    "SPE-CONV-MINIGP": ("COLL- CONV", "COLL ADULTES - SPE", "PROGRAMMÉS"),
    "SPE-CONV-SENIOR-28H": ("COLL- CONV", "COLL ADULTES - SPE", "PROGRAMMÉS"),
    "SPE-DALF EXPRESS (10+10)": ("PREP EXAMENS", "COLL ADULTES - SPE", "PROGRAMMÉS"),
    "SPE-DALF EXT": ("PREP EXAMENS", "COLL ADULTES - SPE", "PROGRAMMÉS"),
    "SPE-DELF B2 EXPRESS (6+10)": ("PREP EXAMENS", "COLL ADULTES - SPE", "PROGRAMMÉS"),
    "SPE-DELF B2 EXT": ("PREP EXAMENS", "COLL ADULTES - SPE", "PROGRAMMÉS"),
    "SPE-LECT-6H": ("COLL- THÉMATIQUES", "COLL ADULTES - SPE", "PROGRAMMÉS"),
    "SPE-LECT-6H ": ("COLL- THÉMATIQUES", "COLL ADULTES - SPE", "PROGRAMMÉS"),
    "SPE-THÉÂTRE": ("COLL- THÉMATIQUES", "COLL ADULTES - SPE", "PROGRAMMÉS"),
    "SPE/PRO": ("COLL - SPECIFIQUE", "COLL ADULTES - SPE", "PROGRAMMÉS"),
    "SPE/TRAD": ("COLL - SPECIFIQUE", "COLL ADULTES - SPE", "PROGRAMMÉS"),
    "THÉMATIQUES": ("COLL- THÉMATIQUES", "COLL ADULTES - SPE", "PROGRAMMÉS"),
    "UEL 20H": ("COLL- CONV", "COLL ADULTES - SPE", "PROGRAMMÉS"),

    # PROGRAMMÉS - COLL ADULTES - GRL
    "GRL-15H (P)": ("COLL- GRL P ", "COLL ADULTES - GRL", "PROGRAMMÉS"),
    "GRL-20H": ("COLL- GRL P ", "COLL ADULTES - GRL", "PROGRAMMÉS"),
    "GRL-20H (D)": ("COLL- GRL D", "COLL ADULTES - GRL", "PROGRAMMÉS"),
    "GRL-20H (P)": ("COLL- GRL P ", "COLL ADULTES - GRL", "PROGRAMMÉS"),
    "GRL-30H (BASE)": ("COLL- GRL P ", "COLL ADULTES - GRL", "PROGRAMMÉS"),
    "GRL-30H (BASE) - V": ("COLL- GRL D", "COLL ADULTES - GRL", "PROGRAMMÉS"),
    "GRL-30H (D)": ("COLL- GRL D", "COLL ADULTES - GRL", "PROGRAMMÉS"),
    "GRL-30H (MAJ)": ("COLL- GRL P ", "COLL ADULTES - GRL", "PROGRAMMÉS"),
    "GRL-30H (MAJ) - V": ("COLL- GRL D", "COLL ADULTES - GRL", "PROGRAMMÉS"),
    "GRL-30H (P)": ("COLL- GRL P ", "COLL ADULTES - GRL", "PROGRAMMÉS"),
    "GRL-45H (BASE)": ("COLL- GRL P ", "COLL ADULTES - GRL", "PROGRAMMÉS"),
    "GRL-45h (D)": ("COLL- GRL D", "COLL ADULTES - GRL", "PROGRAMMÉS"),
    "GRL-45H (D)": ("COLL- GRL D", "COLL ADULTES - GRL", "PROGRAMMÉS"),
    "GRL-45H (D) ": ("COLL- GRL D", "COLL ADULTES - GRL", "PROGRAMMÉS"),
    "GRL-45H (MAJ)": ("COLL- GRL P ", "COLL ADULTES - GRL", "PROGRAMMÉS"),
    "GRL-45h (P)": ("COLL- GRL P ", "COLL ADULTES - GRL", "PROGRAMMÉS"),
    "GRL-45H (P)": ("COLL- GRL P ", "COLL ADULTES - GRL", "PROGRAMMÉS"),
    "GRL-60H (45+15) (BASE)": ("COLL- GRL D", "COLL ADULTES - GRL", "PROGRAMMÉS"),
    "GRL-60H (45+15) (MAJ)": ("COLL- GRL D", "COLL ADULTES - GRL", "PROGRAMMÉS"),
    "GRL-60H (50+10)": ("COLL- GRL D", "COLL ADULTES - GRL", "PROGRAMMÉS"),
    "GRL-60H (BASE)": ("COLL- GRL P ", "COLL ADULTES - GRL", "PROGRAMMÉS"),
    "GRL-60H (BASE) - V": ("COLL- GRL D", "COLL ADULTES - GRL", "PROGRAMMÉS"),
    "GRL-60H (D)": ("COLL- GRL D", "COLL ADULTES - GRL", "PROGRAMMÉS"),
    "GRL-60H (D) ": ("COLL- GRL D", "COLL ADULTES - GRL", "PROGRAMMÉS"),
    "GRL-60H (MAJ)": ("COLL- GRL P ", "COLL ADULTES - GRL", "PROGRAMMÉS"),
    "GRL-60H (MAJ) - V": ("COLL- GRL D", "COLL ADULTES - GRL", "PROGRAMMÉS"),
    "GRL-60H (P)": ("COLL- GRL P ", "COLL ADULTES - GRL", "PROGRAMMÉS"),
    "GRL-90H": ("COLL- GRL P ", "COLL ADULTES - GRL", "PROGRAMMÉS"),
    "GRL-90H (D)": ("COLL- GRL D", "COLL ADULTES - GRL", "PROGRAMMÉS"),
    "GRL-90H (P)": ("COLL- GRL P ", "COLL ADULTES - GRL", "PROGRAMMÉS"),
    "GRL-UEL 20H": ("COLL- GRL P ", "COLL ADULTES - GRL", "PROGRAMMÉS"),
    "INT-16h (P)": ("INTENSIFS P", "COLL ADULTES - GRL", "PROGRAMMÉS"),
    "INT-16H (P)": ("INTENSIFS P", "COLL ADULTES - GRL", "PROGRAMMÉS"),
    "INT-30H (BASE)": ("INTENSIFS P", "COLL ADULTES - GRL", "PROGRAMMÉS"),
    "INT-30H (D)": ("INTENSIFS D", "COLL ADULTES - GRL", "PROGRAMMÉS"),
    "INT-30H (MAJ)": ("INTENSIFS P", "COLL ADULTES - GRL", "PROGRAMMÉS"),
    "INT-30H (P)": ("INTENSIFS P", "COLL ADULTES - GRL", "PROGRAMMÉS"),
    "INT-30H (VIRT)": ("INTENSIFS D", "COLL ADULTES - GRL", "PROGRAMMÉS"),

    # ECOLES
    "ECOLES - Ateliers": ("ECOLES - Ateliers", "ECOLES - Ateliers", "ECOLES"),
    "ECOLES - Classes Découverte": ("ECOLES - Classes Découverte", "ECOLES - Classes Découverte", "ECOLES"),
    "ECOLES - GRL": ("ECOLES - COURS", "ECOLES - COURS", "ECOLES"),
    "ECOLES - immersion (GRL)": ("ECOLES - COURS", "ECOLES - COURS", "ECOLES"),
    "ECOLES - Matinée": ("ECOLES - Matinée", "ECOLES - Matinée", "ECOLES"),
    "ECOLES - PCTO Au Travail": ("ECOLES - PCTO", "ECOLES - PCTO", "ECOLES"),
    "ECOLES - PCTO Au Travail ": ("ECOLES - PCTO", "ECOLES - PCTO", "ECOLES"),
    "ECOLES - PCTO Ciné": ("ECOLES - PCTO", "ECOLES - PCTO", "ECOLES"),
    "ECOLES - PCTO Prim'Aria": ("ECOLES - PCTO", "ECOLES - PCTO", "ECOLES"),
    "ECOLES - PON": ("ECOLES - COURS", "ECOLES - COURS", "ECOLES"),
    "ECOLES - SPE": ("ECOLES - COURS", "ECOLES - COURS", "ECOLES"),

    # SUR MESURE
    "PART-DUO": ("PART-SEMI COLL", "SUR MESURE - GRL", "SUR MESURE"),
    "PART-FR GRL": ("PART-FR GRL", "SUR MESURE - GRL", "SUR MESURE"),
    "PART-FR GRL>=20": ("PART-FR GRL", "SUR MESURE - GRL", "SUR MESURE"),
    "PART-FR SPE": ("PART-FR SPE", "SUR MESURE - SPE", "SUR MESURE"),
    "PART-FR SPE<20": ("PART-FR SPE", "SUR MESURE - SPE", "SUR MESURE"),
    "PART-FR SPE>=20": ("PART-FR SPE", "SUR MESURE - SPE", "SUR MESURE"),
    "PART-GP": ("PART-SEMI COLL", "SUR MESURE - GRL", "SUR MESURE"),
    "PART-ITA": ("PART-ITA", "SUR MESURE - SPE", "SUR MESURE"),
    "PART-TRIO": ("PART-SEMI COLL", "SUR MESURE - GRL", "SUR MESURE"),

    # SOCIÉTÉS
    "SOC-GEN": ("ENTREPRISES - GRL", "ENTREPRISES - GRL", "SOCIÉTÉS"),
    "SOC-SPE": ("ENTREPRISES - SPE", "ENTREPRISES - SPE", "SOCIÉTÉS"),
}

# Configurable CSV path - can be overridden by environment variable for server deployment.
# Default points to the repo's data/ directory (two levels up from api/).
CSV_MAPPING_PATH = os.environ.get(
    "AEC_CATEGORY_MAPPING_PATH",
    os.path.join(os.path.dirname(__file__), "..", "..", "data", "category_mapping.csv"),
)

# Order for each level
SECTOR_ORDER = ["PROGRAMMÉS", "PLATEFORMES", "ECOLES", "SUR MESURE", "SOCIÉTÉS", "AUTRE"]
SOUS_SECTEUR_ORDER = [
    "COLL ADULTES - GRL", "COLL ADULTES - SPE", "COLLECTIFS ADOS/ENFANTS", "Ateliers thématiques",
    "PLATEFORME - Autonomie", "PLATEFORME - Tuteur",
    "ECOLES - COURS", "ECOLES - Ateliers", "ECOLES - Classes Découverte", "ECOLES - Matinée", "ECOLES - PCTO",
    "SUR MESURE - GRL", "SUR MESURE - SPE",
    "ENTREPRISES - GRL", "ENTREPRISES - SPE", "AUTRE",
]

# Antenna display order: Milan, Florence, Naples, Palermo
ANTENNA_ORDER = ["IFM", "IFF", "IFN", "IFP"]

SEDE_COLORS = {
    "IFM": "#FF8C00", "IFF": "#8B5CF6", "IFN": "#22C55E",
    "IFP": "#EF4444", "IFI": "#3B82F6",
}

SEDE_COORDS = {
    "IFM": {"lat": 45.4642, "lon": 9.1900, "city": "Milano"},
    "IFF": {"lat": 43.7696, "lon": 11.2558, "city": "Firenze"},
    "IFN": {"lat": 40.8518, "lon": 14.2681, "city": "Napoli"},
    "IFP": {"lat": 38.1157, "lon": 13.3615, "city": "Palermo"},
}

AGE_GROUP_MAPPING = {
    "Adultes (25 ans+)": "Adultes",
    "Adultes (18-24 ans)": "Adultes",
    "Adultes": "Adultes",
    "ADULTES": "Adultes",
    "Adolescents (13-17 ans)": "Ados",
    "ADOLESCENTS": "Ados",
    "Ados": "Ados",
    "Enfants (6-12 ans)": "Enfants",
    "Enfants (3-5 ans)": "Enfants",
    "ENFANTS": "Enfants",
    "Enfants": "Enfants",
}

PERIOD_LABELS = {"sem1": "janv-juillet", "sem2": "sept-dec", "annuel": "année complète"}

CENTRE_TO_SEDE = {
    "Milano": "IFM", "Firenze": "IFF", "Napoli": "IFN", "Palermo": "IFP",
}

MONTH_FR_TO_NUM = {
    "JANVIER": 1, "FEVRIER": 2, "FÉVRIER": 2, "MARS": 3, "AVRIL": 4,
    "MAI": 5, "JUIN": 6, "JUILLET": 7, "AOUT": 8, "AOÛT": 8,
    "SEPTEMBRE": 9, "OCTOBRE": 10, "NOVEMBRE": 11, "DECEMBRE": 12, "DÉCEMBRE": 12,
}

# Module-level tracking of unmapped categories (replaces st.session_state usage).
UNKNOWN_CATEGORIES: dict = {}


# ---------------------------------------------------------------------------
# CSV mapping loader
# ---------------------------------------------------------------------------

def get_csv_mapping_path():
    """Get the path to the category mapping CSV file."""
    return CSV_MAPPING_PATH


def load_csv_mappings(csv_path=None):
    """Load additional category mappings from CSV file (mutates CATEGORY_MAPPING)."""
    csv_path = csv_path or get_csv_mapping_path()
    if os.path.exists(csv_path):
        try:
            df = pd.read_csv(csv_path)
            for _, row in df.iterrows():
                if all(col in df.columns for col in ["Catégorie", "Macro-catégorie", "Sous-secteur", "Secteur"]):
                    cat = row["Catégorie"]
                    CATEGORY_MAPPING[cat] = (row["Macro-catégorie"], row["Sous-secteur"], row["Secteur"])
        except Exception as e:  # noqa: BLE001
            print(f"Warning: Could not load category mapping CSV: {e}")


# Try to load CSV mappings at import (overrides any duplicates from the dict).
try:
    load_csv_mappings()
except Exception:  # noqa: BLE001
    pass


# Snapshot du mapping « de base » (dict codé en dur + surcharge CSV) une fois le
# CSV chargé. Sert de socle stable pour ré-appliquer proprement les overrides
# runtime (édités depuis le site) : on repart toujours de cette base, puis on
# empile les overrides — de sorte qu'une suppression d'override revienne bien au
# mapping par défaut.
_BASE_CATEGORY_MAPPING: dict = dict(CATEGORY_MAPPING)


def refresh_base_mapping() -> None:
    """Re-capture le socle du mapping à partir de l'état COURANT de
    CATEGORY_MAPPING. À appeler après tout chargement de CSV supplémentaire
    (ex. build_snapshot charge server/data/category_mapping.csv) pour que ces
    correspondances fassent partie du socle — sinon set_runtime_overrides les
    effacerait en réinitialisant au socle d'import."""
    global _BASE_CATEGORY_MAPPING
    _BASE_CATEGORY_MAPPING = dict(CATEGORY_MAPPING)


def set_runtime_overrides(overrides: dict) -> None:
    """Réinitialise CATEGORY_MAPPING au socle (dict + CSV) puis applique les
    overrides runtime édités depuis le site.

    overrides : {catégorie: (macro, sous_secteur, secteur)}."""
    CATEGORY_MAPPING.clear()
    CATEGORY_MAPPING.update(_BASE_CATEGORY_MAPPING)
    for cat, val in (overrides or {}).items():
        key = str(cat).strip()
        if not key:
            continue
        if isinstance(val, dict):
            CATEGORY_MAPPING[key] = (
                val.get("macro", ""), val.get("sousSecteur", ""), val.get("secteur", ""),
            )
        elif isinstance(val, (list, tuple)) and len(val) == 3:
            CATEGORY_MAPPING[key] = tuple(val)


# ---------------------------------------------------------------------------
# Category mapping
# ---------------------------------------------------------------------------

def map_category_to_levels(category):
    """Map category to all 3 levels: (macro_category, sous_secteur, secteur)."""
    if pd.isna(category) or str(category).strip() == "":
        UNKNOWN_CATEGORIES["[VIDE/NULL]"] = "Catégorie vide ou nulle dans les données AEC"
        return ("NON RATTACHÉ", "NON RATTACHÉ", "NON RATTACHÉ")

    cat_str = str(category).strip()

    if cat_str in CATEGORY_MAPPING:
        return CATEGORY_MAPPING[cat_str]
    if cat_str + " " in CATEGORY_MAPPING:
        return CATEGORY_MAPPING[cat_str + " "]
    if cat_str.rstrip() in CATEGORY_MAPPING:
        return CATEGORY_MAPPING[cat_str.rstrip()]
    for key, value in CATEGORY_MAPPING.items():
        if key.strip().upper() == cat_str.strip().upper():
            return value

    UNKNOWN_CATEGORIES[cat_str] = f"Catégorie '{cat_str}' non trouvée dans le mapping"
    return ("NON RATTACHÉ", "NON RATTACHÉ", "NON RATTACHÉ")


def map_category_to_sector(category):
    """Legacy function - returns just the sector (3rd element)."""
    return map_category_to_levels(category)[2]


def get_unknown_categories():
    """Return dict of unknown categories detected during import with details."""
    return dict(UNKNOWN_CATEGORIES)


# ---------------------------------------------------------------------------
# File loaders
# ---------------------------------------------------------------------------

def detect_from_filename(filename):
    """Detect (sede, semester, year) from a filename."""
    filename_upper = filename.upper()
    sede = None
    for s in ["IFM", "IFF", "IFN", "IFP"]:
        if s in filename_upper:
            sede = s
            break
    semester = None
    filename_lower = filename.lower()
    if "semestre 1" in filename_lower or "sem1" in filename_lower or "sem 1" in filename_lower:
        semester = "sem1"
    elif "semestre 2" in filename_lower or "sem2" in filename_lower or "sem 2" in filename_lower:
        semester = "sem2"
    elif "janv" in filename_lower or "jan-" in filename_lower or "janvier" in filename_lower:
        semester = "sem1"
    elif "sept" in filename_lower or "dec" in filename_lower:
        semester = "sem2"
    year = None
    match = re.search(r"20\d{2}", filename)
    if match:
        year = int(match.group())
    return sede, semester, year


def load_excel(file_content, filename=""):
    """Load Excel file - tries 'AEC' sheet first, then first sheet."""
    try:
        if hasattr(file_content, "getvalue"):
            data = BytesIO(file_content.getvalue())
        elif hasattr(file_content, "read"):
            file_content.seek(0)
            data = BytesIO(file_content.read())
        else:
            data = file_content
        df = pd.read_excel(data, sheet_name="AEC")
        return df, None
    except Exception:  # noqa: BLE001
        try:
            if hasattr(file_content, "getvalue"):
                data = BytesIO(file_content.getvalue())
            elif hasattr(file_content, "read"):
                file_content.seek(0)
                data = BytesIO(file_content.read())
            else:
                data = file_content
            df = pd.read_excel(data, sheet_name=0)
            return df, None
        except Exception as e:  # noqa: BLE001
            return None, str(e)


def load_csv_file(file_content, filename=""):
    """Load CSV file with encoding auto-detection."""
    try:
        if hasattr(file_content, "getvalue"):
            data = BytesIO(file_content.getvalue())
        elif hasattr(file_content, "read"):
            file_content.seek(0)
            data = BytesIO(file_content.read())
        else:
            data = file_content
        df = pd.read_csv(data, encoding="utf-8", low_memory=False)
        return df, None
    except Exception:  # noqa: BLE001
        try:
            if hasattr(file_content, "getvalue"):
                data = BytesIO(file_content.getvalue())
            elif hasattr(file_content, "read"):
                file_content.seek(0)
                data = BytesIO(file_content.read())
            else:
                data = file_content
            df = pd.read_csv(data, encoding="latin-1", low_memory=False)
            return df, None
        except Exception as e:  # noqa: BLE001
            return None, str(e)


def load_file_auto(file_content, filename):
    """Load Excel or CSV file based on extension."""
    if filename.lower().endswith(".csv"):
        return load_csv_file(file_content, filename)
    df, error = load_excel(file_content, filename)
    if error:
        try:
            if hasattr(file_content, "getvalue"):
                data = BytesIO(file_content.getvalue())
            elif hasattr(file_content, "read"):
                file_content.seek(0)
                data = BytesIO(file_content.read())
            else:
                data = file_content
            df = pd.read_excel(data, sheet_name=0)
            return df, None
        except Exception as e2:  # noqa: BLE001
            return None, f"{error} / {str(e2)}"
    return df, error


# ---------------------------------------------------------------------------
# Core processing
# ---------------------------------------------------------------------------

def get_age_group(tranche):
    """Map AEC age categories to simplified groups."""
    if pd.isna(tranche):
        return "Adultes"
    tranche_str = str(tranche).strip()
    return AGE_GROUP_MAPPING.get(tranche_str, "Adultes")


def process_data(df, year, semester, sede):
    """Tag a raw AEC dataframe with Année/Semestre/Période/Sede + sector levels."""
    df = df.copy()
    if "Tranche d'âge du cours" in df.columns:
        df = df[df["Tranche d'âge du cours"].notna()]
        df = df[df["Tranche d'âge du cours"] != "TOTAL"]
        df["Groupe_Age"] = df["Tranche d'âge du cours"].apply(get_age_group)
    else:
        df["Groupe_Age"] = "Adultes"
    effective_semester = semester if semester else "annuel"
    period_label = f"{year} {PERIOD_LABELS.get(effective_semester, effective_semester)}"
    df.insert(0, "Année", year)
    df.insert(1, "Semestre", effective_semester)
    df.insert(2, "Période", period_label)
    df.insert(3, "Sede", sede)
    if "Catégorie de cours" in df.columns:
        levels = df["Catégorie de cours"].apply(map_category_to_levels)
        df["Macro-catégorie"] = levels.apply(lambda x: x[0])
        df["Sous-secteur"] = levels.apply(lambda x: x[1])
        df["Secteur"] = levels.apply(lambda x: x[2])
    else:
        df["Macro-catégorie"] = "NON RATTACHÉ"
        df["Sous-secteur"] = "NON RATTACHÉ"
        df["Secteur"] = "NON RATTACHÉ"
    return df


def aggregate_by_sector(df, group_cols=None, add_total_row=False):
    """Aggregate metrics by the given group columns (default Année/Période/Sede/Secteur)."""
    if group_cols is None:
        group_cols = ["Année", "Période", "Sede", "Secteur"]
    agg_dict = {}
    col_mapping = {
        "Nb. de Cours": "sum", "Nb. d'inscriptions": "sum", "Nouveaux inscrits": "sum",
        "Réinscrits": "sum", "Qté heures": "sum",
        "Nombre total d'heures vendues (heures-étudiants)": "sum",
        "Heures synchrones vendues (heures-étudiants)": "sum", "Recettes": "sum", "Dépenses": "sum",
    }
    for col, func in col_mapping.items():
        if col in df.columns:
            agg_dict[col] = func
    if not agg_dict:
        return pd.DataFrame()
    grouped = df.groupby(group_cols, as_index=False).agg(agg_dict)
    if "Nb. d'inscriptions" in grouped.columns and "Nb. de Cours" in grouped.columns:
        grouped["Taux de remplissage"] = (
            grouped["Nb. d'inscriptions"] / grouped["Nb. de Cours"].replace(0, pd.NA)
        ).round(2)

    if add_total_row and not grouped.empty:
        total_row = {}
        for col in grouped.columns:
            if col in ["Année", "Période", "Sede"]:
                total_row[col] = ""
            elif col == "Secteur":
                total_row[col] = "TOTAL"
            elif col == "Taux de remplissage":
                total_inscr = grouped["Nb. d'inscriptions"].sum() if "Nb. d'inscriptions" in grouped.columns else 0
                total_cours = grouped["Nb. de Cours"].sum() if "Nb. de Cours" in grouped.columns else 0
                total_row[col] = round(total_inscr / total_cours, 2) if total_cours > 0 else 0
            else:
                total_row[col] = grouped[col].sum()
        grouped = pd.concat([grouped, pd.DataFrame([total_row])], ignore_index=True)

    return grouped


def create_prova_stats_format(df, aggregate_year=False, add_total_row=False):
    """Create the 'prova stats' sector table format used by the dashboard."""
    if aggregate_year:
        agg = aggregate_by_sector(df, group_cols=["Année", "Sede", "Secteur"])
        if not agg.empty:
            agg["Période"] = agg["Année"].astype(str)
    else:
        agg = aggregate_by_sector(df)
    if agg.empty:
        return pd.DataFrame()
    rename_map = {
        "Nombre total d'heures vendues (heures-étudiants)": "Nombre d'heures-élèves",
        "Heures synchrones vendues (heures-étudiants)": "Heures synchrones (h-élèves)",
    }
    agg = agg.rename(columns={k: v for k, v in rename_map.items() if k in agg.columns})

    inscr_col = "Nb. d'inscriptions"
    if inscr_col in agg.columns:
        if "Nouveaux inscrits" in agg.columns:
            agg["% nouveaux"] = (agg["Nouveaux inscrits"] / agg[inscr_col] * 100).round(1)
            agg["% nouveaux"] = agg["% nouveaux"].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "")
        if "Réinscrits" in agg.columns:
            agg["% réinscrits"] = (agg["Réinscrits"] / agg[inscr_col] * 100).round(1)
            agg["% réinscrits"] = agg["% réinscrits"].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "")

    desired_cols = [
        "Année", "Période", "Sede", "Secteur", "Nb. de Cours", "Nb. d'inscriptions",
        "Nouveaux inscrits", "% nouveaux", "Réinscrits", "% réinscrits", "Qté heures",
        "Nombre d'heures-élèves", "Heures synchrones (h-élèves)",
        "Recettes", "Dépenses", "Taux de remplissage",
    ]
    final_cols = [c for c in desired_cols if c in agg.columns]
    result = agg[final_cols].copy()
    if "Secteur" in result.columns:
        result["_sort"] = result["Secteur"].apply(
            lambda x: SECTOR_ORDER.index(x) if x in SECTOR_ORDER else 999
        )
        sort_cols = ["Période", "Sede", "_sort"] if "Période" in result.columns else ["Sede", "_sort"]
        sort_cols = [c for c in sort_cols if c in result.columns]
        if sort_cols:
            result = result.sort_values(sort_cols)
        result = result.drop(columns=["_sort"])

    if add_total_row and not result.empty:
        total_row = {}
        for col in result.columns:
            if col in ["Année", "Période", "Sede"]:
                total_row[col] = ""
            elif col == "Secteur":
                total_row[col] = "TOTAL"
            elif col == "Taux de remplissage":
                total_inscr = result["Nb. d'inscriptions"].sum() if "Nb. d'inscriptions" in result.columns else 0
                total_cours = result["Nb. de Cours"].sum() if "Nb. de Cours" in result.columns else 0
                total_row[col] = round(total_inscr / total_cours, 2) if total_cours > 0 else 0
            else:
                total_row[col] = result[col].sum()
        result = pd.concat([result, pd.DataFrame([total_row])], ignore_index=True)

    return result


def create_ifi_totals(df):
    """Aggregate all sedi into a single 'IFI' global view by sector."""
    df_ifi = df.copy()
    df_ifi["Sede"] = "IFI"
    return aggregate_by_sector(df_ifi)


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------

def calculate_profitability(df):
    """Calculate revenue per inscription (ARPI) by sector and sede."""
    inscr_col = "Nb. d'inscriptions"

    by_sector = df.groupby("Secteur").agg({inscr_col: "sum", "Recettes": "sum"}).reset_index()
    by_sector["ARPI"] = (by_sector["Recettes"] / by_sector[inscr_col]).round(2)
    by_sector = by_sector.sort_values("ARPI", ascending=False)

    by_sede = df.groupby("Sede").agg({inscr_col: "sum", "Recettes": "sum"}).reset_index()
    by_sede["ARPI"] = (by_sede["Recettes"] / by_sede[inscr_col]).round(2)
    by_sede = by_sede.sort_values("ARPI", ascending=False)

    by_sector_sede = df.groupby(["Secteur", "Sede"]).agg({inscr_col: "sum", "Recettes": "sum"}).reset_index()
    by_sector_sede["ARPI"] = (by_sector_sede["Recettes"] / by_sector_sede[inscr_col]).round(2)

    return by_sector, by_sede, by_sector_sede


def calculate_yoy_comparison(df):
    """Calculate year-over-year variations (global)."""
    inscr_col = "Nb. d'inscriptions"
    years = sorted(df["Année"].unique())

    if len(years) < 2:
        return None, years

    results = []
    for year in years:
        year_data = df[df["Année"] == year]
        results.append({
            "Année": year,
            "Inscriptions": year_data[inscr_col].sum(),
            "Cours": year_data["Nb. de Cours"].sum(),
            "Recettes": year_data["Recettes"].sum() if "Recettes" in year_data.columns else 0,
            "Heures": year_data["Nombre total d'heures vendues (heures-étudiants)"].sum()
            if "Nombre total d'heures vendues (heures-étudiants)" in year_data.columns else 0,
        })

    comparison_df = pd.DataFrame(results)
    for col in ["Inscriptions", "Cours", "Recettes", "Heures"]:
        comparison_df[f"{col}_var"] = comparison_df[col].pct_change() * 100

    return comparison_df, years


def calculate_yoy_by_sede(df):
    """Calculate year-over-year by sede (one row per sede x year)."""
    inscr_col = "Nb. d'inscriptions"
    years = sorted(df["Année"].unique())

    if len(years) < 2:
        return None

    results = []
    for sede in df["Sede"].unique():
        sede_data = df[df["Sede"] == sede]
        for year in years:
            year_data = sede_data[sede_data["Année"] == year]
            results.append({
                "Sede": sede,
                "Année": year,
                "Inscriptions": year_data[inscr_col].sum(),
                "Recettes": year_data["Recettes"].sum() if "Recettes" in year_data.columns else 0,
            })

    return pd.DataFrame(results)


# ---------------------------------------------------------------------------
# Course-fiche export helpers
# ---------------------------------------------------------------------------

def detect_export_type(df):
    """Detect export type from DataFrame columns."""
    cols = set(df.columns)
    activite_markers = {"Période", "Élèves différents", "Heures-Élèves", "Heures enseignées"}
    fiches_markers = {"Centre", "Catégorie", "Nb total de participants", "Date début"}
    report_markers = {"Catégorie de cours"}
    profils_markers = {"Tranche d'âge de l'élève", "Nationalité", "Profil client", "Code Client"}
    produits_markers = {"Type de produit", "Nom du produit", "Code article", "Nombre maximum de places"}

    fiches_score = len(fiches_markers & cols)
    report_score = len(report_markers & cols)
    profils_score = len(profils_markers & cols)
    produits_score = len(produits_markers & cols)
    activite_score = len(activite_markers & cols)

    if activite_score >= 3:
        return "activite_periode"
    elif profils_score >= 3:
        return "profils_clients"
    elif produits_score >= 3:
        return "produits"
    elif fiches_score >= 3:
        return "fiches_cours"
    elif report_score >= 1:
        return "rapport_categories"
    return "unknown"


def parse_french_number(value):
    """Parse French-formatted number (handles 1,440.00 and 1.440,00 formats)."""
    if pd.isna(value):
        return 0.0
    s = str(value).strip().replace("%", "").strip()
    if s == "":
        return 0.0
    if "," in s and "." in s:
        if s.index(",") < s.index("."):
            s = s.replace(",", "")
        else:
            s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        parts = s.split(",")
        if len(parts) == 2 and len(parts[1]) <= 2:
            s = s.replace(",", ".")
        else:
            s = s.replace(",", "")
    try:
        return float(s)
    except Exception:  # noqa: BLE001
        return 0.0


def extract_sede_from_centre(centre_value):
    """Extract sede code (IFM, IFF, IFN, IFP) from Centre field."""
    if pd.isna(centre_value):
        return "???"
    for city, code in CENTRE_TO_SEDE.items():
        if city.lower() in str(centre_value).lower():
            return code
    return "???"


def parse_periode_field(val):
    """Parse Période field like '2026-FEVRIER' → (year, month_num). Uses first month."""
    if pd.isna(val):
        return None, None
    val_str = str(val).strip()
    if "," in val_str:
        val_str = val_str.split(",")[0].strip()
    m = re.match(r"(\d{4})-(\w+)", val_str)
    if m:
        year = int(m.group(1))
        month_num = MONTH_FR_TO_NUM.get(m.group(2).upper())
        return year, month_num
    return None, None


def assign_semester_from_month(month):
    """Jan-Aug → sem1, Sep-Dec → sem2."""
    if month is None:
        return "sem1"
    return "sem1" if 1 <= month <= 8 else "sem2"


# =====================================================
# PRODUCTS CATALOG EXPORT SUPPORT
# (ported from dashboard_aec_v2.py, st.* stripped)
# =====================================================

def extract_sede_from_filename(filename):
    """Extract sede code (IFM, IFF, IFN, IFP) from a product export filename."""
    fn_upper = str(filename).upper()
    for code in ["IFM", "IFF", "IFN", "IFP"]:
        if code in fn_upper:
            return code
    fn_lower = str(filename).lower()
    for city, code in CENTRE_TO_SEDE.items():
        if city.lower() in fn_lower:
            return code
    return "???"


def process_produits(df, sede_code="???"):
    """Process the products catalog export DataFrame (adds Sede, parses numbers, Actif)."""
    df = df.copy()
    df["Sede"] = sede_code

    # Parse numeric columns (French number formats)
    num_cols = ["Prix", "Tarif réduit", "Prix membre", "Ventes", "Heures",
                "Nombre d'UE", "Nombre maximum de places"]
    for col in num_cols:
        if col in df.columns:
            df[col] = df[col].apply(parse_french_number)

    # Derive boolean Actif from "Actif ?"
    if "Actif ?" in df.columns:
        df["Actif"] = df["Actif ?"].apply(
            lambda x: True if str(x).strip().lower() in ["oui", "yes", "true", "1", "vrai"] else False
        )

    return df


def format_number(n, prefix="", suffix=""):
    """Human-friendly number formatting (1.23M / 1.2K / 1,234)."""
    if pd.isna(n):
        return "N/A"
    if n >= 1_000_000:
        return f"{prefix}{n / 1_000_000:.2f}M{suffix}"
    elif n >= 1_000:
        return f"{prefix}{n / 1_000:.1f}K{suffix}"
    else:
        return f"{prefix}{n:,.0f}{suffix}"


# ===========================================================================
# Profils clients (appended) — ported verbatim from dashboard_aec_v2.py
# Functions: process_profils_clients, _infer_gender_from_prenom,
#   assign_custom_age_bracket, translate_course_type, _match_nationality_to_iso
# Constants: _COURSE_TYPE_RAW, CUSTOM_AGE_BRACKETS, CUSTOM_AGE_BRACKET_ORDER,
#   MACRO_LEVEL_MAP, _NATIONALITY_TO_ISO_RAW, NATIONALITY_TO_ISO,
#   _PRENOM_GENRE_MAP, _MALE_ENDING_A
# Reuses existing extract_sede_from_centre / parse_periode_field above.
# (st.* dependencies: none in these blocks.)
# ===========================================================================

_COURSE_TYPE_RAW = {
    "catalogue": "Du catalogue",
    "du catalogue": "Du catalogue",
    "group": "Cours programmés",
    "group - private": "Cours programmés",
    "cours programmés": "Cours programmés",
    "cours programmes": "Cours programmés",
    "corporate": "Entreprises (organismes)",
    "corporate-group - private": "Entreprises (organismes)",
    "private": "À la carte",
    "à la carte": "À la carte",
    "a la carte": "À la carte",
    "entreprises": "Entreprises (organismes)",
    "entreprises (organismes)": "Entreprises (organismes)",
}
COURSE_TYPE_FR = _COURSE_TYPE_RAW  # kept for reference


CUSTOM_AGE_BRACKETS = [
    ("Enfants / jeunes ados (3-13)", 3, 13),
    ("Lycéens (14-18)", 14, 18),
    ("Jeunes U25 (19-25)", 19, 25),
    ("Jeunes adultes U35 (26-35)", 26, 35),
    ("Adultes actifs (36-50)", 36, 50),
    ("Adultes confirmés (51-65)", 51, 65),
    ("Seniors (65+)", 66, 200),
]
CUSTOM_AGE_BRACKET_ORDER = [b[0] for b in CUSTOM_AGE_BRACKETS]


MACRO_LEVEL_MAP = {
    "A0": "A0",
    "A1": "A1", "A1.1": "A1", "A1.2": "A1",
    "A2": "A2", "A2.1": "A2", "A2.2": "A2",
    "B1": "B1", "B1.1": "B1", "B1.2": "B1",
    "B2": "B2", "B2.1": "B2", "B2.2": "B2",
    "C1": "C1", "C1.1": "C1", "C1.2": "C1",
    "C2": "C2",
}
MACRO_LEVEL_ORDER = ["A0", "A1", "A2", "B1", "B2", "C1", "C2"]


_NATIONALITY_TO_ISO_RAW = {
    "Italien": "ITA", "Italiana": "ITA", "Italienne": "ITA", "ITALIANA": "ITA",
    "Français": "FRA", "Francese": "FRA", "Française": "FRA", "FRANCESE": "FRA",
    "Allemand": "DEU", "Tedesca": "DEU", "Allemande": "DEU", "TEDESCA": "DEU",
    "Espagnol": "ESP", "Spagnola": "ESP", "Espagnole": "ESP", "SPAGNOLA": "ESP",
    "Américain": "USA", "Americana": "USA", "Américaine": "USA", "AMERICANA": "USA",
    "Britannique": "GBR", "Britannica": "GBR", "BRITANNICA": "GBR",
    "Anglais": "GBR", "Inglese": "GBR", "Anglaise": "GBR", "INGLESE": "GBR",
    "Brésilien": "BRA", "Brasiliana": "BRA", "Brésilienne": "BRA", "BRASILIANA": "BRA",
    "Chinois": "CHN", "Cinese": "CHN", "Chinoise": "CHN", "CINESE": "CHN",
    "Japonais": "JPN", "Giapponese": "JPN", "Japonaise": "JPN", "GIAPPONESE": "JPN",
    "Russe": "RUS", "Russa": "RUS", "RUSSA": "RUS",
    "Colombien": "COL", "Colombiana": "COL", "Colombienne": "COL", "COLOMBIANA": "COL",
    "Argentin": "ARG", "Argentina": "ARG", "Argentine": "ARG", "ARGENTINA": "ARG",
    "Mexicain": "MEX", "Messicana": "MEX", "Mexicaine": "MEX", "MESSICANA": "MEX",
    "Roumain": "ROU", "Rumena": "ROU", "Roumaine": "ROU", "Romena": "ROU", "RUMENA": "ROU",
    "Ukrainien": "UKR", "Ucraina": "UKR", "Ukrainienne": "UKR", "UCRAINA": "UKR",
    "Polonais": "POL", "Polacca": "POL", "Polonaise": "POL", "POLACCA": "POL",
    "Tunisien": "TUN", "Tunisina": "TUN", "Tunisienne": "TUN", "TUNISINA": "TUN",
    "Marocain": "MAR", "Marocchina": "MAR", "Marocaine": "MAR", "MAROCCHINA": "MAR",
    "Algérien": "DZA", "Algerina": "DZA", "Algérienne": "DZA", "ALGERINA": "DZA",
    "Belge": "BEL", "Belga": "BEL", "BELGA": "BEL",
    "Suisse": "CHE", "Svizzera": "CHE", "SVIZZERA": "CHE",
    "Portugais": "PRT", "Portoghese": "PRT", "Portugaise": "PRT", "PORTOGHESE": "PRT",
    "Néerlandais": "NLD", "Olandese": "NLD", "Néerlandaise": "NLD", "OLANDESE": "NLD",
    "Grec": "GRC", "Greca": "GRC", "Grecque": "GRC", "GRECA": "GRC",
    "Turc": "TUR", "Turca": "TUR", "Turque": "TUR", "TURCA": "TUR",
    "Indien": "IND", "Indiana": "IND", "Indienne": "IND", "INDIANA": "IND",
    "Coréen": "KOR", "Coreana": "KOR", "Coréenne": "KOR", "COREANA": "KOR",
    "Australien": "AUS", "Australiana": "AUS", "Australienne": "AUS", "AUSTRALIANA": "AUS",
    "Canadien": "CAN", "Canadese": "CAN", "Canadienne": "CAN", "CANADESE": "CAN",
    "Péruvien": "PER", "Peruviana": "PER", "Péruvienne": "PER", "PERUVIANA": "PER",
    "Vénézuélien": "VEN", "Venezuelana": "VEN", "Vénézuélienne": "VEN", "VENEZUELANA": "VEN",
    "Chilien": "CHL", "Cilena": "CHL", "Chilienne": "CHL", "CILENA": "CHL",
    "Iranien": "IRN", "Iraniana": "IRN", "Iranienne": "IRN", "IRANIANA": "IRN",
    "Égyptien": "EGY", "Egiziana": "EGY", "Égyptienne": "EGY", "EGIZIANA": "EGY",
    "Libanais": "LBN", "Libanese": "LBN", "Libanaise": "LBN", "LIBANESE": "LBN",
    "Autrichien": "AUT", "Austriaca": "AUT", "Autrichienne": "AUT", "AUSTRIACA": "AUT",
    "Irlandais": "IRL", "Irlandese": "IRL", "Irlandaise": "IRL", "IRLANDESE": "IRL",
    "Philippin": "PHL", "Filippina": "PHL", "Philippine": "PHL", "FILIPPINA": "PHL",
    "Hongrois": "HUN", "Ungherese": "HUN", "Hongroise": "HUN", "UNGHERESE": "HUN",
    "Tchèque": "CZE", "Ceca": "CZE", "CECA": "CZE",
    "Bulgare": "BGR", "Bulgara": "BGR", "BULGARA": "BGR",
    "Croate": "HRV", "Croata": "HRV", "CROATA": "HRV",
    "Serbe": "SRB", "Serba": "SRB", "SERBA": "SRB",
    "Slovène": "SVN", "Slovena": "SVN", "SLOVENA": "SVN",
    "Slovaque": "SVK", "Slovacca": "SVK", "SLOVACCA": "SVK",
    "Danois": "DNK", "Danese": "DNK", "Danoise": "DNK", "DANESE": "DNK",
    "Suédois": "SWE", "Svedese": "SWE", "Suédoise": "SWE", "SVEDESE": "SWE",
    "Norvégien": "NOR", "Norvegese": "NOR", "Norvégienne": "NOR", "NORVEGESE": "NOR",
    "Finlandais": "FIN", "Finlandese": "FIN", "Finlandaise": "FIN", "FINLANDESE": "FIN",
    "Albanais": "ALB", "Albanese": "ALB", "Albanaise": "ALB", "ALBANESE": "ALB",
    "Cubain": "CUB", "Cubana": "CUB", "Cubaine": "CUB", "CUBANA": "CUB",
    "Sénégalais": "SEN", "Senegalese": "SEN", "Sénégalaise": "SEN", "SENEGALESE": "SEN",
    "Congolais": "COD", "Congolese": "COD", "Congolaise": "COD", "CONGOLESE": "COD",
    "Ivoirien": "CIV", "Ivoriana": "CIV", "Ivoirienne": "CIV", "IVORIANA": "CIV",
    "Camerounais": "CMR", "Camerunese": "CMR", "Camerounaise": "CMR", "CAMERUNESE": "CMR",
    "Pakistanais": "PAK", "Pakistana": "PAK", "Pakistanaise": "PAK", "PAKISTANA": "PAK",
    "Sri Lankais": "LKA", "Srilankese": "LKA", "Sri Lankaise": "LKA", "SRILANKESE": "LKA",
    "Bangladais": "BGD", "Bangladese": "BGD", "Bangladaise": "BGD", "BANGLADESE": "BGD",
    "Thaïlandais": "THA", "Thailandese": "THA", "Thaïlandaise": "THA", "THAILANDESE": "THA",
    "Vietnamien": "VNM", "Vietnamita": "VNM", "Vietnamienne": "VNM", "VIETNAMITA": "VNM",
    "Indonésien": "IDN", "Indonesiana": "IDN", "Indonésienne": "IDN", "INDONESIANA": "IDN",
    "Nigérian": "NGA", "Nigeriana": "NGA", "Nigériane": "NGA", "NIGERIANA": "NGA",
    "Sud-Africain": "ZAF", "Sudafricana": "ZAF", "Sud-Africaine": "ZAF", "SUDAFRICANA": "ZAF",
    # Additional nationalities found in AEC data
    "Biélorusse": "BLR", "BIÉLORUSSE": "BLR", "Bielorussa": "BLR",
    "Mauricienne": "MUS", "MAURICIENNE": "MUS", "Mauriziana": "MUS",
    "Nord-Coréenne": "PRK", "NORD-CORÉENNE": "PRK", "Nordcoreana": "PRK",
    "Arménienne": "ARM", "ARMÉNIENNE": "ARM", "Armena": "ARM",
    "Salvadorienne": "SLV", "SALVADORIENNE": "SLV", "Salvadoregna": "SLV",
    "Sri-Lankaise": "LKA", "SRI-LANKAISE": "LKA",
    "Uruguayenne": "URY", "URUGUAYENNE": "URY", "Uruguaiana": "URY",
    "Monténégrine": "MNE", "MONTÉNÉGRINE": "MNE", "Montenegrina": "MNE",
    "Angolaise": "AGO", "ANGOLAISE": "AGO", "Angolana": "AGO",
    "Birmane": "MMR", "BIRMANE": "MMR", "Birmana": "MMR",
    "Cap-Verdienne": "CPV", "CAP-VERDIENNE": "CPV", "Capoverdiana": "CPV",
    "Moldave": "MDA", "MOLDAVE": "MDA", "Moldava": "MDA",
    "Djiboutienne": "DJI", "DJIBOUTIENNE": "DJI", "Gibutiana": "DJI",
    "Géorgienne": "GEO", "GÉORGIENNE": "GEO", "Georgiana": "GEO",
    "Hondurienne": "HND", "HONDURIENNE": "HND", "Honduregna": "HND",
    "Lettone": "LVA", "LETTONE": "LVA", "Lettone": "LVA",
    "Lituanienne": "LTU", "LITUANIENNE": "LTU", "Lituana": "LTU",
    # Common extras
    "Costaricaine": "CRI", "COSTARICAINE": "CRI",
    "Equatorienne": "ECU", "EQUATORIENNE": "ECU", "Équatorienne": "ECU",
    "Paraguayenne": "PRY", "PARAGUAYENNE": "PRY",
    "Bolivienne": "BOL", "BOLIVIENNE": "BOL",
    "Dominicaine": "DOM", "DOMINICAINE": "DOM",
    "Haïtienne": "HTI", "HAÏTIENNE": "HTI",
    "Jamaïcaine": "JAM", "JAMAÏCAINE": "JAM",
    "Nicaraguayenne": "NIC", "NICARAGUAYENNE": "NIC",
    "Panaméenne": "PAN", "PANAMÉENNE": "PAN",
    "Guatémaltèque": "GTM", "GUATÉMALTÈQUE": "GTM",
    "Kényane": "KEN", "KÉNYANE": "KEN", "Keniota": "KEN",
    "Malgache": "MDG", "MALGACHE": "MDG",
    "Togolaise": "TGO", "TOGOLAISE": "TGO",
    "Béninoise": "BEN", "BÉNINOISE": "BEN",
    "Gabonaise": "GAB", "GABONAISE": "GAB",
    "Guinéenne": "GIN", "GUINÉENNE": "GIN",
    "Malienne": "MLI", "MALIENNE": "MLI",
    "Burkinabè": "BFA", "BURKINABÈ": "BFA",
    "Tchadienne": "TCD", "TCHADIENNE": "TCD",
    "Rwandaise": "RWA", "RWANDAISE": "RWA",
    "Tanzanienne": "TZA", "TANZANIENNE": "TZA",
    "Ougandaise": "UGA", "OUGANDAISE": "UGA",
    "Éthiopienne": "ETH", "ÉTHIOPIENNE": "ETH",
    "Népalaise": "NPL", "NÉPALAISE": "NPL",
    "Israélienne": "ISR", "ISRAÉLIENNE": "ISR",
    "Irakienne": "IRQ", "IRAKIENNE": "IRQ",
    "Syrienne": "SYR", "SYRIENNE": "SYR",
    "Jordanienne": "JOR", "JORDANIENNE": "JOR",
    "Estonienne": "EST", "ESTONIENNE": "EST",
    "Islandaise": "ISL", "ISLANDAISE": "ISL",
    "Luxembourgeoise": "LUX", "LUXEMBOURGEOISE": "LUX",
    "Maltaise": "MLT", "MALTAISE": "MLT",
    "Chypriote": "CYP", "CHYPRIOTE": "CYP",
    "Bosniaque": "BIH", "BOSNIAQUE": "BIH",
    "Macédonienne": "MKD", "MACÉDONIENNE": "MKD",
    "Kosovar": "XKX", "KOSOVAR": "XKX", "Kosovare": "XKX",
}
# Build case-insensitive nationality lookup
NATIONALITY_TO_ISO = {k.lower(): v for k, v in _NATIONALITY_TO_ISO_RAW.items()}


def _match_nationality_to_iso(nat_str):
    """Match a nationality string to ISO-3 code, case-insensitive with fuzzy fallback."""
    if pd.isna(nat_str) or str(nat_str).strip() == "":
        return None
    clean = str(nat_str).strip().lower()
    # Direct match
    if clean in NATIONALITY_TO_ISO:
        return NATIONALITY_TO_ISO[clean]
    # Fuzzy match: require at least 6 common starting characters to avoid false positives
    if len(clean) >= 6:
        for key, code in NATIONALITY_TO_ISO.items():
            if len(key) >= 6 and (clean.startswith(key[:6]) or key.startswith(clean[:6])):
                return code
    # Fallback: try difflib for close matches
    import difflib
    matches = difflib.get_close_matches(clean, NATIONALITY_TO_ISO.keys(), n=1, cutoff=0.8)
    if matches:
        return NATIONALITY_TO_ISO[matches[0]]
    return None


def assign_custom_age_bracket(age):
    """Assign a custom age bracket label based on IFI segmentation."""
    if pd.isna(age):
        return None
    age = int(age)
    for label, low, high in CUSTOM_AGE_BRACKETS:
        if low <= age <= high:
            return label
    if age < 3:
        return "Enfants / jeunes ados (3-13)"
    return "Seniors (65+)"


def translate_course_type(val):
    """Translate English AEC course type to French (case-insensitive)."""
    if pd.isna(val):
        return val
    import re as _re
    val_str = _re.sub(r'\s+', ' ', str(val).strip())  # normalise whitespace
    key = val_str.lower()
    if key in _COURSE_TYPE_RAW:
        return _COURSE_TYPE_RAW[key]
    # Partial match fallback
    for k, v in _COURSE_TYPE_RAW.items():
        if k in key or key in k:
            return v
    return val_str


_PRENOM_GENRE_MAP: dict[str, str] = {
    # ── Female ──
    "Adele": "F", "Adriana": "F", "Agnese": "F", "Agostina": "F", "Aida": "F",
    "Albina": "F", "Alessandra": "F", "Alessia": "F", "Alexandra": "F", "Alice": "F",
    "Alina": "F", "Allegra": "F", "Amalia": "F", "Amanda": "F", "Ambra": "F",
    "Amelia": "F", "Anastasia": "F", "Angela": "F", "Angelica": "F", "Anita": "F",
    "Anna": "F", "Annalaura": "F", "Annalisa": "F", "Annamaria": "F", "Annarita": "F",
    "Antonia": "F", "Antonietta": "F", "Arianna": "F", "Asia": "F", "Astrid": "F",
    "Aurora": "F", "Barbara": "F", "Beatrice": "F", "Benedetta": "F", "Berenice": "F",
    "Bianca": "F", "Bruna": "F", "Camilla": "F", "Carla": "F", "Carlotta": "F",
    "Carmen": "F", "Carolina": "F", "Caterina": "F", "Cecilia": "F", "Celeste": "F",
    "Chiara": "F", "Cinzia": "F", "Clara": "F", "Claudia": "F", "Clelia": "F",
    "Clotilde": "F", "Concetta": "F", "Costanza": "F", "Cristina": "F",
    "Dalila": "F", "Daniela": "F", "Daria": "F", "Debora": "F", "Denise": "F",
    "Desiree": "F", "Diana": "F", "Diletta": "F", "Dina": "F", "Donatella": "F",
    "Doriana": "F", "Edith": "F", "Elda": "F", "Elena": "F", "Eleonora": "F",
    "Elettra": "F", "Eliana": "F", "Elisa": "F", "Elisabetta": "F", "Eloisa": "F",
    "Emanuela": "F", "Emilia": "F", "Emma": "F", "Erica": "F", "Erika": "F",
    "Ester": "F", "Eugenia": "F", "Eva": "F", "Fabiana": "F", "Fabiola": "F",
    "Federica": "F", "Fiorella": "F", "Flavia": "F", "Flora": "F", "Francesca": "F",
    "Frida": "F", "Gaia": "F", "Gemma": "F", "Giada": "F", "Ginevra": "F",
    "Gioia": "F", "Giorgia": "F", "Giovanna": "F", "Giulia": "F", "Giuliana": "F",
    "Giuseppina": "F", "Giusy": "F", "Gloria": "F", "Grazia": "F", "Greta": "F",
    "Ida": "F", "Ilaria": "F", "Ilary": "F", "Ilda": "F", "Ilenia": "F",
    "Immacolata": "F", "Ines": "F", "Irene": "F", "Iris": "F", "Isabel": "F",
    "Isabella": "F", "Jessica": "F", "Jolanda": "F", "Katia": "F", "Lara": "F",
    "Laura": "F", "Lavinia": "F", "Lea": "F", "Leila": "F", "Letizia": "F",
    "Lidia": "F", "Liliana": "F", "Linda": "F", "Lisa": "F", "Livia": "F",
    "Lorena": "F", "Lorenza": "F", "Luana": "F", "Lucia": "F", "Luciana": "F",
    "Lucrezia": "F", "Lucyana": "F", "Ludovica": "F", "Luisa": "F", "Luna": "F",
    "Maddalena": "F", "Manuela": "F", "Mara": "F", "Margherita": "F", "Maria": "F",
    "Mariafrancesca": "F", "Mariarosaria": "F", "Marianna": "F", "Marina": "F",
    "Marta": "F", "Martina": "F", "Matilde": "F", "Maya": "F", "Melania": "F",
    "Melissa": "F", "Michela": "F", "Milena": "F", "Mirella": "F", "Miriam": "F",
    "Miriana": "F", "Monica": "F", "Nadia": "F", "Natalia": "F", "Nicole": "F",
    "Nicoletta": "F", "Nina": "F", "Noemi": "F", "Nora": "F", "Nunzia": "F",
    "Olivia": "F", "Ornella": "F", "Paola": "F", "Patrizia": "F", "Penelope": "F",
    "Petra": "F", "Rachele": "F", "Raffaella": "F", "Rebecca": "F", "Renata": "F",
    "Rita": "F", "Roberta": "F", "Rosa": "F", "Rosanna": "F", "Rossana": "F",
    "Rossella": "F", "Sabrina": "F", "Samantha": "F", "Sandra": "F", "Sara": "F",
    "Selene": "F", "Serena": "F", "Sibilla": "F", "Silvia": "F", "Simona": "F",
    "Sofia": "F", "Sonia": "F", "Sophia": "F", "Stefania": "F", "Stella": "F",
    "Susanna": "F", "Sveva": "F", "Teresa": "F", "Tiziana": "F", "Valentina": "F",
    "Valeria": "F", "Vanessa": "F", "Vera": "F", "Veronica": "F", "Viola": "F",
    "Virginia": "F", "Vittoria": "F", "Viviana": "F",
    # French female
    "Adèle": "F", "Agathe": "F", "Agnès": "F", "Aimée": "F", "Amélie": "F",
    "Anaïs": "F", "Angélique": "F", "Anouk": "F", "Brigitte": "F", "Camille": "F",
    "Capucine": "F", "Caroline": "F", "Catherine": "F", "Céline": "F", "Charlotte": "F",
    "Chloé": "F", "Christine": "F", "Claire": "F", "Clémence": "F", "Colette": "F",
    "Corinne": "F", "Delphine": "F", "Dominique": "F", "Éléonore": "F", "Élise": "F",
    "Élodie": "F", "Émilie": "F", "Estelle": "F", "Fleur": "F", "Florence": "F",
    "Françoise": "F", "Gaëlle": "F", "Geneviève": "F", "Hélène": "F", "Inès": "F",
    "Isabelle": "F", "Jeanne": "F", "Joséphine": "F", "Julie": "F", "Juliette": "F",
    "Léa": "F", "Léonie": "F", "Louise": "F", "Lucie": "F", "Madeleine": "F",
    "Manon": "F", "Margaux": "F", "Marie": "F", "Marion": "F", "Mathilde": "F",
    "Nathalie": "F", "Noémie": "F", "Pauline": "F", "Rose": "F", "Sandrine": "F",
    "Sophie": "F", "Sylvie": "F", "Thérèse": "F", "Valérie": "F", "Véronique": "F",
    # ── Male ──
    "Adriano": "M", "Alberto": "M", "Aldo": "M", "Alessandro": "M", "Alessio": "M",
    "Alfonso": "M", "Alfredo": "M", "Amedeo": "M", "Andrea": "M", "Angelo": "M",
    "Antonio": "M", "Arturo": "M", "Bruno": "M", "Carlo": "M", "Cesare": "M",
    "Christian": "M", "Claudio": "M", "Corrado": "M", "Cosimo": "M", "Cristian": "M",
    "Daniel": "M", "Daniele": "M", "Dario": "M", "Davide": "M", "Diego": "M",
    "Domenico": "M", "Donato": "M", "Edoardo": "M", "Elia": "M", "Emanuele": "M",
    "Emiliano": "M", "Enrico": "M", "Enzo": "M", "Ernesto": "M", "Ettore": "M",
    "Eugenio": "M", "Fabio": "M", "Fabrizio": "M", "Federico": "M", "Felice": "M",
    "Filippo": "M", "Francesco": "M", "Franco": "M", "Fulvio": "M", "Gabriele": "M",
    "Gaetano": "M", "Gennaro": "M", "Giacomo": "M", "Gianluca": "M", "Gianmarco": "M",
    "Gianpaolo": "M", "Giorgio": "M", "Giovanni": "M", "Giuliano": "M", "Giulio": "M",
    "Giuseppe": "M", "Guglielmo": "M", "Guido": "M", "Jacopo": "M", "Lapo": "M",
    "Leonardo": "M", "Lorenzo": "M", "Luca": "M", "Luciano": "M", "Luigi": "M",
    "Manuel": "M", "Marcello": "M", "Marcelo": "M", "Marco": "M", "Mario": "M",
    "Massimiliano": "M", "Massimo": "M", "Matteo": "M", "Mattia": "M", "Maurizio": "M",
    "Mauro": "M", "Michael": "M", "Michele": "M", "Mirko": "M", "Niccolò": "M",
    "Nicola": "M", "Nicolò": "M", "Nunzio": "M", "Omar": "M", "Oreste": "M",
    "Oscar": "M", "Paolo": "M", "Pasquale": "M", "Patrick": "M", "Piero": "M",
    "Pietro": "M", "Raffaele": "M", "Renato": "M", "Riccardo": "M", "Roberto": "M",
    "Rocco": "M", "Salvatore": "M", "Samuele": "M", "Sandro": "M", "Saverio": "M",
    "Sebastiano": "M", "Sergio": "M", "Silvio": "M", "Simone": "M", "Stefano": "M",
    "Thomas": "M", "Tommaso": "M", "Ugo": "M", "Umberto": "M", "Valerio": "M",
    "Vincenzo": "M", "Vittorio": "M",
    # Additional Italian names
    "Teodoro": "M", "Zeno": "M", "Duccio": "M", "Tancredi": "M", "Ruggero": "M",
    "Tito": "M", "Achille": "M", "Neri": "M", "Flavio": "M", "Gherardo": "M",
    "Ivo": "M", "Nino": "M", "Biagio": "M", "Ciro": "M", "Donato": "M",
    "Simon": "M", "Sasha": "M", "Damiano": "M", "Tiziano": "M", "Corrado": "M",
    "Novella": "F", "Azzurra": "F", "Morena": "F", "Carmela": "F", "Alba": "F",
    "Florinda": "F", "Assunta": "F", "Rosella": "F", "Marika": "F", "Sarah": "F",
    "Elide": "F", "Concettina": "F", "Oriana": "F", "Loredana": "F", "Wanda": "F",
    "Filomena": "F", "Giuseppa": "F", "Graziella": "F", "Addolorata": "F", "Nicolina": "F",
    "Palmina": "F", "Agata": "F", "Micaela": "F", "Noelia": "F", "Giordana": "F",
    "Celeste": "F", "Clelia": "F", "Romina": "F", "Bruna": "F",
    "Deborah": "F", "Priscilla": "F", "Floriana": "F", "Olimpia": "F",
    "Gabriella": "F", "Carol": "F", "Mihaela": "F", "Lilla": "F", "Guya": "F",
    "Olha": "F", "Marialaura": "F", "Eleonore": "F", "Rosario": "M",
    "David": "M", "Brando": "M", "Ruben": "M", "Adrián": "M",
    "Julia": "F", "Marzia": "F", "Ella": "F", "Antonella": "F", "Fiammetta": "F",
    "Viktoriia": "F", "Philip": "M", "Kevin": "M", "Cristiano": "M",
    "Gianmaria": "M", "Gabriel": "M", "Dimitri": "M", "Pedro": "M",
    # ── Exhaustive additions from CSV data ──
    # Female – international / rare Italian
    "Melany": "F", "Chanel": "F", "Nancy": "F", "Ingrid": "F", "Hanna": "F",
    "Guia": "F", "Fatoumata": "F", "Samia": "F", "Amira": "F", "Olga": "F",
    "Fulvia": "F", "Karla": "F", "Tereza": "F", "Antonina": "F", "Réka": "F",
    "Judith": "F", "Klara": "F", "Galina": "F", "Pamela": "F", "Melisa": "F",
    "Zainab": "F", "Danielle": "F", "Allana": "F", "Maia": "F", "Alisa": "F",
    "Milana": "F", "Alma": "F", "Zita": "F", "Florencia": "F", "Dunia": "F",
    "Aylin": "F", "Noura": "F", "Briselda": "F", "Amaranta": "F", "Elvira": "F",
    "Oumaima": "F", "Mariachiara": "F", "Jule": "F", "Darla": "F", "Aura": "F",
    "Anisa": "F", "Ramona": "F", "Vivian": "F", "Mia": "F", "Anduela": "F",
    "Elif": "F", "Ayako": "F", "Elina": "F", "Biljana": "F", "Jennifer": "F",
    "Angelique": "F", "Elodie": "F", "Josephine": "F", "Anamika": "F",
    "Germana": "F", "Rubina": "F", "Tara": "F", "Olympia": "F", "Ariana": "F",
    "Mila": "F", "Tabatha": "F", "Tamara": "F", "Darina": "F", "Meggy": "F",
    "Matilda": "F", "Erisa": "F", "Alissa": "F", "Perla": "F", "Sibora": "F",
    "Dafne": "F", "Rania": "F", "Esmeralda": "F", "Ada": "F", "Madelyn": "F",
    "Mariangela": "F", "Jackie": "F", "Mary": "F", "Conchita": "F", "Franca": "F",
    "Alexia": "F", "Damiana": "F", "Adalgisa": "F", "Victoria": "F",
    "Gessica": "F", "Erjola": "F", "Mariastella": "F", "Clementina": "F",
    "Guja": "F", "Yvonne": "F", "Fiamma": "F", "Marica": "F", "Clarice": "F",
    "Orsola": "F", "Ottavia": "F", "Mariasole": "F", "Luise": "F",
    "Leonore": "F", "Amelina": "F", "Ciara": "F", "Chantal": "F",
    "Ailide": "F", "Laila": "F", "Elisaveta": "F", "Georgia": "F",
    "Silvana": "F", "Johanna": "F", "Anastazja": "F", "Margaret": "F",
    "Monika": "F", "Catalina": "F", "Lola": "F", "Marsida": "F",
    "Justina": "F", "Tanja": "F", "Polina": "F", "Iryna": "F", "Brenda": "F",
    "Tommasina": "F", "Fabrizia": "F", "Marialuisa": "F", "Rosalba": "F",
    "Jennyfer": "F", "Cristiana": "F", "Aicha": "F", "Mirea": "F",
    "Jorja": "F", "Nausica": "F", "Denisa": "F", "Angiola": "F",
    "Fiorinda": "F", "Miryam": "F", "Annarosa": "F", "Rosamaria": "F",
    "Ilenya": "F", "Alberta": "F", "Brunella": "F", "Lia": "F",
    "Ekaterina": "F", "Mascia": "F", "Nataliia": "F", "Ashley": "F",
    "Ann": "F", "Jole": "F", "Micol": "F", "Sydney": "F", "Raffaela": "F",
    "Fatima": "F", "Jiya": "F", "Darlina": "F", "Marija": "F", "Aisha": "F",
    "Mariagiovanna": "F", "Jeanine": "F", "Fabia": "F", "Zoe": "F",
    "Cloe": "F", "Rachel": "F", "Lilian": "F", "Darya": "F", "Leanne": "F",
    "Ilana": "F", "Rosanella": "F", "Teodora": "F", "Lorella": "F",
    "Mariacristina": "F", "Gerarda": "F", "Stela": "F", "Martha": "F",
    "Mariana": "F", "Siria": "F", "Mayra": "F", "Tresy": "F", "Gayane": "F",
    "Shirley": "F", "Isra": "F", "Michelle": "F", "Oxana": "F",
    "Yasmine": "F", "Iasmin": "F", "Enrica": "F", "Patricia": "F",
    "Rosalexia": "F", "Alyssa": "F", "Piera": "F", "Irina": "F",
    "Alona": "F", "Elsa": "F", "Dayanna": "F", "Asja": "F", "Mireia": "F",
    "Iuliia": "F", "Kristina": "F", "Lily": "F", "Tabitha": "F",
    "Beatriz": "F", "Sirya": "F", "Milica": "F", "Isabela": "F",
    "Milla": "F", "Daphne": "F", "Violante": "F", "Brigitta": "F",
    "Rut": "F", "Malak": "F", "Nadiia": "F", "Sefora": "F", "Magda": "F",
    "Iolanda": "F", "Consiglia": "F", "Manola": "F", "Nikol": "F",
    "Annapaola": "F", "Mariam": "F", "Yasmin": "F", "Emmanuela": "F",
    "Cristel": "F", "Naomi": "F", "Flaviana": "F", "Arazely": "F",
    "Yasmayra": "F", "Leslie": "F", "Jade": "F", "Carolin": "F",
    "Mari": "F", "Xhenisa": "F", "Joelma": "F", "Fiorenza": "F",
    "Francescapia": "F", "Keyara": "F", "Shavindi": "F", "Astou": "F",
    "Margot": "F", "Lucrezi": "F", "Parveen": "F", "Necmiye": "F",
    "Muberra": "F", "Pannita": "F", "Aulona": "F", "Saniah": "F",
    "Dorota": "F", "Tomiris": "F", "Suri": "F", "Zoemicol": "F",
    "Abril": "F", "Yana": "F", "Maram": "F", "Shusma": "F",
    "Rejoice": "F", "Dilber": "F", "Zumrud": "F", "Ngoc": "F", "Nao": "F",
    "Indra": "F", "Samntha": "F", "Noja": "F", "Mame": "F",
    "Amber": "F", "Ana": "F", "Marari": "F", "Anava": "F",
    "Desiré": "F", "Anay": "F", "Jashwanni": "F", "Mahnas": "F",
    "Neralia": "F", "Dislaira": "F", "Rosalba": "F",
    # Female – rare/exotic
    "Anamika": "F", "Rubina": "F", "Kafaet": "F", "Yucen": "F",
    "Galina": "F", "Allana": "F", "Miky": "F", "Ozum": "F",
    "Omodunni": "F", "Yen": "F", "Banni": "F",
    # Male – international / rare Italian
    "Carlos": "M", "Valentino": "M", "Carmine": "M", "Niklas": "M",
    "Giordano": "M", "Naofal": "M", "Biniam": "M", "Prince": "M",
    "Ziad": "M", "Adrian": "M", "Mukesh": "M", "Leon": "M", "Angel": "M",
    "Jochem": "M", "Jan": "M", "Ivan": "M", "Demir": "M",
    "Mohamoud": "M", "Mohamed": "M", "Anish": "M", "Anastasios": "M",
    "Vasileios": "M", "Christopher": "M", "Tim": "M", "Emilio": "M",
    "Ahmet": "M", "Igor": "M", "Gustavo": "M", "Hektor": "M",
    "William": "M", "Elias": "M", "Andrzej": "M", "Ryan": "M",
    "Joshua": "M", "Carmelo": "M", "Paride": "M", "Björn": "M",
    "Rasmus": "M", "Jusuf": "M", "Georgios": "M", "Laszlo": "M",
    "Karsten": "M", "Augusto": "M", "Ludovico": "M", "Giancarlo": "M",
    "Geronimo": "M", "Antonios": "M", "John": "M", "Yehor": "M",
    "Giustino": "M", "Gianluigi": "M", "Guilherme": "M", "Urbano": "M",
    "Roman": "M", "Evan": "M", "Costanzo": "M", "Mohammed": "M",
    "Andy": "M", "Fausto": "M", "Leo": "M", "Sean": "M", "Leone": "M",
    "Ranieri": "M", "Peter": "M", "Ayrton": "M", "Orlando": "M",
    "Martino": "M", "Rayan": "M", "Wolf": "M", "Gianmichele": "M",
    "Okan": "M", "Filipponeri": "M", "Romano": "M", "Felix": "M",
    "Dino": "M", "Biase": "M", "Lars": "M", "Haowen": "M",
    "Ikenna": "M", "Agostino": "M", "Loris": "M", "Attilio": "M",
    "Orazio": "M", "Alvaro": "M", "Gianfilippo": "M", "Celestino": "M",
    "Dimitrios": "M", "Jakob": "M", "Ezequiel": "M", "Stephen": "M",
    "Piergiorgio": "M", "Pierluigi": "M", "Nicholas": "M", "Finn": "M",
    "Brayan": "M", "Dominik": "M", "Gioele": "M", "Alex": "M",
    "Martìn": "M", "Micah": "M", "Pier": "M", "James": "M",
    "Andreas": "M", "Tomas": "M", "Theo": "M", "Milan": "M",
    "Dmitrij": "M", "Salih": "M", "Muhmmad": "M", "Olurotimi": "M",
    "Corso": "M", "Sjors": "M", "Eike": "M", "Giaime": "M",
    "Skand": "M", "Deiner": "M", "Ranidu": "M", "Ariel": "M",
    "Hao": "M", "Mirco": "M", "Giacono": "M",
    # Male – non-European
    "Yamam": "M", "Xiaolin": "M", "Mohammad-shadman": "M",
    "Abhisheka": "M", "Yuchen": "M", "Arosha": "M",
    "Wenzheng": "M", "Luhua": "M", "Yang": "M", "Yimu": "M",
    "Yunlan": "M", "Beck": "M",
    # Data artifacts / surnames used as first names → best-effort gender
    "De": "M", "D": "M", "Le": "M", "Di": "M",
    "D'alessandro": "M", "Casizzone": "M", "Curci": "M", "Dabbiero": "M",
    "Burgada": "M", "Raspaolo": "M", "Russo": "M", "Caccavallo": "M",
    "Muneghina": "F", "Abenante": "M", "Caprile": "M", "Orlanducci": "M",
    "Benseghier": "M", "Mosca": "M", "Rande": "M",
    "Anonyme": "M",
    # Remaining edge cases
    "Desiree'": "F", "Jorge": "M", "Parveen": "F",
    "Joelma": "F", "Astou": "F", "Sefora": "F",
    "Consiglia": "F", "Manola": "F", "Nikol": "F",
    "Cristel": "F", "Noja": "F", "Samntha": "F",
    "Enrica": "F", "Patricia": "F", "Costanzo": "M",
    "Yurie": "F", "Rosalexia": "F", "Dislaira": "F",
    "Piera": "F", "Irina": "F", "Mari": "F",
    "Alona": "F", "Elsa": "F", "Dayanna": "F",
    "Asja": "F", "Mireia": "F", "Iuliia": "F",
    "Kristina": "F", "Jung": "F", "Lily": "F",
    "Omodunni": "F", "Beatriz": "F", "Sirya": "F",
    "Milica": "F", "Isabela": "F", "Milla": "F",
    "Daphne": "F", "Violante": "F", "Brigitta": "F",
    "Leone": "M", "Ranieri": "M", "Ayrton": "M",
    "Orlando": "M", "Martino": "M", "Rayan": "M",
    "Wolf": "M", "Gianmichele": "M", "Okan": "M",
    "Filipponeri": "M", "Romano": "M", "Felix": "M",
    "Dino": "M", "Biase": "M", "Lars": "M",
    "Haowen": "M", "Ikenna": "M", "Agostino": "M",
    "Loris": "M", "Attilio": "M", "Orazio": "M",
    "Alvaro": "M", "Gianfilippo": "M", "Celestino": "M",
    "Dimitrios": "M", "Jakob": "M", "Ezequiel": "M",
    "Stephen": "M",
    # French male
    "Alain": "M", "Alexandre": "M", "Antoine": "M", "Arnaud": "M", "Baptiste": "M",
    "Benoît": "M", "Bernard": "M", "Bertrand": "M", "Cédric": "M", "Charles": "M",
    "Christophe": "M", "Claude": "M", "Clément": "M", "Damien": "M", "Denis": "M",
    "Didier": "M", "Éric": "M", "Étienne": "M", "Fabien": "M", "Florian": "M",
    "Franck": "M", "François": "M", "Frédéric": "M", "Gauthier": "M", "Gérard": "M",
    "Grégoire": "M", "Guillaume": "M", "Henri": "M", "Hervé": "M", "Hugo": "M",
    "Jacques": "M", "Jean": "M", "Jérôme": "M", "Julien": "M", "Laurent": "M",
    "Léo": "M", "Louis": "M", "Luc": "M", "Lucas": "M", "Marc": "M",
    "Marcel": "M", "Martin": "M", "Mathieu": "M", "Matthieu": "M", "Maxime": "M",
    "Nicolas": "M", "Noël": "M", "Olivier": "M", "Pascal": "M", "Patrice": "M",
    "Paul": "M", "Philippe": "M", "Pierre": "M", "Raphaël": "M", "Rémi": "M",
    "René": "M", "Romain": "M", "Sébastien": "M", "Serge": "M", "Stéphane": "M",
    "Théo": "M", "Thibault": "M", "Thierry": "M", "Vincent": "M", "Xavier": "M",
    "Yves": "M",
}


# ── Male Italian names that end in -a (exceptions to the heuristic) ──
_MALE_ENDING_A: set[str] = {
    "Andrea", "Luca", "Mattia", "Nicola", "Elia", "Gianluca",
    "Battista", "Enea", "Cosma", "Evangelista",
}


def _infer_gender_from_prenom(name):
    """Return 'F' or 'M' from a first name, or None if unknown."""
    if pd.isna(name) or not str(name).strip():
        return None
    raw = str(name).strip()
    # Try full name first (handles "Annalaura", "Mariafrancesca", etc.)
    key_full = raw.split()[0]            # first token for compound "Francesco Pio"
    # capitalise for lookup
    key_cap = key_full.capitalize()
    result = _PRENOM_GENRE_MAP.get(key_cap)
    if result:
        return result
    # Try with accents stripped (common CSV artefacts)
    import unicodedata as _ud
    key_ascii = ''.join(
        c for c in _ud.normalize('NFD', key_cap) if _ud.category(c) != 'Mn'
    )
    result = _PRENOM_GENRE_MAP.get(key_ascii)
    if result:
        return result
    # ── Heuristic fallback based on Italian name endings ──
    token = key_ascii if key_ascii else key_cap
    if len(token) >= 2:
        if token in _MALE_ENDING_A:
            return "M"
        if token.endswith("a"):
            return "F"
        if token.endswith("o"):
            return "M"
        if token.endswith("e"):
            return "M"   # most -e endings in Italian are male (Simone, Daniele…)
        if token.endswith("i"):
            return "M"   # -i ending typically male (Giovanni → Gianni, etc.)
    # Last resort: return "M" to avoid leaving any unmatched
    return "M"


def process_profils_clients(df):
    """Process the client profiles export DataFrame."""
    df = df.copy()
    
    # Extract Sede from Centre
    if "Centre" in df.columns:
        df["Sede"] = df["Centre"].apply(extract_sede_from_centre)
    else:
        df["Sede"] = "???"
    
    # Parse Période de creation de l'élève for year/month
    periode_col = None
    for col_name in ["Période de creation de l'élève", "Période de création de l'élève"]:
        if col_name in df.columns:
            periode_col = col_name
            break
    
    if periode_col:
        parsed = df[periode_col].apply(parse_periode_field)
        df["Année_Creation"] = parsed.apply(lambda x: x[0])
        df["Mois_Creation"] = parsed.apply(lambda x: x[1])
    
    # Parse Date d'inscription
    if "Date d'inscription" in df.columns:
        df["Date_Inscription_parsed"] = pd.to_datetime(df["Date d'inscription"], format="%d/%m/%Y", errors="coerce")
        if "Année_Creation" not in df.columns:
            df["Année_Creation"] = df["Date_Inscription_parsed"].dt.year
            df["Mois_Creation"] = df["Date_Inscription_parsed"].dt.month
    
    # ── Infer gender from first names for rows missing genre ──
    if "Genre" in df.columns and "Prénom" in df.columns:
        _no_genre = df["Genre"].isna()
        if _no_genre.any():
            inferred = df.loc[_no_genre, "Prénom"].apply(_infer_gender_from_prenom)
            _found = inferred.notna()
            if _found.any():
                df.loc[_no_genre & _found.reindex(df.index, fill_value=False), "Genre"] = inferred[_found]

    # Clean Genre: map 'O' and NaN to 'Non spécifié'
    if "Genre" in df.columns:
        df["Genre"] = df["Genre"].fillna("Non spécifié")
        df["Genre"] = df["Genre"].replace({"O": "Non spécifié"})

    # Compute semester from month
    if "Mois_Creation" in df.columns:
        df["Semestre"] = df["Mois_Creation"].apply(lambda m: 1 if pd.notna(m) and 1 <= m <= 8 else (2 if pd.notna(m) else None))
    
    # Clean age data - filter outliers (age > 120 is bad data), keep age >= 3
    if "Age" in df.columns:
        df["Age_Clean"] = pd.to_numeric(df["Age"], errors="coerce")
        df.loc[df["Age_Clean"] > 120, "Age_Clean"] = pd.NA
        df.loc[df["Age_Clean"] < 0, "Age_Clean"] = pd.NA
        # Flag missing ages
        df["Age_Missing"] = df["Age_Clean"].isna()
        # Assign custom age bracket
        df["Tranche_Custom"] = df["Age_Clean"].apply(assign_custom_age_bracket)
    
    # Translate course types to French
    type_col = None
    for candidate in ["Type du dernier cours suivi", "Type de cours", "Type cours",
                       "Dernier type de cours", "Course Type"]:
        if candidate in df.columns:
            type_col = candidate
            break
    # Fallback: case-insensitive column search
    if type_col is None:
        for c in df.columns:
            if "type" in c.lower() and "cours" in c.lower():
                type_col = c
                break
    if type_col is not None:
        df["Type_Cours_FR"] = df[type_col].apply(translate_course_type)
    
    # Assign macro-level
    if "Niveau suivi" in df.columns:
        df["Macro_Niveau"] = df["Niveau suivi"].map(MACRO_LEVEL_MAP).fillna("Autre")
    
    # Clean Nb de cours
    if "Nb de cours" in df.columns:
        df["Nb_Cours_Client"] = pd.to_numeric(df["Nb de cours"], errors="coerce").fillna(0).astype(int)
    
    # ── RGPD: Strip PII columns — keep only analytical fields ──
    _SAFE_COLUMNS = {
        # Identifiers (anonymized)
        "Centre", "Sede",
        # Temporal
        "Année_Creation", "Mois_Creation", "Semestre",
        # Demographics (non-identifying aggregates)
        "Genre", "Age", "Age_Clean", "Age_Missing", "Tranche_Custom",
        "Tranche d'âge de l'élève", "Groupe_Age",
        "Nationalité",
        # Course info
        "Type_Cours_FR", "Macro_Niveau", "Niveau suivi",
        "Nb de cours", "Nb_Cours_Client",
        "Profil client",
        # Motivation & acquisition (no PII)
        "Motivation",
        "Catégorie socio-professionnelle",
        # Derived
        "Date_Inscription_parsed",
    }
    # Also keep any column matching "comment.*connu" (canal d'acquisition)
    keep_cols = [c for c in df.columns if c in _SAFE_COLUMNS
                 or ("comment" in c.lower() and "connu" in c.lower())]
    df = df[keep_cols]
    
    return df
