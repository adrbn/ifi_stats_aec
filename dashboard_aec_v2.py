"""
O.S.C.A.R. - Outil de Suivi des Cours et d'Analyse du Réseau v3.0
================================================================
Dashboard interactif pour l'analyse des données AEC
- 8+ fichiers: 4 sedi × 2 semestres (multi-années supporté)
- Auto-détection sede + semestre depuis le nom du fichier
- Vue globale IFI + détails par antenne
- Format final compatible avec "prova stats"
- Mode nuit / jour
- Assistant IA intégré
- Mode comparaisons (Sede, Semestre, Type, ANNÉE vs ANNÉE)
- Bilingue FR/IT
- NOUVEAUTÉS v2.9:
  - Panoramica multi-années avec tableau récapitulatif par année
  - Indicateurs colorés vert/rouge dans tableau Year vs Year
  - Fix marge graphiques évolution (barres plus coupées)
  - Aide contextuelle pour "Anno predefinito"
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from io import BytesIO
import zipfile
import re
import json
import sys
import shutil
from datetime import datetime
from pathlib import Path

# =====================================================

# RECENT FILES — persist uploads across app restarts
# =====================================================

def _oscar_data_dir() -> Path:
    """Return (and create) the OS-appropriate OSCAR data directory."""
    if getattr(sys, "frozen", False):
        # Running as packaged app — use OS config dir
        if sys.platform == "darwin":
            base = Path.home() / "Library" / "Application Support" / "OSCAR"
        elif sys.platform == "win32":
            base = Path(os.environ.get("APPDATA", Path.home())) / "OSCAR"
        else:
            base = Path.home() / ".config" / "oscar"
    else:
        # Dev mode — store next to the script
        base = Path(__file__).parent / ".oscar_data"
    data_dir = base / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def _recent_index_path() -> Path:
    return _oscar_data_dir().parent / "recent_sessions.json"


def load_recent_sessions() -> list:
    """Return list of recent session dicts (newest first), max 10."""
    idx = _recent_index_path()
    if not idx.exists():
        return []
    try:
        with open(idx, "r", encoding="utf-8") as f:
            sessions = json.load(f)
        # Remove sessions whose files have been deleted
        sessions = [s for s in sessions if Path(s["zip_path"]).exists()]
        return sessions[:10]
    except Exception:
        return []


def save_recent_session(stored_files: list) -> None:
    """
    Save current stored_files list to a ZIP on disk and update the index.
    stored_files: list of {'name': str, 'data': bytes}
    """
    if not stored_files:
        return
    try:
        data_dir = _oscar_data_dir()
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        # Build a human label from detected years in filenames
        years = set()
        for sf in stored_files:
            import re as _re
            m = _re.search(r"20\d{2}", sf["name"])
            if m:
                years.add(m.group())
        years_str = "-".join(sorted(years)) if years else ts[:8]
        label = f"Session {years_str}  ({len(stored_files)} fichiers)"
        zip_name = f"session_{ts}.zip"
        zip_path = data_dir / zip_name

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for sf in stored_files:
                zf.writestr(sf["name"], sf["data"])

        idx_path = _recent_index_path()
        sessions = load_recent_sessions()
        # Remove duplicate (same set of filenames)
        file_set = {sf["name"] for sf in stored_files}
        sessions = [s for s in sessions if set(s.get("files", [])) != file_set]
        sessions.insert(0, {
            "label": label,
            "zip_path": str(zip_path),
            "date": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "files": [sf["name"] for sf in stored_files],
            "count": len(stored_files),
        })
        sessions = sessions[:10]
        with open(idx_path, "w", encoding="utf-8") as f:
            json.dump(sessions, f, ensure_ascii=False, indent=2)
    except Exception:
        pass  # Never crash the app over recent-files bookkeeping


def restore_recent_session(session: dict) -> list:
    """Load stored_files list from a saved session ZIP."""
    result = []
    try:
        with zipfile.ZipFile(session["zip_path"], "r") as zf:
            for name in zf.namelist():
                result.append({"name": name, "data": zf.read(name)})
    except Exception:
        pass
    return result


def delete_recent_session(zip_path: str) -> None:
    """Remove a session from disk and from the index."""
    try:
        Path(zip_path).unlink(missing_ok=True)
    except Exception:
        pass
    idx_path = _recent_index_path()
    sessions = load_recent_sessions()
    sessions = [s for s in sessions if s["zip_path"] != zip_path]
    try:
        with open(idx_path, "w", encoding="utf-8") as f:
            json.dump(sessions, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


# =====================================================
# CONFIGURATION & MAPPING - 4-level structure
# =====================================================

# Mapping structure: Category → (Macro-catégorie, Sous-secteur, Secteur)
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

# Load additional mappings from CSV file if it exists
import os

# Configurable CSV path - can be overridden by environment variable for server deployment
CSV_MAPPING_PATH = os.environ.get(
    "AEC_CATEGORY_MAPPING_PATH",
    os.path.join(os.path.dirname(__file__), "data", "category_mapping.csv")
)

def get_csv_mapping_path():
    """Get the path to the category mapping CSV file"""
    return CSV_MAPPING_PATH

def load_csv_mappings():
    """Load additional category mappings from CSV file"""
    csv_path = get_csv_mapping_path()
    if os.path.exists(csv_path):
        try:
            df = pd.read_csv(csv_path)
            for _, row in df.iterrows():
                if all(col in df.columns for col in ["Catégorie", "Macro-catégorie", "Sous-secteur", "Secteur"]):
                    cat = row["Catégorie"]
                    CATEGORY_MAPPING[cat] = (row["Macro-catégorie"], row["Sous-secteur"], row["Secteur"])
        except Exception as e:
            print(f"Warning: Could not load category mapping CSV: {e}")

# Try to load CSV mappings (will override any duplicates from the hard-coded dict)
try:
    load_csv_mappings()
except:
    pass  # File might not exist yet, that's OK

# Order for each level
SECTOR_ORDER = ["PROGRAMMÉS", "PLATEFORMES", "ECOLES", "SUR MESURE", "SOCIÉTÉS", "AUTRE"]
SOUS_SECTEUR_ORDER = [
    "COLL ADULTES - GRL", "COLL ADULTES - SPE", "COLLECTIFS ADOS/ENFANTS", "Ateliers thématiques",
    "PLATEFORME - Autonomie", "PLATEFORME - Tuteur",
    "ECOLES - COURS", "ECOLES - Ateliers", "ECOLES - Classes Découverte", "ECOLES - Matinée", "ECOLES - PCTO",
    "SUR MESURE - GRL", "SUR MESURE - SPE",
    "ENTREPRISES - GRL", "ENTREPRISES - SPE", "AUTRE"
]
MACRO_CATEGORY_ORDER = [
    "COLL- GRL P ", "COLL- GRL D", "INTENSIFS P", "INTENSIFS D",
    "COLL- CONV", "COLL- THÉMATIQUES", "PREP EXAMENS", "COLL - SPECIFIQUE",
    "COLL- ADOS", "COURS COLL ENFANTS", "CAMPUS JEUNES", "ATELIERS ADOS/ ENFANTS", "ATELIERS ADULTES",
    "PLATEFORME AbcDelf - Autonomie", "PLATEFORME AbcDelf - Ecoles", "PLATEFORME AbcDelf - Tuteur",
    "PLATEFORME Madrid - Autonomie", "PLATEFORME Madrid -  Tuteur", "PLATEFORME - Autres",
    "ECOLES - COURS", "ECOLES - Ateliers", "ECOLES - Classes Découverte", "ECOLES - Matinée", "ECOLES - PCTO",
    "PART-FR GRL", "PART-FR SPE", "PART-SEMI COLL", "PART-ITA",
    "ENTREPRISES - GRL", "ENTREPRISES - SPE", "AUTRE"
]

# Antenna display order: Milan, Florence, Naples, Palermo
ANTENNA_ORDER = ["IFM", "IFF", "IFN", "IFP"]

SEDE_COLORS = {
    "IFM": "#FF8C00", "IFF": "#8B5CF6", "IFN": "#22C55E",
    "IFP": "#EF4444", "IFI": "#3B82F6"
}

# Geographic coordinates for Italian cities (for map)
SEDE_COORDS = {
    "IFM": {"lat": 45.4642, "lon": 9.1900, "city": "Milano"},
    "IFF": {"lat": 43.7696, "lon": 11.2558, "city": "Firenze"},
    "IFN": {"lat": 40.8518, "lon": 14.2681, "city": "Napoli"},
    "IFP": {"lat": 38.1157, "lon": 13.3615, "city": "Palermo"}
}

# Age group mapping from AEC
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
    "Enfants": "Enfants"
}

PERIOD_LABELS = {"sem1": "janv-juillet", "sem2": "sept-dec", "annuel": "année complète"}

# =====================================================
# TRANSLATIONS
# =====================================================
TRANSLATIONS = {
    "fr": {
        "title": "Institut français Italia",
        "subtitle": "Dashboard statistiques AEC - Analyse des cours de français",
        "mode": "Thème", "language": "Langue", "default_year": "Année par défaut",
        "load_files": "Charger les données", "sedi_semesters": "4 sedi × 2 semestres",
        "preloaded_files": "Données disponibles", "load_year": "Charger l'année", "or_upload_files": "Ou importez vos propres fichiers",
        "drag_files": "Glissez vos fichiers Excel", "files_detected": "Fichiers détectés",
        "expected_structure": "Structure attendue", "you_must_load": "Vous devez charger",
        "files": "fichiers", "sede": "Sede", "semester1": "Semestre 1", "semester2": "Semestre 2",
        "recommended_format": "Format de nom recommandé",
        "load_files_sidebar": "Chargez vos fichiers AEC dans la barre latérale pour commencer l'analyse.",
        "overview": "Analyse des cours", "inscriptions": "Inscriptions", "courses": "Cours",
        "student_hours": "Heures-élèves", "planned_hours": "Heures prévues", "revenue": "Recettes", "students_per_course": "Élèves/cours",
        "tab_prova_stats": "Synthèse", "tab_by_sede": "Par antenne",
        "tab_by_sector": "Par secteurs", "tab_by_sous_secteur": "Par sous-secteurs", "tab_by_macro_category": "Par macro-catégories", "tab_by_category": "Par catégories", "tab_comparisons": "Comparaisons",
        "tab_graphs": "Graphiques", "tab_ai": "Aide rapide", "tab_export": "Export", "tab_config": "Configuration",
        "filter_by_sede": "Filtrer par antenne", "filter_by_period": "Filtrer par période", "filter_by_sector": "Filtrer par secteur",
        "all": "Tous", "ifi_totals": "Totaux IFI (toutes sedi)",
        "analysis_by_sede": "Analyse par antenne", "inscriptions_by_sede": "Inscriptions par antenne",
        "distribution": "Répartition des inscriptions", "detail_by_sede": "Détail par antenne",
        "analysis_by_sector": "Analyse par secteurs", "inscriptions_by_sector": "Inscriptions par secteur", "ifi_all_antennas": "IFI - total toutes antennes confondues", "details_by_antenna": "Détails par antenne",
        "analysis_by_sous_secteur": "Analyse par sous-secteurs", "inscriptions_by_sous_secteur": "Inscriptions par sous-secteur",
        "analysis_by_macro_category": "Analyse par macro-catégories", "inscriptions_by_macro_category": "Inscriptions par macro-catégorie",
        "courses_by_sector": "Nb de cours par secteur",
        "analysis_by_category": "Analyse par catégories", "inscriptions_by_category": "Inscriptions par catégorie",
        "courses_by_category": "Nb de cours par catégorie", "top_categories": "Top catégories",
        "heatmap_title": "Heatmap", "heatmap_subtitle": "Catégories par secteur (par antenne)", "comparison_mode": "Mode comparaisons",
        "category_mapping_title": "Correspondances catégories → secteurs", "show_mapping": "Afficher le tableau de correspondances",
        "unlinked_categories": "Catégories non rattachées", "unlinked_cat_warning": "Les catégories suivantes ne sont pas rattachées dans le tableau de correspondance",
        "assign_macro_category": "Assigner une macro-catégorie", "create_new_macro_category": "Créer une nouvelle macro-catégorie",
        "filter_by_category": "Filtrer par catégorie", "category_view": "Vue par catégorie",
        "filter_by_sous_secteur": "Filtrer par sous-secteur", "filter_by_macro_category": "Filtrer par macro-catégorie",
        "multi_selection": "Sélection multiple", "comparison_by_antenna": "Comparaison par antenne",
        "comparison_type": "Type de comparaison", "sede_vs_sede": "Antenne vs antenne",
        "semester_vs_semester": "Semestre vs semestre", "sector_vs_sector": "Secteur vs secteur",
        "first_sede": "Première antenne", "second_sede": "Deuxième antenne",
        "first_sector": "Premier secteur", "second_sector": "Deuxième secteur",
        "comparison_by_sede": "Comparaison par antenne",
        "load_both_semesters": "Chargez les données des deux semestres pour comparer.",
        "graphs": "Graphiques", "flow_sede_sector": "Flux : antenne → secteur",
        "inscr_by_sector_sede": "Inscriptions par secteur et antenne", "treemap_title": "Répartition hiérarchique",
        "sunburst_title": "Vue en rayons de soleil", "ai_assistant": "Aide rapide",
        "auto_insights": "Analyses automatiques", "ask_question": "Posez une question",
        "question_placeholder": "Ex : Quelle est la meilleure antenne ? Comparer IFM et IFF...",
        "suggestions": "Suggestions", "export_data": "Exporter les données", "format": "Format",
        "excel_multi": "Excel (multi-feuilles)", "download_excel": "Télécharger Excel",
        "download_csv": "Télécharger CSV", "dataset_summary": "Résumé du dataset",
        "files_loaded": "Fichiers chargés", "total_rows": "Lignes totales", "periods": "Périodes",
        "footer_mode": "Thème", "night": "sombre", "day": "clair",
        "dominates_with": "domine avec", "of_inscriptions": "des inscriptions",
        "avg_revenue_per_inscr": "Revenu moyen par inscription",
        "sem1_beats_sem2": "Le semestre 1 surpasse le S2 de",
        "sem2_beats_sem1": "Le semestre 2 surpasse le S1 de",
        "dominant_sector": "Secteur dominant", "total_inscriptions": "Total des inscriptions",
        "by_sede": "Par antenne", "total_revenue": "Recettes totales", "best_sede": "Meilleure antenne",
        "possible_questions": "Questions possibles", "q_total_inscr": "Combien d'inscriptions au total ?",
        "q_revenue": "Quelles sont les recettes ?", "q_best_sede": "Quelle est la meilleure antenne ?",
        "q_compare": "Comparer IFM et IFF", "q_about": "Parle-moi de IFN",
        "graph_navigation": "Navigation graphiques", "prev_graph": "< Précédent", "next_graph": "Suivant >",
        "graph_counter": "Graphique", "of": "sur",
        # New translations for v2.8 features
        "year_comparison": "Comparaison annuelle", "yoy_variation": "Variation A/A",
        "year_vs_year": "Année vs année", "first_year": "Première année", "second_year": "Deuxième année",
        "variation": "Variation", "evolution": "Évolution", "profitability": "Rentabilité",
        "revenue_per_inscr": "€/inscription", "most_profitable": "Plus rentables",
        "least_profitable": "Moins rentables", "profitability_by_sector": "Rentabilité par secteur",
        "profitability_by_sede": "Rentabilité par antenne", "age_groups": "Tranches d'âge",
        "filter_by_age": "Filtrer par âge", "adults": "Adultes", "teens": "Ados", "children": "Enfants",
        "age_distribution": "Répartition par âge", "italy_map": "Carte d'Italie",
        "map_by_inscriptions": "Inscriptions par ville", "tab_yoy": "Par année",
        "tab_profitability": "Rentabilité", "tab_map": "Carte", "tab_evolutions": "Évolutions",
        "evolution_title": "Évolution multi-indicateurs", "evolution_ifi": "IFI - Total national", "evolution_by_antenna": "Par antenne",
        "increase": "hausse", "decrease": "baisse", "stable": "stable",
        "multi_year_evolution": "Évolution pluriannuelle", "need_multiple_years": "Chargez les données de plusieurs années pour voir l'évolution.",
        "arpi": "ARPI (€/inscr)", "total_years": "Années", "load_more_years": "Chargez plus d'années pour comparer",
        "default_year_help": "Utilisé si l'année n'est pas détectable dans le nom de fichier",
        "total_all_years": "TOTAL (toutes années)", "breakdown_by_year": "Répartition par année",
        "multi_year_warning": "Plusieurs années chargées", "showing_combined": "Données combinées de",
        "welcome": "Bienvenue sur O.S.C.A.R.", "welcome_subtitle": "Outil de suivi des cours et d'analyse du réseau — Institut français Italia",
        "quick_start": "Démarrage rapide", "upload_here": "Déposez vos fichiers Excel ici",
        "features": "Fonctionnalités", "feature_1": "Analyse des cours par catégorie, secteur et macro-catégorie",
        "feature_2": "Analyse des fiches de cours (niveaux, inscriptions, tendances)",
        "feature_3": "Analyse des profils clients (démographie, nationalités, motivation)",
        "feature_4": "Analyse du catalogue produits (types, tarifs, par antenne)",
        "feature_5": "Comparaisons inter-annuelles et inter-antennes",
        "feature_6": "Carte d'Italie, rentabilité (ARPI) et export Excel",
        "feature_7": "Aide rapide intégrée pour l'analyse des données",
        "how_to_export": "Obtenir les fichiers depuis AEC",
        "export_steps": "Utilisez le script d'export pour générer automatiquement les fichiers depuis AEC.",
        "export_script_link": "Télécharger le script d'export",
        "supported_exports": "Exports supportés",
        "export_type_1": "Rapport par catégories (.xlsx) — 4 antennes × 2 semestres",
        "export_type_2": "Fiches de cours (.csv) — export global",
        "export_type_3": "Profils clients (.xlsx) — par antenne",
        "export_type_4": "Catalogue produits (.xlsx) — par antenne",
        "need_help": "Besoin d'aide ?", "contact_support": "Contactez le support",
        "filter_years": "Sélectionner les années", "showing_years": "Années affichées",
        "showing_all_years": "Toutes les années",
        "view_mode": "Vue", "by_sede": "Par antenne", "year": "Année",
        "calculation_details": "Détails des calculs",
        "pct_new": "% nouveaux", "pct_returning": "% réinscrits",
        "choose_indicator": "Choisissez un indicateur", "global_view": "Vue globale",
        "new_students": "Nouveaux inscrits", "returning_students": "Réinscrits",
        "ifi_total": "IFI Total",
        # Course fiches export
        "tab_fiches_synthese": "Synthèse",
        "tab_fiches_niveaux": "Par niveau",
        "tab_fiches_inscriptions": "Inscriptions",
        "fiches_cours_loaded": "Export fiches de cours détecté",
        "total_courses_fiches": "Nb total de cours",
        "online_courses": "Cours en ligne",
        "avg_students_per_course": "Moy. élèves/cours",
        "total_hours_fiches": "Total heures",
        "total_sales": "Total ventes",
        "analysis_by_level": "Analyse par niveau",
        "monthly_inscriptions": "Inscriptions mensuelles",
        "new_vs_returning": "Nouveaux vs Réinscrits",
        "semester_filter": "Filtrer par semestre",
        "courses_by_level": "Cours par niveau",
        "students_by_level": "Élèves par niveau",
        "hours_by_level": "Heures par niveau",
        "monthly_evolution": "Évolution mensuelle",
        "fill_rate": "Taux de remplissage",
        "by_category_aec": "Par catégorie AEC",
        "by_semester": "Par semestre",
        "filters": "Filtres",
        "fiches_cours_section": "Analyse des fiches de cours",
        # Profils clients
        "profils_section": "Analyse des profils",
        "profils_loaded": "Export profils clients détecté",
        "tab_profils_synthese": "Synthèse",
        "tab_profils_demo": "Démographie",
        "tab_profils_nationalites": "Nationalités",
        "tab_profils_motivation": "Motivation & acquisition",
        "profils_nb_clients": "Nb clients",
        "profils_nb_antennes": "Nb antennes",
        "profils_pct_f": "% Femmes",
        "profils_pct_m": "% Hommes",
        "profils_pct_ns": "% Non spécifié",
        "profils_avg_age": "Âge moyen",
        "profils_median_age": "Âge médian",
        "profils_min_age": "Âge min",
        "profils_max_age": "Âge max",
        "profils_age_group": "Tranche d'âge",
        "profils_age_groups": "Tranches d'âge",
        "profils_age_histogram": "Distribution des âges",
        "profils_age_by_sede": "Âge par antenne",
        "profils_age": "Âge",
        "profils_gender": "Genre",
        "profils_gender_by_sede": "Genre par antenne",
        "profils_by_level": "Par niveau suivi",
        "profils_by_course_type": "Par type de cours",
        "profils_course_type": "Type de cours",
        "profils_clients_by_sede": "Clients par antenne",
        "profils_nationalities": "Nationalités",
        "profils_nb_nationalities": "Nb nationalités",
        "profils_top_nationality": "Nationalité principale",
        "profils_top_nat_pct": "Part (%)",
        "profils_others": "Autres nationalités",
        "profils_not_specified": "Non indiquée",
        "profils_demographics": "Démographie",
        "profils_motivation_acq": "Motivation & Canal d'acquisition",
        "profils_motivation": "Motivation",
        "profils_motivation_by_antenna": "Motivation par antenne",
        "profils_acquisition": "Canal d'acquisition",
        "profils_acquisition_by_antenna": "Top 5 Canal d'acquisition par antenne",
        "profils_csp": "Catégorie socio-professionnelle",
        "profils_filter_period": "Filtrer par période",
        "profils_all_periods": "Toutes les périodes",
        "profils_semester1": "Semestre 1",
        "profils_semester2": "Semestre 2",
        "profils_age_overlay": "Distribution des âges par antenne",
        "profils_view_sum": "Somme",
        "profils_view_compare": "Comparaison",
        "profils_levels_progressive": "Niveaux (ordre progressif)",
        "profils_macro_levels": "Macro-niveaux",
        "profils_nat_by_antenna": "Nationalités par antenne",
        "profils_nat_map": "Carte des nationalités",
        "profils_student_type": "Type d'élève",
        "profils_student_types": "Types d'élèves",
        "profils_age_groups_by_antenna": "Tranches d'âge par antenne",
        # Produits
        "produits_section": "Analyse du catalogue produits",
        "produits_loaded": "Export produits détecté",
        "tab_produits_catalogue": "Catalogue",
        "tab_produits_types": "Par type",
        "tab_produits_tarifs": "Tarifs",
        "produits_nb_products": "Nb produits",
        "produits_nb_types": "Nb types",
        "produits_nb_active": "Produits actifs",
        "produits_avg_price": "Prix moyen",
        "produits_total_hours": "Total heures",
        "produits_total_capacity": "Capacité totale",
        "produits_by_sede": "Produits par antenne",
        "produits_full_catalog": "Catalogue complet",
        "produits_filter_type": "Type de produit",
        "produits_status": "Statut",
        "produits_active_only": "Actifs uniquement",
        "produits_inactive_only": "Inactifs uniquement",
        "produits_analysis_by_type": "Analyse par type de produit",
        "produits_type_by_sede": "Type × Sede",
        "produits_price_comparison": "Comparaison des prix par type",
        "produits_pricing_analysis": "Analyse tarifaire",
        "produits_price_distribution": "Distribution des prix",
        "produits_price_stats": "Statistiques de prix par antenne",
        "produits_reduced_tariff": "Tarif réduit",
        "produits_nb_with_reduction": "Produits avec réduction",
        "produits_avg_reduction": "Réduction moyenne",
        "produits_max_reduction": "Réduction max",
        "produits_price_vs_reduced": "Prix vs Tarif réduit",
        "produits_member_price": "Prix membre",
        "produits_nb_member_price": "Avec prix membre",
        "produits_avg_member_advantage": "Avantage membre moyen",
        "produits_hours_analysis": "Analyse des heures",
        "produits_price_per_hour": "Prix moyen par heure",
    },
}

def t(key):
    """Return French label for a given key."""
    return TRANSLATIONS['fr'].get(key, key)

# =====================================================
# PAGE CONFIG
# =====================================================
st.set_page_config(
    page_title="O.S.C.A.R.",
    page_icon=os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon_curves.png"),
    layout="wide",
    initial_sidebar_state="expanded"
)


# =====================================================
# AUTHENTICATION
# =====================================================
import hashlib

def _hash_pw(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()

def _load_users() -> dict:
    """Charge les comptes depuis st.secrets (Streamlit Cloud) ou fallback local."""
    users = {}
    try:
        # Lecture depuis st.secrets (TOML dans Streamlit Cloud > Settings > Secrets)
        # Format attendu dans le TOML:
        #   [users.adrien]
        #   name = "Adrien"
        #   password = "oscar2026"
        #
        #   [users.stephanie]
        #   name = "Stéphanie Sauvignon"
        #   password = "ifi2026"
        secrets_users = st.secrets.get("users", {})
        for uid, udata in secrets_users.items():
            users[uid] = {
                "name": udata["name"],
                "password_hash": _hash_pw(udata["password"]),
            }
        if users:
            return users
    except Exception:
        pass

    # Fallback local (dev uniquement — hashes statiques, pas de mots de passe en clair)
    users = {
        "adrien": {
            "name": "Adrien",
            "password_hash": "d610dd4971f71ed75688f7014046f69b7f3bdcec898ca3eb7d4d821dff9b789f",
        },
        "stephanie": {
            "name": "Stéphanie Sauvignon",
            "password_hash": "88f01b87632b0f347b5ec38d98aada648828f9159f452b513a69cf6ba758efa8",
        },
    }
    return users

USERS = _load_users()

# --- Persistent login via query params (survives page refresh) ---
import hmac as _hmac_mod

def _get_persist_secret() -> bytes:
    """Get HMAC secret from st.secrets or fallback."""
    try:
        return st.secrets.get("hmac_secret", "oscar_aec_persist_2026").encode()
    except Exception:
        return b"oscar_aec_persist_2026"

_PERSIST_SECRET = _get_persist_secret()

def _make_login_token(username):
    return _hmac_mod.new(_PERSIST_SECRET, username.encode(), hashlib.sha256).hexdigest()[:20]

def _check_persistent_login():
    """Restore session from URL query params if valid token present."""
    params = st.query_params
    u = params.get("u", "")
    tk = params.get("t", "")
    if u and tk and _hmac_mod.compare_digest(_make_login_token(u), tk):
        # Find the user's display name
        user = USERS.get(u)
        display_name = user["name"] if user else u
        st.session_state.authenticated = True
        st.session_state.user_name = display_name
        return True
    return False

def _set_persistent_login(username):
    st.query_params["u"] = username
    st.query_params["t"] = _make_login_token(username)

def _clear_persistent_login():
    st.query_params.clear()

if "authenticated" not in st.session_state:
    # Desktop mode: la licence a déjà validé l'accès — on bypass le login
    if os.environ.get("OSCAR_DESKTOP_MODE") == "1":
        st.session_state.authenticated = True
        st.session_state.user_name = os.environ.get("OSCAR_LICENSE_CUSTOMER", "OSCAR")
    else:
        # Try restoring from persistent login (query params)
        if not _check_persistent_login():
            st.session_state.authenticated = False
if "user_name" not in st.session_state:
    st.session_state.user_name = ""

def _login_page():
    """Affiche la page de connexion."""
    # Hide sidebar completely during login.
    # This CSS only exists in the login render; after st.rerun() on successful
    # login, _login_page() is never called so this CSS simply doesn't exist.
    st.markdown("""
    <style>
        [data-testid="stSidebar"] { display: none !important; }
        [data-testid="stSidebarCollapsedControl"] { display: none !important; }
        #oscar-sidebar-btn { display: none !important; }
    </style>
    """, unsafe_allow_html=True)

    # Logo
    import os as _os_login
    _lp = _os_login.path.join(_os_login.path.dirname(_os_login.path.abspath(__file__)), "IFI_noir_logo.png")
    if _os_login.path.exists(_lp):
        import base64 as _b64_login
        with open(_lp, "rb") as _fl:
            _lb = _b64_login.b64encode(_fl.read()).decode()
        st.markdown(f'<div style="text-align:center;margin-top:6vh;"><img src="data:image/png;base64,{_lb}" style="width:120px;"></div>', unsafe_allow_html=True)

    st.markdown('<div style="font-size:2rem;font-weight:800;letter-spacing:0.15em;color:#1a1a1a;text-align:center;">OSCAR</div>', unsafe_allow_html=True)
    st.markdown('<div style="font-size:0.75rem;color:#64748b;text-align:center;margin-bottom:2rem;">Outil de Suivi des Cours et d\'Analyse du Réseau</div>', unsafe_allow_html=True)

    col_l, col_form, col_r = st.columns([1, 2, 1])
    with col_form:
        with st.form("login_form"):
            username = st.text_input("Identifiant", placeholder="ex: adrien")
            password = st.text_input("Mot de passe", type="password", placeholder="••••••••")
            submitted = st.form_submit_button("Se connecter", use_container_width=True, type="primary")

            if submitted:
                user = USERS.get(username.strip().lower())
                if user and user["password_hash"] == _hash_pw(password):
                    st.session_state.authenticated = True
                    st.session_state.user_name = user["name"]
                    _set_persistent_login(username.strip().lower())
                    st.rerun()
                else:
                    st.error("Identifiant ou mot de passe incorrect.")

    st.markdown('<div style="text-align:center;color:#94a3b8;font-size:0.7rem;margin-top:2rem;">Accès réservé au personnel autorisé</div>', unsafe_allow_html=True)

# Afficher la page login si non authentifié
if not st.session_state.authenticated:
    _login_page()
    st.stop()

# =====================================================
# SESSION STATE INITIALIZATION
# =====================================================
if 'graph_index' not in st.session_state:
    st.session_state.graph_index = 0
# Store processed data in session state to prevent loss on theme/language toggle
if 'processed_data' not in st.session_state:
    st.session_state.processed_data = None
if 'file_info' not in st.session_state:
    st.session_state.file_info = None
if 'course_fiches_data' not in st.session_state:
    st.session_state.course_fiches_data = None
if 'profils_clients_data' not in st.session_state:
    st.session_state.profils_clients_data = None
if 'profils_file_info' not in st.session_state:
    st.session_state.profils_file_info = None
if 'produits_data' not in st.session_state:
    st.session_state.produits_data = None
if 'produits_file_info' not in st.session_state:
    st.session_state.produits_file_info = None
if 'fiches_file_info' not in st.session_state:
    st.session_state.fiches_file_info = None

# =====================================================
# CUSTOM CSS
# =====================================================
def get_css():
    return """
    <style>
        /* Pin sidebar content to top */
        [data-testid="stSidebar"] > div:first-child {
            padding-top: 1rem !important;
        }
        /* Add more top padding to push content down */
        .block-container {
            padding-top: 2.5rem !important;
        }
        .stApp > header {
            background: transparent !important;
        }
        
        /* Fix heading truncation - IMPORTANT */
        h1, h2, h3, .main-header {
            white-space: normal !important;
            overflow: visible !important;
            text-overflow: unset !important;
            word-wrap: break-word !important;
        }
        
        /* Fix metric delta to display inline */
        [data-testid="stMetric"] {
            display: flex !important;
            flex-direction: column !important;
        }
        [data-testid="stMetric"] > div {
            display: flex !important;
            flex-wrap: nowrap !important;
            align-items: baseline !important;
            gap: 8px !important;
        }
        [data-testid="stMetricDelta"] {
            position: relative !important;
            margin-left: auto !important;
        }
        
        .main-header {
            font-size: 2.5rem; font-weight: bold; color: #1E3A5F;
            text-align: center; margin-bottom: 0.5rem;
        }
        .sub-header {
            font-size: 1.2rem; color: #666;
            text-align: center; margin-bottom: 1rem;
        }
        .insight-card {
            background: #f0f9ff; 
            border-left: 4px solid #60a5fa;
            padding: 1rem; margin: 0.5rem 0; border-radius: 0 10px 10px 0; color: #1e293b;
        }
        .insight-card strong { color: #3b82f6; }
        .ai-box {
            background: #f0fdfa; 
            border: 1px solid #a7f3d0;
            border-radius: 10px; padding: 1rem; margin: 1rem 0;
        }
        .graph-counter {
            color: #3b82f6; font-size: 1.2rem; font-weight: bold; text-align: center;
        }
        
        /* Metric cards - clean style */
        .stMetric {
            background: #f8fafc !important;
            border-radius: 12px !important;
            border: 1px solid #e2e8f0 !important;
            padding: 1rem !important;
        }
        
        /* TABS - clean style */
        .stTabs [data-baseweb="tab-list"] {
            background: #f8fafc !important;
            border-radius: 12px;
            padding: 8px;
            gap: 4px !important;
        }
        .stTabs [data-baseweb="tab"] {
            padding: 10px 16px !important;
            font-size: 13px !important;
            white-space: nowrap !important;
            width: auto !important;
            min-width: auto !important;
            border-radius: 8px !important;
            transition: all 0.2s ease !important;
            flex-shrink: 0 !important;
        }
        .stTabs [data-baseweb="tab-list"] button {
            overflow: visible !important;
        }
        .stTabs [aria-selected="true"] {
            background: #3b82f6 !important;
            border-radius: 8px !important;
            color: white !important;
            font-weight: 600 !important;
        }
        .stTabs [aria-selected="false"] {
            background: transparent !important;
            color: #475569 !important;
        }
        .stTabs [aria-selected="false"]:hover {
            background: #e0f2fe !important;
            color: #1e40af !important;
        }
        
        /* Year buttons */
        .stButton > button[kind="primary"] {
            background: #3b82f6 !important;
            border: none !important;
            color: white !important;
        }
        .stButton > button[kind="secondary"] {
            background: #f1f5f9 !important;
            border: 1px solid #cbd5e1 !important;
            color: #475569 !important;
        }
        
        /* Download button */
        .stDownloadButton > button {
            background: #4ade80 !important;
            color: #166534 !important;
            border: none !important;
        }

        /* Compact multiselect tags */
        .stMultiSelect [data-baseweb="tag"] {
            font-size: 0.75rem !important;
            padding: 2px 6px !important;
            height: auto !important;
            line-height: 1.4 !important;
            margin: 1px 2px !important;
            border-radius: 4px !important;
        }
        .stMultiSelect [data-baseweb="tag"] span {
            font-size: 0.75rem !important;
        }
        .stMultiSelect [data-baseweb="tag"] svg {
            width: 12px !important;
            height: 12px !important;
        }
        div[data-baseweb="select"] > div {
            flex-wrap: wrap !important;
            max-height: 38px !important;
            overflow-y: auto !important;
        }
        
        /* ── Hide Streamlit chrome (toolbar, deploy, rerun, hamburger menu) ── */
        [data-testid="stToolbar"],
        [data-testid="stDecoration"],
        [data-testid="stStatusWidget"],
        .stDeployButton,
        #MainMenu,
        footer {
            display: none !important;
            visibility: hidden !important;
        }

        /* ── Force sidebar collapse/expand button to ALWAYS be visible ── */
        [data-testid="stSidebarCollapsedControl"] {
            display: flex !important;
            visibility: visible !important;
            opacity: 1 !important;
            position: fixed !important;
            top: 0.5rem !important;
            left: 0.5rem !important;
            z-index: 999999 !important;
            background: white !important;
            border-radius: 6px !important;
            box-shadow: 0 1px 4px rgba(0,0,0,0.15) !important;
        }
        /* Also try Streamlit 1.40+ selector names */
        [data-testid="stSidebarNavToggle"],
        [data-testid="collapsedControl"] {
            display: flex !important;
            visibility: visible !important;
            opacity: 1 !important;
            position: fixed !important;
            top: 0.5rem !important;
            left: 0.5rem !important;
            z-index: 999999 !important;
        }
        /* Keep the header wrapper visible so the collapse control can render */
        [data-testid="stHeader"] {
            visibility: visible !important;
            pointer-events: auto !important;
            z-index: 999998 !important;
        }
        /* Ensure the collapse button itself is styled and clickable */
        [data-testid="stSidebarCollapsedControl"] button,
        [data-testid="stSidebarNavToggle"] button,
        [data-testid="collapsedControl"] button {
            visibility: visible !important;
            opacity: 1 !important;
            pointer-events: auto !important;
        }
        /* Remove the top padding left by the hidden header */
        .block-container {
            padding-top: 1.5rem !important;
        }

        /* ── Custom sidebar toggle fallback (JS-injected #oscar-sidebar-btn) ── */
        #oscar-sidebar-btn {
            position: fixed !important;
            top: 0.6rem;
            left: 0.6rem;
            z-index: 9999999;
            width: 36px;
            height: 36px;
            border-radius: 8px;
            border: 1px solid #cbd5e1;
            background: white;
            color: #334155;
            font-size: 1.2rem;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 2px 6px rgba(0,0,0,0.12);
            transition: background 0.15s, box-shadow 0.15s;
        }
        #oscar-sidebar-btn:hover {
            background: #f1f5f9;
            box-shadow: 0 3px 8px rgba(0,0,0,0.18);
        }

        /* ── Print / PDF export styles ── */
        @media print {
            /* Hide Streamlit chrome & interactive controls */
            [data-testid="stSidebar"],
            [data-testid="stHeader"],
            [data-testid="stToolbar"],
            [data-testid="stDecoration"],
            header, footer,
            .stDeployButton,
            #MainMenu,
            .no-print,
            .print-btn-fixed,
            button,
            .stButton,
            .stDownloadButton,
            .stFileUploader,
            .stRadio,
            .stMultiSelect,
            .stSelectbox,
            [data-testid="stExpander"] summary,
            /* Hide ALL iframes (plotly charts, components) – they render blank */
            iframe {
                display: none !important;
            }

            /* Full-width layout – remove sidebar gap */
            .main .block-container {
                max-width: 100% !important;
                padding: 0.3cm 0.5cm !important;
                margin: 0 !important;
            }
            [data-testid="stAppViewContainer"] {
                margin-left: 0 !important;
            }
            .main {
                margin-left: 0 !important;
                padding-left: 0 !important;
            }

            /* Reduce spacing between elements */
            .element-container {
                margin-bottom: 0.2cm !important;
                padding: 0 !important;
            }
            [data-testid="stVerticalBlock"] > div {
                margin-bottom: 0.1cm !important;
            }

            /* Avoid page-breaks inside key blocks */
            .element-container,
            [data-testid="stMetric"],
            .stDataFrame {
                overflow: visible !important;
                break-inside: avoid !important;
                page-break-inside: avoid !important;
            }

            /* Section headings stay with content */
            h1, h2, h3 {
                break-after: avoid !important;
                page-break-after: avoid !important;
                margin-top: 0.3cm !important;
                margin-bottom: 0.1cm !important;
            }

            /* Tables – compact */
            .stDataFrame {
                break-inside: avoid !important;
                page-break-inside: avoid !important;
                font-size: 8pt !important;
            }
            table {
                font-size: 7pt !important;
            }

            /* Metrics row */
            [data-testid="stHorizontalBlock"] {
                break-inside: avoid !important;
                page-break-inside: avoid !important;
            }

            /* Tabs – show all tab content, hide tab bar */
            .stTabs [data-baseweb="tab-panel"] {
                display: block !important;
                visibility: visible !important;
                height: auto !important;
                overflow: visible !important;
            }
            .stTabs [data-baseweb="tab-list"] {
                display: none !important;
            }

            /* Page setup */
            @page {
                size: A4 landscape;
                margin: 0.8cm;
            }

            /* Force backgrounds & colours */
            * {
                -webkit-print-color-adjust: exact !important;
                print-color-adjust: exact !important;
                color-adjust: exact !important;
            }

            /* Expander content: force open */
            [data-testid="stExpander"] details {
                open: true !important;
            }
            [data-testid="stExpander"] [data-testid="stExpanderDetails"] {
                display: block !important;
                visibility: visible !important;
            }

            /* Plotly static-image fallbacks (if any img in charts) */
            .js-plotly-plot img,
            .plotly img {
                max-width: 100% !important;
                height: auto !important;
            }
        }
    </style>
    """

st.markdown(get_css(), unsafe_allow_html=True)

# ── Fixed print button (top-right corner) ──
import streamlit.components.v1 as _stc
_stc.html("""
<div class="print-btn-fixed" style="
    position:fixed; top:12px; right:70px; z-index:999999;
">
    <button onclick="window.parent.print()" title="Exporter PDF / Imprimer" style="
        background:rgba(59,130,246,0.85); color:white; border:none; border-radius:6px;
        padding:5px 10px; font-size:12px; cursor:pointer; display:flex;
        align-items:center; gap:4px; font-family:sans-serif;
        box-shadow:0 1px 4px rgba(0,0,0,0.15); backdrop-filter:blur(4px);
    ">
        <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" fill="currentColor" viewBox="0 0 16 16">
            <path d="M5 1a2 2 0 0 0-2 2v2H2a2 2 0 0 0-2 2v3a2 2 0 0 0 2 2h1v1a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2v-1h1a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-1V3a2 2 0 0 0-2-2H5zM4 3a1 1 0 0 1 1-1h6a1 1 0 0 1 1 1v2H4V3zm1 10a1 1 0 0 1-1-1V9h8v3a1 1 0 0 1-1 1H5z"/>
        </svg>
        PDF
    </button>
</div>
""", height=0)

# ── Custom sidebar toggle button (JS fallback for collapsed sidebar) ──
_stc.html("""
<script>
(function() {
    var doc = window.parent.document;

    // Remove any previously injected button (Streamlit re-runs can duplicate)
    var existing = doc.getElementById('oscar-sidebar-btn');
    if (existing) existing.remove();

    // Create the floating hamburger button
    var btn = doc.createElement('button');
    btn.id = 'oscar-sidebar-btn';
    btn.innerHTML = '&#9776;';
    btn.title = 'Ouvrir / Fermer la sidebar';

    btn.style.cssText = 'position:fixed;top:0.6rem;left:0.6rem;z-index:9999999;' +
        'width:36px;height:36px;border-radius:8px;border:1px solid #cbd5e1;' +
        'background:white;color:#334155;font-size:1.2rem;cursor:pointer;' +
        'display:none;align-items:center;justify-content:center;' +
        'box-shadow:0 2px 6px rgba(0,0,0,0.12);transition:background 0.15s;';

    // Helper: simulate a real user click (mousedown+mouseup+click) for React compat
    function realClick(el) {
        ['mousedown', 'mouseup', 'click'].forEach(function(evtType) {
            el.dispatchEvent(new MouseEvent(evtType, {
                view: window.parent, bubbles: true, cancelable: true
            }));
        });
    }

    // Helper: walk ancestors to check if element lives within a sidebar control
    function isInsideSidebarCtrl(el) {
        var p = el;
        while (p) {
            var tid = (p.getAttribute && p.getAttribute('data-testid')) || '';
            if (/sidebar|collapse/i.test(tid)) return true;
            p = p.parentElement;
        }
        return false;
    }

    btn.addEventListener('click', function(e) {
        e.preventDefault();
        e.stopPropagation();

        // ── Strategy 1: known selectors with full event simulation ──
        var selectors = [
            '[data-testid="stSidebarCollapsedControl"] button',
            '[data-testid="collapsedControl"] button',
            '[data-testid="stSidebarNavToggle"] button',
            'button[aria-label*="sidebar" i]',
            'button[aria-label*="Sidebar" i]',
            'button[aria-label*="navigation" i]',
            'button[aria-label*="menu" i]',
            'button[aria-label*="expand" i]',
            'button[aria-label*="collapse" i]',
        ];
        for (var i = 0; i < selectors.length; i++) {
            try {
                var el = doc.querySelector(selectors[i]);
                if (el) { realClick(el); return; }
            } catch(ex) {}
        }

        // ── Strategy 2: scan ALL buttons for one inside a sidebar control ──
        var allBtns = doc.querySelectorAll('button');
        for (var j = 0; j < allBtns.length; j++) {
            if (isInsideSidebarCtrl(allBtns[j])) {
                realClick(allBtns[j]); return;
            }
        }

        // ── Strategy 3: find the close button INSIDE the expanded sidebar ──
        // (grab the button that collapses, then look for its expand counterpart)
        var closeBtn = doc.querySelector('[data-testid="stSidebar"] button[aria-label]');
        if (closeBtn) {
            realClick(closeBtn); return;
        }

        // ── Strategy 4: brute-force CSS to show the sidebar ──
        var sidebar = doc.querySelector('[data-testid="stSidebar"]');
        if (sidebar) {
            sidebar.setAttribute('aria-expanded', 'true');
            // Walk up to find the section/container that clips
            var target = sidebar;
            for (var k = 0; k < 4; k++) {
                target.style.setProperty('width', '21rem', 'important');
                target.style.setProperty('min-width', '21rem', 'important');
                target.style.setProperty('transform', 'none', 'important');
                target.style.setProperty('margin-left', '0px', 'important');
                target.style.setProperty('visibility', 'visible', 'important');
                target.style.setProperty('display', 'flex', 'important');
                target.style.setProperty('opacity', '1', 'important');
                if (target.parentElement) target = target.parentElement;
                else break;
            }
        }
    });

    btn.addEventListener('mouseenter', function() { btn.style.background = '#f1f5f9'; });
    btn.addEventListener('mouseleave', function() { btn.style.background = 'white'; });

    doc.body.appendChild(btn);

    // ── Visibility: show the hamburger only when sidebar is collapsed ──
    function isSidebarCollapsed() {
        var sidebar = doc.querySelector('[data-testid="stSidebar"]');
        if (!sidebar) return true;
        // Check aria-expanded
        if (sidebar.getAttribute('aria-expanded') === 'false') return true;
        // Check computed width
        var w = sidebar.getBoundingClientRect().width;
        if (w < 10) return true;
        // Check if sidebar is off-screen (transform translateX)
        var cs = window.parent.getComputedStyle(sidebar);
        var tf = cs.transform || cs.webkitTransform || '';
        if (tf && tf !== 'none') {
            var m = tf.match(/matrix.*\((.+)\)/);
            if (m) {
                var vals = m[1].split(',');
                var tx = parseFloat(vals[4] || vals[12] || 0);
                if (tx < -50) return true;
            }
        }
        return false;
    }

    function updateBtnVisibility() {
        btn.style.display = isSidebarCollapsed() ? 'flex' : 'none';
    }

    setInterval(updateBtnVisibility, 300);
    updateBtnVisibility();

    var sidebar = doc.querySelector('[data-testid="stSidebar"]');
    if (sidebar) {
        var obs = new MutationObserver(updateBtnVisibility);
        obs.observe(sidebar, { attributes: true, childList: false, subtree: false });
    }
})();
</script>
""", height=0)


# =====================================================
# FUNCTIONS
# =====================================================

def detect_from_filename(filename):
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
    # If no semester detected but year and sede present, assume annual file
    # semester will be None which is handled by process_data as 'annuel'
    year = None
    match = re.search(r'20\d{2}', filename)
    if match:
        year = int(match.group())
    return sede, semester, year

def load_excel(file_content, filename):
    """Load Excel file - not cached due to file-like object hashing issues"""
    try:
        # Get the raw bytes and wrap in BytesIO for pandas
        if hasattr(file_content, 'getvalue'):
            data = BytesIO(file_content.getvalue())
        elif hasattr(file_content, 'read'):
            file_content.seek(0)
            data = BytesIO(file_content.read())
        else:
            data = file_content
        
        df = pd.read_excel(data, sheet_name='AEC')
        return df, None
    except:
        try:
            if hasattr(file_content, 'getvalue'):
                data = BytesIO(file_content.getvalue())
            elif hasattr(file_content, 'read'):
                file_content.seek(0)
                data = BytesIO(file_content.read())
            else:
                data = file_content
            df = pd.read_excel(data, sheet_name=0)
            return df, None
        except Exception as e:
            return None, str(e)

def map_category_to_levels(category):
    """Map category to all 4 levels: (macro_category, sous_secteur, secteur)"""
    if pd.isna(category) or str(category).strip() == "":
        # Track empty/null categories
        if 'unknown_categories' not in st.session_state:
            st.session_state.unknown_categories = {}
        st.session_state.unknown_categories["[VIDE/NULL]"] = "Catégorie vide ou nulle dans les données AEC"
        return ("NON RATTACHÉ", "NON RATTACHÉ", "NON RATTACHÉ")
    
    cat_str = str(category).strip()
    
    # Direct match
    if cat_str in CATEGORY_MAPPING:
        return CATEGORY_MAPPING[cat_str]
    # Try with trailing space
    if cat_str + " " in CATEGORY_MAPPING:
        return CATEGORY_MAPPING[cat_str + " "]
    # Try without trailing space
    if cat_str.rstrip() in CATEGORY_MAPPING:
        return CATEGORY_MAPPING[cat_str.rstrip()]
    # Case-insensitive match
    for key, value in CATEGORY_MAPPING.items():
        if key.strip().upper() == cat_str.strip().upper():
            return value
    
    # Track unknown category with details
    if 'unknown_categories' not in st.session_state:
        st.session_state.unknown_categories = {}
    st.session_state.unknown_categories[cat_str] = f"Catégorie '{cat_str}' non trouvée dans le mapping"
    return ("NON RATTACHÉ", "NON RATTACHÉ", "NON RATTACHÉ")

def map_category_to_sector(category):
    """Legacy function - returns just the sector"""
    result = map_category_to_levels(category)
    return result[2]  # Return secteur (3rd element)

def get_unknown_categories():
    """Return dict of unknown categories detected during import with details"""
    return st.session_state.get('unknown_categories', {})

def process_data(df, year, semester, sede):
    df = df.copy()
    if "Tranche d'âge du cours" in df.columns:
        df = df[df["Tranche d'âge du cours"].notna()]
        df = df[df["Tranche d'âge du cours"] != "TOTAL"]
        # Add simplified age group
        df["Groupe_Age"] = df["Tranche d'âge du cours"].apply(get_age_group)
    else:
        df["Groupe_Age"] = "Adultes"
    # Handle annual files (no semester) - use 'annuel' as period identifier
    effective_semester = semester if semester else "annuel"
    period_label = f"{year} {PERIOD_LABELS.get(effective_semester, effective_semester)}"
    df.insert(0, "Année", year)
    df.insert(1, "Semestre", effective_semester)
    df.insert(2, "Période", period_label)
    df.insert(3, "Sede", sede)
    if "Catégorie de cours" in df.columns:
        # Map to all 4 levels
        levels = df["Catégorie de cours"].apply(map_category_to_levels)
        df["Macro-catégorie"] = levels.apply(lambda x: x[0])
        df["Sous-secteur"] = levels.apply(lambda x: x[1])
        df["Secteur"] = levels.apply(lambda x: x[2])
    else:
        df["Macro-catégorie"] = "NON RATTACHÉ"
        df["Sous-secteur"] = "NON RATTACHÉ"
        df["Secteur"] = "NON RATTACHÉ"
    return df

def aggregate_by_sector(df, group_cols=["Année", "Période", "Sede", "Secteur"], add_total_row=False):
    agg_dict = {}
    col_mapping = {
        "Nb. de Cours": "sum", "Nb. d'inscriptions": "sum", "Nouveaux inscrits": "sum",
        "Réinscrits": "sum", "Nombre d'heures prévues": "sum",
        "Nombre total d'heures vendues (heures-étudiants)": "sum",
        "Heures synchrones vendues (heures-étudiants)": "sum", "Recettes": "sum", "Dépenses": "sum"
    }
    for col, func in col_mapping.items():
        if col in df.columns:
            agg_dict[col] = func
    if not agg_dict:
        return pd.DataFrame()
    grouped = df.groupby(group_cols, as_index=False).agg(agg_dict)
    if "Nb. d'inscriptions" in grouped.columns and "Nb. de Cours" in grouped.columns:
        grouped["N. élèves/cours"] = (grouped["Nb. d'inscriptions"] / grouped["Nb. de Cours"].replace(0, pd.NA)).round(2)
    
    # Add total row if requested
    if add_total_row and not grouped.empty:
        total_row = {}
        for col in grouped.columns:
            if col in ["Année", "Période", "Sede"]:
                total_row[col] = ""
            elif col == "Secteur":
                total_row[col] = "TOTAL"
            elif col == "N. élèves/cours":
                # Recalculate average
                total_inscr = grouped["Nb. d'inscriptions"].sum() if "Nb. d'inscriptions" in grouped.columns else 0
                total_cours = grouped["Nb. de Cours"].sum() if "Nb. de Cours" in grouped.columns else 0
                total_row[col] = round(total_inscr / total_cours, 2) if total_cours > 0 else 0
            else:
                total_row[col] = grouped[col].sum()
        grouped = pd.concat([grouped, pd.DataFrame([total_row])], ignore_index=True)
    
    return grouped

def create_prova_stats_format(df, aggregate_year=False, add_total_row=False):
    """Create prova stats format. If aggregate_year=True, sum both semesters per year.
    If add_total_row=True, add a TOTAL row at the bottom.
    Uses same French column names and order as IFI totals table."""
    if aggregate_year:
        # Group by Year, Sede, Secteur (combining both semesters)
        agg = aggregate_by_sector(df, group_cols=["Année", "Sede", "Secteur"])
        if not agg.empty:
            # Create period label as just the year
            agg["Période"] = agg["Année"].astype(str)
    else:
        agg = aggregate_by_sector(df)
    if agg.empty:
        return pd.DataFrame()
    # Rename columns to French (same format as IFI totals table)
    rename_map = {
        "Nombre total d'heures vendues (heures-étudiants)": "Nombre d'heures-élèves",
        "Heures synchrones vendues (heures-étudiants)": "Heures synchrones (h-élèves)"
    }
    agg = agg.rename(columns={k: v for k, v in rename_map.items() if k in agg.columns})
    
    # Calculate percentages for new/returning students
    inscr_col = "Nb. d'inscriptions"
    if inscr_col in agg.columns:
        if "Nouveaux inscrits" in agg.columns:
            agg["% nouveaux"] = (agg["Nouveaux inscrits"] / agg[inscr_col] * 100).round(1)
            agg["% nouveaux"] = agg["% nouveaux"].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "")
        if "Réinscrits" in agg.columns:
            agg["% réinscrits"] = (agg["Réinscrits"] / agg[inscr_col] * 100).round(1)
            agg["% réinscrits"] = agg["% réinscrits"].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "")
    
    # Column order matching IFI totals table
    desired_cols = [
        "Année", "Période", "Sede", "Secteur", "Nb. de Cours", "Nb. d'inscriptions",
        "Nouveaux inscrits", "% nouveaux", "Réinscrits", "% réinscrits", "Nombre d'heures prévues",
        "Nombre d'heures-élèves", "Heures synchrones (h-élèves)", 
        "Recettes", "Dépenses", "N. élèves/cours"
    ]
    final_cols = [c for c in desired_cols if c in agg.columns]
    result = agg[final_cols].copy()
    if "Secteur" in result.columns:
        result["_sort"] = result["Secteur"].apply(lambda x: SECTOR_ORDER.index(x) if x in SECTOR_ORDER else 999)
        sort_cols = ["Période", "Sede", "_sort"] if "Période" in result.columns else ["Sede", "_sort"]
        sort_cols = [c for c in sort_cols if c in result.columns]
        if sort_cols:
            result = result.sort_values(sort_cols)
        result = result.drop(columns=["_sort"])
    
    # Add total row if requested
    if add_total_row and not result.empty:
        total_row = {}
        for col in result.columns:
            if col in ["Année", "Période", "Sede"]:
                total_row[col] = ""
            elif col == "Secteur":
                total_row[col] = "TOTAL"
            elif col == "N. élèves/cours":
                # Recalculate average
                total_inscr = result["Nb. d'inscriptions"].sum() if "Nb. d'inscriptions" in result.columns else 0
                total_cours = result["Nb. de Cours"].sum() if "Nb. de Cours" in result.columns else 0
                total_row[col] = round(total_inscr / total_cours, 2) if total_cours > 0 else 0
            else:
                total_row[col] = result[col].sum()
        result = pd.concat([result, pd.DataFrame([total_row])], ignore_index=True)
    
    return result

def create_ifi_totals(df):
    df_ifi = df.copy()
    df_ifi["Sede"] = "IFI"
    return aggregate_by_sector(df_ifi)

def export_to_excel(dataframes_dict):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        for sheet_name, df in dataframes_dict.items():
            clean_name = sheet_name[:31].replace("/", "-")
            df.to_excel(writer, sheet_name=clean_name, index=False)
    output.seek(0)
    return output

# =====================================================
# NEW v2.8 FUNCTIONS: Map, Profitability, YoY, Age
# =====================================================

def create_italy_map(df):
    """Create a map of Italy with bubbles for each sede."""
    inscr_col = "Nb. d'inscriptions"
    sede_stats = df.groupby("Sede").agg({
        inscr_col: "sum",
        "Nb. de Cours": "sum",
        "Recettes": "sum"
    }).reset_index()
    
    # Add coordinates
    sede_stats["lat"] = sede_stats["Sede"].map(lambda x: SEDE_COORDS.get(x, {}).get("lat", 0))
    sede_stats["lon"] = sede_stats["Sede"].map(lambda x: SEDE_COORDS.get(x, {}).get("lon", 0))
    sede_stats["city"] = sede_stats["Sede"].map(lambda x: SEDE_COORDS.get(x, {}).get("city", x))
    sede_stats["color"] = sede_stats["Sede"].map(lambda x: SEDE_COLORS.get(x, "#888888"))
    
    # Calculate ARPI
    sede_stats["ARPI"] = (sede_stats["Recettes"] / sede_stats[inscr_col]).round(2)
    
    # Create map figure
    fig = go.Figure()
    
    # Add trace for each sede
    for _, row in sede_stats.iterrows():
        fig.add_trace(go.Scattergeo(
            lon=[row["lon"]],
            lat=[row["lat"]],
            text=f"<b>{row['city']} ({row['Sede']})</b><br>" +
                 f"{row[inscr_col]:,.0f} inscriptions<br>" +
                 f"{row['Nb. de Cours']:,.0f} cours<br>" +
                 f"€{row['Recettes']:,.0f}<br>" +
                 f"ARPI: €{row['ARPI']:.2f}",
            marker=dict(
                size=row[inscr_col] / 100,  # Scale bubble size
                sizemin=15,
                sizemode='area',
                color=row["color"],
                line=dict(width=2, color='white')
            ),
            name=row["Sede"],
            hovertemplate="%{text}<extra></extra>"
        ))
    
    text_color = "#1e293b"
    bg_color = "#f8fafc"
    
    fig.update_geos(
        scope="europe",
        center=dict(lat=42.5, lon=12.5),
        projection_scale=5,
        showland=True,
        landcolor="#e8e8e8",
        showocean=True,
        oceancolor="#dbeafe",
        showlakes=True,
        lakecolor="#93c5fd",
        showcountries=True,
        countrycolor="#94a3b8",
        showcoastlines=True,
        coastlinecolor="#64748b"
    )
    
    fig.update_layout(
        title=dict(text=f"{t('italy_map')} - {t('map_by_inscriptions')}", font=dict(color=text_color, size=18)),
        showlegend=True,
        legend=dict(font=dict(color=text_color)),
        paper_bgcolor=bg_color,
        geo=dict(bgcolor=bg_color),
        height=600,
        margin=dict(l=0, r=0, t=50, b=0)
    )
    
    return fig

def calculate_profitability(df):
    """Calculate revenue per inscription (ARPI) by sector and sede."""
    inscr_col = "Nb. d'inscriptions"
    
    # By Sector
    by_sector = df.groupby("Secteur").agg({
        inscr_col: "sum",
        "Recettes": "sum"
    }).reset_index()
    by_sector["ARPI"] = (by_sector["Recettes"] / by_sector[inscr_col]).round(2)
    by_sector = by_sector.sort_values("ARPI", ascending=False)
    
    # By Sede
    by_sede = df.groupby("Sede").agg({
        inscr_col: "sum",
        "Recettes": "sum"
    }).reset_index()
    by_sede["ARPI"] = (by_sede["Recettes"] / by_sede[inscr_col]).round(2)
    by_sede = by_sede.sort_values("ARPI", ascending=False)
    
    # By Sector and Sede (cross)
    by_sector_sede = df.groupby(["Secteur", "Sede"]).agg({
        inscr_col: "sum",
        "Recettes": "sum"
    }).reset_index()
    by_sector_sede["ARPI"] = (by_sector_sede["Recettes"] / by_sector_sede[inscr_col]).round(2)
    
    return by_sector, by_sede, by_sector_sede

def calculate_yoy_comparison(df):
    """Calculate year-over-year variations."""
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
            "Heures": year_data["Nombre total d'heures vendues (heures-étudiants)"].sum() if "Nombre total d'heures vendues (heures-étudiants)" in year_data.columns else 0
        })
    
    comparison_df = pd.DataFrame(results)
    
    # Calculate variations
    for col in ["Inscriptions", "Cours", "Recettes", "Heures"]:
        comparison_df[f"{col}_var"] = comparison_df[col].pct_change() * 100
    
    return comparison_df, years

def calculate_yoy_by_sede(df):
    """Calculate year-over-year by sede."""
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
                "Recettes": year_data["Recettes"].sum() if "Recettes" in year_data.columns else 0
            })
    
    return pd.DataFrame(results)

def get_age_group(tranche):
    """Map AEC age categories to simplified groups."""
    if pd.isna(tranche):
        return "Adultes"
    tranche_str = str(tranche).strip()
    return AGE_GROUP_MAPPING.get(tranche_str, "Adultes")

def format_number(n, prefix="", suffix=""):
    if pd.isna(n):
        return "N/A"
    if n >= 1_000_000:
        return f"{prefix}{n/1_000_000:.2f}M{suffix}"
    elif n >= 1_000:
        return f"{prefix}{n/1_000:.1f}K{suffix}"
    else:
        return f"{prefix}{n:,.0f}{suffix}"

def create_sankey_diagram(df):
    inscr_col = "Nb. d'inscriptions"
    flow_data = df.groupby(["Sede", "Secteur"])[inscr_col].sum().reset_index()
    sedi = flow_data["Sede"].unique().tolist()
    secteurs = flow_data["Secteur"].unique().tolist()
    labels = sedi + secteurs
    source, target, value, colors = [], [], [], []
    for _, row in flow_data.iterrows():
        source.append(sedi.index(row["Sede"]))
        target.append(len(sedi) + secteurs.index(row["Secteur"]))
        value.append(row[inscr_col])
        colors.append(SEDE_COLORS.get(row["Sede"], "#888888"))
    
    link_colors = []
    for c in colors:
        if c.startswith("#"):
            r, g, b = int(c[1:3], 16), int(c[3:5], 16), int(c[5:7], 16)
            link_colors.append(f"rgba({r},{g},{b},0.4)")
        else:
            link_colors.append(c)
    
    # Better label colors for readability
    text_color = "#1e293b"
    
    fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=20, thickness=25,
            line=dict(color=text_color, width=1),
            label=labels,
            color=[SEDE_COLORS.get(s, "#888888") for s in sedi] + ["#6366f1"] * len(secteurs)
        ),
        link=dict(source=source, target=target, value=value, color=link_colors),
        textfont=dict(color=text_color, size=14, family="Arial Black")
    )])
    fig.update_layout(
        title=dict(text=t("flow_sede_sector"), font=dict(color=text_color, size=18)),
        font=dict(color=text_color, size=14),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", 
        height=600,
        margin=dict(l=20, r=250, t=50, b=20)  # More right margin for labels
    )
    return fig

# =====================================================
# COURSE FICHES EXPORT SUPPORT
# =====================================================

CENTRE_TO_SEDE = {
    "Milano": "IFM", "Firenze": "IFF", "Napoli": "IFN", "Palermo": "IFP",
}

MONTH_FR_TO_NUM = {
    "JANVIER": 1, "FEVRIER": 2, "FÉVRIER": 2, "MARS": 3, "AVRIL": 4,
    "MAI": 5, "JUIN": 6, "JUILLET": 7, "AOUT": 8, "AOÛT": 8,
    "SEPTEMBRE": 9, "OCTOBRE": 10, "NOVEMBRE": 11, "DECEMBRE": 12, "DÉCEMBRE": 12,
}

MONTH_NUM_TO_FR = {
    1: "Janvier", 2: "Février", 3: "Mars", 4: "Avril", 5: "Mai", 6: "Juin",
    7: "Juillet", 8: "Août", 9: "Septembre", 10: "Octobre", 11: "Novembre", 12: "Décembre"
}

def detect_export_type(df):
    """Detect export type from DataFrame columns."""
    cols = set(df.columns)
    # Course fiches: has "Centre", "Catégorie", "Nb total de participants", "Date début"
    fiches_markers = {"Centre", "Catégorie", "Nb total de participants", "Date début"}
    # Category report: has "Catégorie de cours"
    report_markers = {"Catégorie de cours"}
    
    # Client profiles: has "Tranche d'âge de l'élève", "Nationalité", "Profil client", "Code Client"
    profils_markers = {"Tranche d'âge de l'élève", "Nationalité", "Profil client", "Code Client"}
    # Products catalog: has "Type de produit", "Nom du produit", "Code article", "Nombre maximum de places"
    produits_markers = {"Type de produit", "Nom du produit", "Code article", "Nombre maximum de places"}

    fiches_score = len(fiches_markers & cols)
    report_score = len(report_markers & cols)
    profils_score = len(profils_markers & cols)
    produits_score = len(produits_markers & cols)
    
    if profils_score >= 3:
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
    s = str(value).strip().replace('%', '').strip()
    if s == '':
        return 0.0
    if ',' in s and '.' in s:
        if s.index(',') < s.index('.'):
            s = s.replace(',', '')  # 1,440.00 → 1440.00
        else:
            s = s.replace('.', '').replace(',', '.')  # 1.440,00 → 1440.00
    elif ',' in s:
        parts = s.split(',')
        if len(parts) == 2 and len(parts[1]) <= 2:
            s = s.replace(',', '.')  # decimal comma
        else:
            s = s.replace(',', '')  # thousands separator
    try:
        return float(s)
    except:
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
    """Parse Période field like '2026-FEVRIER' → (year, month_num).
    For multi-month values like '2026-FEVRIER, 2026-MARS', use FIRST month only
    (course appears only in its start month's semester)."""
    if pd.isna(val):
        return None, None
    val_str = str(val).strip()
    # Handle multi-month: take first entry
    if ',' in val_str:
        val_str = val_str.split(',')[0].strip()
    m = re.match(r'(\d{4})-(\w+)', val_str)
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

def load_csv_file(file_content, filename):
    """Load CSV file with encoding auto-detection."""
    try:
        if hasattr(file_content, 'getvalue'):
            data = BytesIO(file_content.getvalue())
        elif hasattr(file_content, 'read'):
            file_content.seek(0)
            data = BytesIO(file_content.read())
        else:
            data = file_content
        df = pd.read_csv(data, encoding='utf-8', low_memory=False)
        return df, None
    except:
        try:
            if hasattr(file_content, 'getvalue'):
                data = BytesIO(file_content.getvalue())
            elif hasattr(file_content, 'read'):
                file_content.seek(0)
                data = BytesIO(file_content.read())
            else:
                data = file_content
            df = pd.read_csv(data, encoding='latin-1', low_memory=False)
            return df, None
        except Exception as e:
            return None, str(e)

def load_file_auto(file_content, filename):
    """Load Excel or CSV file based on extension.
    For Excel files, tries 'AEC' sheet first, then first sheet.
    For CSV files, uses CSV reader."""
    if filename.lower().endswith('.csv'):
        return load_csv_file(file_content, filename)
    else:
        # Try standard load_excel first
        df, error = load_excel(file_content, filename)
        if error:
            # If Excel load failed, it might be a different Excel format
            # Try reading first sheet without specifying sheet name
            try:
                if hasattr(file_content, 'getvalue'):
                    data = BytesIO(file_content.getvalue())
                elif hasattr(file_content, 'read'):
                    file_content.seek(0)
                    data = BytesIO(file_content.read())
                else:
                    data = file_content
                df = pd.read_excel(data, sheet_name=0)
                return df, None
            except Exception as e2:
                return None, f"{error} / {str(e2)}"
        return df, error

def process_course_fiches(df):
    """Process the course fiches export DataFrame."""
    df = df.copy()
    
    # Extract Sede from Centre
    if "Centre" in df.columns:
        df["Sede"] = df["Centre"].apply(extract_sede_from_centre)
    else:
        df["Sede"] = "???"
    
    # Parse Période for year and month
    if "Période" in df.columns:
        parsed = df["Période"].apply(parse_periode_field)
        df["Année"] = parsed.apply(lambda x: x[0])
        df["Mois_Num"] = parsed.apply(lambda x: x[1])
    else:
        df["Année"] = None
        df["Mois_Num"] = None
    
    # Fallback to Date début
    if "Date début" in df.columns:
        df["Date_début_parsed"] = pd.to_datetime(df["Date début"], format="%d/%m/%Y", errors="coerce")
        mask = df["Année"].isna()
        if mask.any():
            df.loc[mask, "Année"] = df.loc[mask, "Date_début_parsed"].dt.year
            df.loc[mask, "Mois_Num"] = df.loc[mask, "Date_début_parsed"].dt.month
    
    # Semester assignment: course appears ONLY in its start month's semester
    df["Semestre"] = df["Mois_Num"].apply(assign_semester_from_month)
    
    # Month/Period labels
    df["Mois_Label"] = df["Mois_Num"].apply(lambda x: MONTH_NUM_TO_FR.get(int(x), "?") if pd.notna(x) else "?")
    df["Période_Label"] = df.apply(
        lambda r: f"{int(r['Année'])} S{'1' if r['Semestre']=='sem1' else '2'}" if pd.notna(r["Année"]) else "?",
        axis=1
    )
    
    # Parse numeric columns (handle French number format)
    num_cols = [
        "Nb total de participants", "Inscrits à ce jour", "Capacité", "Places dispo.",
        "Nouveaux inscrits", "Réinscrits", "Qté heures", "Qté heures vendues",
        "Total des ventes", "Prix", "Recettes prévues", "Marge brute", "Marge brute prévue",
        "Total dépenses", "Nbre de séances", "Nb de semaines",
        "Heures restantes", "Seuil d'ouverture", "Élèves prévus"
    ]
    for col in num_cols:
        if col in df.columns:
            df[col] = df[col].apply(parse_french_number)
    
    # Detect online courses
    df["Est_En_Ligne"] = 0
    if "Format" in df.columns:
        df["Est_En_Ligne"] = df["Format"].apply(
            lambda x: 1 if not pd.isna(x) and "distance" in str(x).lower() else 0
        )
    elif "Localisation" in df.columns:
        df["Est_En_Ligne"] = df["Localisation"].apply(
            lambda x: 1 if not pd.isna(x) and "ligne" in str(x).lower() else 0
        )
    
    # Map Catégorie to our sector mapping (reuse existing)
    if "Catégorie" in df.columns:
        levels = df["Catégorie"].apply(map_category_to_levels)
        df["Macro-catégorie"] = levels.apply(lambda x: x[0])
        df["Sous-secteur"] = levels.apply(lambda x: x[1])
        df["Secteur"] = levels.apply(lambda x: x[2])
    
    return df

def render_fiches_tabs(df_fiches):
    """Render analysis tabs for course fiches export data."""
    
    st.markdown(f"## {t('fiches_cours_section')}")
    
    #  Filters 
    st.markdown(f"### {t('filters')}")
    col_f1, col_f2, col_f3 = st.columns(3)
    
    with col_f1:
        available_years_f = sorted([int(y) for y in df_fiches["Année"].dropna().unique()])
        selected_years_f = st.multiselect(
            "Année", available_years_f, default=available_years_f, key="fiches_years"
        )
    
    with col_f2:
        sem_options = ["Tous", "sem1", "sem2"]
        sem_labels_map = {"Tous": t('all'), "sem1": t('semester1'), "sem2": t('semester2')}
        selected_sem_f = st.selectbox(
            t('semester_filter'), sem_options,
            format_func=lambda x: sem_labels_map[x], key="fiches_sem"
        )
    
    with col_f3:
        available_sedi_f = sorted([s for s in df_fiches["Sede"].unique() if s != "???"])
        selected_sedi_f = st.multiselect(
            t('filter_by_sede'), available_sedi_f, default=available_sedi_f, key="fiches_sedi"
        )
    
    # Apply filters
    df_f = df_fiches.copy()
    if selected_years_f:
        df_f = df_f[df_f["Année"].isin(selected_years_f)]
    if selected_sem_f != "Tous":
        df_f = df_f[df_f["Semestre"] == selected_sem_f]
    if selected_sedi_f:
        df_f = df_f[df_f["Sede"].isin(selected_sedi_f)]
    
    if len(df_f) == 0:
        st.warning("Aucune donnée avec ces filtres.")
        return
    
    #  Tabs 
    tab_f1, tab_f2, tab_f3 = st.tabs([
        t("tab_fiches_synthese"), t("tab_fiches_niveaux"), t("tab_fiches_inscriptions")
    ])
    
    #  TAB F1: SYNTHÈSE 
    with tab_f1:
        nb_cours = len(df_f)
        nb_en_ligne = int(df_f["Est_En_Ligne"].sum())
        total_participants = df_f["Nb total de participants"].sum() if "Nb total de participants" in df_f.columns else 0
        avg_per_course = total_participants / nb_cours if nb_cours > 0 else 0
        total_heures = df_f["Qté heures"].sum() if "Qté heures" in df_f.columns else 0
        total_ventes = df_f["Total des ventes"].sum() if "Total des ventes" in df_f.columns else 0
        total_nouveaux = df_f["Nouveaux inscrits"].sum() if "Nouveaux inscrits" in df_f.columns else 0
        total_reinscrits = df_f["Réinscrits"].sum() if "Réinscrits" in df_f.columns else 0
        
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        c1.metric(t('total_courses_fiches'), f"{nb_cours:,}")
        c2.metric(t('online_courses'), f"{nb_en_ligne:,}")
        c3.metric(t('avg_students_per_course'), f"{avg_per_course:.1f}")
        c4.metric(t('total_hours_fiches'), f"{total_heures:,.0f}")
        c5.metric(t('total_sales'), f"{total_ventes:,.0f} €")
        c6.metric("Participants", f"{int(total_participants):,}")
        
        st.markdown("---")
        
        #  Table by Sede & Semester 
        st.markdown(f"#### {t('analysis_by_sede')} & {t('by_semester')}")
        
        agg_dict_sede = {
            "Nb_Cours": ("Catégorie", "count"),
            "Cours_En_Ligne": ("Est_En_Ligne", "sum"),
            "Participants": ("Nb total de participants", "sum"),
        }
        if "Nouveaux inscrits" in df_f.columns:
            agg_dict_sede["Nouveaux"] = ("Nouveaux inscrits", "sum")
        if "Réinscrits" in df_f.columns:
            agg_dict_sede["Réinscrits"] = ("Réinscrits", "sum")
        if "Qté heures" in df_f.columns:
            agg_dict_sede["Heures"] = ("Qté heures", "sum")
        if "Total des ventes" in df_f.columns:
            agg_dict_sede["Ventes"] = ("Total des ventes", "sum")
        
        agg_sede = df_f.groupby(["Sede", "Semestre"]).agg(**agg_dict_sede).reset_index()
        agg_sede["Élèves/Cours"] = (agg_sede["Participants"] / agg_sede["Nb_Cours"]).round(1)
        agg_sede["Cours_En_Ligne"] = agg_sede["Cours_En_Ligne"].astype(int)
        
        format_dict = {"Participants": "{:,.0f}", "Élèves/Cours": "{:.1f}", "Nb_Cours": "{:,.0f}", "Cours_En_Ligne": "{:,.0f}"}
        if "Nouveaux" in agg_sede.columns:
            format_dict["Nouveaux"] = "{:,.0f}"
        if "Réinscrits" in agg_sede.columns:
            format_dict["Réinscrits"] = "{:,.0f}"
        if "Heures" in agg_sede.columns:
            format_dict["Heures"] = "{:,.0f}"
        if "Ventes" in agg_sede.columns:
            format_dict["Ventes"] = "{:,.0f}"
        
        st.dataframe(agg_sede.style.format(format_dict), use_container_width=True)
        
        #  Bar chart: Courses & Participants by sede 
        agg_sede_total = df_f.groupby("Sede").agg(
            Nb_Cours=("Catégorie", "count"),
            Participants=("Nb total de participants", "sum")
        ).reset_index()
        
        fig_sede = make_subplots(specs=[[{"secondary_y": True}]])
        fig_sede.add_trace(
            go.Bar(x=agg_sede_total["Sede"], y=agg_sede_total["Nb_Cours"],
                   name=t('total_courses_fiches'), marker_color="#3b82f6"),
            secondary_y=False,
        )
        fig_sede.add_trace(
            go.Bar(x=agg_sede_total["Sede"], y=agg_sede_total["Participants"],
                   name="Participants", marker_color="#22c55e"),
            secondary_y=True,
        )
        fig_sede.update_layout(
            title=t('analysis_by_sede'), barmode="group",
            margin=dict(l=20, r=20, t=40, b=20)
        )
        fig_sede.update_yaxes(title_text=t('total_courses_fiches'), secondary_y=False)
        fig_sede.update_yaxes(title_text="Participants", secondary_y=True)
        st.plotly_chart(fig_sede, use_container_width=True)
        
        #  Catégorie breakdown 
        st.markdown(f"#### {t('by_category_aec')}")
        agg_cat = df_f.groupby("Catégorie").agg(
            Nb_Cours=("Centre", "count"),
            Participants=("Nb total de participants", "sum"),
            Heures=("Qté heures", "sum") if "Qté heures" in df_f.columns else ("Nb total de participants", "count"),
        ).reset_index().sort_values("Nb_Cours", ascending=False)
        agg_cat["Élèves/Cours"] = (agg_cat["Participants"] / agg_cat["Nb_Cours"]).round(1)
        
        st.dataframe(agg_cat.head(25).style.format({
            "Participants": "{:,.0f}", "Heures": "{:,.0f}", "Élèves/Cours": "{:.1f}", "Nb_Cours": "{:,.0f}"
        }), use_container_width=True)
        
        # Top 15 categories chart
        fig_cat = px.bar(
            agg_cat.head(15), x="Catégorie", y="Nb_Cours",
            color="Participants", title=f"Top 15 {t('by_category_aec')}",
            color_continuous_scale="Blues"
        )
        fig_cat.update_layout(margin=dict(l=20, r=20, t=40, b=80), xaxis_tickangle=-45)
        st.plotly_chart(fig_cat, use_container_width=True)
        
        #  By Secteur (using our mapping) 
        if "Secteur" in df_f.columns:
            st.markdown(f"#### {t('analysis_by_sector')}")
            agg_secteur = df_f.groupby("Secteur").agg(
                Nb_Cours=("Centre", "count"),
                Participants=("Nb total de participants", "sum"),
            ).reset_index().sort_values("Participants", ascending=False)
            agg_secteur["Élèves/Cours"] = (agg_secteur["Participants"] / agg_secteur["Nb_Cours"]).round(1)
            
            col_s1, col_s2 = st.columns(2)
            with col_s1:
                st.dataframe(agg_secteur.style.format({
                    "Participants": "{:,.0f}", "Élèves/Cours": "{:.1f}", "Nb_Cours": "{:,.0f}"
                }), use_container_width=True)
            with col_s2:
                fig_sec = px.pie(agg_secteur, values="Nb_Cours", names="Secteur",
                                title=t('courses_by_sector'))
                st.plotly_chart(fig_sec, use_container_width=True)
    
    #  TAB F2: PAR NIVEAU 
    with tab_f2:
        if "Niveau" in df_f.columns:
            st.markdown(f"### {t('analysis_by_level')}")
            
            agg_dict_niv = {
                "Nb_Cours": ("Centre", "count"),
                "Participants": ("Nb total de participants", "sum"),
            }
            if "Nouveaux inscrits" in df_f.columns:
                agg_dict_niv["Nouveaux"] = ("Nouveaux inscrits", "sum")
            if "Réinscrits" in df_f.columns:
                agg_dict_niv["Réinscrits"] = ("Réinscrits", "sum")
            if "Qté heures" in df_f.columns:
                agg_dict_niv["Heures"] = ("Qté heures", "sum")
            
            agg_niveau = df_f.groupby("Niveau").agg(**agg_dict_niv).reset_index()
            agg_niveau = agg_niveau.sort_values("Participants", ascending=False)
            agg_niveau["Élèves/Cours"] = (agg_niveau["Participants"] / agg_niveau["Nb_Cours"]).round(1)
            
            fmt_niv = {"Participants": "{:,.0f}", "Élèves/Cours": "{:.1f}", "Nb_Cours": "{:,.0f}"}
            if "Nouveaux" in agg_niveau.columns:
                fmt_niv["Nouveaux"] = "{:,.0f}"
            if "Réinscrits" in agg_niveau.columns:
                fmt_niv["Réinscrits"] = "{:,.0f}"
            if "Heures" in agg_niveau.columns:
                fmt_niv["Heures"] = "{:,.0f}"
            
            st.dataframe(agg_niveau.style.format(fmt_niv), use_container_width=True)
            
            #  Chart by level 
            fig_niv = px.bar(
                agg_niveau.head(15), x="Niveau", y="Participants",
                color="Nb_Cours", title=t('students_by_level'),
                color_continuous_scale="Blues"
            )
            fig_niv.update_layout(margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig_niv, use_container_width=True)
            
            #  By Niveau & Sede 
            st.markdown(f"#### {t('analysis_by_level')} × {t('filter_by_sede')}")
            agg_niv_sede = df_f.groupby(["Niveau", "Sede"]).agg(
                Nb_Cours=("Centre", "count"),
                Participants=("Nb total de participants", "sum"),
            ).reset_index()
            
            fig_niv_sede = px.bar(
                agg_niv_sede, x="Niveau", y="Participants", color="Sede",
                barmode="group",
                title=f"{t('students_by_level')} - {t('by_sede')}",
                color_discrete_map=SEDE_COLORS
            )
            fig_niv_sede.update_layout(margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig_niv_sede, use_container_width=True)
            
            #  Tranche d'âge 
            if "Tranche d'âge" in df_f.columns:
                st.markdown(f"#### {t('age_distribution')}")
                agg_age = df_f.groupby("Tranche d'âge").agg(
                    Nb_Cours=("Centre", "count"),
                    Participants=("Nb total de participants", "sum"),
                ).reset_index().sort_values("Participants", ascending=False)
                
                col_a1, col_a2 = st.columns(2)
                with col_a1:
                    st.dataframe(agg_age.style.format({
                        "Participants": "{:,.0f}", "Nb_Cours": "{:,.0f}"
                    }), use_container_width=True)
                with col_a2:
                    fig_age = px.pie(agg_age, values="Participants", names="Tranche d'âge",
                                    title=t('age_distribution'))
                    st.plotly_chart(fig_age, use_container_width=True)
        else:
            st.info("Colonne 'Niveau' non trouvée dans l'export.")
    
    #  TAB F3: INSCRIPTIONS MENSUELLES 
    with tab_f3:
        st.markdown(f"### {t('monthly_inscriptions')}")
        
        # Build year-month grouping
        df_monthly = df_f.copy()
        df_monthly["Année_Mois"] = df_monthly.apply(
            lambda r: f"{int(r['Année'])}-{int(r['Mois_Num']):02d}"
            if pd.notna(r["Année"]) and pd.notna(r["Mois_Num"]) else None,
            axis=1
        )
        df_monthly = df_monthly[df_monthly["Année_Mois"].notna()]
        
        if len(df_monthly) == 0:
            st.warning("Pas de données de période pour l'analyse mensuelle.")
            return
        
        agg_dict_m = {
            "Nb_Cours": ("Centre", "count"),
            "Participants": ("Nb total de participants", "sum"),
        }
        if "Nouveaux inscrits" in df_monthly.columns:
            agg_dict_m["Nouveaux"] = ("Nouveaux inscrits", "sum")
        if "Réinscrits" in df_monthly.columns:
            agg_dict_m["Réinscrits"] = ("Réinscrits", "sum")
        if "Qté heures" in df_monthly.columns:
            agg_dict_m["Heures"] = ("Qté heures", "sum")
        
        agg_monthly = df_monthly.groupby("Année_Mois").agg(**agg_dict_m).reset_index()
        agg_monthly = agg_monthly.sort_values("Année_Mois")
        
        agg_monthly["Mois_Label"] = agg_monthly["Année_Mois"].apply(
            lambda x: MONTH_NUM_TO_FR.get(int(x.split("-")[1]), x.split("-")[1]) + " " + x.split("-")[0]
        )
        agg_monthly["Élèves/Cours"] = (agg_monthly["Participants"] / agg_monthly["Nb_Cours"]).round(1)
        
        st.dataframe(agg_monthly, use_container_width=True)
        
        #  Line chart: monthly evolution 
        fig_evo = go.Figure()
        fig_evo.add_trace(go.Scatter(
            x=agg_monthly["Mois_Label"], y=agg_monthly["Participants"],
            mode="lines+markers", name="Participants",
            line=dict(color="#3b82f6", width=3)
        ))
        fig_evo.add_trace(go.Scatter(
            x=agg_monthly["Mois_Label"], y=agg_monthly["Nb_Cours"],
            mode="lines+markers", name=t('total_courses_fiches'),
            line=dict(color="#22c55e", width=2), yaxis="y2"
        ))
        fig_evo.update_layout(
            title=t('monthly_evolution'),
            yaxis=dict(title="Participants"),
            yaxis2=dict(title=t('total_courses_fiches'), overlaying="y", side="right"),
            margin=dict(l=20, r=60, t=40, b=20),
            hovermode="x unified"
        )
        st.plotly_chart(fig_evo, use_container_width=True)
        
        #  New vs Returning by month 
        if "Nouveaux" in agg_monthly.columns and "Réinscrits" in agg_monthly.columns:
            st.markdown(f"#### {t('new_vs_returning')}")
            fig_nr = go.Figure()
            fig_nr.add_trace(go.Bar(
                x=agg_monthly["Mois_Label"], y=agg_monthly["Nouveaux"],
                name=t('new_students'), marker_color="#3b82f6"
            ))
            fig_nr.add_trace(go.Bar(
                x=agg_monthly["Mois_Label"], y=agg_monthly["Réinscrits"],
                name=t('returning_students'), marker_color="#f59e0b"
            ))
            fig_nr.update_layout(
                title=t('new_vs_returning'),
                barmode="stack",
                margin=dict(l=20, r=20, t=40, b=20)
            )
            st.plotly_chart(fig_nr, use_container_width=True)
        
        #  Fill rate evolution 
        st.markdown(f"#### {t('fill_rate')} {t('monthly_evolution')}")
        fig_fill = go.Figure()
        fig_fill.add_trace(go.Scatter(
            x=agg_monthly["Mois_Label"], y=agg_monthly["Élèves/Cours"],
            mode="lines+markers+text", name=t('avg_students_per_course'),
            text=agg_monthly["Élèves/Cours"].apply(lambda x: f"{x:.1f}"),
            textposition="top center",
            line=dict(color="#8b5cf6", width=3)
        ))
        fig_fill.update_layout(
            title=f"{t('avg_students_per_course')} - {t('monthly_evolution')}",
            yaxis_title=t('avg_students_per_course'),
            margin=dict(l=20, r=20, t=40, b=20)
        )
        st.plotly_chart(fig_fill, use_container_width=True)
        
        #  Semester summary 
        st.markdown(f"#### {t('by_semester')}")
        agg_dict_sem = {
            "Nb_Cours": ("Centre", "count"),
            "Participants": ("Nb total de participants", "sum"),
        }
        if "Nouveaux inscrits" in df_f.columns:
            agg_dict_sem["Nouveaux"] = ("Nouveaux inscrits", "sum")
        if "Réinscrits" in df_f.columns:
            agg_dict_sem["Réinscrits"] = ("Réinscrits", "sum")
        
        agg_sem = df_f.groupby(["Année", "Semestre"]).agg(**agg_dict_sem).reset_index()
        agg_sem["Élèves/Cours"] = (agg_sem["Participants"] / agg_sem["Nb_Cours"]).round(1)
        st.dataframe(agg_sem, use_container_width=True)

    # ── Export CSV ──
    st.divider()
    _csv_fiches = df_fiches.to_csv(index=False).encode('utf-8')
    st.download_button(
        label=f"⬇️ {t('download_csv')} — Fiches de cours",
        data=_csv_fiches,
        file_name="export_fiches_cours.csv",
        mime="text/csv",
        use_container_width=True,
        key="dl_fiches"
    )


# =====================================================
# CLIENT PROFILES EXPORT SUPPORT
# =====================================================

# Course type translation: English AEC values → French labels
# Course type mapping – keys are lowercased for case-insensitive matching
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

# Custom age brackets based on IFI segmentation
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

# Level ordering for progressive display
LEVEL_ORDER = [
    "A0", "A1", "A1.1", "A1.2",
    "A2", "A2.1", "A2.2",
    "B1", "B1.1", "B1.2",
    "B2", "B2.1", "B2.2",
    "C1", "C1.1", "C1.2",
    "C2",
]

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

# Nationality → ISO-3 country code for choropleth
# We build a case-insensitive lookup at runtime
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

# ── First-name → gender dictionary (Italian / French) ─────────────
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

def _infer_gender_from_prenom(name) -> str | None:
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
    
    return df

def render_profils_tabs(df_profils):
    """Render analysis tabs for client profiles export data."""
    
    st.markdown(f"## {t('profils_section')}")
    
    # ── Filters ──────────────────────────────────────────
    st.markdown(f"### {t('filters')}")
    
    # Build period options based on granularity selector
    has_year = "Année_Creation" in df_profils.columns and df_profils["Année_Creation"].notna().any()
    has_semester = "Semestre" in df_profils.columns and df_profils["Semestre"].notna().any()
    has_month = "Mois_Creation" in df_profils.columns and df_profils["Mois_Creation"].notna().any()
    
    # Granularity choice – own row, small columns
    granularity_options = ["Par année"]
    if has_semester:
        granularity_options.append("Par semestre")
    if has_month:
        granularity_options.append("Par mois")
    
    col_g1, col_g2 = st.columns([1, 3])
    with col_g1:
        period_granularity = st.radio(
            "Granularité temporelle", granularity_options, horizontal=True,
            key="profils_period_granularity", label_visibility="collapsed"
        )
    
    # Build period options (with unicode indentation for sub-items)
    _INDENT = "\u2003\u2003"  # em-space for visual indent in dropdown
    period_options = []
    period_lookup = {}
    if has_year:
        years_avail = sorted(df_profils["Année_Creation"].dropna().unique())
        if period_granularity == "Par année":
            for yr in years_avail:
                yr_int = int(yr)
                label = f"{yr_int}"
                period_options.append(label)
                period_lookup[label] = {"year": yr_int}
        elif period_granularity == "Par semestre":
            for yr in years_avail:
                yr_int = int(yr)
                yr_label = f"▸ {yr_int}"
                period_options.append(yr_label)
                period_lookup[yr_label] = {"year": yr_int}
                df_yr = df_profils[df_profils["Année_Creation"] == yr]
                sems = sorted(df_yr["Semestre"].dropna().unique())
                for s in sems:
                    s_int = int(s)
                    label = f"{_INDENT}S{s_int} ({yr_int})"
                    period_options.append(label)
                    period_lookup[label] = {"year": yr_int, "semester": s_int}
        elif period_granularity == "Par mois":
            for yr in years_avail:
                yr_int = int(yr)
                yr_label = f"▸ {yr_int}"
                period_options.append(yr_label)
                period_lookup[yr_label] = {"year": yr_int}
                df_yr = df_profils[df_profils["Année_Creation"] == yr]
                months = sorted(df_yr["Mois_Creation"].dropna().unique())
                for m in months:
                    m_int = int(m)
                    m_label = MONTH_NUM_TO_FR.get(m_int, str(m_int))
                    label = f"{_INDENT}{m_label} {yr_int}"
                    period_options.append(label)
                    period_lookup[label] = {"year": yr_int, "month": m_int}
    
    col_f1, col_f2, col_f3, col_f4, col_f5 = st.columns(5)
    
    with col_f1:
        available_antennes = sorted([s for s in df_profils["Sede"].unique() if s != "???"])
        selected_antennes = st.multiselect(
            "Filtrer par antenne", available_antennes, default=[], key="profils_antennes",
            placeholder="Toutes"
        )
    
    with col_f2:
        selected_periods = st.multiselect(
            "Filtrer par période", period_options, default=[], key="profils_periods",
            placeholder="Toutes les périodes"
        )
    
    with col_f3:
        if "Tranche_Custom" in df_profils.columns:
            all_tranches = [b for b in CUSTOM_AGE_BRACKET_ORDER if b in df_profils["Tranche_Custom"].values]
            selected_tranches = st.multiselect(
                "Tranche d'âge", all_tranches, default=[], key="profils_tranches",
                placeholder="Toutes"
            )
        else:
            selected_tranches = None
    
    with col_f4:
        if "Type_Cours_FR" in df_profils.columns:
            all_types = sorted(df_profils["Type_Cours_FR"].dropna().unique())
            selected_types = st.multiselect(
                "Type de cours", all_types, default=[], key="profils_types",
                placeholder="Tous"
            )
        else:
            selected_types = None
    
    with col_f5:
        if "Profil client" in df_profils.columns:
            # Extract individual profile tags from comma-separated values
            _all_profil_tags = set()
            for val in df_profils["Profil client"].dropna().unique():
                for tag in str(val).split(","):
                    tag = tag.strip()
                    if tag:
                        _all_profil_tags.add(tag)
            all_profils = sorted(_all_profil_tags)
            selected_profils = st.multiselect(
                "Profil client", all_profils, default=[], key="profils_profil_client",
                placeholder="Tous"
            )
        else:
            selected_profils = None
    
    # Apply filters (empty selection = no filter = all)
    df_p = df_profils.copy()
    
    if selected_antennes:
        df_p = df_p[df_p["Sede"].isin(selected_antennes)]
    
    # Apply period filter
    if selected_periods:
        mask = pd.Series(False, index=df_p.index)
        for period_str in selected_periods:
            info = period_lookup.get(period_str, {})
            if "month" in info:
                mask |= (df_p["Année_Creation"] == info["year"]) & (df_p["Mois_Creation"] == info["month"])
            elif "semester" in info:
                mask |= (df_p["Année_Creation"] == info["year"]) & (df_p["Semestre"] == info["semester"])
            elif "year" in info:
                mask |= (df_p["Année_Creation"] == info["year"])
        df_p = df_p[mask]
    
    if selected_tranches and "Tranche_Custom" in df_p.columns:
        df_p = df_p[df_p["Tranche_Custom"].isin(selected_tranches) | df_p["Tranche_Custom"].isna()]
    if selected_types and "Type_Cours_FR" in df_p.columns:
        df_p = df_p[df_p["Type_Cours_FR"].isin(selected_types)]
    if selected_profils and "Profil client" in df_p.columns:
        # Keep rows where at least one selected tag appears in the comma-separated profile
        _prof_mask = df_p["Profil client"].apply(
            lambda v: any(tag in str(v) for tag in selected_profils) if pd.notna(v) else False
        )
        df_p = df_p[_prof_mask]
    
    if len(df_p) == 0:
        st.warning("Aucune donnée avec ces filtres.")
        return
    
    # ── Tabs ─────────────────────────────────────────────
    tab_p1, tab_p2, tab_p3, tab_p4 = st.tabs([
        t("tab_profils_synthese"), t("tab_profils_demo"),
        t("tab_profils_nationalites"), t("tab_profils_motivation")
    ])
    
    # ════════════════════════════════════════════════════════
    # TAB P1: SYNTHÈSE
    # ════════════════════════════════════════════════════════
    with tab_p1:
        nb_clients = len(df_p)
        nb_antennes = df_p["Sede"].nunique()
        
        # Gender distribution
        genre_counts = df_p["Genre"].value_counts() if "Genre" in df_p.columns else pd.Series(dtype=int)
        nb_f = int(genre_counts.get("F", 0))
        nb_m = int(genre_counts.get("M", 0))
        nb_ns = int(genre_counts.get("Non spécifié", 0))
        
        # Age stats
        age_mean = df_p["Age_Clean"].mean() if "Age_Clean" in df_p.columns else 0
        
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        c1.metric(t('profils_nb_clients'), f"{nb_clients:,}")
        c2.metric(t('profils_nb_antennes'), f"{nb_antennes}")
        c3.metric(t('profils_pct_f'), f"{nb_f / nb_clients * 100:.1f}%" if nb_clients > 0 else "0%")
        c4.metric(t('profils_pct_m'), f"{nb_m / nb_clients * 100:.1f}%" if nb_clients > 0 else "0%")
        c5.metric(t('profils_pct_ns'), f"{nb_ns / nb_clients * 100:.1f}%" if nb_clients > 0 else "0%")
        c6.metric(t('profils_avg_age'), f"{age_mean:.1f}" if pd.notna(age_mean) else "N/A")
        
        st.markdown("---")
        
        # Clients by antenna
        st.markdown(f"#### {t('analysis_by_sede')}")
        agg_sede_p = df_p.groupby("Sede").agg(
            Nb_Clients=("Sede", "count"),
        ).reset_index()
        
        if "Genre" in df_p.columns:
            gender_sede = df_p.groupby(["Sede", "Genre"]).size().unstack(fill_value=0).reset_index()
            agg_sede_p = agg_sede_p.merge(gender_sede, on="Sede", how="left")
        
        if "Age_Clean" in df_p.columns:
            age_sede = df_p.groupby("Sede")["Age_Clean"].agg(["mean", "median"]).reset_index()
            age_sede.columns = ["Sede", "Âge_Moyen", "Âge_Médian"]
            age_sede["Âge_Moyen"] = age_sede["Âge_Moyen"].round(1)
            age_sede["Âge_Médian"] = age_sede["Âge_Médian"].round(1)
            agg_sede_p = agg_sede_p.merge(age_sede, on="Sede", how="left")
        
        st.dataframe(agg_sede_p, use_container_width=True)
        
        fig_sede_p = px.bar(
            agg_sede_p, x="Sede", y="Nb_Clients",
            color="Sede", color_discrete_map=SEDE_COLORS,
            title=t('profils_clients_by_sede')
        )
        fig_sede_p.update_layout(margin=dict(l=20, r=20, t=40, b=20), showlegend=False)
        st.plotly_chart(fig_sede_p, use_container_width=True)
        
        # Custom age brackets summary
        if "Tranche_Custom" in df_p.columns:
            st.markdown(f"#### {t('profils_age_groups')}")
            agg_tranche = df_p[df_p["Tranche_Custom"].notna()].groupby("Tranche_Custom").size().reset_index(name="Nb_Clients")
            # Order by custom brackets
            agg_tranche["_order"] = agg_tranche["Tranche_Custom"].apply(
                lambda x: CUSTOM_AGE_BRACKET_ORDER.index(x) if x in CUSTOM_AGE_BRACKET_ORDER else 99
            )
            agg_tranche = agg_tranche.sort_values("_order").drop(columns="_order")
            agg_tranche["Pct"] = (agg_tranche["Nb_Clients"] / agg_tranche["Nb_Clients"].sum() * 100).round(1)
            
            # Count missing ages
            nb_missing = int(df_p["Age_Missing"].sum()) if "Age_Missing" in df_p.columns else 0
            
            col_t1, col_t2 = st.columns(2)
            with col_t1:
                st.dataframe(agg_tranche[["Tranche_Custom", "Nb_Clients", "Pct"]].style.format({"Pct": "{:.1f}%", "Nb_Clients": "{:,}"}), use_container_width=True)
                if nb_missing > 0:
                    st.caption(f"Âge non renseigné : {nb_missing} clients ({nb_missing / nb_clients * 100:.1f}%)")
            with col_t2:
                fig_tranche = px.pie(agg_tranche, values="Nb_Clients", names="Tranche_Custom",
                                     title=t('profils_age_groups'),
                                     category_orders={"Tranche_Custom": CUSTOM_AGE_BRACKET_ORDER})
                fig_tranche.update_traces(sort=False)  # preserve bracket order
                st.plotly_chart(fig_tranche, use_container_width=True)
        
        # Course type summary (translated)
        if "Type_Cours_FR" in df_p.columns:
            st.markdown(f"#### {t('profils_by_course_type')}")
            agg_type = df_p[df_p["Type_Cours_FR"].notna()].groupby("Type_Cours_FR").size().reset_index(name="Nb_Clients")
            agg_type = agg_type.sort_values("Nb_Clients", ascending=False)
            agg_type["Pct"] = (agg_type["Nb_Clients"] / agg_type["Nb_Clients"].sum() * 100).round(1)
            
            col_ct1, col_ct2 = st.columns(2)
            with col_ct1:
                st.dataframe(agg_type.style.format({"Pct": "{:.1f}%", "Nb_Clients": "{:,}"}), use_container_width=True)
            with col_ct2:
                fig_type = px.pie(agg_type, values="Nb_Clients", names="Type_Cours_FR",
                                  title=t('profils_by_course_type'))
                st.plotly_chart(fig_type, use_container_width=True)
        
        # Student type
        if "Type d'élève" in df_p.columns:
            st.markdown(f"#### {t('profils_student_types')}")
            df_st = df_p[df_p["Type d'élève"].notna()]
            if len(df_st) > 0:
                agg_st = df_st.groupby("Type d'élève").size().reset_index(name="Nb_Clients")
                agg_st = agg_st.sort_values("Nb_Clients", ascending=False)
                agg_st["Pct"] = (agg_st["Nb_Clients"] / agg_st["Nb_Clients"].sum() * 100).round(1)
                col_st1, col_st2 = st.columns(2)
                with col_st1:
                    st.dataframe(agg_st.style.format({"Pct": "{:.1f}%", "Nb_Clients": "{:,}"}), use_container_width=True)
                with col_st2:
                    fig_st = px.pie(agg_st, values="Nb_Clients", names="Type d'élève",
                                    title=t('profils_student_types'))
                    st.plotly_chart(fig_st, use_container_width=True)
    
    # ════════════════════════════════════════════════════════
    # TAB P2: DÉMOGRAPHIE
    # ════════════════════════════════════════════════════════
    with tab_p2:
        st.markdown(f"### {t('profils_demographics')}")
        
        # Age histogram with overlay toggle
        if "Age_Clean" in df_p.columns:
            # Keep all valid ages (including very young - data is real)
            df_age_valid = df_p[df_p["Age_Clean"].notna()]
            nb_age_missing = int(df_p["Age_Missing"].sum()) if "Age_Missing" in df_p.columns else 0
            
            if len(df_age_valid) > 0:
                st.markdown(f"#### {t('age_distribution')}")
                
                # Toggle: sum vs comparison (overlay)
                col_toggle, _ = st.columns([1, 3])
                with col_toggle:
                    view_mode = st.radio(
                        "Vue", [t('profils_view_sum'), t('profils_view_compare')],
                        horizontal=True, key="profils_age_view_mode", label_visibility="collapsed"
                    )
                
                # Build the 3D chart data (needed for both modes)
                antennes_3d = sorted(df_age_valid["Sede"].unique())
                age_min_3d = int(df_age_valid["Age_Clean"].min())
                age_max_3d = int(df_age_valid["Age_Clean"].max())
                bin_edges = list(range(age_min_3d, age_max_3d + 2, 2))
                
                fig_3d = go.Figure()
                for idx, ant in enumerate(antennes_3d):
                    df_ant_3d = df_age_valid[df_age_valid["Sede"] == ant]["Age_Clean"]
                    counts, edges = np.histogram(df_ant_3d, bins=bin_edges)
                    bin_centers = [(edges[i] + edges[i+1]) / 2 for i in range(len(edges) - 1)]
                    color = SEDE_COLORS.get(ant, "#888888")
                    fig_3d.add_trace(go.Scatter3d(
                        x=bin_centers, y=[idx] * len(bin_centers), z=counts.tolist(),
                        mode="lines+markers", name=ant,
                        line=dict(color=color, width=4), marker=dict(color=color, size=3),
                    ))
                    for bc, cnt in zip(bin_centers, counts):
                        if cnt > 0:
                            fig_3d.add_trace(go.Scatter3d(
                                x=[bc, bc], y=[idx, idx], z=[0, cnt],
                                mode="lines", line=dict(color=color, width=6),
                                showlegend=False, hoverinfo="skip",
                            ))
                fig_3d.update_layout(
                    scene=dict(
                        xaxis_title="Âge",
                        yaxis=dict(title="Antenne", tickvals=list(range(len(antennes_3d))), ticktext=antennes_3d),
                        zaxis_title="Nb clients",
                        camera=dict(eye=dict(x=1.5, y=-1.8, z=0.8)),
                    ),
                    title="Distribution 3D", height=500,
                    margin=dict(l=0, r=0, t=40, b=0),
                )
                
                # 2D + 3D side by side
                col_2d, col_3d = st.columns(2)
                
                with col_2d:
                    if view_mode == t('profils_view_sum'):
                        fig_age_hist = px.histogram(
                            df_age_valid, x="Age_Clean", nbins=40,
                            title=t('profils_age_histogram'),
                            color_discrete_sequence=["#3b82f6"],
                            labels={"Age_Clean": t('profils_age')}
                        )
                        fig_age_hist.update_layout(margin=dict(l=20, r=20, t=40, b=20), height=500)
                        st.plotly_chart(fig_age_hist, use_container_width=True)
                    else:
                        fig_age_overlay = go.Figure()
                        antennes = sorted(df_age_valid["Sede"].unique())
                        for i, ant in enumerate(antennes):
                            df_ant = df_age_valid[df_age_valid["Sede"] == ant]
                            color = SEDE_COLORS.get(ant, "#888888")
                            fig_age_overlay.add_trace(go.Histogram(
                                x=df_ant["Age_Clean"], name=ant, opacity=0.55,
                                marker_color=color, nbinsx=40,
                            ))
                        fig_age_overlay.update_layout(
                            barmode="overlay", title=t('profils_age_overlay'),
                            xaxis_title=t('profils_age'), yaxis_title="Nb clients",
                            margin=dict(l=20, r=20, t=40, b=20), height=500,
                            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                        )
                        st.plotly_chart(fig_age_overlay, use_container_width=True)
                
                with col_3d:
                    st.plotly_chart(fig_3d, use_container_width=True)
                
                # Age stats (exclude age < 3)
                c1, c2, c3, c4 = st.columns(4)
                c1.metric(t('profils_avg_age'), f"{df_age_valid['Age_Clean'].mean():.1f}")
                c2.metric(t('profils_median_age'), f"{df_age_valid['Age_Clean'].median():.0f}")
                c3.metric(t('profils_min_age'), f"{df_age_valid['Age_Clean'].min():.0f}")
                c4.metric(t('profils_max_age'), f"{df_age_valid['Age_Clean'].max():.0f}")
                
                # Show info about excluded/missing ages
                info_parts = []
                if nb_age_missing > 0:
                    info_parts.append(f"Âge non renseigné : {nb_age_missing}")
                if info_parts:
                    st.caption(" | ".join(info_parts))
                
                # Age by antenna (box plot)
                st.markdown(f"#### {t('profils_age_by_sede')}")
                fig_age_sede = px.box(
                    df_age_valid, x="Sede", y="Age_Clean",
                    title=t('profils_age_by_sede'),
                    color="Sede", color_discrete_map=SEDE_COLORS,
                    labels={"Age_Clean": t('profils_age')}
                )
                fig_age_sede.update_layout(margin=dict(l=20, r=20, t=40, b=20), showlegend=False)
                st.plotly_chart(fig_age_sede, use_container_width=True)
        
        # Gender breakdown
        if "Genre" in df_p.columns:
            st.markdown(f"#### {t('profils_gender')}")
            gender_sede_data = df_p.groupby(["Sede", "Genre"]).size().reset_index(name="Nb")
            fig_gender = px.bar(
                gender_sede_data, x="Sede", y="Nb", color="Genre",
                barmode="group", title=t('profils_gender_by_sede'),
                color_discrete_map={"F": "#ec4899", "M": "#3b82f6", "Non spécifié": "#a855f7"}
            )
            fig_gender.update_layout(margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig_gender, use_container_width=True)
        
        # Custom age brackets by antenna
        if "Tranche_Custom" in df_p.columns:
            st.markdown(f"#### {t('profils_age_groups_by_antenna')}")
            tranche_sede = df_p[df_p["Tranche_Custom"].notna()].groupby(["Sede", "Tranche_Custom"]).size().reset_index(name="Nb")
            tranche_sede["_order"] = tranche_sede["Tranche_Custom"].apply(
                lambda x: CUSTOM_AGE_BRACKET_ORDER.index(x) if x in CUSTOM_AGE_BRACKET_ORDER else 99
            )
            tranche_sede = tranche_sede.sort_values("_order").drop(columns="_order")
            fig_tranche_sede = px.bar(
                tranche_sede, x="Sede", y="Nb", color="Tranche_Custom",
                barmode="group", title=t('profils_age_groups_by_antenna'),
                category_orders={"Tranche_Custom": CUSTOM_AGE_BRACKET_ORDER},
            )
            fig_tranche_sede.update_layout(margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig_tranche_sede, use_container_width=True)
        
        # Niveau breakdown - progressive order
        if "Niveau suivi" in df_p.columns:
            st.markdown(f"#### {t('profils_levels_progressive')}")
            agg_niveau_p = df_p[df_p["Niveau suivi"].notna()].groupby("Niveau suivi").size().reset_index(name="Nb_Clients")
            
            # Sort by progressive order
            known_levels = [lv for lv in LEVEL_ORDER if lv in agg_niveau_p["Niveau suivi"].values]
            other_levels = [lv for lv in agg_niveau_p["Niveau suivi"].values if lv not in LEVEL_ORDER]
            level_order_full = known_levels + sorted(other_levels)
            
            agg_niveau_p["_order"] = agg_niveau_p["Niveau suivi"].apply(
                lambda x: level_order_full.index(x) if x in level_order_full else 999
            )
            agg_niveau_p = agg_niveau_p.sort_values("_order").drop(columns="_order")
            
            # Color scale by importance (nb clients)
            max_val = agg_niveau_p["Nb_Clients"].max() if len(agg_niveau_p) > 0 else 1
            agg_niveau_p["Intensity"] = agg_niveau_p["Nb_Clients"] / max_val
            
            fig_niveau_p = px.bar(
                agg_niveau_p, x="Niveau suivi", y="Nb_Clients",
                title=t('profils_levels_progressive'),
                color="Nb_Clients",
                color_continuous_scale="Blues",
                labels={"Nb_Clients": "Nb clients"},
                category_orders={"Niveau suivi": level_order_full},
            )
            fig_niveau_p.update_layout(margin=dict(l=20, r=20, t=40, b=80), xaxis_tickangle=-45)
            st.plotly_chart(fig_niveau_p, use_container_width=True)
            
            # Macro-levels grouped histogram
            if "Macro_Niveau" in df_p.columns:
                st.markdown(f"#### {t('profils_macro_levels')}")
                agg_macro = df_p[df_p["Macro_Niveau"].notna()].groupby("Macro_Niveau").size().reset_index(name="Nb_Clients")
                agg_macro["_order"] = agg_macro["Macro_Niveau"].apply(
                    lambda x: MACRO_LEVEL_ORDER.index(x) if x in MACRO_LEVEL_ORDER else 99
                )
                agg_macro = agg_macro.sort_values("_order").drop(columns="_order")
                
                macro_colors = {
                    "A0": "#e0f2fe", "A1": "#7dd3fc", "A2": "#38bdf8",
                    "B1": "#0284c7", "B2": "#0369a1",
                    "C1": "#075985", "C2": "#0c4a6e",
                    "Autre": "#94a3b8"
                }
                
                fig_macro = px.bar(
                    agg_macro, x="Macro_Niveau", y="Nb_Clients",
                    title=t('profils_macro_levels'),
                    color="Macro_Niveau",
                    color_discrete_map=macro_colors,
                    category_orders={"Macro_Niveau": MACRO_LEVEL_ORDER + ["Autre"]},
                    text="Nb_Clients",
                )
                fig_macro.update_layout(margin=dict(l=20, r=20, t=40, b=20), showlegend=False)
                fig_macro.update_traces(textposition="outside")
                st.plotly_chart(fig_macro, use_container_width=True)
        
        # Student type section
        if "Type d'élève" in df_p.columns:
            st.markdown(f"#### {t('profils_student_types')}")
            df_st = df_p[df_p["Type d'élève"].notna()]
            if len(df_st) > 0:
                agg_st = df_st.groupby("Type d'élève").size().reset_index(name="Nb_Clients")
                agg_st = agg_st.sort_values("Nb_Clients", ascending=False)
                agg_st["Pct"] = (agg_st["Nb_Clients"] / agg_st["Nb_Clients"].sum() * 100).round(1)
                
                fig_st = px.bar(
                    agg_st, x="Type d'élève", y="Nb_Clients",
                    title=t('profils_student_types'),
                    color_discrete_sequence=["#f59e0b"],
                    text="Nb_Clients",
                )
                fig_st.update_layout(margin=dict(l=20, r=20, t=40, b=80), xaxis_tickangle=-45)
                fig_st.update_traces(textposition="outside")
                st.plotly_chart(fig_st, use_container_width=True)
    
    # ════════════════════════════════════════════════════════
    # TAB P3: NATIONALITÉS
    # ════════════════════════════════════════════════════════
    with tab_p3:
        if "Nationalité" in df_p.columns:
            st.markdown(f"### {t('profils_nationalities')}")
            
            # Separate empty/missing and actual nationalities
            df_nat_all = df_p.copy()
            df_nat_all["Nationalité_Clean"] = df_nat_all["Nationalité"].fillna("").str.strip()
            nb_not_specified = int((df_nat_all["Nationalité_Clean"] == "").sum())
            
            df_nat = df_nat_all[df_nat_all["Nationalité_Clean"] != ""]
            
            if len(df_nat) > 0:
                agg_nat = df_nat.groupby("Nationalité_Clean").size().reset_index(name="Nb_Clients")
                agg_nat = agg_nat.sort_values("Nb_Clients", ascending=False)
                total_nat = agg_nat["Nb_Clients"].sum() + nb_not_specified
                agg_nat["Pct"] = (agg_nat["Nb_Clients"] / total_nat * 100).round(1)
                
                # KPIs
                nb_nat = agg_nat["Nationalité_Clean"].nunique()
                top_nat = agg_nat.iloc[0]["Nationalité_Clean"] if len(agg_nat) > 0 else "N/A"
                top_nat_pct = agg_nat.iloc[0]["Pct"] if len(agg_nat) > 0 else 0
                
                c1, c2, c3 = st.columns(3)
                c1.metric(t('profils_nb_nationalities'), f"{nb_nat}")
                c2.metric(t('profils_top_nationality'), top_nat)
                c3.metric(t('profils_top_nat_pct'), f"{top_nat_pct:.1f}%")
                
                st.markdown("---")
                
                # Top 20 table
                st.markdown(f"#### Top 20 {t('profils_nationalities')}")
                st.dataframe(agg_nat.head(20).rename(columns={"Nationalité_Clean": "Nationalité"}).style.format({"Pct": "{:.1f}%", "Nb_Clients": "{:,}"}), use_container_width=True)
                
                # Pie chart top 10 + "Autres nationalités" + "Non indiquée"
                top_10_nat = agg_nat.head(10).copy()
                others_count = agg_nat.iloc[10:]["Nb_Clients"].sum() if len(agg_nat) > 10 else 0
                extra_rows = []
                if others_count > 0:
                    extra_rows.append({"Nationalité_Clean": t('profils_others'), "Nb_Clients": others_count})
                if nb_not_specified > 0:
                    extra_rows.append({"Nationalité_Clean": t('profils_not_specified'), "Nb_Clients": nb_not_specified})
                if extra_rows:
                    top_10_nat = pd.concat([top_10_nat, pd.DataFrame(extra_rows)], ignore_index=True)
                
                fig_nat_pie = px.pie(
                    top_10_nat, values="Nb_Clients", names="Nationalité_Clean",
                    title=f"Top 10 {t('profils_nationalities')}"
                )
                st.plotly_chart(fig_nat_pie, use_container_width=True)
                
                if nb_not_specified > 0:
                    st.caption(f"{t('profils_not_specified')} : {nb_not_specified} clients ({nb_not_specified / total_nat * 100:.1f}%)")
                
                # Nationality by antenna
                st.markdown(f"#### {t('profils_nat_by_antenna')}")
                top5_nats = agg_nat.head(5)["Nationalité_Clean"].tolist()
                df_nat_top = df_nat[df_nat["Nationalité_Clean"].isin(top5_nats)]
                nat_sede = df_nat_top.groupby(["Sede", "Nationalité_Clean"]).size().reset_index(name="Nb")
                
                fig_nat_sede = px.bar(
                    nat_sede, x="Nationalité_Clean", y="Nb", color="Sede",
                    barmode="group", title=t('profils_nat_by_antenna'),
                    color_discrete_map=SEDE_COLORS,
                    labels={"Nationalité_Clean": "Nationalité"},
                )
                fig_nat_sede.update_layout(margin=dict(l=20, r=20, t=40, b=20))
                st.plotly_chart(fig_nat_sede, use_container_width=True)
                
                # Choropleth map
                st.markdown(f"#### {t('profils_nat_map')}")
                # Map nationality names to ISO-3 codes (case-insensitive)
                agg_nat_map = agg_nat.copy()
                agg_nat_map["ISO_3"] = agg_nat_map["Nationalité_Clean"].apply(_match_nationality_to_iso)
                agg_nat_map_valid = agg_nat_map[agg_nat_map["ISO_3"].notna()]
                
                if len(agg_nat_map_valid) > 0:
                    # Aggregate by ISO code in case multiple nationality names map to same country
                    agg_map = agg_nat_map_valid.groupby("ISO_3").agg(
                        Nb_Clients=("Nb_Clients", "sum"),
                        Nationalité=("Nationalité_Clean", "first")
                    ).reset_index()
                    
                    # Use log scale to handle extreme range (e.g. Italy vs small countries)
                    agg_map["Nb_Log"] = np.log10(agg_map["Nb_Clients"].clip(lower=1))
                    max_log = agg_map["Nb_Log"].max()
                    
                    fig_map = px.choropleth(
                        agg_map,
                        locations="ISO_3",
                        color="Nb_Log",
                        hover_name="Nationalité",
                        hover_data={"Nb_Clients": True, "Nb_Log": False, "ISO_3": False},
                        color_continuous_scale="Blues",
                        title=t('profils_nat_map'),
                        labels={"Nb_Log": "Log₁₀(clients)", "Nb_Clients": "Nb clients"},
                    )
                    # Custom colorbar with real values
                    tick_vals = [0, 1, 2, 3, 4]
                    tick_text = ["1", "10", "100", "1k", "10k"]
                    tick_vals_f = [v for v in tick_vals if v <= max_log + 0.5]
                    tick_text_f = tick_text[:len(tick_vals_f)]
                    fig_map.update_layout(
                        margin=dict(l=0, r=0, t=40, b=0),
                        geo=dict(showframe=False, showcoastlines=True, projection_type="natural earth"),
                        coloraxis_colorbar=dict(
                            title="Nb clients",
                            tickvals=tick_vals_f,
                            ticktext=tick_text_f,
                        ),
                    )
                    st.plotly_chart(fig_map, use_container_width=True)
                else:
                    unmatched = agg_nat_map[agg_nat_map["ISO_3"].isna()]["Nationalité_Clean"].tolist()
                    st.info(f"Aucune correspondance trouvée pour la carte. Nationalités non reconnues : {', '.join(unmatched[:15])}")
                
                # Show unmatched info after the map too
                unmatched_nats = agg_nat_map[agg_nat_map["ISO_3"].isna()]
                if len(unmatched_nats) > 0 and len(agg_nat_map_valid) > 0:
                    with st.expander(f"{len(unmatched_nats)} nationalité(s) non placée(s) sur la carte"):
                        st.dataframe(unmatched_nats[["Nationalité_Clean", "Nb_Clients"]].rename(columns={"Nationalité_Clean": "Nationalité"}), use_container_width=True)
        else:
            st.info("Colonne 'Nationalité' non trouvée dans l'export.")
    
    # ════════════════════════════════════════════════════════
    # TAB P4: MOTIVATION & ACQUISITION
    # ════════════════════════════════════════════════════════
    with tab_p4:
        st.markdown(f"### {t('profils_motivation_acq')}")
        
        # Motivation
        if "Motivation" in df_p.columns:
            st.markdown(f"#### {t('profils_motivation')}")
            df_motiv = df_p[df_p["Motivation"].notna()]
            if len(df_motiv) > 0:
                agg_motiv = df_motiv.groupby("Motivation").size().reset_index(name="Nb_Clients")
                agg_motiv = agg_motiv.sort_values("Nb_Clients", ascending=False)
                agg_motiv["Pct"] = (agg_motiv["Nb_Clients"] / agg_motiv["Nb_Clients"].sum() * 100).round(1)
                
                col_m1, col_m2 = st.columns(2)
                with col_m1:
                    st.dataframe(agg_motiv.style.format({"Pct": "{:.1f}%", "Nb_Clients": "{:,}"}), use_container_width=True)
                with col_m2:
                    fig_motiv = px.pie(agg_motiv, values="Nb_Clients", names="Motivation",
                                       title=t('profils_motivation'))
                    st.plotly_chart(fig_motiv, use_container_width=True)
                
                # Motivation by antenna - PERCENTAGE
                st.markdown(f"#### {t('profils_motivation_by_antenna')}")
                motiv_sede = df_motiv.groupby(["Sede", "Motivation"]).size().reset_index(name="Nb")
                motiv_sede_total = motiv_sede.groupby("Sede")["Nb"].transform("sum")
                motiv_sede["Pct"] = (motiv_sede["Nb"] / motiv_sede_total * 100).round(1)
                fig_motiv_sede = px.bar(
                    motiv_sede, x="Motivation", y="Pct", color="Sede",
                    barmode="group", title=t('profils_motivation_by_antenna'),
                    color_discrete_map=SEDE_COLORS,
                    labels={"Pct": "%"},
                )
                fig_motiv_sede.update_layout(margin=dict(l=20, r=20, t=40, b=80), xaxis_tickangle=-45)
                st.plotly_chart(fig_motiv_sede, use_container_width=True)
        
        # Channel (Comment nous avez-vous connu ?)
        canal_col = None
        for c in df_p.columns:
            if "comment" in c.lower() and "connu" in c.lower():
                canal_col = c
                break
        
        if canal_col and canal_col in df_p.columns:
            st.markdown(f"#### {t('profils_acquisition')}")
            df_canal = df_p[df_p[canal_col].notna()]
            if len(df_canal) > 0:
                agg_canal = df_canal.groupby(canal_col).size().reset_index(name="Nb_Clients")
                agg_canal = agg_canal.sort_values("Nb_Clients", ascending=False)
                agg_canal["Pct"] = (agg_canal["Nb_Clients"] / agg_canal["Nb_Clients"].sum() * 100).round(1)
                
                col_a1, col_a2 = st.columns(2)
                with col_a1:
                    st.dataframe(agg_canal.style.format({"Pct": "{:.1f}%", "Nb_Clients": "{:,}"}), use_container_width=True)
                with col_a2:
                    fig_canal = px.pie(agg_canal, values="Nb_Clients", names=canal_col,
                                       title=t('profils_acquisition'))
                    st.plotly_chart(fig_canal, use_container_width=True)
                
                # Channel by antenna - TOP 5, PERCENTAGE
                st.markdown(f"#### {t('profils_acquisition_by_antenna')}")
                top5_canaux = agg_canal.head(5)[canal_col].tolist()
                canal_sede = df_canal.groupby(["Sede", canal_col]).size().reset_index(name="Nb")
                canal_sede_top = canal_sede[canal_sede[canal_col].isin(top5_canaux)]
                canal_sede_total = canal_sede_top.groupby("Sede")["Nb"].transform("sum")
                canal_sede_top = canal_sede_top.copy()
                canal_sede_top["Pct"] = (canal_sede_top["Nb"] / canal_sede_total * 100).round(1)
                fig_canal_sede = px.bar(
                    canal_sede_top, x=canal_col, y="Pct", color="Sede",
                    barmode="group", title=t('profils_acquisition_by_antenna'),
                    color_discrete_map=SEDE_COLORS,
                    labels={"Pct": "%"},
                )
                fig_canal_sede.update_layout(margin=dict(l=20, r=20, t=40, b=80), xaxis_tickangle=-45)
                st.plotly_chart(fig_canal_sede, use_container_width=True)
        
        # CSP (Catégorie socio-professionnelle)
        if "Catégorie socio-professionnelle" in df_p.columns:
            st.markdown(f"#### {t('profils_csp')}")
            df_csp = df_p[df_p["Catégorie socio-professionnelle"].notna()]
            if len(df_csp) > 0:
                agg_csp = df_csp.groupby("Catégorie socio-professionnelle").size().reset_index(name="Nb_Clients")
                agg_csp = agg_csp.sort_values("Nb_Clients", ascending=False)
                agg_csp["Pct"] = (agg_csp["Nb_Clients"] / agg_csp["Nb_Clients"].sum() * 100).round(1)
                
                st.dataframe(agg_csp.head(15).style.format({"Pct": "{:.1f}%", "Nb_Clients": "{:,}"}), use_container_width=True)
                
                fig_csp = px.bar(
                    agg_csp.head(10), x="Catégorie socio-professionnelle", y="Nb_Clients",
                    title=f"Top 10 {t('profils_csp')}",
                    color_discrete_sequence=["#8b5cf6"]
                )
                fig_csp.update_layout(margin=dict(l=20, r=20, t=40, b=80), xaxis_tickangle=-45)
                st.plotly_chart(fig_csp, use_container_width=True)

    # ── Export CSV ──
    st.divider()
    _csv_profils = df_profils.to_csv(index=False).encode('utf-8')
    st.download_button(
        label=f"⬇️ {t('download_csv')} — Profils",
        data=_csv_profils,
        file_name="export_profils_clients.csv",
        mime="text/csv",
        use_container_width=True,
        key="dl_profils"
    )

# =====================================================
# PRODUCTS CATALOG EXPORT SUPPORT
# =====================================================

def extract_sede_from_filename(filename):
    """Extract sede code from product export filename."""
    fn_upper = filename.upper()
    for code in ["IFM", "IFF", "IFN", "IFP"]:
        if code in fn_upper:
            return code
    fn_lower = filename.lower()
    for city, code in CENTRE_TO_SEDE.items():
        if city.lower() in fn_lower:
            return code
    return "???"

def process_produits(df, sede_code="???"):
    """Process the products catalog export DataFrame."""
    df = df.copy()
    df["Sede"] = sede_code
    
    # Parse numeric columns
    num_cols = ["Prix", "Tarif réduit", "Prix membre", "Ventes", "Heures",
                "Nombre d'UE", "Nombre maximum de places"]
    for col in num_cols:
        if col in df.columns:
            df[col] = df[col].apply(parse_french_number)
    
    # Clean boolean columns
    if "Actif ?" in df.columns:
        df["Actif"] = df["Actif ?"].apply(
            lambda x: True if str(x).strip().lower() in ["oui", "yes", "true", "1", "vrai"] else False
        )
    
    return df

def render_produits_tabs(df_produits):
    """Render analysis tabs for products catalog export data."""
    
    st.markdown(f"## {t('produits_section')}")
    
    # Filters 
    st.markdown(f"### {t('filters')}")
    col_f1, col_f2, col_f3 = st.columns(3)
    
    with col_f1:
        available_sedi_pr = sorted([s for s in df_produits["Sede"].unique() if s != "???"])
        selected_sedi_pr = st.multiselect(
            t('filter_by_sede'), available_sedi_pr, default=[], key="produits_sedi",
            placeholder="Toutes"
        )
    
    with col_f2:
        if "Type de produit" in df_produits.columns:
            all_prod_types = sorted(df_produits["Type de produit"].dropna().unique())
            selected_prod_types = st.multiselect(
                t('produits_filter_type'), all_prod_types, default=[], key="produits_types",
                placeholder="Tous"
            )
        else:
            selected_prod_types = None
    
    with col_f3:
        if "Actif" in df_produits.columns:
            actif_options = [t('all'), t('produits_active_only'), t('produits_inactive_only')]
            selected_actif = st.selectbox(t('produits_status'), actif_options, key="produits_actif")
        else:
            selected_actif = t('all')
    
    # Apply filters (empty selection = no filter = all)
    df_pr = df_produits.copy()
    if selected_sedi_pr:
        df_pr = df_pr[df_pr["Sede"].isin(selected_sedi_pr)]
    if selected_prod_types:
        df_pr = df_pr[df_pr["Type de produit"].isin(selected_prod_types)]
    if "Actif" in df_pr.columns:
        if selected_actif == t('produits_active_only'):
            df_pr = df_pr[df_pr["Actif"] == True]
        elif selected_actif == t('produits_inactive_only'):
            df_pr = df_pr[df_pr["Actif"] == False]
    
    if len(df_pr) == 0:
        st.warning("Aucune donnée avec ces filtres.")
        return
    
    # Tabs 
    tab_pr1, tab_pr2, tab_pr3 = st.tabs([
        t("tab_produits_catalogue"), t("tab_produits_types"), t("tab_produits_tarifs")
    ])
    
    # TAB PR1: CATALOGUE 
    with tab_pr1:
        nb_produits = len(df_pr)
        nb_types = df_pr["Type de produit"].nunique() if "Type de produit" in df_pr.columns else 0
        nb_actifs = int(df_pr["Actif"].sum()) if "Actif" in df_pr.columns else nb_produits
        prix_moyen = df_pr["Prix"].mean() if "Prix" in df_pr.columns else 0
        total_heures = df_pr["Heures"].sum() if "Heures" in df_pr.columns else 0
        capacite_totale = df_pr["Nombre maximum de places"].sum() if "Nombre maximum de places" in df_pr.columns else 0
        
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        c1.metric(t('produits_nb_products'), f"{nb_produits:,}")
        c2.metric(t('produits_nb_types'), f"{nb_types}")
        c3.metric(t('produits_nb_active'), f"{nb_actifs:,}")
        c4.metric(t('produits_avg_price'), f"{prix_moyen:,.0f} €")
        c5.metric(t('produits_total_hours'), f"{total_heures:,.0f}")
        c6.metric(t('produits_total_capacity'), f"{capacite_totale:,.0f}")
        
        st.markdown("---")
        
        # Products by sede
        st.markdown(f"#### {t('produits_by_sede')}")
        agg_sede_pr = df_pr.groupby("Sede").agg(
            Nb_Produits=("Sede", "count"),
        ).reset_index()
        if "Prix" in df_pr.columns:
            prix_sede = df_pr.groupby("Sede")["Prix"].mean().reset_index()
            prix_sede.columns = ["Sede", "Prix_Moyen"]
            prix_sede["Prix_Moyen"] = prix_sede["Prix_Moyen"].round(1)
            agg_sede_pr = agg_sede_pr.merge(prix_sede, on="Sede", how="left")
        if "Heures" in df_pr.columns:
            heures_sede = df_pr.groupby("Sede")["Heures"].sum().reset_index()
            heures_sede.columns = ["Sede", "Total_Heures"]
            agg_sede_pr = agg_sede_pr.merge(heures_sede, on="Sede", how="left")
        
        st.dataframe(agg_sede_pr, use_container_width=True)
        
        fig_sede_pr = px.bar(
            agg_sede_pr, x="Sede", y="Nb_Produits",
            color="Sede", color_discrete_map=SEDE_COLORS,
            title=t('produits_by_sede')
        )
        fig_sede_pr.update_layout(margin=dict(l=20, r=20, t=40, b=20), showlegend=False)
        st.plotly_chart(fig_sede_pr, use_container_width=True)
        
        # Full catalog table
        st.markdown(f"#### {t('produits_full_catalog')}")
        display_cols = ["Sede", "Type de produit", "Nom du produit"]
        if "Prix" in df_pr.columns:
            display_cols.append("Prix")
        if "Heures" in df_pr.columns:
            display_cols.append("Heures")
        if "Nombre maximum de places" in df_pr.columns:
            display_cols.append("Nombre maximum de places")
        if "Actif" in df_pr.columns:
            display_cols.append("Actif")
        
        display_cols = [c for c in display_cols if c in df_pr.columns]
        fmt_dict = {}
        if "Prix" in display_cols:
            fmt_dict["Prix"] = "{:,.0f}"
        if "Heures" in display_cols:
            fmt_dict["Heures"] = "{:,.1f}"
        
        st.dataframe(df_pr[display_cols].style.format(fmt_dict), use_container_width=True, height=400)
    
    # TAB PR2: PAR TYPE DE PRODUIT 
    with tab_pr2:
        if "Type de produit" not in df_pr.columns:
            st.info("Colonne 'Type de produit' non trouvée.")
            return
        
        st.markdown(f"### {t('produits_analysis_by_type')}")
        
        agg_type_pr = df_pr.groupby("Type de produit").agg(
            Nb_Produits=("Nom du produit", "count"),
        ).reset_index()
        if "Prix" in df_pr.columns:
            prix_type = df_pr.groupby("Type de produit")["Prix"].agg(["mean", "min", "max"]).reset_index()
            prix_type.columns = ["Type de produit", "Prix_Moyen", "Prix_Min", "Prix_Max"]
            prix_type = prix_type.round(0)
            agg_type_pr = agg_type_pr.merge(prix_type, on="Type de produit", how="left")
        if "Heures" in df_pr.columns:
            heures_type = df_pr.groupby("Type de produit")["Heures"].agg(["sum", "mean"]).reset_index()
            heures_type.columns = ["Type de produit", "Heures_Total", "Heures_Moy"]
            heures_type = heures_type.round(1)
            agg_type_pr = agg_type_pr.merge(heures_type, on="Type de produit", how="left")
        
        agg_type_pr = agg_type_pr.sort_values("Nb_Produits", ascending=False)
        st.dataframe(agg_type_pr, use_container_width=True)
        
        fig_type_pr = px.bar(
            agg_type_pr, x="Type de produit", y="Nb_Produits",
            title=t('produits_analysis_by_type'),
            color_discrete_sequence=["#3b82f6"]
        )
        fig_type_pr.update_layout(margin=dict(l=20, r=20, t=40, b=100), xaxis_tickangle=-45)
        st.plotly_chart(fig_type_pr, use_container_width=True)
        
        # Type by sede
        st.markdown(f"#### {t('produits_type_by_sede')}")
        type_sede = df_pr.groupby(["Type de produit", "Sede"]).size().reset_index(name="Nb_Produits")
        fig_type_sede = px.bar(
            type_sede, x="Type de produit", y="Nb_Produits", color="Sede",
            barmode="group", title=f"{t('produits_analysis_by_type')} - {t('by_sede')}",
            color_discrete_map=SEDE_COLORS
        )
        fig_type_sede.update_layout(margin=dict(l=20, r=20, t=40, b=100), xaxis_tickangle=-45)
        st.plotly_chart(fig_type_sede, use_container_width=True)
        
        # Price comparison by type
        if "Prix" in df_pr.columns:
            st.markdown(f"#### {t('produits_price_comparison')}")
            fig_price_comp = px.box(
                df_pr, x="Type de produit", y="Prix", color="Sede",
                title=t('produits_price_comparison'),
                color_discrete_map=SEDE_COLORS
            )
            fig_price_comp.update_layout(margin=dict(l=20, r=20, t=40, b=100), xaxis_tickangle=-45)
            st.plotly_chart(fig_price_comp, use_container_width=True)
    
    # TAB PR3: ANALYSE TARIFAIRE 
    with tab_pr3:
        st.markdown(f"### {t('produits_pricing_analysis')}")
        
        if "Prix" in df_pr.columns:
            # Price distribution
            st.markdown(f"#### {t('produits_price_distribution')}")
            fig_prix_hist = px.histogram(
                df_pr[df_pr["Prix"] > 0], x="Prix", nbins=30,
                title=t('produits_price_distribution'),
                color_discrete_sequence=["#22c55e"],
                labels={"Prix": "Prix (€)"}
            )
            fig_prix_hist.update_layout(margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig_prix_hist, use_container_width=True)
            
            # Price stats by sede
            st.markdown(f"#### {t('produits_price_stats')}")
            prix_stats = df_pr.groupby("Sede")["Prix"].agg(["count", "mean", "median", "min", "max", "std"]).reset_index()
            prix_stats.columns = ["Sede", "Nb_Produits", "Prix_Moyen", "Prix_Médian", "Prix_Min", "Prix_Max", "Écart_Type"]
            prix_stats = prix_stats.round(1)
            st.dataframe(prix_stats.style.format({
                "Prix_Moyen": "{:,.1f}", "Prix_Médian": "{:,.1f}",
                "Prix_Min": "{:,.0f}", "Prix_Max": "{:,.0f}", "Écart_Type": "{:,.1f}"
            }), use_container_width=True)
            
            # Reduced tariff analysis
            if "Tarif réduit" in df_pr.columns:
                st.markdown(f"#### {t('produits_reduced_tariff')}")
                df_tarif = df_pr[(df_pr["Tarif réduit"] > 0) & (df_pr["Prix"] > 0)].copy()
                if len(df_tarif) > 0:
                    df_tarif["Remise_Pct"] = ((df_tarif["Prix"] - df_tarif["Tarif réduit"]) / df_tarif["Prix"] * 100).round(1)
                    
                    c1, c2, c3 = st.columns(3)
                    c1.metric(t('produits_nb_with_reduction'), f"{len(df_tarif):,}")
                    c2.metric(t('produits_avg_reduction'), f"{df_tarif['Remise_Pct'].mean():.1f}%")
                    c3.metric(t('produits_max_reduction'), f"{df_tarif['Remise_Pct'].max():.1f}%")
                    
                    fig_remise = px.scatter(
                        df_tarif, x="Prix", y="Tarif réduit", color="Sede",
                        hover_data=["Nom du produit", "Type de produit"] if "Nom du produit" in df_tarif.columns else None,
                        title=t('produits_price_vs_reduced'),
                        color_discrete_map=SEDE_COLORS
                    )
                    max_prix = df_tarif["Prix"].max()
                    fig_remise.add_shape(type="line", x0=0, y0=0, x1=max_prix, y1=max_prix,
                                         line=dict(color="gray", width=1, dash="dash"))
                    fig_remise.update_layout(margin=dict(l=20, r=20, t=40, b=20))
                    st.plotly_chart(fig_remise, use_container_width=True)
            
            # Member price analysis
            if "Prix membre" in df_pr.columns:
                st.markdown(f"#### {t('produits_member_price')}")
                df_membre = df_pr[(df_pr["Prix membre"] > 0) & (df_pr["Prix"] > 0)].copy()
                if len(df_membre) > 0:
                    df_membre["Avantage_Pct"] = ((df_membre["Prix"] - df_membre["Prix membre"]) / df_membre["Prix"] * 100).round(1)
                    
                    c1, c2 = st.columns(2)
                    c1.metric(t('produits_nb_member_price'), f"{len(df_membre):,}")
                    c2.metric(t('produits_avg_member_advantage'), f"{df_membre['Avantage_Pct'].mean():.1f}%")
            
            # Hours analysis
            if "Heures" in df_pr.columns:
                st.markdown(f"#### {t('produits_hours_analysis')}")
                df_heures = df_pr[df_pr["Heures"] > 0]
                if len(df_heures) > 0 and "Prix" in df_heures.columns:
                    df_heures = df_heures.copy()
                    df_heures["Prix_Par_Heure"] = (df_heures["Prix"] / df_heures["Heures"]).round(1)
                    
                    prix_heure_by_type = df_heures.groupby("Type de produit")["Prix_Par_Heure"].agg(["mean", "count"]).reset_index()
                    prix_heure_by_type.columns = ["Type de produit", "Prix_Moyen_Par_Heure", "Nb_Produits"]
                    prix_heure_by_type = prix_heure_by_type.sort_values("Prix_Moyen_Par_Heure", ascending=False)
                    prix_heure_by_type["Prix_Moyen_Par_Heure"] = prix_heure_by_type["Prix_Moyen_Par_Heure"].round(1)
                    
                    st.dataframe(prix_heure_by_type.style.format({
                        "Prix_Moyen_Par_Heure": "{:,.1f} €/h"
                    }), use_container_width=True)
                    
                    fig_prix_h = px.bar(
                        prix_heure_by_type, x="Type de produit", y="Prix_Moyen_Par_Heure",
                        title=t('produits_price_per_hour'),
                        color_discrete_sequence=["#f59e0b"]
                    )
                    fig_prix_h.update_layout(margin=dict(l=20, r=20, t=40, b=100), xaxis_tickangle=-45)
                    st.plotly_chart(fig_prix_h, use_container_width=True)

    # ── Export CSV ──
    st.divider()
    _csv_produits = df_produits.to_csv(index=False).encode('utf-8')
    st.download_button(
        label=f"⬇️ {t('download_csv')} — Produits",
        data=_csv_produits,
        file_name="export_produits.csv",
        mime="text/csv",
        use_container_width=True,
        key="dl_produits"
    )


# =====================================================
# AI ASSISTANT CLASS
# =====================================================
class DataAssistant:
    def __init__(self, df):
        self.df = df
        self.inscr_col = "Nb. d'inscriptions"
        self.context = self._build_context()
    
    def _build_context(self):
        ctx = {}
        ctx['total_inscriptions'] = int(self.df[self.inscr_col].sum())
        ctx['total_courses'] = int(self.df["Nb. de Cours"].sum())
        ctx['total_revenue'] = float(self.df["Recettes"].sum()) if "Recettes" in self.df.columns else 0
        ctx['by_sede'] = self.df.groupby("Sede").agg({
            self.inscr_col: "sum", "Nb. de Cours": "sum", "Recettes": "sum"
        }).to_dict('index')
        ctx['by_sector'] = self.df.groupby("Secteur").agg({
            self.inscr_col: "sum", "Nb. de Cours": "sum"
        }).to_dict('index')
        if "Semestre" in self.df.columns:
            ctx['by_semester'] = self.df.groupby("Semestre")[self.inscr_col].sum().to_dict()
        return ctx
    
    def get_insights(self):
        insights = []
        total = self.context['total_inscriptions']
        sedi = sorted(self.context['by_sede'].items(), key=lambda x: x[1][self.inscr_col], reverse=True)
        if sedi:
            top = sedi[0]
            top_inscr = top[1][self.inscr_col]
            pct = top_inscr / total * 100
            insights.append(f"<strong>{top[0]}</strong> {t('dominates_with')} {pct:.0f}% {t('of_inscriptions')} ({top_inscr:,.0f})")
        if self.context['total_revenue'] > 0:
            rev_per = self.context['total_revenue'] / total
            insights.append(f"{t('avg_revenue_per_inscr')}: <strong>€{rev_per:.0f}</strong>")
        if self.context.get('by_semester'):
            sem1 = self.context['by_semester'].get('sem1', 0)
            sem2 = self.context['by_semester'].get('sem2', 0)
            if sem1 > 0 and sem2 > 0:
                if sem1 > sem2:
                    diff = (sem1 - sem2) / sem2 * 100
                    insights.append(f"{t('sem1_beats_sem2')} <strong>{diff:.0f}%</strong>")
                else:
                    diff = (sem2 - sem1) / sem1 * 100
                    insights.append(f"{t('sem2_beats_sem1')} <strong>{diff:.0f}%</strong>")
        secteurs = sorted(self.context['by_sector'].items(), key=lambda x: x[1][self.inscr_col], reverse=True)
        if secteurs:
            top_sector = secteurs[0]
            pct = top_sector[1][self.inscr_col] / total * 100
            insights.append(f"{t('dominant_sector')}: <strong>{top_sector[0]}</strong> ({pct:.0f}%)")
        return insights
    
    def answer(self, question):
        q = question.lower().strip()
        total = self.context['total_inscriptions']
        if any(word in q for word in ["inscri", "iscriz", "total", "combien", "quant"]):
            lines = [f"<strong>{t('total_inscriptions')}</strong>: {format_number(total)}", "", f"{t('by_sede')}:"]
            for sede, data in self.context['by_sede'].items():
                inscr = data[self.inscr_col]
                pct = inscr / total * 100
                lines.append(f"• {sede}: {format_number(inscr)} ({pct:.1f}%)")
            return "<br>".join(lines)
        if any(word in q for word in ["recettes", "ricavi", "revenue", "fatturato"]):
            lines = [f"<strong>{t('total_revenue')}</strong>: {format_number(self.context['total_revenue'], '€')}", "", f"{t('by_sede')}:"]
            for sede, data in self.context['by_sede'].items():
                lines.append(f"• {sede}: €{data['Recettes']:,.0f}")
            return "<br>".join(lines)
        if any(word in q for word in ["meilleur", "migliore", "best", "top"]):
            best = max(self.context['by_sede'].items(), key=lambda x: x[1][self.inscr_col])
            best_inscr = best[1][self.inscr_col]
            best_recettes = best[1]['Recettes']
            return f"<strong>{t('best_sede')}</strong>: {best[0]}<br>• {t('inscriptions')}: {format_number(best_inscr)}<br>• {t('revenue')}: €{best_recettes:,.0f}"
        if "compar" in q or "vs" in q or "confronta" in q:
            for s1 in ["ifm", "iff", "ifn", "ifp"]:
                for s2 in ["ifm", "iff", "ifn", "ifp"]:
                    if s1 != s2 and s1 in q and s2 in q:
                        d1 = self.context['by_sede'].get(s1.upper(), {})
                        d2 = self.context['by_sede'].get(s2.upper(), {})
                        if d1 and d2:
                            inscr1 = d1.get(self.inscr_col, 0)
                            inscr2 = d2.get(self.inscr_col, 0)
                            rec1 = d1.get('Recettes', 0)
                            rec2 = d2.get('Recettes', 0)
                            return f"<strong>{s1.upper()} vs {s2.upper()}</strong><br><br>| | {s1.upper()} | {s2.upper()} |<br>|---|---|---|<br>| {t('inscriptions')} | {inscr1:,} | {inscr2:,} |<br>| {t('revenue')} | €{rec1:,.0f} | €{rec2:,.0f} |"
        for sede in ["IFM", "IFF", "IFN", "IFP"]:
            if sede.lower() in q:
                data = self.context['by_sede'].get(sede, {})
                if data:
                    inscr = data[self.inscr_col]
                    pct = inscr / total * 100
                    return f"<strong>{sede}</strong><br>• {t('inscriptions')}: {format_number(inscr)} ({pct:.1f}%)<br>• {t('courses')}: {data['Nb. de Cours']}<br>• {t('revenue')}: €{data['Recettes']:,.0f}"
        return f"""<strong>{t('possible_questions')}:</strong><br>
• "{t('q_total_inscr')}"<br>
• "{t('q_revenue')}"<br>
• "{t('q_best_sede')}"<br>
• "{t('q_compare')}"<br>
• "{t('q_about')}"
"""

# =====================================================
# SIDEBAR
# =====================================================

# Check for preloaded data files (available on Streamlit Cloud)
import os
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "data")
PRELOADED_FILES = {}       # year -> zip path (category reports)
PRELOADED_CLIENTS = []     # list of csv paths
PRELOADED_PRODUITS = []    # list of xlsx paths

if os.path.exists(DATA_DIR):
    for filename in os.listdir(DATA_DIR):
        filepath = os.path.join(DATA_DIR, filename)
        if filename.endswith('.zip') and 'exports_AEC_' in filename:
            # Extract year from filename: exports_AEC_2024_annuel.zip -> 2024
            match = re.search(r'exports_AEC_(\d{4})_annuel\.zip', filename)
            if match:
                year = match.group(1)
                PRELOADED_FILES[year] = filepath
        elif filename.endswith('.csv') and 'clients' in filename.lower():
            PRELOADED_CLIENTS.append(filepath)
        elif filename.endswith('.xlsx') and 'produits' in filename.lower():
            PRELOADED_PRODUITS.append(filepath)

HAS_PRELOADED_DATA = bool(PRELOADED_FILES) or bool(PRELOADED_CLIENTS) or bool(PRELOADED_PRODUITS)

with st.sidebar:
    # ── Branding ──
    import base64 as _b64
    _logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "IFI_noir_logo.png")
    _logo_html = ""
    if os.path.exists(_logo_path):
        with open(_logo_path, "rb") as _f:
            _logo_b64 = _b64.b64encode(_f.read()).decode()
        _logo_html = f'<img src="data:image/png;base64,{_logo_b64}" style="width:80px; display:block; margin-bottom:10px;">'
    st.markdown(f"""
    <div style="padding:0; text-align:left;">
    {_logo_html}
    <div style="font-size:1.3rem; font-weight:800; letter-spacing:0.12em; color:#1a1a1a; line-height:1.2;">O.S.C.A.R.</div>
    <div style="font-size:0.55rem; color:#94a3b8; margin-top:2px;">Outil de Suivi des Cours et d'Analyse du Réseau</div>
    </div>
    """, unsafe_allow_html=True)

    # ── Utilisateur + déconnexion ──
    _user_col, _logout_col = st.columns([3, 2])
    with _user_col:
        st.markdown(f"<span style='font-size:0.8rem;color:#475569;'>👤 {st.session_state.user_name}</span>", unsafe_allow_html=True)
    with _logout_col:
        if os.environ.get("OSCAR_DESKTOP_MODE") != "1":
            if st.button("Déconnexion", key="logout_btn", type="secondary", use_container_width=True):
                st.session_state.authenticated = False
                st.session_state.user_name = ""
                _clear_persistent_login()
                st.rerun()

    st.markdown("---")

    # ── Chargement des données ──
    with st.expander(t('load_files'), expanded=True):
        # Show preloaded files section if available
        if HAS_PRELOADED_DATA:
            st.markdown(f"**📦 {t('preloaded_files')}**")

            # --- Catégories (ZIP par année) ---
            if PRELOADED_FILES:
                st.markdown("**Catégories** (rapports par année)")
                available_years = sorted(PRELOADED_FILES.keys(), reverse=True)
                selected_years = []
                cols = st.columns(len(available_years))
                for idx, year in enumerate(available_years):
                    with cols[idx]:
                        if st.checkbox(f"{year}", key=f"check_year_{year}", value=True):
                            selected_years.append(year)

            # --- Clients ---
            load_clients = False
            if PRELOADED_CLIENTS:
                load_clients = st.checkbox("Profils", key="check_clients", value=True,
                                           help=f"{len(PRELOADED_CLIENTS)} fichier(s) disponible(s)")

            # --- Produits ---
            load_produits = False
            if PRELOADED_PRODUITS:
                load_produits = st.checkbox("Catalogue produits", key="check_produits", value=True,
                                            help=f"{len(PRELOADED_PRODUITS)} fichier(s) — IFM, IFF, IFN, IFP")

            # Single load button
            anything_selected = (PRELOADED_FILES and selected_years) or (PRELOADED_CLIENTS and load_clients) or (PRELOADED_PRODUITS and load_produits)
            if anything_selected:
                if st.button("🚀 Charger les données sélectionnées", key="load_all_preloaded", use_container_width=True, type="primary"):
                    st.session_state.stored_files = []
                    # Load category ZIPs
                    if PRELOADED_FILES and selected_years:
                        for year in selected_years:
                            zip_path = PRELOADED_FILES[year]
                            try:
                                with open(zip_path, 'rb') as f:
                                    zip_data = f.read()
                                with zipfile.ZipFile(BytesIO(zip_data), 'r') as zf:
                                    for name in zf.namelist():
                                        if name.lower().endswith(('.xlsx', '.xls')) and not name.startswith('__MACOSX'):
                                            file_data = zf.read(name)
                                            st.session_state.stored_files.append({
                                                'name': name.split('/')[-1],
                                                'data': file_data
                                            })
                            except Exception as e:
                                st.error(f"Erreur catégories {year}: {e}")
                    # Load clients CSVs
                    if PRELOADED_CLIENTS and load_clients:
                        for csv_path in PRELOADED_CLIENTS:
                            try:
                                with open(csv_path, 'rb') as f:
                                    st.session_state.stored_files.append({
                                        'name': os.path.basename(csv_path),
                                        'data': f.read()
                                    })
                            except Exception as e:
                                st.error(f"Erreur clients: {e}")
                    # Load produits XLSX
                    if PRELOADED_PRODUITS and load_produits:
                        for xlsx_path in PRELOADED_PRODUITS:
                            try:
                                with open(xlsx_path, 'rb') as f:
                                    st.session_state.stored_files.append({
                                        'name': os.path.basename(xlsx_path),
                                        'data': f.read()
                                    })
                            except Exception as e:
                                st.error(f"Erreur produits: {e}")
                    # Clear processed data to force reprocessing
                    if 'processed_data' in st.session_state:
                        del st.session_state.processed_data
                    if 'file_info' in st.session_state:
                        del st.session_state.file_info
                    st.rerun()
            
            st.caption(t('or_upload_files'))
        else:
            st.caption(t('sedi_semesters'))

        # ── Fichiers récents ──────────────────────────────────────────────────
        recent_sessions = load_recent_sessions()
        if recent_sessions:
            st.markdown("**📂 Fichiers récents**")
            for i, session in enumerate(recent_sessions):
                col_btn, col_del = st.columns([5, 1])
                with col_btn:
                    btn_label = f"**{session['label']}**\n\n_{session['date']}_"
                    if st.button(
                        f"📂  {session['label']}  ·  {session['date']}",
                        key=f"recent_{i}",
                        use_container_width=True,
                        help="\n".join(session.get("files", []))
                    ):
                        restored = restore_recent_session(session)
                        if restored:
                            st.session_state.stored_files = restored
                            if 'processed_data' in st.session_state:
                                del st.session_state.processed_data
                            if 'file_info' in st.session_state:
                                del st.session_state.file_info
                            st.rerun()
                        else:
                            st.error("Impossible de charger cette session.")
                with col_del:
                    if st.button("🗑", key=f"del_recent_{i}", help="Supprimer de l'historique"):
                        delete_recent_session(session["zip_path"])
                        st.rerun()
            st.markdown("---")

        raw_uploaded_files = st.file_uploader(
            t('drag_files'), type=['xlsx', 'xls', 'zip', 'csv'], accept_multiple_files=True,
            help="export AEC semestre X YYYY SEDE.xlsx ou exports_AEC.zip",
            key="file_uploader"
        )
        
        # Process uploads: extract ZIP files if present
        uploaded_files = []
        if raw_uploaded_files:
            for f in raw_uploaded_files:
                if f.name.lower().endswith('.zip'):
                    # Extract Excel files from ZIP
                    try:
                        with zipfile.ZipFile(BytesIO(f.read()), 'r') as zf:
                            for name in zf.namelist():
                                if name.lower().endswith(('.xlsx', '.xls')) and not name.startswith('__MACOSX'):
                                    file_data = zf.read(name)
                                    # Create a file-like object that mimics UploadedFile
                                    class ZipExtractedFile:
                                        def __init__(self, name, data):
                                            self.name = name.split('/')[-1]  # Get just filename
                                            self._data = BytesIO(data)
                                        def read(self, size=-1):
                                            self._data.seek(0)
                                            return self._data.read(size) if size != -1 else self._data.read()
                                        def seek(self, pos, whence=0):
                                            return self._data.seek(pos, whence)
                                        def getvalue(self):
                                            return self._data.getvalue()
                                    uploaded_files.append(ZipExtractedFile(name, file_data))
                        st.info(f"ZIP extrait: {f.name}")
                    except Exception as e:
                        st.error(f"Erreur extraction ZIP: {e}")
                else:
                    uploaded_files.append(f)
            
            # Store raw file data in session state for persistence across refreshes
            # Always update when we have new uploaded files
            if uploaded_files:
                st.session_state.stored_files = []
                for f in uploaded_files:
                    if hasattr(f, 'getvalue'):
                        st.session_state.stored_files.append({
                            'name': f.name,
                            'data': f.getvalue()
                        })
                    elif hasattr(f, 'read'):
                        f.seek(0)
                        st.session_state.stored_files.append({
                            'name': f.name,
                            'data': f.read()
                        })
                # ── Save to recent files (persists across app restarts) ──
                save_recent_session(st.session_state.stored_files)
        
        # If no new upload, try to use stored files from session state
        if not uploaded_files and 'stored_files' in st.session_state and st.session_state.stored_files:
            class StoredFile:
                def __init__(self, name, data):
                    self.name = name
                    self._data = BytesIO(data)
                def read(self, size=-1):
                    self._data.seek(0)
                    return self._data.read(size) if size != -1 else self._data.read()
                def seek(self, pos, whence=0):
                    return self._data.seek(pos, whence)
                def getvalue(self):
                    return self._data.getvalue()
            
            uploaded_files = [StoredFile(sf['name'], sf['data']) for sf in st.session_state.stored_files]
            st.info(f" {len(uploaded_files)} fichiers restaurés depuis la session")
        
        # Button to clear stored data
        if 'stored_files' in st.session_state and st.session_state.stored_files:
            if st.button(" Effacer les données en cache", key="clear_cache"):
                del st.session_state.stored_files
                if 'processed_data' in st.session_state:
                    del st.session_state.processed_data
                if 'file_info' in st.session_state:
                    del st.session_state.file_info
                st.rerun()
    
    if uploaded_files:
        with st.expander(f"📂 {len(uploaded_files)} fichiers chargés", expanded=False):
            # Build tree structure: Year > Semester > Sede
            file_tree = {}
            csv_files = []
            produits_files = []
            for f in uploaded_files:
                if f.name.lower().endswith('.csv'):
                    csv_files.append(f.name)
                    continue
                if 'produit' in f.name.lower():
                    produits_files.append(f.name)
                    continue
                sede, sem, year = detect_from_filename(f.name)
                if sede and year:
                    if year not in file_tree:
                        file_tree[year] = {"sem1": [], "sem2": [], "annuel": []}
                    sem_key = sem if sem else "annuel"
                    file_tree[year][sem_key].append(sede)
            
            # Category reports
            if file_tree:
                st.markdown("**Catégories**")
                for year in sorted(file_tree.keys(), reverse=True):
                    sem_labels = {"sem1": "S1", "sem2": "S2", "annuel": "Annuel"}
                    parts = []
                    for sem_key in ["sem1", "sem2", "annuel"]:
                        sedi_list = file_tree[year].get(sem_key, [])
                        if sedi_list:
                            parts.append(f"{sem_labels[sem_key]}: {', '.join(sorted(sedi_list))}")
                    st.caption(f"**{year}** — {' | '.join(parts)}")
            if csv_files:
                st.markdown("**Clients**")
                for fn in csv_files:
                    st.caption(fn)
            if produits_files:
                st.markdown("**Produits**")
                for fn in produits_files:
                    st.caption(fn)

    # ── Infos ──
    st.markdown("---")
    st.caption("O.S.C.A.R. v3.0 · Institut français Italia")

# Default year fallback (when not detected from filename)
default_year = 2025

# =====================================================
# MAIN CONTENT
# =====================================================
# Use files from sidebar uploader
all_uploaded_files = uploaded_files if uploaded_files else []

if not all_uploaded_files:
    # Welcome screen
    st.markdown(f"## {t('welcome')}")
    st.markdown(f"*{t('welcome_subtitle')}*")
    
    st.markdown("---")
    
    col_left, col_right = st.columns([3, 2])
    
    with col_left:
        st.markdown(f"### {t('quick_start')}")
        st.info(t('load_files_sidebar'))
        
        st.markdown(f"#### {t('supported_exports')}")
        st.markdown(f"""
        - {t('export_type_1')}
        - {t('export_type_2')}
        - {t('export_type_3')}
        - {t('export_type_4')}
        """)
    
    with col_right:
        st.markdown(f"### {t('features')}")
        st.markdown(f"""
        - {t('feature_1')}
        - {t('feature_2')}
        - {t('feature_3')}
        - {t('feature_4')}
        - {t('feature_5')}
        - {t('feature_6')}
        - {t('feature_7')}
        """)
    
    # ── Parcours de récupération des fichiers (editable by adrien) ──
    st.markdown("---")
    _DEFAULT_INSTRUCTIONS = (
        "### 📂 Parcours de récupération des fichiers depuis AEC\n\n"
        "1. **Rapport par catégories** : AEC → *Rapports* → *Par catégories* → exporter en .xlsx "
        "(un fichier par antenne × par semestre)\n"
        "2. **Fiches de cours** : AEC → *Cours* → *Fiches de cours* → filtrer → exporter en .csv\n"
        "3. **Profils clients** : AEC → *Clients* → sélectionner les colonnes utiles → exporter en .xlsx\n"
        "4. **Catalogue produits** : AEC → *Catalogue* → *Produits* → exporter en .xlsx\n\n"
        "*Déposez ensuite les fichiers via le panneau latéral gauche.*"
    )
    _INSTR_KEY = "_welcome_instructions"
    if _INSTR_KEY not in st.session_state:
        st.session_state[_INSTR_KEY] = _DEFAULT_INSTRUCTIONS
    
    _is_admin = st.query_params.get("u", "").strip().lower() == "adrien"
    
    if _is_admin:
        with st.expander("📝 Modifier les instructions d'import (admin)", expanded=False):
            # Initialise widget state from saved instructions (only once)
            if "_instr_editor" not in st.session_state:
                st.session_state["_instr_editor"] = st.session_state[_INSTR_KEY]
            _new_text = st.text_area(
                "Instructions (Markdown)",
                height=260,
                key="_instr_editor",
            )
            _col_save, _col_reset = st.columns([1, 1])
            with _col_save:
                if st.button("💾 Sauvegarder", key="_save_instr", use_container_width=True):
                    st.session_state[_INSTR_KEY] = st.session_state["_instr_editor"]
                    st.toast("Instructions sauvegardées ✓", icon="✅")
                    st.rerun()
            with _col_reset:
                if st.button("↩️ Réinitialiser", key="_reset_instr", use_container_width=True):
                    st.session_state[_INSTR_KEY] = _DEFAULT_INSTRUCTIONS
                    st.session_state["_instr_editor"] = _DEFAULT_INSTRUCTIONS
                    st.toast("Instructions réinitialisées", icon="🔄")
                    st.rerun()
    
    st.markdown(st.session_state[_INSTR_KEY])
    
    st.stop()

# Process files - dual pipeline (category reports + course fiches)
files_to_process = all_uploaded_files

# ── Session state cache: skip re-processing if same files already processed ──
_file_names_hash = hashlib.md5("|".join(sorted(f.name for f in files_to_process)).encode()).hexdigest()[:12]
_cache_hit = (
    st.session_state.get('_files_hash') == _file_names_hash
    and st.session_state.get('processed_data') is not None
)

if _cache_hit:
    # Restore from cache — skip file parsing
    df_combined = st.session_state.processed_data
    df_fiches = st.session_state.get('course_fiches_data')
    df_profils = st.session_state.get('profils_clients_data')
    df_produits = st.session_state.get('produits_data')
    file_info = st.session_state.get('file_info', [])
    fiches_info = st.session_state.get('fiches_file_info', [])
    profils_info = st.session_state.get('profils_file_info', [])
    produits_info = st.session_state.get('produits_file_info', [])
else:
    # Full processing
    all_data, all_fiches, all_profils, all_produits = [], [], [], []
    file_info, fiches_info, profils_info, produits_info, errors = [], [], [], [], []
    with st.spinner("Traitement des fichiers en cours..."):
        for uploaded_file in files_to_process:
            # Load file (auto-detect CSV vs Excel)
            df, error = load_file_auto(uploaded_file, uploaded_file.name)
            if error:
                errors.append(f"Erreur: {uploaded_file.name}: {error}")
                continue

            # Detect export type from column structure
            export_type = detect_export_type(df)

            if export_type == "fiches_cours":
                # Course fiches export - sede/year/semester extracted from data content
                processed = process_course_fiches(df)
                all_fiches.append(processed)
                sedi_found = processed["Sede"].unique().tolist()
                years_found = [int(y) for y in processed["Année"].dropna().unique()]
                fiches_info.append({
                    "Fichier": uploaded_file.name, "Type": "Fiches cours",
                    "Sedi": ", ".join(sedi_found), "Années": ", ".join(map(str, years_found)),
                    "Lignes": len(processed)
                })
            elif export_type == "profils_clients":
                # Client profiles export
                processed = process_profils_clients(df)
                all_profils.append(processed)
                sedi_found = [s for s in processed["Sede"].unique() if s != "???"]
                profils_info.append({
                    "Fichier": uploaded_file.name, "Type": "Profils clients",
                    "Sedi": ", ".join(sedi_found),
                    "Lignes": len(processed)
                })
            elif export_type == "produits":
                # Products catalog export - sede from filename
                sede_code = extract_sede_from_filename(uploaded_file.name)
                processed = process_produits(df, sede_code)
                all_produits.append(processed)
                produits_info.append({
                    "Fichier": uploaded_file.name, "Type": "Produits",
                    "Sede": sede_code,
                    "Lignes": len(processed)
                })
            else:
                # Category report export (existing flow)
                sede, semester, year = detect_from_filename(uploaded_file.name)
                year = year or default_year
                if not sede:
                    errors.append(f"Sede non détectée: {uploaded_file.name}")
                    continue
                processed = process_data(df, year, semester, sede)
                all_data.append(processed)
                semester_label = semester if semester else "annuel"
                file_info.append({"Fichier": uploaded_file.name, "Sede": sede, "Semestre": semester_label, "Année": year, "Lignes": len(processed)})

    if errors:
        for err in errors:
            st.warning(err)

    # Build combined DataFrames
    df_combined = None
    df_fiches = None
    df_profils = None
    df_produits = None
    if all_data:
        df_combined = pd.concat(all_data, ignore_index=True)
    if all_fiches:
        df_fiches = pd.concat(all_fiches, ignore_index=True)
    if all_profils:
        df_profils = pd.concat(all_profils, ignore_index=True)
    if all_produits:
        df_produits = pd.concat(all_produits, ignore_index=True)

    has_any_data = any(x is not None for x in [df_combined, df_fiches, df_profils, df_produits])
    if not has_any_data:
        st.error("Aucune donnée valide chargée.")
        st.stop()

    # Store in session state
    st.session_state.processed_data = df_combined
    st.session_state.file_info = file_info
    st.session_state.course_fiches_data = df_fiches
    st.session_state.fiches_file_info = fiches_info
    st.session_state.profils_clients_data = df_profils
    st.session_state.profils_file_info = profils_info
    st.session_state.produits_data = df_produits
    st.session_state.produits_file_info = produits_info
    st.session_state._files_hash = _file_names_hash

    # Show detection toasts (bottom-right, auto-dismiss)
    _toast_msgs = []
    if df_fiches is not None:
        nb_fiches = len(df_fiches)
        sedi_fiches = [s for s in df_fiches["Sede"].unique() if s != "???"]
        _toast_msgs.append(f"{t('fiches_cours_loaded')}: {nb_fiches} cours ({', '.join(sedi_fiches)})")
    if df_profils is not None:
        nb_profils = len(df_profils)
        sedi_profils = [s for s in df_profils["Sede"].unique() if s != "???"]
        _toast_msgs.append(f"{t('profils_loaded')}: {nb_profils} clients ({', '.join(sedi_profils)})")
    if df_produits is not None:
        nb_produits = len(df_produits)
        sedi_produits = [s for s in df_produits["Sede"].unique() if s != "???"]
        _toast_msgs.append(f"{t('produits_loaded')}: {nb_produits} produits ({', '.join(sedi_produits)})")
    for _msg in _toast_msgs:
        st.toast(_msg, icon="\u2705")

# If no category report data, render other export analyses with tabs and stop
if df_combined is None:
    available_tabs = []
    if df_profils is not None:
        available_tabs.append("Profils")
    if df_fiches is not None:
        available_tabs.append("Fiches de cours")
    if df_produits is not None:
        available_tabs.append("Produits")
    
    if len(available_tabs) == 1:
        # Single export type - render directly without tabs
        if df_profils is not None:
            render_profils_tabs(df_profils)
        elif df_fiches is not None:
            render_fiches_tabs(df_fiches)
        elif df_produits is not None:
            render_produits_tabs(df_produits)
    else:
        # Multiple export types - use top-level tabs
        export_tabs = st.tabs(available_tabs)
        tab_idx = 0
        if df_profils is not None:
            with export_tabs[tab_idx]:
                render_profils_tabs(df_profils)
            tab_idx += 1
        if df_fiches is not None:
            with export_tabs[tab_idx]:
                render_fiches_tabs(df_fiches)
            tab_idx += 1
        if df_produits is not None:
            with export_tabs[tab_idx]:
                render_produits_tabs(df_produits)
            tab_idx += 1
    st.markdown("---")
    st.caption("O.S.C.A.R. v3.0 • Institut français Italia")
    st.stop()


# =====================================================
# TOP-LEVEL EXPORT TABS
# =====================================================
_has_other_exports = any([
    df_fiches is not None,
    df_profils is not None,
    df_produits is not None
])

if _has_other_exports:
    _top_labels = []
    if df_profils is not None: _top_labels.append("Profils")
    _top_labels.append("Cours")
    if df_fiches is not None: _top_labels.append("Fiches de cours")
    if df_produits is not None: _top_labels.append("Produits")
    _top_tabs = st.tabs(_top_labels)
    _cours_ctx = _top_tabs[_top_labels.index("Cours")]
else:
    _cours_ctx = st.container()

with _cours_ctx:
    inscr_col = "Nb. d'inscriptions"

    # =====================================================
    # KEY METRICS
    # =====================================================
    st.markdown(f"## {t('overview')}")

    # Check if multiple years are loaded
    available_years = sorted(df_combined["Année"].unique())
    multiple_years = len(available_years) > 1

    # Initialize year selection in session state
    if 'selected_years' not in st.session_state:
        st.session_state.selected_years = {year: True for year in available_years}

    # Ensure all available years are in the selection dict
    for year in available_years:
        if year not in st.session_state.selected_years:
            st.session_state.selected_years[year] = True

    # Year filter buttons (only show if multiple years)
    if multiple_years:
        st.markdown(f"#### {t('filter_years')}")

        year_cols = st.columns(len(available_years) + 1)

        for i, year in enumerate(available_years):
            with year_cols[i]:
                is_selected = st.session_state.selected_years.get(year, True)
                btn_type = "primary" if is_selected else "secondary"
                if st.button(str(year), key=f"year_btn_{year}", use_container_width=True, type=btn_type):
                    st.session_state.selected_years[year] = not is_selected
                    st.rerun()

        # "All years" button
        with year_cols[-1]:
            all_selected = all(st.session_state.selected_years.get(y, True) for y in available_years)
            btn_type = "primary" if all_selected else "secondary"
            if st.button(t('all'), key="year_btn_all", use_container_width=True, type=btn_type):
                new_state = not all_selected
                for y in available_years:
                    st.session_state.selected_years[y] = new_state
                st.rerun()

        st.markdown("---")

    # Filter data by selected years
    selected_years_list = [y for y in available_years if st.session_state.selected_years.get(y, True)]
    if not selected_years_list:
        selected_years_list = available_years  # Fallback: show all if none selected

    df_filtered_years = df_combined[df_combined["Année"].isin(selected_years_list)]

    # Calculate metrics for selected years
    total_inscriptions = df_filtered_years[inscr_col].sum()
    total_courses = df_filtered_years["Nb. de Cours"].sum()
    total_hours = df_filtered_years["Nombre total d'heures vendues (heures-étudiants)"].sum() if "Nombre total d'heures vendues (heures-étudiants)" in df_filtered_years.columns else 0
    total_revenue = df_filtered_years["Recettes"].sum() if "Recettes" in df_filtered_years.columns else 0
    avg_per_course = total_inscriptions / total_courses if total_courses > 0 else 0

    # Show selected years indicator
    if multiple_years:
        years_label = ", ".join(map(str, selected_years_list))
        if len(selected_years_list) == len(available_years):
            st.caption(f"{t('showing_all_years')}: {years_label}")
        else:
            st.caption(f"{t('showing_years')}: {years_label}")

    # =====================================================
    # TABS - Right after year selection
    # =====================================================
    tab1, tab2, tab3, tab3_ss, tab3_mc, tab3b, tab4, tab_evo, tab5, tab6, tab7, tab8, tab9, tab10, tab11 = st.tabs([
        t("tab_prova_stats"), t("tab_by_sede"), t("tab_by_sector"), t("tab_by_sous_secteur"), t("tab_by_macro_category"), t("tab_by_category"),
        t("tab_yoy"), t("tab_evolutions"), t("tab_profitability"), t("tab_map"),
        t("tab_comparisons"), t("tab_graphs"), t("tab_ai"), t("tab_export"), t("tab_config")
    ])

    # Day mode colors
    text_color = "#1e293b"
    bg_color = "rgba(0,0,0,0)"

    # TAB 1: SYNTHESE (Main metrics + summary table)
    with tab1:
        # Main metrics - always show as 5 cards
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric(t('inscriptions'), f"{total_inscriptions:,.0f}")
        with col2:
            st.metric(t('courses'), f"{total_courses:,.0f}")
        with col3:
            st.metric(t('student_hours'), f"{total_hours:,.0f}")
        with col4:
            st.metric(t('revenue'), f"€{total_revenue:,.0f}")
        with col5:
            st.metric(t('students_per_course'), f"{avg_per_course:.1f}")

        # Summary table - always show (national/IFI level)
        st.markdown(f"#### {t('breakdown_by_year')} (national/IFI)")

        # Build summary table data
        summary_metrics = []

        # Aggregate view by year only
        for year in selected_years_list:
            df_year = df_filtered_years[df_filtered_years["Année"] == year]
            year_inscr = df_year[inscr_col].sum()
            year_courses = df_year["Nb. de Cours"].sum()
            year_planned_hours = df_year["Nombre d'heures prévues"].sum() if "Nombre d'heures prévues" in df_year.columns else 0
            year_hours = df_year["Nombre total d'heures vendues (heures-étudiants)"].sum() if "Nombre total d'heures vendues (heures-étudiants)" in df_year.columns else 0
            year_revenue = df_year["Recettes"].sum() if "Recettes" in df_year.columns else 0
            year_new = df_year["Nouveaux inscrits"].sum() if "Nouveaux inscrits" in df_year.columns else 0
            year_returning = df_year["Réinscrits"].sum() if "Réinscrits" in df_year.columns else 0
            pct_new = round(year_new / year_inscr * 100 if year_inscr > 0 else 0, 1)
            pct_returning = round(year_returning / year_inscr * 100 if year_inscr > 0 else 0, 1)

            summary_metrics.append({
                t('year'): str(year),
                t('inscriptions'): int(year_inscr),
                t('new_students'): int(year_new),
                t('pct_new'): pct_new,
                t('returning_students'): int(year_returning),
                t('pct_returning'): pct_returning,
                t('courses'): int(year_courses),
                t('planned_hours'): int(year_planned_hours),
                t('student_hours'): int(year_hours),
                t('revenue'): year_revenue,
                t('students_per_course'): round(year_inscr / year_courses if year_courses > 0 else 0, 1),
            })

        # Add total row if multiple years
        if len(selected_years_list) > 1:
            total_new = df_filtered_years["Nouveaux inscrits"].sum() if "Nouveaux inscrits" in df_filtered_years.columns else 0
            total_returning = df_filtered_years["Réinscrits"].sum() if "Réinscrits" in df_filtered_years.columns else 0
            total_pct_new = round(total_new / total_inscriptions * 100 if total_inscriptions > 0 else 0, 1)
            total_pct_returning = round(total_returning / total_inscriptions * 100 if total_inscriptions > 0 else 0, 1)
            summary_metrics.append({
                t('year'): "TOTAL",
                t('inscriptions'): int(total_inscriptions),
                t('new_students'): int(total_new),
                t('pct_new'): total_pct_new,
                t('returning_students'): int(total_returning),
                t('pct_returning'): total_pct_returning,
                t('courses'): int(total_courses),
                t('planned_hours'): int(df_filtered_years["Nombre d'heures prévues"].sum() if "Nombre d'heures prévues" in df_filtered_years.columns else 0),
                t('student_hours'): int(total_hours),
                t('revenue'): total_revenue,
                t('students_per_course'): round(avg_per_course, 1),
            })

        if summary_metrics:
            df_summary = pd.DataFrame(summary_metrics)

            # Format columns for display
            df_display = df_summary.copy()
            df_display[t('inscriptions')] = df_display[t('inscriptions')].apply(lambda x: f"{x:,}")
            df_display[t('new_students')] = df_display[t('new_students')].apply(lambda x: f"{x:,}")
            df_display[t('pct_new')] = df_display[t('pct_new')].apply(lambda x: f"{x:.1f}%")
            df_display[t('returning_students')] = df_display[t('returning_students')].apply(lambda x: f"{x:,}")
            df_display[t('pct_returning')] = df_display[t('pct_returning')].apply(lambda x: f"{x:.1f}%")
            df_display[t('courses')] = df_display[t('courses')].apply(lambda x: f"{x:,}")
            df_display[t('planned_hours')] = df_display[t('planned_hours')].apply(lambda x: f"{x:,}")
            df_display[t('student_hours')] = df_display[t('student_hours')].apply(lambda x: f"{x:,}")
            df_display[t('revenue')] = df_display[t('revenue')].apply(lambda x: f"€{x:,.0f}")
            df_display[t('students_per_course')] = df_display[t('students_per_course')].apply(lambda x: f"{x:.1f}")

            # Highlight total rows
            def highlight_totals(row):
                if row[t('year')] == "TOTAL":
                    return ['background-color: #e2e8f0; font-weight: bold'] * len(row)
                return [''] * len(row)

            styled_df = df_display.style.apply(highlight_totals, axis=1)
            st.dataframe(styled_df, hide_index=True, use_container_width=True)

    # Day mode colors
    text_color = "#1e293b"
    bg_color = "rgba(0,0,0,0)"

    # Continue TAB 1: PROVA STATS content
    with tab1:

        # Build period options with year aggregation
        # Get available years and semesters
        available_years = sorted(df_combined["Année"].unique())
        available_periods = sorted(df_combined["Période"].unique())

        # Create hierarchical period options: Year (full) > Semester 1 > Semester 2
        period_options = [t("all")]
        for year in available_years:
            year_str = str(year)
            period_options.append(f"{year} (année complète)")
            # Add semesters for this year
            for period in available_periods:
                if str(year) in period:
                    period_options.append(f"    ↳ {period}")

        col1, col2 = st.columns(2)
        with col1:
            sedi_list = [t("all")] + sorted(df_combined["Sede"].unique().tolist())
            selected_sede = st.selectbox(t("filter_by_sede"), sedi_list, key="prova_sede")
        with col2:
            selected_period = st.selectbox(t("filter_by_period"), period_options, key="prova_period")

        # Determine if we need year aggregation
        is_year_aggregate = "année complète" in selected_period or "anno completo" in selected_period

        # Determine if a single sede is selected (for total row)
        is_single_sede = selected_sede != t("all")

        # Filter data first by sede if needed
        df_filtered = df_combined.copy()
        if is_single_sede:
            df_filtered = df_filtered[df_filtered["Sede"] == selected_sede]

        # Handle period filtering
        if selected_period == t("all"):
            prova_stats = create_prova_stats_format(df_filtered, add_total_row=is_single_sede)
        elif is_year_aggregate:
            # Extract year from selection like "2025 (année complète)"
            year_match = re.search(r'(\d{4})', selected_period)
            if year_match:
                year = int(year_match.group(1))
                df_filtered = df_filtered[df_filtered["Année"] == year]
            prova_stats = create_prova_stats_format(df_filtered, aggregate_year=True, add_total_row=is_single_sede)
        else:
            # Specific semester selected (remove indent prefix)
            period_clean = selected_period.replace("    ↳ ", "").strip()
            df_filtered = df_filtered[df_filtered["Période"] == period_clean]
            prova_stats = create_prova_stats_format(df_filtered, add_total_row=is_single_sede)

        if not prova_stats.empty:
            # Dynamic height: 35px per row + 40px header, min 100, max 600
            dynamic_height = min(600, max(100, len(prova_stats) * 35 + 40))
            st.dataframe(prova_stats, hide_index=True, use_container_width=True, height=dynamic_height)

            # Show IFI totals (only when not single sede, since main table already has totals)
            if not is_single_sede:
                st.markdown(f"#### {t('ifi_totals')}")
                df_ifi = df_filtered.copy()
                df_ifi["Sede"] = "IFI"
                if is_year_aggregate:
                    ifi_totals = aggregate_by_sector(df_ifi, group_cols=["Année", "Sede", "Secteur"], add_total_row=True)
                else:
                    ifi_totals = aggregate_by_sector(df_ifi, add_total_row=True)
                if not ifi_totals.empty:
                    dynamic_height_ifi = min(600, max(100, len(ifi_totals) * 35 + 40))
                    st.dataframe(ifi_totals, hide_index=True, use_container_width=True, height=dynamic_height_ifi)
        else:
            st.info("Aucune donnée pour cette sélection.")

    # TAB 2: PAR ANTENNE
    with tab2:
        st.markdown(f"### {t('analysis_by_sede')}")

        # Year selector for this tab
        tab2_years = sorted(df_combined["Année"].unique())
        if len(tab2_years) > 1:
            selected_year_tab2 = st.selectbox(
                t("filter_by_period"), 
                tab2_years, 
                index=len(tab2_years)-1,  # Default to most recent year
                key="sede_year_filter"
            )
            df_tab2 = df_combined[df_combined["Année"] == selected_year_tab2]
        else:
            df_tab2 = df_combined

        sede_summary = df_tab2.groupby("Sede").agg({inscr_col: "sum", "Nb. de Cours": "sum", "Recettes": "sum"}).reset_index()
        col1, col2 = st.columns(2)
        with col1:
            fig = px.bar(sede_summary.sort_values(inscr_col, ascending=True), y="Sede", x=inscr_col, orientation='h',
                        color="Sede", color_discrete_map=SEDE_COLORS, title=t('inscriptions_by_sede'),
                        text=inscr_col)
            fig.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
            fig.update_layout(showlegend=False, height=350, paper_bgcolor=bg_color, plot_bgcolor=bg_color, font=dict(color=text_color))
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            fig = px.pie(sede_summary, values=inscr_col, names="Sede", color="Sede", color_discrete_map=SEDE_COLORS, title=t('distribution'))
            fig.update_traces(textposition='inside', textinfo='percent+label+value')
            fig.update_layout(height=350, paper_bgcolor=bg_color, plot_bgcolor=bg_color, font=dict(color=text_color))
            st.plotly_chart(fig, use_container_width=True)
        st.markdown(f"#### {t('detail_by_sede')}")
        sede_summary[t("students_per_course")] = (sede_summary[inscr_col] / sede_summary["Nb. de Cours"]).round(2)
        st.dataframe(sede_summary, hide_index=True, use_container_width=True)

    # TAB 3: VUE SECTEURS
    with tab3:
        st.markdown(f"### {t('analysis_by_sector')}")

        # Filters row: Year, Antenna, Sector
        filter_col1, filter_col2, filter_col3 = st.columns(3)

        # Year selector
        tab3_years = sorted(df_combined["Année"].unique())
        with filter_col1:
            if len(tab3_years) > 1:
                selected_year_tab3 = st.selectbox(
                    t("filter_by_period"), 
                    tab3_years, 
                    index=len(tab3_years)-1,
                    key="sector_year_filter"
                )
                df_tab3_base = df_combined[df_combined["Année"] == selected_year_tab3]
            else:
                df_tab3_base = df_combined

        # Get list of antennas and sectors
        antennas_all = sorted(df_tab3_base["Sede"].unique().tolist())
        sectors = sorted(df_tab3_base["Secteur"].unique().tolist())

        # Antenna filter
        with filter_col2:
            antenna_options = [t("all")] + antennas_all
            selected_antenna_tab3 = st.selectbox(
                t("filter_by_sede"), 
                antenna_options, 
                key="sector_antenna_filter"
            )

        # Sector filter - multiselect
        with filter_col3:
            selected_sectors_tab3 = st.multiselect(
                "Filtrer par secteur", 
                sectors,
                default=[],
                key="sector_sector_filter",
                placeholder=t("all")
            )

        # Apply antenna filter
        if selected_antenna_tab3 != t("all"):
            df_tab3 = df_tab3_base[df_tab3_base["Sede"] == selected_antenna_tab3]
        else:
            df_tab3 = df_tab3_base

        # Check if sector(s) are selected
        sector_filter_active = len(selected_sectors_tab3) > 0
        is_multi_sector = len(selected_sectors_tab3) > 1

        # Auto-scroll to comparison section when sector filter is active
        if sector_filter_active:
            st.markdown("""
            <script>
                setTimeout(function() {
                    var element = document.getElementById('comparison-section');
                    if (element) {
                        element.scrollIntoView({behavior: 'smooth', block: 'start'});
                    }
                }, 500);
            </script>
            """, unsafe_allow_html=True)

        # Custom blue scale with darker minimum for better visibility on white background
        # Min value = medium blue (visible), Max value = dark blue
        BLUE_SCALE_IFI = [[0, "#93c5fd"], [0.25, "#60a5fa"], [0.5, "#3b82f6"], [0.75, "#2563eb"], [1, "#1e40af"]]

        # Text above sub-tabs
        st.markdown(f"**{t('choose_indicator')}**")

        # Initialize session state for selected indicator if not exists
        if "sector_selected_indicator" not in st.session_state:
            st.session_state.sector_selected_indicator = 0

        # Define indicator options
        indicator_options = [
            t('global_view'), 
            t('inscriptions'), 
            t('new_students'), 
            t('returning_students'), 
            t('courses'), 
            t('planned_hours'), 
            t('student_hours'), 
            t('revenue')
        ]

        # Use radio buttons with horizontal layout for persistent selection
        selected_indicator = st.radio(
            "",  # Empty label since we have the title above
            indicator_options,
            index=st.session_state.sector_selected_indicator,
            horizontal=True,
            key="sector_indicator_radio",
            label_visibility="collapsed"
        )

        # Update session state
        st.session_state.sector_selected_indicator = indicator_options.index(selected_indicator)

        # Indicator configurations: (column_name, translation_key)
        indicator_configs = [
            (inscr_col, 'inscriptions'),
            (inscr_col, 'inscriptions'),
            ("Nouveaux inscrits", 'new_students'),
            ("Réinscrits", 'returning_students'),
            ("Nb. de Cours", 'courses'),
            ("Nombre d'heures prévues", 'planned_hours'),
            ("Nombre total d'heures vendues (heures-étudiants)", 'student_hours'),
            ("Recettes", 'revenue')
        ]

        # Function to create histogram + pie chart pair for IFI totals
        def create_ifi_graphs(df_data, value_col, title_suffix, tab_key, single_sector=False):
            """Create histogram + pie chart pair for IFI (all antennas combined)"""
            ifi_summary = df_data.groupby("Secteur").agg({value_col: "sum"}).reset_index()
            ifi_summary = ifi_summary.sort_values(value_col, ascending=False)

            # Larger height when sector filter is active
            chart_height = 500 if single_sector else 400

            col1, col2 = st.columns(2)
            with col1:
                # Histogram with darker blue scale
                fig_bar = px.bar(ifi_summary, y="Secteur", x=value_col, orientation='h',
                                color=value_col, color_continuous_scale=BLUE_SCALE_IFI,
                                title=f"{title_suffix} - Histogramme",
                                text=value_col)
                fig_bar.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
                fig_bar.update_layout(height=chart_height, 
                                     paper_bgcolor=bg_color, plot_bgcolor=bg_color, 
                                     font=dict(color=text_color))
                st.plotly_chart(fig_bar, use_container_width=True, key=f"ifi_bar_{tab_key}")

            with col2:
                # Pie chart with high contrast blue shades
                blue_colors = ['#0c1445', '#1e3a8a', '#1e40af', '#2563eb', '#3b82f6', '#60a5fa', '#93c5fd', '#c7d9f5', '#e8f0fc']
                fig_pie = px.pie(ifi_summary, values=value_col, names="Secteur",
                                title=f"{title_suffix} - Répartition",
                                color_discrete_sequence=blue_colors)
                fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                fig_pie.update_layout(height=chart_height, 
                                     paper_bgcolor=bg_color, plot_bgcolor=bg_color, 
                                     font=dict(color=text_color))
                st.plotly_chart(fig_pie, use_container_width=True, key=f"ifi_pie_{tab_key}")

        # Function to create histogram + pie chart pair for a specific antenna
        def create_antenna_graphs(df_data, value_col, antenna, title_suffix, tab_key):
            """Create histogram + pie chart pair for a specific antenna with its own color"""
            antenna_data = df_data[df_data["Sede"] == antenna].groupby("Secteur").agg({value_col: "sum"}).reset_index()
            antenna_data = antenna_data.sort_values(value_col, ascending=False)

            if antenna_data.empty:
                st.info(f"Aucune donnée pour {antenna}")
                return

            antenna_color = SEDE_COLORS.get(antenna, "#888888")
            # Create gradient for this antenna color
            def hex_to_rgb(hex_color):
                hex_color = hex_color.lstrip('#')
                return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

            def rgb_to_hex(rgb):
                return '#{:02x}{:02x}{:02x}'.format(int(rgb[0]), int(rgb[1]), int(rgb[2]))

            base_rgb = hex_to_rgb(antenna_color)
            # Create color gradient from very dark to very light for better contrast
            color_scale = []
            for i in range(10):
                factor = 0.15 + (i * 0.09)  # 0.15 to 0.96 - wider range for more contrast
                new_rgb = tuple(min(255, int(c * factor + 255 * (1 - factor))) for c in base_rgb)
                color_scale.append(rgb_to_hex(new_rgb))

            # Larger height when sector filter is active
            chart_height = 400 if sector_filter_active else 350

            col1, col2 = st.columns(2)
            with col1:
                # Inverse scale: low values get medium color, high values get darker
                fig_bar = px.bar(antenna_data, y="Secteur", x=value_col, orientation='h',
                                color=value_col, 
                                color_continuous_scale=[[0, color_scale[3]], [0.5, antenna_color], [1, color_scale[-1]]],
                                title=f"{title_suffix} - {antenna}",
                                text=value_col)
                fig_bar.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
                fig_bar.update_layout(height=chart_height, paper_bgcolor=bg_color, plot_bgcolor=bg_color, 
                                     font=dict(color=text_color), coloraxis_showscale=False, margin=dict(l=150))
                st.plotly_chart(fig_bar, use_container_width=True, key=f"antenna_bar_{antenna}_{tab_key}")

            with col2:
                fig_pie = px.pie(antenna_data, values=value_col, names="Secteur",
                                title=f"{title_suffix} - {antenna}",
                                color_discrete_sequence=color_scale)
                fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                fig_pie.update_layout(height=chart_height, paper_bgcolor=bg_color, plot_bgcolor=bg_color, 
                                     font=dict(color=text_color))
                st.plotly_chart(fig_pie, use_container_width=True, key=f"antenna_pie_{antenna}_{tab_key}")

        # Function to create heatmap with IFI column
        def create_heatmap(df_data, value_col, title_suffix, tab_key, is_revenue=False):
            """Create heatmap with Total (IFI) column on the right"""
            heatmap_base = df_data.groupby(["Secteur", "Sede"])[value_col].sum().unstack(fill_value=0)
            # Add Total (IFI) column (sum of all antennas)
            heatmap_base["Total (IFI)"] = heatmap_base.sum(axis=1)
            # Reorder columns: antennas first, then Total (IFI) at the end
            ordered_cols = [a for a in ANTENNA_ORDER if a in heatmap_base.columns] + ["Total (IFI)"]
            heatmap_base = heatmap_base[[c for c in ordered_cols if c in heatmap_base.columns]]

            # Create figure with go.Heatmap for more control
            # Separate the Total column from colored data
            antenna_cols = [c for c in heatmap_base.columns if c != "Total (IFI)"]

            fig = make_subplots(rows=1, cols=2, column_widths=[0.85, 0.15], horizontal_spacing=0.02)

            # Format template for values (euros or numbers)
            text_template = "€%{text:,.0f}" if is_revenue else "%{text:.0f}"
            total_template = "<b>€%{text:,.0f}</b>" if is_revenue else "<b>%{text:.0f}</b>"

            # Main heatmap (antennas only)
            z_main = heatmap_base[antenna_cols].values
            fig.add_trace(
                go.Heatmap(
                    z=z_main,
                    x=antenna_cols,
                    y=heatmap_base.index.tolist(),
                    colorscale="YlOrRd",
                    text=z_main,
                    texttemplate=text_template,
                    textfont=dict(size=14),
                    showscale=True,
                    colorbar=dict(title=title_suffix, x=0.82)
                ),
                row=1, col=1
            )

            # Total column (white background, bold text)
            z_total = heatmap_base["Total (IFI)"].values.reshape(-1, 1)
            fig.add_trace(
                go.Heatmap(
                    z=[[1]] * len(z_total),  # Uniform color (white)
                    x=["Total (IFI)"],
                    y=heatmap_base.index.tolist(),
                    colorscale=[[0, "white"], [1, "white"]],
                    text=z_total,
                    texttemplate=total_template,
                    textfont=dict(size=14, color="black"),
                    showscale=False,
                    hovertemplate="Secteur: %{y}<br>Total (IFI): %{text}<extra></extra>"
                ),
                row=1, col=2
            )

            fig.update_layout(
                height=500, 
                paper_bgcolor=bg_color, 
                plot_bgcolor=bg_color, 
                font=dict(color=text_color),
                xaxis=dict(side="top", tickfont=dict(size=14)),
                xaxis2=dict(side="top", tickfont=dict(size=14, color="black")),
                yaxis=dict(tickfont=dict(size=12)),
                yaxis2=dict(showticklabels=False)
            )

            # Add subtitle
            st.caption(t('heatmap_subtitle'))
            st.plotly_chart(fig, use_container_width=True, key=f"heatmap_{tab_key}")

        # Function to create sector comparison histogram (when sector(s) are selected)
        def create_sector_antenna_comparison(df_data, value_col, sector_names, title_suffix, tab_key, is_multi=False):
            """Create histogram + pie chart comparing antennas for selected sector(s)"""
            if isinstance(sector_names, str):
                sector_names = [sector_names]

            sector_data = df_data[df_data["Secteur"].isin(sector_names)].copy()
            antenna_summary = sector_data.groupby("Sede").agg({value_col: "sum"}).reset_index()

            # For histogram: include IFI total
            ifi_total = sector_data[value_col].sum()
            ifi_row = pd.DataFrame([{"Sede": "IFI", value_col: ifi_total}])
            antenna_summary_with_ifi = pd.concat([ifi_row, antenna_summary], ignore_index=True)

            # Reorder: IFI first, then IFM, IFF, IFN, IFP
            sede_order = ["IFI"] + ANTENNA_ORDER
            antenna_summary_with_ifi["Sede"] = pd.Categorical(antenna_summary_with_ifi["Sede"], categories=sede_order, ordered=True)
            antenna_summary_with_ifi = antenna_summary_with_ifi.sort_values("Sede")

            # Apply antenna colors
            antenna_summary_with_ifi["color"] = antenna_summary_with_ifi["Sede"].map(lambda x: SEDE_COLORS.get(x, "#888888"))

            # Title based on selection
            if is_multi or len(sector_names) > 1:
                title_label = f"Sélection multiple ({'/'.join(sector_names[:3])}{'...' if len(sector_names) > 3 else ''})"
            else:
                title_label = sector_names[0]

            # Larger height when sector filter is active
            chart_height = 450

            col1, col2 = st.columns(2)
            with col1:
                fig = px.bar(antenna_summary_with_ifi, x="Sede", y=value_col,
                            color="Sede", color_discrete_map=SEDE_COLORS,
                            title=f"{title_suffix} - {title_label} (Histogramme)",
                            text=value_col)
                fig.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
                fig.update_layout(height=chart_height, paper_bgcolor=bg_color, plot_bgcolor=bg_color, 
                                 font=dict(color=text_color), showlegend=False)
                st.plotly_chart(fig, use_container_width=True, key=f"sector_compare_bar_{tab_key}")

            with col2:
                # Pie chart WITHOUT IFI (only antennas, since IFI = sum of all)
                # Reorder antenna_summary for pie chart
                antenna_summary["Sede"] = pd.Categorical(antenna_summary["Sede"], categories=ANTENNA_ORDER, ordered=True)
                antenna_summary = antenna_summary.sort_values("Sede")

                fig_pie = px.pie(antenna_summary, values=value_col, names="Sede",
                                title=f"{title_suffix} - {title_label} (Répartition)",
                                color="Sede", color_discrete_map=SEDE_COLORS)
                fig_pie.update_traces(textposition='inside', textinfo='percent+label+value')
                fig_pie.update_layout(height=chart_height, paper_bgcolor=bg_color, plot_bgcolor=bg_color, 
                                     font=dict(color=text_color))
                st.plotly_chart(fig_pie, use_container_width=True, key=f"sector_compare_pie_{tab_key}")

        # Function to render full view for an indicator (with proper order based on filter)
        def render_indicator_view(df_data, value_col, title_suffix, tab_key, is_global_view=False, is_revenue=False):
            """Render the full view for an indicator"""

            # Chart height depends on sector filter
            chart_height = 450 if sector_filter_active else 400

            # If sector(s) selected, show filtered content FIRST
            if sector_filter_active:
                # SECTION 1: Filtered sector(s) graphs
                df_filtered = df_data[df_data["Secteur"].isin(selected_sectors_tab3)]

                filter_label = '/'.join(selected_sectors_tab3[:3]) + ('...' if len(selected_sectors_tab3) > 3 else '')
                st.markdown(f"#### Sélection : {filter_label}")

                # Filtered IFI graphs
                create_ifi_graphs(df_filtered, value_col, title_suffix, f"{tab_key}_filtered", single_sector=True)
                st.markdown("---")

                # Filtered heatmap
                st.markdown(f"#### {t('heatmap_title')} - {filter_label}")
                create_heatmap(df_filtered, value_col, title_suffix, f"{tab_key}_filtered_heatmap", is_revenue=is_revenue)
                st.markdown("---")

                # Comparison by antenna for selected sector(s)
                comparison_title = f"{t('comparison_by_antenna')} - "
                if is_multi_sector:
                    comparison_title += f"Sélection multiple ({filter_label})"
                else:
                    comparison_title += selected_sectors_tab3[0]
                st.markdown(f"<div id='comparison-section'></div>", unsafe_allow_html=True)
                st.markdown(f"#### {comparison_title}")
                create_sector_antenna_comparison(df_tab3_base, value_col, selected_sectors_tab3, title_suffix, f"{tab_key}_sector_cmp", is_multi=is_multi_sector)
                st.markdown("---")

            # IFI - Total toutes antennes confondues
            st.markdown(f"#### {t('ifi_all_antennas')}")
            create_ifi_graphs(df_data, value_col, title_suffix, tab_key, single_sector=sector_filter_active)
            st.markdown("---")

            # Heatmap with dynamic title
            st.markdown(f"#### {t('heatmap_title')} - {title_suffix}")
            create_heatmap(df_tab3_base, value_col, title_suffix, f"{tab_key}_heatmap", is_revenue=is_revenue)
            st.markdown("---")

            # SECTION: Détails par antenne
            st.markdown(f"#### {t('details_by_antenna')}")

            # Display antennas in order: Milan, Florence, Naples, Palermo
            for antenna in ANTENNA_ORDER:
                if antenna in df_data["Sede"].unique():
                    create_antenna_graphs(df_data, value_col, antenna, title_suffix, f"{tab_key}_{antenna}")

        # Render content based on selected indicator (using session state instead of tabs)
        selected_idx = st.session_state.sector_selected_indicator

        if selected_idx == 0:
            # Vue globale - Show all IFI graphs for all indicators
            st.markdown("#### Vue d'ensemble - Tous les indicateurs (IFI)")

            # Skip index 0 (global_view itself) and index 1 (duplicate inscriptions)
            for i, (value_col, trans_key) in enumerate(indicator_configs[1:], start=1):
                if i == 1:  # Skip duplicate inscriptions at index 1
                    continue
                if value_col in df_tab3.columns:
                    st.markdown(f"##### {t(trans_key)}")
                    create_ifi_graphs(df_tab3, value_col, t(trans_key), f"global_{trans_key}", single_sector=False)
                    st.markdown("---")
        else:
            # Render specific indicator
            value_col, trans_key = indicator_configs[selected_idx]
            if value_col in df_tab3.columns:
                # Check if this is revenue for euro formatting
                is_revenue = (trans_key == 'revenue')
                render_indicator_view(
                    df_tab3, value_col, t(trans_key), 
                    f"{trans_key}_{selected_idx}",
                    is_revenue=is_revenue
                )
            else:
                st.warning(f"Colonne '{value_col}' non disponible")

    # TAB 3_SS: PAR SOUS-SECTEURS (same structure as Par secteurs)
    with tab3_ss:
        st.markdown(f"### {t('analysis_by_sous_secteur')}")

        # Filters row: Year, Antenna, Sous-secteur
        filter_col1_ss, filter_col2_ss, filter_col3_ss = st.columns(3)

        # Year selector
        tab3_ss_years = sorted(df_combined["Année"].unique())
        with filter_col1_ss:
            if len(tab3_ss_years) > 1:
                selected_year_tab3_ss = st.selectbox(
                    t("filter_by_period"), 
                    tab3_ss_years, 
                    index=len(tab3_ss_years)-1,
                    key="sous_secteur_year_filter"
                )
                df_tab3_ss_base = df_combined[df_combined["Année"] == selected_year_tab3_ss]
            else:
                df_tab3_ss_base = df_combined

        if "Sous-secteur" in df_tab3_ss_base.columns:
            # Get list of antennas and sous-secteurs
            antennas_all_ss = sorted(df_tab3_ss_base["Sede"].unique().tolist())
            sous_secteurs = sorted(df_tab3_ss_base["Sous-secteur"].dropna().unique().tolist())

            # Antenna filter
            with filter_col2_ss:
                antenna_options_ss = [t("all")] + antennas_all_ss
                selected_antenna_ss = st.selectbox(
                    t("filter_by_sede"), 
                    antenna_options_ss, 
                    key="sous_secteur_antenna_filter"
                )

            # Sous-secteur filter - multiselect
            with filter_col3_ss:
                selected_sous_secteurs = st.multiselect(
                    t("filter_by_sous_secteur"), 
                    sous_secteurs,
                    default=[],
                    key="sous_secteur_filter",
                    placeholder=t("all")
                )

            # Apply antenna filter
            if selected_antenna_ss != t("all"):
                df_tab3_ss = df_tab3_ss_base[df_tab3_ss_base["Sede"] == selected_antenna_ss]
            else:
                df_tab3_ss = df_tab3_ss_base

            # Check if sous-secteur(s) are selected
            sous_secteur_filter_active = len(selected_sous_secteurs) > 0

            # Text above sub-tabs
            st.markdown(f"**{t('choose_indicator')}**")

            # Initialize session state for selected indicator if not exists
            if "ss_selected_indicator" not in st.session_state:
                st.session_state.ss_selected_indicator = 0

            # Define indicator options
            ss_indicator_options = [
                t('global_view'), 
                t('inscriptions'), 
                t('new_students'), 
                t('returning_students'), 
                t('courses'), 
                t('planned_hours'), 
                t('student_hours'), 
                t('revenue')
            ]

            # Use radio buttons with horizontal layout for persistent selection
            selected_ss_indicator = st.radio(
                "",
                ss_indicator_options,
                index=st.session_state.ss_selected_indicator,
                horizontal=True,
                key="ss_indicator_radio",
                label_visibility="collapsed"
            )

            # Update session state
            st.session_state.ss_selected_indicator = ss_indicator_options.index(selected_ss_indicator)

            # Function to create sous-secteur graphs (IFI level)
            def create_sous_secteur_ifi_graphs(df_data, value_col, title_suffix, tab_key):
                """Create histogram + pie chart by sous-secteur (IFI level)"""
                ss_summary = df_data.groupby("Sous-secteur").agg({value_col: "sum"}).reset_index()
                ss_summary = ss_summary.sort_values(value_col, ascending=False)

                # Custom green scale with visible minimum
                GREEN_SCALE = [[0, "#86efac"], [0.25, "#4ade80"], [0.5, "#22c55e"], [0.75, "#16a34a"], [1, "#166534"]]

                col1, col2 = st.columns(2)
                with col1:
                    fig_bar = px.bar(ss_summary, y="Sous-secteur", x=value_col, orientation='h',
                                    color=value_col, color_continuous_scale=GREEN_SCALE,
                                    title=f"{title_suffix} - Histogramme (IFI)",
                                    text=value_col)
                    fig_bar.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
                    fig_bar.update_layout(height=max(500, len(ss_summary)*25), paper_bgcolor=bg_color, plot_bgcolor=bg_color, 
                                         font=dict(color=text_color), margin=dict(l=200))
                    st.plotly_chart(fig_bar, use_container_width=True, key=f"ss_ifi_bar_{tab_key}")

                with col2:
                    green_colors = ['#052e16', '#14532d', '#166534', '#15803d', '#22c55e', '#4ade80', '#86efac', '#bbf7d0', '#dcfce7']
                    fig_pie = px.pie(ss_summary, values=value_col, names="Sous-secteur",
                                    title=f"{title_suffix} - Répartition (IFI)",
                                    color_discrete_sequence=green_colors)
                    fig_pie.update_traces(textposition='inside', textinfo='percent+label+value')
                    fig_pie.update_layout(height=500, paper_bgcolor=bg_color, plot_bgcolor=bg_color, 
                                         font=dict(color=text_color))
                    st.plotly_chart(fig_pie, use_container_width=True, key=f"ss_ifi_pie_{tab_key}")

            # Function to create sous-secteur heatmap
            def create_sous_secteur_heatmap(df_data, value_col, title_suffix, tab_key, is_revenue=False):
                """Create heatmap by sous-secteur × antenna"""
                heatmap_data = df_data.groupby(["Sous-secteur", "Sede"])[value_col].sum().unstack(fill_value=0)
                heatmap_data["Total (IFI)"] = heatmap_data.sum(axis=1)
                ordered_cols = [a for a in ANTENNA_ORDER if a in heatmap_data.columns] + ["Total (IFI)"]
                heatmap_data = heatmap_data[[c for c in ordered_cols if c in heatmap_data.columns]]
                heatmap_data = heatmap_data.sort_values("Total (IFI)", ascending=False)

                text_template = "€%{text:,.0f}" if is_revenue else "%{text:.0f}"

                fig = px.imshow(heatmap_data, labels=dict(x="Sede", y="Sous-secteur", color=title_suffix), 
                               aspect="auto", color_continuous_scale=[[0, "#d9f99d"], [0.25, "#a3e635"], [0.5, "#65a30d"], [0.75, "#4d7c0f"], [1, "#3f6212"]], text_auto=True)
                fig.update_layout(height=600, paper_bgcolor=bg_color, plot_bgcolor=bg_color, font=dict(color=text_color),
                                 title=f"Heatmap - {title_suffix}",
                                 xaxis=dict(side="top", tickfont=dict(size=14)),
                                 yaxis=dict(tickfont=dict(size=10)))
                fig.update_traces(textfont=dict(size=12))
                st.plotly_chart(fig, use_container_width=True, key=f"ss_heatmap_{tab_key}")

            # Function to create antenna graphs for sous-secteur view
            def create_ss_antenna_graphs(df_data, value_col, antenna, title_suffix, tab_key):
                """Create histogram + pie chart pair for a specific antenna (sous-secteur view)"""
                antenna_data = df_data[df_data["Sede"] == antenna].groupby("Sous-secteur").agg({value_col: "sum"}).reset_index()
                antenna_data = antenna_data.sort_values(value_col, ascending=False)

                if antenna_data.empty:
                    st.info(f"Aucune donnée pour {antenna}")
                    return

                antenna_color = SEDE_COLORS.get(antenna, "#888888")
                # Create gradient for this antenna color
                def hex_to_rgb(hex_color):
                    hex_color = hex_color.lstrip('#')
                    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

                def rgb_to_hex(rgb):
                    return '#{:02x}{:02x}{:02x}'.format(int(rgb[0]), int(rgb[1]), int(rgb[2]))

                base_rgb = hex_to_rgb(antenna_color)
                color_scale = []
                for i in range(10):
                    factor = 0.15 + (i * 0.09)
                    new_rgb = tuple(min(255, int(c * factor + 255 * (1 - factor))) for c in base_rgb)
                    color_scale.append(rgb_to_hex(new_rgb))

                col1, col2 = st.columns(2)
                with col1:
                    # Inverse scale: low values get visible color
                    fig_bar = px.bar(antenna_data, y="Sous-secteur", x=value_col, orientation='h',
                                    color=value_col, 
                                    color_continuous_scale=[[0, color_scale[3]], [0.5, antenna_color], [1, color_scale[-1]]],
                                    title=f"{title_suffix} - {antenna}",
                                    text=value_col)
                    fig_bar.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
                    fig_bar.update_layout(height=max(400, len(antenna_data)*25), paper_bgcolor=bg_color, plot_bgcolor=bg_color, 
                                         font=dict(color=text_color), coloraxis_showscale=False, margin=dict(l=200))
                    st.plotly_chart(fig_bar, use_container_width=True, key=f"ss_antenna_bar_{antenna}_{tab_key}")

                with col2:
                    fig_pie = px.pie(antenna_data, values=value_col, names="Sous-secteur",
                                    title=f"{title_suffix} - {antenna}",
                                    color_discrete_sequence=color_scale)
                    fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                    fig_pie.update_layout(height=400, paper_bgcolor=bg_color, plot_bgcolor=bg_color, 
                                         font=dict(color=text_color))
                    st.plotly_chart(fig_pie, use_container_width=True, key=f"ss_antenna_pie_{antenna}_{tab_key}")

            # Function to create sous-secteur comparison by antenna (when filter is active)
            def create_ss_antenna_comparison(df_data, value_col, ss_names, title_suffix, tab_key, is_multi=False):
                """Create histogram + pie chart comparing antennas for selected sous-secteur(s)"""
                if isinstance(ss_names, str):
                    ss_names = [ss_names]

                ss_data = df_data[df_data["Sous-secteur"].isin(ss_names)].copy()
                antenna_summary = ss_data.groupby("Sede").agg({value_col: "sum"}).reset_index()

                # For histogram: include IFI total
                ifi_total = ss_data[value_col].sum()
                ifi_row = pd.DataFrame([{"Sede": "IFI", value_col: ifi_total}])
                antenna_summary_with_ifi = pd.concat([ifi_row, antenna_summary], ignore_index=True)

                # Reorder: IFI first, then antennas
                sede_order = ["IFI"] + ANTENNA_ORDER
                antenna_summary_with_ifi["Sede"] = pd.Categorical(antenna_summary_with_ifi["Sede"], categories=sede_order, ordered=True)
                antenna_summary_with_ifi = antenna_summary_with_ifi.sort_values("Sede")

                # Title based on selection
                if is_multi or len(ss_names) > 1:
                    title_label = f"Sélection multiple ({'/'.join(ss_names[:3])}{'...' if len(ss_names) > 3 else ''})"
                else:
                    title_label = ss_names[0]

                col1, col2 = st.columns(2)
                with col1:
                    fig = px.bar(antenna_summary_with_ifi, x="Sede", y=value_col,
                                color="Sede", color_discrete_map=SEDE_COLORS,
                                title=f"{title_suffix} - {title_label} (Histogramme)",
                                text=value_col)
                    fig.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
                    fig.update_layout(height=450, paper_bgcolor=bg_color, plot_bgcolor=bg_color, 
                                     font=dict(color=text_color), showlegend=False)
                    st.plotly_chart(fig, use_container_width=True, key=f"ss_compare_bar_{tab_key}")

                with col2:
                    # Pie chart WITHOUT IFI
                    antenna_summary["Sede"] = pd.Categorical(antenna_summary["Sede"], categories=ANTENNA_ORDER, ordered=True)
                    antenna_summary = antenna_summary.sort_values("Sede")

                    fig_pie = px.pie(antenna_summary, values=value_col, names="Sede",
                                    title=f"{title_suffix} - {title_label} (Répartition)",
                                    color="Sede", color_discrete_map=SEDE_COLORS)
                    fig_pie.update_traces(textposition='inside', textinfo='percent+label+value')
                    fig_pie.update_layout(height=450, paper_bgcolor=bg_color, plot_bgcolor=bg_color, 
                                         font=dict(color=text_color))
                    st.plotly_chart(fig_pie, use_container_width=True, key=f"ss_compare_pie_{tab_key}")

            # Function to render sous-secteur indicator view (with proper order based on filter)
            def render_sous_secteur_indicator_view(df_data, value_col, title_suffix, tab_key, is_revenue=False):
                # If filter is active, show filtered content first
                if sous_secteur_filter_active:
                    # SECTION 1: Filtered sous-secteur(s) graphs
                    is_multi = len(selected_sous_secteurs) > 1
                    df_filtered = df_data[df_data["Sous-secteur"].isin(selected_sous_secteurs)]

                    filter_label = '/'.join(selected_sous_secteurs[:3]) + ('...' if len(selected_sous_secteurs) > 3 else '')
                    st.markdown(f"#### Sélection : {filter_label}")

                    # Filtered IFI graphs
                    create_sous_secteur_ifi_graphs(df_filtered, value_col, title_suffix, f"{tab_key}_filtered")
                    st.markdown("---")

                    # Filtered heatmap
                    create_sous_secteur_heatmap(df_filtered, value_col, title_suffix, f"{tab_key}_filtered_heatmap", is_revenue=is_revenue)
                    st.markdown("---")

                    # Comparison by antenna for selected sous-secteur(s)
                    comparison_title = f"{t('comparison_by_antenna')} - {filter_label}"
                    st.markdown(f"#### {comparison_title}")
                    create_ss_antenna_comparison(df_data, value_col, selected_sous_secteurs, title_suffix, f"{tab_key}_ss_cmp", is_multi=is_multi)
                    st.markdown("---")

                # IFI Total (all antennas combined)
                st.markdown(f"#### {t('ifi_all_antennas')}")
                create_sous_secteur_ifi_graphs(df_data, value_col, title_suffix, tab_key)
                st.markdown("---")

                # Heatmap
                create_sous_secteur_heatmap(df_data, value_col, title_suffix, f"{tab_key}_heatmap", is_revenue=is_revenue)
                st.markdown("---")

                # SECTION: Détails par antenne
                st.markdown(f"#### {t('details_by_antenna')}")
                for antenna in ANTENNA_ORDER:
                    if antenna in df_data["Sede"].unique():
                        create_ss_antenna_graphs(df_data, value_col, antenna, title_suffix, f"{tab_key}_{antenna}")

            indicator_configs_ss = [
                (inscr_col, 'inscriptions'),
                (inscr_col, 'inscriptions'),
                ("Nouveaux inscrits", 'new_students'),
                ("Réinscrits", 'returning_students'),
                ("Nb. de Cours", 'courses'),
                ("Nombre d'heures prévues", 'planned_hours'),
                ("Nombre total d'heures vendues (heures-étudiants)", 'student_hours'),
                ("Recettes", 'revenue')
            ]

            # Render content based on selected indicator (using session state)
            selected_ss_idx = st.session_state.ss_selected_indicator

            if selected_ss_idx == 0:
                # Vue globale
                st.markdown("#### Vue d'ensemble - Tous les indicateurs (IFI)")
                for i, (value_col, trans_key) in enumerate(indicator_configs_ss[1:], start=1):
                    if i == 1:
                        continue
                    if value_col in df_tab3_ss.columns:
                        st.markdown(f"##### {t(trans_key)}")
                        create_sous_secteur_ifi_graphs(df_tab3_ss, value_col, t(trans_key), f"ss_global_{trans_key}")
                        st.markdown("---")
            else:
                # Render specific indicator
                value_col, trans_key = indicator_configs_ss[selected_ss_idx]
                if value_col in df_tab3_ss.columns:
                    is_revenue = (trans_key == 'revenue')
                    render_sous_secteur_indicator_view(df_tab3_ss, value_col, t(trans_key), f"ss_{trans_key}_{selected_ss_idx}", is_revenue=is_revenue)
                else:
                    st.warning(f"Colonne '{value_col}' non disponible")
        else:
            st.warning("Colonne 'Sous-secteur' non disponible dans les données.")

    # TAB 3_MC: PAR MACRO-CATÉGORIES (same structure as Par secteurs)
    with tab3_mc:
        st.markdown(f"### {t('analysis_by_macro_category')}")

        # Filters row: Year, Antenna, Macro-catégorie
        filter_col1_mc, filter_col2_mc, filter_col3_mc = st.columns(3)

        # Year selector
        tab3_mc_years = sorted(df_combined["Année"].unique())
        with filter_col1_mc:
            if len(tab3_mc_years) > 1:
                selected_year_tab3_mc = st.selectbox(
                    t("filter_by_period"), 
                    tab3_mc_years, 
                    index=len(tab3_mc_years)-1,
                    key="macro_category_year_filter"
                )
                df_tab3_mc_base = df_combined[df_combined["Année"] == selected_year_tab3_mc]
            else:
                df_tab3_mc_base = df_combined

        if "Macro-catégorie" in df_tab3_mc_base.columns:
            # Get list of antennas and macro-catégories
            antennas_all_mc = sorted(df_tab3_mc_base["Sede"].unique().tolist())
            macro_categories = sorted(df_tab3_mc_base["Macro-catégorie"].dropna().unique().tolist())

            # Antenna filter
            with filter_col2_mc:
                antenna_options_mc = [t("all")] + antennas_all_mc
                selected_antenna_mc = st.selectbox(
                    t("filter_by_sede"), 
                    antenna_options_mc, 
                    key="macro_category_antenna_filter"
                )

            # Macro-catégorie filter - multiselect
            with filter_col3_mc:
                selected_macro_categories = st.multiselect(
                    t("filter_by_macro_category"), 
                    macro_categories,
                    default=[],
                    key="macro_category_filter",
                    placeholder=t("all")
                )

            # Apply antenna filter
            if selected_antenna_mc != t("all"):
                df_tab3_mc = df_tab3_mc_base[df_tab3_mc_base["Sede"] == selected_antenna_mc]
            else:
                df_tab3_mc = df_tab3_mc_base

            # Check if macro-catégorie(s) are selected
            macro_category_filter_active = len(selected_macro_categories) > 0

            # Text above sub-tabs
            st.markdown(f"**{t('choose_indicator')}**")

            # Initialize session state for selected indicator if not exists
            if "mc_selected_indicator" not in st.session_state:
                st.session_state.mc_selected_indicator = 0

            # Define indicator options
            mc_indicator_options = [
                t('global_view'), 
                t('inscriptions'), 
                t('new_students'), 
                t('returning_students'), 
                t('courses'), 
                t('planned_hours'), 
                t('student_hours'), 
                t('revenue')
            ]

            # Use radio buttons with horizontal layout for persistent selection
            selected_mc_indicator = st.radio(
                "",
                mc_indicator_options,
                index=st.session_state.mc_selected_indicator,
                horizontal=True,
                key="mc_indicator_radio",
                label_visibility="collapsed"
            )

            # Update session state
            st.session_state.mc_selected_indicator = mc_indicator_options.index(selected_mc_indicator)

            # Function to create macro-catégorie graphs (IFI level)
            def create_macro_category_ifi_graphs(df_data, value_col, title_suffix, tab_key):
                """Create histogram + pie chart by macro-catégorie (IFI level)"""
                mc_summary = df_data.groupby("Macro-catégorie").agg({value_col: "sum"}).reset_index()
                mc_summary = mc_summary.sort_values(value_col, ascending=False).head(15)

                # Custom purple scale with visible minimum
                PURPLE_SCALE = [[0, "#c4b5fd"], [0.25, "#a78bfa"], [0.5, "#8b5cf6"], [0.75, "#7c3aed"], [1, "#5b21b6"]]

                col1, col2 = st.columns(2)
                with col1:
                    fig_bar = px.bar(mc_summary, y="Macro-catégorie", x=value_col, orientation='h',
                                    color=value_col, color_continuous_scale=PURPLE_SCALE,
                                    title=f"{title_suffix} - Histogramme (IFI)",
                                    text=value_col)
                    fig_bar.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
                    fig_bar.update_layout(height=max(500, len(mc_summary)*30), paper_bgcolor=bg_color, plot_bgcolor=bg_color, 
                                         font=dict(color=text_color), margin=dict(l=220))
                    st.plotly_chart(fig_bar, use_container_width=True, key=f"mc_ifi_bar_{tab_key}")

                with col2:
                    purple_colors = ['#2e1065', '#4c1d95', '#5b21b6', '#6d28d9', '#7c3aed', '#8b5cf6', '#a78bfa', '#c4b5fd', '#ddd6fe']
                    fig_pie = px.pie(mc_summary, values=value_col, names="Macro-catégorie",
                                    title=f"{title_suffix} - Répartition (IFI)",
                                    color_discrete_sequence=purple_colors)
                    fig_pie.update_traces(textposition='inside', textinfo='percent+label+value')
                    fig_pie.update_layout(height=500, paper_bgcolor=bg_color, plot_bgcolor=bg_color, 
                                         font=dict(color=text_color))
                    st.plotly_chart(fig_pie, use_container_width=True, key=f"mc_ifi_pie_{tab_key}")

            # Function to create macro-catégorie heatmap
            def create_macro_category_heatmap(df_data, value_col, title_suffix, tab_key, is_revenue=False):
                """Create heatmap by macro-catégorie × antenna"""
                heatmap_data = df_data.groupby(["Macro-catégorie", "Sede"])[value_col].sum().unstack(fill_value=0)
                heatmap_data["Total (IFI)"] = heatmap_data.sum(axis=1)
                ordered_cols = [a for a in ANTENNA_ORDER if a in heatmap_data.columns] + ["Total (IFI)"]
                heatmap_data = heatmap_data[[c for c in ordered_cols if c in heatmap_data.columns]]
                heatmap_data = heatmap_data.sort_values("Total (IFI)", ascending=False).head(20)

                text_template = "€%{text:,.0f}" if is_revenue else "%{text:.0f}"

                fig = px.imshow(heatmap_data, labels=dict(x="Sede", y="Macro-catégorie", color=title_suffix), 
                               aspect="auto", color_continuous_scale=[[0, "#fbcfe8"], [0.25, "#f472b6"], [0.5, "#db2777"], [0.75, "#be185d"], [1, "#9d174d"]], text_auto=True)
                fig.update_layout(height=600, paper_bgcolor=bg_color, plot_bgcolor=bg_color, font=dict(color=text_color),
                                 title=f"Heatmap - {title_suffix}",
                                 xaxis=dict(side="top", tickfont=dict(size=14)),
                                 yaxis=dict(tickfont=dict(size=10)))
                fig.update_traces(textfont=dict(size=12))
                st.plotly_chart(fig, use_container_width=True, key=f"mc_heatmap_{tab_key}")

            # Function to create antenna graphs for macro-catégorie view
            def create_mc_antenna_graphs(df_data, value_col, antenna, title_suffix, tab_key):
                """Create histogram + pie chart pair for a specific antenna (macro-catégorie view)"""
                antenna_data = df_data[df_data["Sede"] == antenna].groupby("Macro-catégorie").agg({value_col: "sum"}).reset_index()
                antenna_data = antenna_data.sort_values(value_col, ascending=False).head(15)

                if antenna_data.empty:
                    st.info(f"Aucune donnée pour {antenna}")
                    return

                antenna_color = SEDE_COLORS.get(antenna, "#888888")
                # Create gradient for this antenna color
                def hex_to_rgb(hex_color):
                    hex_color = hex_color.lstrip('#')
                    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

                def rgb_to_hex(rgb):
                    return '#{:02x}{:02x}{:02x}'.format(int(rgb[0]), int(rgb[1]), int(rgb[2]))

                base_rgb = hex_to_rgb(antenna_color)
                color_scale = []
                for i in range(10):
                    factor = 0.15 + (i * 0.09)
                    new_rgb = tuple(min(255, int(c * factor + 255 * (1 - factor))) for c in base_rgb)
                    color_scale.append(rgb_to_hex(new_rgb))

                col1, col2 = st.columns(2)
                with col1:
                    # Inverse scale: low values get visible color
                    fig_bar = px.bar(antenna_data, y="Macro-catégorie", x=value_col, orientation='h',
                                    color=value_col, 
                                    color_continuous_scale=[[0, color_scale[3]], [0.5, antenna_color], [1, color_scale[-1]]],
                                    title=f"{title_suffix} - {antenna}",
                                    text=value_col)
                    fig_bar.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
                    fig_bar.update_layout(height=max(450, len(antenna_data)*25), paper_bgcolor=bg_color, plot_bgcolor=bg_color, 
                                         font=dict(color=text_color), coloraxis_showscale=False, margin=dict(l=220))
                    st.plotly_chart(fig_bar, use_container_width=True, key=f"mc_antenna_bar_{antenna}_{tab_key}")

                with col2:
                    fig_pie = px.pie(antenna_data, values=value_col, names="Macro-catégorie",
                                    title=f"{title_suffix} - {antenna}",
                                    color_discrete_sequence=color_scale)
                    fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                    fig_pie.update_layout(height=450, paper_bgcolor=bg_color, plot_bgcolor=bg_color, 
                                         font=dict(color=text_color))
                    st.plotly_chart(fig_pie, use_container_width=True, key=f"mc_antenna_pie_{antenna}_{tab_key}")

            # Function to create macro-catégorie comparison by antenna (when filter is active)
            def create_mc_antenna_comparison(df_data, value_col, mc_names, title_suffix, tab_key, is_multi=False):
                """Create histogram + pie chart comparing antennas for selected macro-catégorie(s)"""
                if isinstance(mc_names, str):
                    mc_names = [mc_names]

                mc_data = df_data[df_data["Macro-catégorie"].isin(mc_names)].copy()
                antenna_summary = mc_data.groupby("Sede").agg({value_col: "sum"}).reset_index()

                # For histogram: include IFI total
                ifi_total = mc_data[value_col].sum()
                ifi_row = pd.DataFrame([{"Sede": "IFI", value_col: ifi_total}])
                antenna_summary_with_ifi = pd.concat([ifi_row, antenna_summary], ignore_index=True)

                # Reorder: IFI first, then antennas
                sede_order = ["IFI"] + ANTENNA_ORDER
                antenna_summary_with_ifi["Sede"] = pd.Categorical(antenna_summary_with_ifi["Sede"], categories=sede_order, ordered=True)
                antenna_summary_with_ifi = antenna_summary_with_ifi.sort_values("Sede")

                # Title based on selection
                if is_multi or len(mc_names) > 1:
                    title_label = f"Sélection multiple ({'/'.join(mc_names[:3])}{'...' if len(mc_names) > 3 else ''})"
                else:
                    title_label = mc_names[0]

                col1, col2 = st.columns(2)
                with col1:
                    fig = px.bar(antenna_summary_with_ifi, x="Sede", y=value_col,
                                color="Sede", color_discrete_map=SEDE_COLORS,
                                title=f"{title_suffix} - {title_label} (Histogramme)",
                                text=value_col)
                    fig.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
                    fig.update_layout(height=450, paper_bgcolor=bg_color, plot_bgcolor=bg_color, 
                                     font=dict(color=text_color), showlegend=False)
                    st.plotly_chart(fig, use_container_width=True, key=f"mc_compare_bar_{tab_key}")

                with col2:
                    # Pie chart WITHOUT IFI
                    antenna_summary["Sede"] = pd.Categorical(antenna_summary["Sede"], categories=ANTENNA_ORDER, ordered=True)
                    antenna_summary = antenna_summary.sort_values("Sede")

                    fig_pie = px.pie(antenna_summary, values=value_col, names="Sede",
                                    title=f"{title_suffix} - {title_label} (Répartition)",
                                    color="Sede", color_discrete_map=SEDE_COLORS)
                    fig_pie.update_traces(textposition='inside', textinfo='percent+label+value')
                    fig_pie.update_layout(height=450, paper_bgcolor=bg_color, plot_bgcolor=bg_color, 
                                         font=dict(color=text_color))
                    st.plotly_chart(fig_pie, use_container_width=True, key=f"mc_compare_pie_{tab_key}")

            # Function to render macro-catégorie indicator view (with proper order based on filter)
            def render_macro_category_indicator_view(df_data, value_col, title_suffix, tab_key, is_revenue=False):
                # If filter is active, show filtered content first
                if macro_category_filter_active:
                    # SECTION 1: Filtered macro-catégorie(s) graphs
                    is_multi = len(selected_macro_categories) > 1
                    df_filtered = df_data[df_data["Macro-catégorie"].isin(selected_macro_categories)]

                    filter_label = '/'.join(selected_macro_categories[:3]) + ('...' if len(selected_macro_categories) > 3 else '')
                    st.markdown(f"#### Sélection : {filter_label}")

                    # Filtered IFI graphs
                    create_macro_category_ifi_graphs(df_filtered, value_col, title_suffix, f"{tab_key}_filtered")
                    st.markdown("---")

                    # Filtered heatmap
                    create_macro_category_heatmap(df_filtered, value_col, title_suffix, f"{tab_key}_filtered_heatmap", is_revenue=is_revenue)
                    st.markdown("---")

                    # Comparison by antenna for selected macro-catégorie(s)
                    comparison_title = f"{t('comparison_by_antenna')} - {filter_label}"
                    st.markdown(f"#### {comparison_title}")
                    create_mc_antenna_comparison(df_data, value_col, selected_macro_categories, title_suffix, f"{tab_key}_mc_cmp", is_multi=is_multi)
                    st.markdown("---")

                # IFI Total (all antennas combined)
                st.markdown(f"#### {t('ifi_all_antennas')}")
                create_macro_category_ifi_graphs(df_data, value_col, title_suffix, tab_key)
                st.markdown("---")

                # Heatmap
                create_macro_category_heatmap(df_data, value_col, title_suffix, f"{tab_key}_heatmap", is_revenue=is_revenue)
                st.markdown("---")

                # SECTION: Détails par antenne
                st.markdown(f"#### {t('details_by_antenna')}")
                for antenna in ANTENNA_ORDER:
                    if antenna in df_data["Sede"].unique():
                        create_mc_antenna_graphs(df_data, value_col, antenna, title_suffix, f"{tab_key}_{antenna}")

            indicator_configs_mc = [
                (inscr_col, 'inscriptions'),
                (inscr_col, 'inscriptions'),
                ("Nouveaux inscrits", 'new_students'),
                ("Réinscrits", 'returning_students'),
                ("Nb. de Cours", 'courses'),
                ("Nombre d'heures prévues", 'planned_hours'),
                ("Nombre total d'heures vendues (heures-étudiants)", 'student_hours'),
                ("Recettes", 'revenue')
            ]

            # Render content based on selected indicator (using session state)
            selected_mc_idx = st.session_state.mc_selected_indicator

            if selected_mc_idx == 0:
                # Vue globale
                st.markdown("#### Vue d'ensemble - Tous les indicateurs (IFI)")
                for i, (value_col, trans_key) in enumerate(indicator_configs_mc[1:], start=1):
                    if i == 1:
                        continue
                    if value_col in df_tab3_mc.columns:
                        st.markdown(f"##### {t(trans_key)}")
                        create_macro_category_ifi_graphs(df_tab3_mc, value_col, t(trans_key), f"mc_global_{trans_key}")
                        st.markdown("---")
            else:
                # Render specific indicator
                value_col, trans_key = indicator_configs_mc[selected_mc_idx]
                if value_col in df_tab3_mc.columns:
                    is_revenue = (trans_key == 'revenue')
                    render_macro_category_indicator_view(df_tab3_mc, value_col, t(trans_key), f"mc_{trans_key}_{selected_mc_idx}", is_revenue=is_revenue)
                else:
                    st.warning(f"Colonne '{value_col}' non disponible")
        else:
            st.warning("Colonne 'Macro-catégorie' non disponible dans les données.")

    # TAB 3B: PAR CATÉGORIES (structure like Vue secteurs but by category)
    with tab3b:
        st.markdown(f"### {t('analysis_by_category')}")

        # Filters row: Year, Antenna, Category
        filter_col1_cat, filter_col2_cat, filter_col3_cat = st.columns(3)

        # Year selector
        tab3b_years = sorted(df_combined["Année"].unique())
        with filter_col1_cat:
            if len(tab3b_years) > 1:
                selected_year_tab3b = st.selectbox(
                    t("filter_by_period"), 
                    tab3b_years, 
                    index=len(tab3b_years)-1,
                    key="category_year_filter"
                )
                df_tab3b_base = df_combined[df_combined["Année"] == selected_year_tab3b]
            else:
                df_tab3b_base = df_combined

        # Check if "Catégorie de cours" column exists
        if "Catégorie de cours" in df_tab3b_base.columns:
            # Get list of antennas and categories
            antennas_all_cat = sorted(df_tab3b_base["Sede"].unique().tolist())
            categories = sorted(df_tab3b_base["Catégorie de cours"].dropna().unique().tolist())

            # Antenna filter
            with filter_col2_cat:
                antenna_options_cat = [t("all")] + antennas_all_cat
                selected_antenna_cat = st.selectbox(
                    t("filter_by_sede"), 
                    antenna_options_cat, 
                    key="category_antenna_filter"
                )

            # Category filter - multiselect
            with filter_col3_cat:
                selected_categories = st.multiselect(
                    t("filter_by_category"), 
                    categories,
                    default=[],
                    key="category_category_filter",
                    placeholder=t("all")
                )

            # Apply antenna filter
            if selected_antenna_cat != t("all"):
                df_tab3b = df_tab3b_base[df_tab3b_base["Sede"] == selected_antenna_cat]
            else:
                df_tab3b = df_tab3b_base

            # Check if category(ies) are selected
            category_filter_active = len(selected_categories) > 0
            is_multi_category = len(selected_categories) > 1

            # Text above sub-tabs
            st.markdown(f"**{t('choose_indicator')}**")

            # Initialize session state for selected indicator if not exists
            if "cat_selected_indicator" not in st.session_state:
                st.session_state.cat_selected_indicator = 0

            # Define indicator options
            cat_indicator_options = [
                t('global_view'), 
                t('inscriptions'), 
                t('new_students'), 
                t('returning_students'), 
                t('courses'), 
                t('planned_hours'), 
                t('student_hours'), 
                t('revenue')
            ]

            # Use radio buttons with horizontal layout for persistent selection
            selected_cat_indicator = st.radio(
                "",
                cat_indicator_options,
                index=st.session_state.cat_selected_indicator,
                horizontal=True,
                key="cat_indicator_radio",
                label_visibility="collapsed"
            )

            # Update session state
            st.session_state.cat_selected_indicator = cat_indicator_options.index(selected_cat_indicator)

            # Indicator configurations
            indicator_configs_cat = [
                (inscr_col, 'inscriptions'),
                (inscr_col, 'inscriptions'),
                ("Nouveaux inscrits", 'new_students'),
                ("Réinscrits", 'returning_students'),
                ("Nb. de Cours", 'courses'),
                ("Nombre d'heures prévues", 'planned_hours'),
                ("Nombre total d'heures vendues (heures-étudiants)", 'student_hours'),
                ("Recettes", 'revenue')
            ]

            # Function to create category graphs (IFI level - by category)
            def create_category_ifi_graphs(df_data, value_col, title_suffix, tab_key):
                """Create histogram + pie chart by category (IFI level)"""
                cat_summary = df_data.groupby("Catégorie de cours").agg({value_col: "sum"}).reset_index()
                cat_summary = cat_summary.sort_values(value_col, ascending=False).head(15)  # Top 15 for readability

                # Custom blue scale with visible minimum
                BLUE_SCALE = [[0, "#93c5fd"], [0.25, "#60a5fa"], [0.5, "#3b82f6"], [0.75, "#2563eb"], [1, "#1e40af"]]

                col1, col2 = st.columns(2)
                with col1:
                    fig_bar = px.bar(cat_summary, y="Catégorie de cours", x=value_col, orientation='h',
                                    color=value_col, color_continuous_scale=BLUE_SCALE,
                                    title=f"{title_suffix} - Top catégories (IFI)",
                                    text=value_col)
                    fig_bar.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
                    fig_bar.update_layout(height=max(500, len(cat_summary)*30), paper_bgcolor=bg_color, plot_bgcolor=bg_color, 
                                         font=dict(color=text_color), margin=dict(l=200))
                    st.plotly_chart(fig_bar, use_container_width=True, key=f"cat_ifi_bar_{tab_key}")

                with col2:
                    blue_colors = ['#0c1445', '#1e3a8a', '#1e40af', '#2563eb', '#3b82f6', '#60a5fa', '#93c5fd', '#c7d9f5', '#e8f0fc']
                    fig_pie = px.pie(cat_summary, values=value_col, names="Catégorie de cours",
                                    title=f"{title_suffix} - Répartition (IFI)",
                                    color_discrete_sequence=blue_colors)
                    fig_pie.update_traces(textposition='inside', textinfo='percent+label+value')
                    fig_pie.update_layout(height=500, paper_bgcolor=bg_color, plot_bgcolor=bg_color, 
                                         font=dict(color=text_color))
                    st.plotly_chart(fig_pie, use_container_width=True, key=f"cat_ifi_pie_{tab_key}")

            # Function to create category heatmap (category × antenna)
            def create_category_heatmap(df_data, value_col, title_suffix, tab_key, is_revenue=False):
                """Create heatmap by category × antenna"""
                heatmap_data = df_data.groupby(["Catégorie de cours", "Sede"])[value_col].sum().unstack(fill_value=0)
                # Add Total column
                heatmap_data["Total (IFI)"] = heatmap_data.sum(axis=1)
                # Reorder columns
                ordered_cols = [a for a in ANTENNA_ORDER if a in heatmap_data.columns] + ["Total (IFI)"]
                heatmap_data = heatmap_data[[c for c in ordered_cols if c in heatmap_data.columns]]
                # Sort by Total descending and take top 20
                heatmap_data = heatmap_data.sort_values("Total (IFI)", ascending=False).head(20)

                # Format template
                text_template = "€%{text:,.0f}" if is_revenue else "%{text:.0f}"

                fig = px.imshow(heatmap_data, labels=dict(x="Sede", y="Catégorie", color=title_suffix), 
                               aspect="auto", color_continuous_scale=[[0, "#fef3c7"], [0.25, "#fcd34d"], [0.5, "#f97316"], [0.75, "#ea580c"], [1, "#c2410c"]], text_auto=True)
                fig.update_layout(height=600, paper_bgcolor=bg_color, plot_bgcolor=bg_color, font=dict(color=text_color),
                                 xaxis=dict(side="top", tickfont=dict(size=14)),
                                 yaxis=dict(tickfont=dict(size=10)))
                fig.update_traces(textfont=dict(size=12))
                st.caption(t('heatmap_subtitle').replace("secteur", "catégorie"))
                st.plotly_chart(fig, use_container_width=True, key=f"cat_heatmap_{tab_key}")

            # Function for category comparison by antenna
            def create_category_antenna_comparison(df_data, value_col, category_names, title_suffix, tab_key, is_multi=False):
                """Create histogram + pie chart comparing antennas for selected category(ies)"""
                if isinstance(category_names, str):
                    category_names = [category_names]

                cat_data = df_data[df_data["Catégorie de cours"].isin(category_names)].copy()
                antenna_summary = cat_data.groupby("Sede").agg({value_col: "sum"}).reset_index()

                # Add IFI total
                ifi_total = cat_data[value_col].sum()
                ifi_row = pd.DataFrame([{"Sede": "IFI", value_col: ifi_total}])
                antenna_summary_with_ifi = pd.concat([ifi_row, antenna_summary], ignore_index=True)

                # Reorder
                sede_order = ["IFI"] + ANTENNA_ORDER
                antenna_summary_with_ifi["Sede"] = pd.Categorical(antenna_summary_with_ifi["Sede"], categories=sede_order, ordered=True)
                antenna_summary_with_ifi = antenna_summary_with_ifi.sort_values("Sede")

                # Title
                if is_multi or len(category_names) > 1:
                    title_label = f"Sélection multiple ({'/'.join([c[:20] for c in category_names[:2]])}{'...' if len(category_names) > 2 else ''})"
                else:
                    title_label = category_names[0]

                col1, col2 = st.columns(2)
                with col1:
                    fig = px.bar(antenna_summary_with_ifi, x="Sede", y=value_col,
                                color="Sede", color_discrete_map=SEDE_COLORS,
                                title=f"{title_suffix} - {title_label}",
                                text=value_col)
                    fig.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
                    fig.update_layout(height=450, paper_bgcolor=bg_color, plot_bgcolor=bg_color, 
                                     font=dict(color=text_color), showlegend=False)
                    st.plotly_chart(fig, use_container_width=True, key=f"cat_compare_bar_{tab_key}")

                with col2:
                    antenna_summary["Sede"] = pd.Categorical(antenna_summary["Sede"], categories=ANTENNA_ORDER, ordered=True)
                    antenna_summary = antenna_summary.sort_values("Sede")
                    fig_pie = px.pie(antenna_summary, values=value_col, names="Sede",
                                    title=f"{title_suffix} - {title_label} (Répartition)",
                                    color="Sede", color_discrete_map=SEDE_COLORS)
                    fig_pie.update_traces(textposition='inside', textinfo='percent+label+value')
                    fig_pie.update_layout(height=450, paper_bgcolor=bg_color, plot_bgcolor=bg_color, 
                                         font=dict(color=text_color))
                    st.plotly_chart(fig_pie, use_container_width=True, key=f"cat_compare_pie_{tab_key}")

            # Function to create per-antenna category graphs
            def create_antenna_category_graphs(df_data, value_col, antenna, title_suffix, tab_key):
                """Create histogram + pie chart for a specific antenna showing categories"""
                antenna_data = df_data[df_data["Sede"] == antenna].groupby("Catégorie de cours").agg({value_col: "sum"}).reset_index()
                antenna_data = antenna_data.sort_values(value_col, ascending=False).head(10)

                if antenna_data.empty:
                    st.info(f"Aucune donnée pour {antenna}")
                    return

                antenna_color = SEDE_COLORS.get(antenna, "#888888")

                col1, col2 = st.columns(2)
                with col1:
                    # Create gradient for this antenna with visible min/max
                    def hex_to_rgb(hex_color):
                        hex_color = hex_color.lstrip('#')
                        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

                    def rgb_to_hex(rgb):
                        return '#{:02x}{:02x}{:02x}'.format(int(rgb[0]), int(rgb[1]), int(rgb[2]))

                    base_rgb = hex_to_rgb(antenna_color)
                    # Light version of antenna color for min values
                    light_color = rgb_to_hex(tuple(min(255, int(c * 0.4 + 255 * 0.6)) for c in base_rgb))
                    # Dark version for max values
                    dark_color = rgb_to_hex(tuple(int(c * 0.7) for c in base_rgb))

                    fig_bar = px.bar(antenna_data, y="Catégorie de cours", x=value_col, orientation='h',
                                    color=value_col, 
                                    color_continuous_scale=[[0, light_color], [0.5, antenna_color], [1, dark_color]],
                                    title=f"{title_suffix} - {antenna}",
                                    text=value_col)
                    fig_bar.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
                    fig_bar.update_layout(height=max(350, len(antenna_data)*30), paper_bgcolor=bg_color, plot_bgcolor=bg_color, 
                                         font=dict(color=text_color), coloraxis_showscale=False, margin=dict(l=200))
                    st.plotly_chart(fig_bar, use_container_width=True, key=f"cat_antenna_bar_{antenna}_{tab_key}")

                with col2:
                    fig_pie = px.pie(antenna_data, values=value_col, names="Catégorie de cours",
                                    title=f"{title_suffix} - {antenna}")
                    fig_pie.update_traces(textposition='inside', textinfo='percent+label+value')
                    fig_pie.update_layout(height=350, paper_bgcolor=bg_color, plot_bgcolor=bg_color, 
                                         font=dict(color=text_color))
                    st.plotly_chart(fig_pie, use_container_width=True, key=f"cat_antenna_pie_{antenna}_{tab_key}")

            # Function to render full category view (with proper order based on filter)
            def render_category_indicator_view(df_data, value_col, title_suffix, tab_key, is_revenue=False):
                """Render the full view for an indicator in category tab"""

                # If filter is active, show filtered content first
                if category_filter_active:
                    # SECTION 1: Filtered category(ies) graphs
                    is_multi = len(selected_categories) > 1
                    df_filtered = df_data[df_data["Catégorie de cours"].isin(selected_categories)]

                    filter_label = '/'.join([c[:25] for c in selected_categories[:2]]) + ('...' if len(selected_categories) > 2 else '')
                    st.markdown(f"#### Sélection : {filter_label}")

                    # Filtered IFI graphs
                    create_category_ifi_graphs(df_filtered, value_col, title_suffix, f"{tab_key}_filtered")
                    st.markdown("---")

                    # Filtered heatmap
                    create_category_heatmap(df_filtered, value_col, title_suffix, f"{tab_key}_filtered_heatmap", is_revenue=is_revenue)
                    st.markdown("---")

                    # Comparison by antenna for selected category(ies)
                    comparison_title = f"{t('comparison_by_antenna')} - {filter_label}"
                    st.markdown(f"#### {comparison_title}")
                    create_category_antenna_comparison(df_tab3b_base, value_col, selected_categories, title_suffix, f"{tab_key}_cat_cmp", is_multi=is_multi)
                    st.markdown("---")

                # IFI Total (all antennas combined) - by category
                st.markdown(f"#### {t('ifi_all_antennas')} - Par catégorie")
                create_category_ifi_graphs(df_data, value_col, title_suffix, tab_key)
                st.markdown("---")

                # Heatmap
                st.markdown(f"#### {t('heatmap_title')} - {title_suffix}")
                create_category_heatmap(df_tab3b_base, value_col, title_suffix, f"{tab_key}_heatmap", is_revenue=is_revenue)
                st.markdown("---")

                # SECTION: Détails par antenne
                st.markdown(f"#### {t('details_by_antenna')}")
                for antenna in ANTENNA_ORDER:
                    if antenna in df_data["Sede"].unique():
                        create_antenna_category_graphs(df_data, value_col, antenna, title_suffix, f"{tab_key}_{antenna}")

            # Render content based on selected indicator (using session state)
            selected_cat_idx = st.session_state.cat_selected_indicator

            if selected_cat_idx == 0:
                # Global view
                st.markdown("#### Vue d'ensemble - Tous les indicateurs (IFI)")
                for i, (value_col_cat, trans_key_cat) in enumerate(indicator_configs_cat[1:], start=1):
                    if i == 1:
                        continue
                    if value_col_cat in df_tab3b.columns:
                        st.markdown(f"##### {t(trans_key_cat)}")
                        create_category_ifi_graphs(df_tab3b, value_col_cat, t(trans_key_cat), f"cat_global_{trans_key_cat}")
                        st.markdown("---")
            else:
                # Render specific indicator
                value_col_cat, trans_key_cat = indicator_configs_cat[selected_cat_idx]
                if value_col_cat in df_tab3b.columns:
                    is_revenue_cat = (trans_key_cat == 'revenue')
                    render_category_indicator_view(
                        df_tab3b, value_col_cat, t(trans_key_cat), 
                        f"cat_{trans_key_cat}_{selected_cat_idx}",
                        is_revenue=is_revenue_cat
                    )
                else:
                    st.warning(f"Colonne '{value_col_cat}' non disponible")
        else:
            st.warning("La colonne 'Catégorie de cours' n'est pas disponible dans les données.")

    # TAB 4: PAR ANNÉE (refonte complète)
    with tab4:
        st.markdown("### Analyse par année")

        years = sorted(df_combined["Année"].unique())

        if len(years) < 1:
            st.warning("Aucune donnée chargée.")
        else:
            # 3 sub-levels using expanders

            # ============================================
            # NIVEAU 1: RÉSUMÉ DE L'ANNÉE
            # ============================================
            with st.expander("Résumé de l'année", expanded=True):
                # Year filter for this section
                col_filter1, col_filter2, col_filter3 = st.columns([1, 2, 2])
                with col_filter1:
                    selected_year_resume = st.selectbox(
                        "Année à analyser",
                        years,
                        index=len(years)-1,
                        key="resume_year_filter"
                    )

                # Filter data for selected year only (no multi-year sum)
                df_resume = df_combined[df_combined["Année"] == selected_year_resume]

                st.markdown(f"#### Indicateurs {selected_year_resume}")

                # Show metrics for selected year
                col1, col2, col3, col4 = st.columns(4)
                col5, col6, col7, col8 = st.columns(4)

                with col1:
                    val = df_resume[inscr_col].sum() if inscr_col in df_resume.columns else 0
                    st.metric(t('inscriptions'), f"{val:,.0f}")
                with col2:
                    val = df_resume["Nb. de Cours"].sum() if "Nb. de Cours" in df_resume.columns else 0
                    st.metric(t('courses'), f"{val:,.0f}")
                with col3:
                    val = df_resume["Recettes"].sum() if "Recettes" in df_resume.columns else 0
                    st.metric(t('revenue'), f"€{val:,.0f}")
                with col4:
                    val = df_resume["Nombre d'heures prévues"].sum() if "Nombre d'heures prévues" in df_resume.columns else 0
                    st.metric(t('planned_hours'), f"{val:,.0f}")
                with col5:
                    val = df_resume["Nouveaux inscrits"].sum() if "Nouveaux inscrits" in df_resume.columns else 0
                    st.metric(t('new_students'), f"{val:,.0f}")
                with col6:
                    val = df_resume["Réinscrits"].sum() if "Réinscrits" in df_resume.columns else 0
                    st.metric(t('returning_students'), f"{val:,.0f}")
                with col7:
                    val = df_resume["Nombre total d'heures vendues (heures-étudiants)"].sum() if "Nombre total d'heures vendues (heures-étudiants)" in df_resume.columns else 0
                    st.metric(t('student_hours'), f"{val:,.0f}")
                with col8:
                    # ARPI
                    inscr = df_resume[inscr_col].sum() if inscr_col in df_resume.columns else 0
                    recettes = df_resume["Recettes"].sum() if "Recettes" in df_resume.columns else 0
                    arpi = recettes / inscr if inscr > 0 else 0
                    st.metric("ARPI (€/inscr)", f"€{arpi:.2f}")

                # Répartition par antenne pour l'année sélectionnée
                st.markdown(f"#### Répartition par antenne - {selected_year_resume}")
                sede_resume = df_resume.groupby("Sede").agg({
                    inscr_col: "sum",
                    "Nb. de Cours": "sum",
                    "Recettes": "sum"
                }).reset_index() if all(c in df_resume.columns for c in [inscr_col, "Nb. de Cours", "Recettes"]) else None

                if sede_resume is not None:
                    col1, col2 = st.columns(2)
                    with col1:
                        fig = px.bar(sede_resume, x="Sede", y=inscr_col, color="Sede", 
                                    color_discrete_map=SEDE_COLORS, text=inscr_col,
                                    title=f"Inscriptions par antenne - {selected_year_resume}")
                        fig.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
                        fig.update_layout(height=400, showlegend=False, paper_bgcolor=bg_color, plot_bgcolor=bg_color, font=dict(color=text_color))
                        st.plotly_chart(fig, use_container_width=True, key="resume_inscr_sede")
                    with col2:
                        fig = px.pie(sede_resume, values=inscr_col, names="Sede", color="Sede",
                                    color_discrete_map=SEDE_COLORS, title=f"Répartition - {selected_year_resume}")
                        fig.update_traces(textposition='inside', textinfo='percent+label+value')
                        fig.update_layout(height=400, paper_bgcolor=bg_color, font=dict(color=text_color))
                        st.plotly_chart(fig, use_container_width=True, key="resume_inscr_pie")

            # ============================================
            # NIVEAU 2: ÉVOLUTION PLURIANNUELLE
            # ============================================
            with st.expander("Évolution pluriannuelle", expanded=True if len(years) > 1 else False):
                if len(years) < 2:
                    st.info("Chargez les données de plusieurs années pour voir l'évolution.")
                else:
                    # Filters row
                    filter_col1, filter_col2, filter_col3, filter_col4, filter_col5 = st.columns(5)

                    with filter_col1:
                        antenna_options_yoy = [t("all")] + sorted(df_combined["Sede"].unique().tolist())
                        selected_antenna_yoy = st.selectbox(
                            t("filter_by_sede"),
                            antenna_options_yoy,
                            key="yoy_antenna_filter"
                        )

                    with filter_col2:
                        sector_options_yoy = [t("all")] + sorted(df_combined["Secteur"].dropna().unique().tolist()) if "Secteur" in df_combined.columns else [t("all")]
                        selected_sector_yoy = st.selectbox(
                            t("filter_by_sector"),
                            sector_options_yoy,
                            key="yoy_sector_filter"
                        )

                    with filter_col3:
                        ss_options_yoy = [t("all")] + sorted(df_combined["Sous-secteur"].dropna().unique().tolist()) if "Sous-secteur" in df_combined.columns else [t("all")]
                        selected_ss_yoy = st.selectbox(
                            t("filter_by_sous_secteur"),
                            ss_options_yoy,
                            key="yoy_ss_filter"
                        )

                    with filter_col4:
                        mc_options_yoy = [t("all")] + sorted(df_combined["Macro-catégorie"].dropna().unique().tolist()) if "Macro-catégorie" in df_combined.columns else [t("all")]
                        selected_mc_yoy = st.selectbox(
                            t("filter_by_macro_category"),
                            mc_options_yoy,
                            key="yoy_mc_filter"
                        )

                    with filter_col5:
                        cat_options_yoy = [t("all")] + sorted(df_combined["Catégorie de cours"].dropna().unique().tolist()) if "Catégorie de cours" in df_combined.columns else [t("all")]
                        selected_cat_yoy = st.selectbox(
                            t("filter_by_category"),
                            cat_options_yoy,
                            key="yoy_cat_filter"
                        )

                    # Apply filters
                    df_yoy = df_combined.copy()
                    if selected_antenna_yoy != t("all"):
                        df_yoy = df_yoy[df_yoy["Sede"] == selected_antenna_yoy]
                    if selected_sector_yoy != t("all") and "Secteur" in df_yoy.columns:
                        df_yoy = df_yoy[df_yoy["Secteur"] == selected_sector_yoy]
                    if selected_ss_yoy != t("all") and "Sous-secteur" in df_yoy.columns:
                        df_yoy = df_yoy[df_yoy["Sous-secteur"] == selected_ss_yoy]
                    if selected_mc_yoy != t("all") and "Macro-catégorie" in df_yoy.columns:
                        df_yoy = df_yoy[df_yoy["Macro-catégorie"] == selected_mc_yoy]
                    if selected_cat_yoy != t("all") and "Catégorie de cours" in df_yoy.columns:
                        df_yoy = df_yoy[df_yoy["Catégorie de cours"] == selected_cat_yoy]

                    # Build evolution data
                    evolution_data = df_yoy.groupby("Année").agg({
                        inscr_col: "sum",
                        "Nb. de Cours": "sum",
                        "Recettes": "sum",
                        "Nombre d'heures prévues": "sum",
                        "Nouveaux inscrits": "sum",
                        "Réinscrits": "sum",
                        "Nombre total d'heures vendues (heures-étudiants)": "sum"
                    }).reset_index() if all(c in df_yoy.columns for c in [inscr_col, "Nb. de Cours", "Recettes"]) else None

                    if evolution_data is not None and len(evolution_data) > 0:
                        # Rename columns for easier use
                        evolution_data.columns = ["Année", "Inscriptions", "Cours", "Recettes", "Heures prévues", "Nouveaux", "Réinscrits", "Heures-élèves"]

                        # Grid of histograms: 2 rows x 4 cols
                        st.markdown("#### Évolution des indicateurs")

                        indicators_yoy = [
                            ("Inscriptions", "#6366f1"),
                            ("Cours", "#10b981"),
                            ("Recettes", "#f59e0b"),
                            ("Heures prévues", "#ef4444"),
                            ("Nouveaux", "#8b5cf6"),
                            ("Réinscrits", "#ec4899"),
                            ("Heures-élèves", "#14b8a6"),
                        ]

                        # 2 rows of histograms
                        col1, col2, col3, col4 = st.columns(4)
                        cols_row1 = [col1, col2, col3, col4]

                        for i, (indicator, color) in enumerate(indicators_yoy[:4]):
                            with cols_row1[i]:
                                fig = px.bar(evolution_data, x="Année", y=indicator, color_discrete_sequence=[color],
                                            title=indicator, text=indicator)
                                fig.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
                                fig.update_layout(height=300, showlegend=False, paper_bgcolor=bg_color, plot_bgcolor=bg_color, 
                                                font=dict(color=text_color), margin=dict(t=40, b=20))
                                fig.update_xaxes(type='category')
                                st.plotly_chart(fig, use_container_width=True, key=f"yoy_evol_{indicator}")

                        col5, col6, col7, _ = st.columns(4)
                        cols_row2 = [col5, col6, col7]

                        for i, (indicator, color) in enumerate(indicators_yoy[4:7]):
                            with cols_row2[i]:
                                fig = px.bar(evolution_data, x="Année", y=indicator, color_discrete_sequence=[color],
                                            title=indicator, text=indicator)
                                fig.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
                                fig.update_layout(height=300, showlegend=False, paper_bgcolor=bg_color, plot_bgcolor=bg_color, 
                                                font=dict(color=text_color), margin=dict(t=40, b=20))
                                fig.update_xaxes(type='category')
                                st.plotly_chart(fig, use_container_width=True, key=f"yoy_evol_{indicator}")
                    else:
                        st.warning("Données insuffisantes pour l'évolution pluriannuelle avec les filtres sélectionnés.")

            # ============================================
            # NIVEAU 3: VARIATIONS PAR ANTENNE
            # ============================================
            with st.expander("Variations par antenne", expanded=True if len(years) > 1 else False):
                if len(years) < 2:
                    st.info("Chargez les données de plusieurs années pour voir les variations.")
                else:
                    # Filters row (same as level 2)
                    var_filter_col1, var_filter_col2, var_filter_col3, var_filter_col4, var_filter_col5 = st.columns(5)

                    with var_filter_col1:
                        var_antenna_options = [t("all")] + sorted(df_combined["Sede"].unique().tolist())
                        var_selected_antenna = st.selectbox(
                            t("filter_by_sede"),
                            var_antenna_options,
                            key="var_antenna_filter"
                        )

                    with var_filter_col2:
                        var_sector_options = [t("all")] + sorted(df_combined["Secteur"].dropna().unique().tolist()) if "Secteur" in df_combined.columns else [t("all")]
                        var_selected_sector = st.selectbox(
                            t("filter_by_sector"),
                            var_sector_options,
                            key="var_sector_filter"
                        )

                    with var_filter_col3:
                        var_ss_options = [t("all")] + sorted(df_combined["Sous-secteur"].dropna().unique().tolist()) if "Sous-secteur" in df_combined.columns else [t("all")]
                        var_selected_ss = st.selectbox(
                            t("filter_by_sous_secteur"),
                            var_ss_options,
                            key="var_ss_filter"
                        )

                    with var_filter_col4:
                        var_mc_options = [t("all")] + sorted(df_combined["Macro-catégorie"].dropna().unique().tolist()) if "Macro-catégorie" in df_combined.columns else [t("all")]
                        var_selected_mc = st.selectbox(
                            t("filter_by_macro_category"),
                            var_mc_options,
                            key="var_mc_filter"
                        )

                    with var_filter_col5:
                        var_cat_options = [t("all")] + sorted(df_combined["Catégorie de cours"].dropna().unique().tolist()) if "Catégorie de cours" in df_combined.columns else [t("all")]
                        var_selected_cat = st.selectbox(
                            t("filter_by_category"),
                            var_cat_options,
                            key="var_cat_filter"
                        )

                    # Apply filters
                    df_var = df_combined.copy()
                    if var_selected_antenna != t("all"):
                        df_var = df_var[df_var["Sede"] == var_selected_antenna]
                    if var_selected_sector != t("all") and "Secteur" in df_var.columns:
                        df_var = df_var[df_var["Secteur"] == var_selected_sector]
                    if var_selected_ss != t("all") and "Sous-secteur" in df_var.columns:
                        df_var = df_var[df_var["Sous-secteur"] == var_selected_ss]
                    if var_selected_mc != t("all") and "Macro-catégorie" in df_var.columns:
                        df_var = df_var[df_var["Macro-catégorie"] == var_selected_mc]
                    if var_selected_cat != t("all") and "Catégorie de cours" in df_var.columns:
                        df_var = df_var[df_var["Catégorie de cours"] == var_selected_cat]

                    st.markdown("#### Tableaux de variations et histogrammes par indicateur")

                    # Indicator configs for this section
                    variation_indicators = [
                        (inscr_col, "Inscriptions", "#6366f1"),
                        ("Nb. de Cours", "Cours", "#10b981"),
                        ("Recettes", "Recettes (€)", "#f59e0b"),
                        ("Nombre d'heures prévues", "Heures prévues", "#ef4444"),
                        ("Nouveaux inscrits", "Nouveaux inscrits", "#8b5cf6"),
                        ("Réinscrits", "Réinscrits", "#ec4899"),
                        ("Nombre total d'heures vendues (heures-étudiants)", "Heures-élèves", "#14b8a6"),
                    ]

                    for col_name, indicator_label, color in variation_indicators:
                        if col_name not in df_var.columns:
                            continue

                        st.markdown(f"##### {indicator_label}")

                        # Create pivot: Years as rows, Antennas as columns
                        pivot_data = df_var.groupby(["Année", "Sede"])[col_name].sum().unstack(fill_value=0)

                        # Add IFI total column
                        pivot_data["IFI (Total)"] = pivot_data.sum(axis=1)

                        # Reorder columns
                        ordered_cols = [a for a in ANTENNA_ORDER if a in pivot_data.columns] + ["IFI (Total)"]
                        pivot_data = pivot_data[[c for c in ordered_cols if c in pivot_data.columns]]

                        # Create variation rows between years
                        years_list = sorted(pivot_data.index.tolist())
                        result_rows = []

                        for i, year in enumerate(years_list):
                            # Add year data row
                            row_data = {"Période": str(year)}
                            for col in pivot_data.columns:
                                val = pivot_data.loc[year, col]
                                row_data[col] = f"{val:,.0f}" if indicator_label != "Recettes (€)" else f"€{val:,.0f}"
                            result_rows.append(row_data)

                            # Add variation row if not last year
                            if i < len(years_list) - 1:
                                next_year = years_list[i + 1]
                                var_row = {"Période": f"Δ {year}→{next_year}"}
                                for col in pivot_data.columns:
                                    prev_val = pivot_data.loc[year, col]
                                    next_val = pivot_data.loc[next_year, col]
                                    if prev_val > 0:
                                        pct_change = ((next_val - prev_val) / prev_val) * 100
                                        var_row[col] = f"{pct_change:+.1f}%"
                                    else:
                                        var_row[col] = "N/A"
                                result_rows.append(var_row)

                        result_df = pd.DataFrame(result_rows)

                        # Display table and histogram side by side
                        col_table, col_chart = st.columns([1, 1])

                        with col_table:
                            st.dataframe(result_df, hide_index=True, use_container_width=True)

                        with col_chart:
                            # Histogram: grouped bar by year
                            chart_data = df_var.groupby(["Année", "Sede"])[col_name].sum().reset_index()
                            fig = px.bar(
                                chart_data, x="Sede", y=col_name, color="Année",
                                barmode="group", 
                                color_discrete_sequence=px.colors.qualitative.Set2,
                                title=f"{indicator_label} par antenne - Comparaison annuelle",
                                text=col_name
                            )
                            fig.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
                            fig.update_layout(height=350, paper_bgcolor=bg_color, plot_bgcolor=bg_color, 
                                             font=dict(color=text_color), margin=dict(t=40, b=20))
                            st.plotly_chart(fig, use_container_width=True, key=f"var_chart_{indicator_label}")

                        st.markdown("---")

    # TAB EVOLUTIONS: Multi-indicator evolution curves
    with tab_evo:
        st.markdown(f"### {t('evolution_title')}")

        # Check if we have multiple years
        evo_years = sorted(df_combined["Année"].unique())

        if len(evo_years) < 2:
            st.warning(t('need_multiple_years'))
        else:
            # Filters section
            st.markdown("**Filtres**")
            filter_cols = st.columns(4)

            with filter_cols[0]:
                evo_sectors = [t("all")] + sorted(df_combined["Secteur"].dropna().unique().tolist())
                evo_selected_sector = st.selectbox(t("filter_by_sector"), evo_sectors, key="evo_sector_filter")

            with filter_cols[1]:
                if evo_selected_sector != t("all"):
                    evo_ss_options = [t("all")] + sorted(df_combined[df_combined["Secteur"] == evo_selected_sector]["Sous-secteur"].dropna().unique().tolist())
                else:
                    evo_ss_options = [t("all")] + sorted(df_combined["Sous-secteur"].dropna().unique().tolist())
                evo_selected_ss = st.selectbox(t("filter_by_sous_secteur"), evo_ss_options, key="evo_ss_filter")

            with filter_cols[2]:
                if evo_selected_ss != t("all"):
                    evo_mc_options = [t("all")] + sorted(df_combined[df_combined["Sous-secteur"] == evo_selected_ss]["Macro-catégorie"].dropna().unique().tolist())
                elif evo_selected_sector != t("all"):
                    evo_mc_options = [t("all")] + sorted(df_combined[df_combined["Secteur"] == evo_selected_sector]["Macro-catégorie"].dropna().unique().tolist())
                else:
                    evo_mc_options = [t("all")] + sorted(df_combined["Macro-catégorie"].dropna().unique().tolist())
                evo_selected_mc = st.selectbox(t("filter_by_macro_category"), evo_mc_options, key="evo_mc_filter")

            with filter_cols[3]:
                if evo_selected_mc != t("all"):
                    evo_cat_options = [t("all")] + sorted(df_combined[df_combined["Macro-catégorie"] == evo_selected_mc]["Catégorie de cours"].dropna().unique().tolist())
                elif evo_selected_ss != t("all"):
                    evo_cat_options = [t("all")] + sorted(df_combined[df_combined["Sous-secteur"] == evo_selected_ss]["Catégorie de cours"].dropna().unique().tolist())
                elif evo_selected_sector != t("all"):
                    evo_cat_options = [t("all")] + sorted(df_combined[df_combined["Secteur"] == evo_selected_sector]["Catégorie de cours"].dropna().unique().tolist())
                else:
                    evo_cat_options = [t("all")] + sorted(df_combined["Catégorie de cours"].dropna().unique().tolist())
                evo_selected_cat = st.selectbox(t("filter_by_category"), evo_cat_options, key="evo_cat_filter")

            # Apply filters
            df_evo = df_combined.copy()
            if evo_selected_sector != t("all"):
                df_evo = df_evo[df_evo["Secteur"] == evo_selected_sector]
            if evo_selected_ss != t("all"):
                df_evo = df_evo[df_evo["Sous-secteur"] == evo_selected_ss]
            if evo_selected_mc != t("all"):
                df_evo = df_evo[df_evo["Macro-catégorie"] == evo_selected_mc]
            if evo_selected_cat != t("all"):
                df_evo = df_evo[df_evo["Catégorie de cours"] == evo_selected_cat]

            # Show active filters
            active_filters = []
            if evo_selected_sector != t("all"):
                active_filters.append(f"Secteur: {evo_selected_sector}")
            if evo_selected_ss != t("all"):
                active_filters.append(f"Sous-secteur: {evo_selected_ss}")
            if evo_selected_mc != t("all"):
                active_filters.append(f"Macro-cat: {evo_selected_mc}")
            if evo_selected_cat != t("all"):
                active_filters.append(f"Catégorie: {evo_selected_cat}")
            if active_filters:
                st.info(f"Filtres actifs: {' | '.join(active_filters)}")

            # Define colors for indicators
            EVO_COLORS = {
                "Inscriptions": "#6366f1",  # Indigo
                "Heures": "#10b981",  # Green
                "Recettes": "#f59e0b"  # Orange
            }

            # Function to create evolution chart
            def create_evolution_chart(df_data, title, chart_key):
                # Group by year
                yearly_data = df_data.groupby("Année").agg({
                    inscr_col: "sum",
                    "Nombre d'heures prévues": "sum",
                    "Recettes": "sum"
                }).reset_index()
                yearly_data.columns = ["Année", "Inscriptions", "Heures", "Recettes"]
                yearly_data = yearly_data.sort_values("Année")

                # Create figure with secondary y-axis
                fig = make_subplots(specs=[[{"secondary_y": True}]])

                # Add traces
                fig.add_trace(
                    go.Scatter(x=yearly_data["Année"].astype(str), y=yearly_data["Inscriptions"], 
                              name="Inscriptions", mode="lines+markers+text",
                              line=dict(color=EVO_COLORS["Inscriptions"], width=3),
                              marker=dict(size=10),
                              text=yearly_data["Inscriptions"].apply(lambda x: f"{x:,.0f}"),
                              textposition="top center"),
                    secondary_y=False
                )

                fig.add_trace(
                    go.Scatter(x=yearly_data["Année"].astype(str), y=yearly_data["Heures"], 
                              name="Heures", mode="lines+markers+text",
                              line=dict(color=EVO_COLORS["Heures"], width=3),
                              marker=dict(size=10),
                              text=yearly_data["Heures"].apply(lambda x: f"{x:,.0f}"),
                              textposition="top center"),
                    secondary_y=False
                )

                fig.add_trace(
                    go.Scatter(x=yearly_data["Année"].astype(str), y=yearly_data["Recettes"], 
                              name="Recettes (€)", mode="lines+markers+text",
                              line=dict(color=EVO_COLORS["Recettes"], width=3, dash="dash"),
                              marker=dict(size=10),
                              text=yearly_data["Recettes"].apply(lambda x: f"€{x:,.0f}"),
                              textposition="top center"),
                    secondary_y=True
                )

                # Update layout
                fig.update_layout(
                    title=dict(text=title, font=dict(size=16)),
                    height=400,
                    paper_bgcolor=bg_color,
                    plot_bgcolor=bg_color,
                    font=dict(color=text_color),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
                    margin=dict(t=80, b=40, l=60, r=60),
                    hovermode="x unified"
                )

                fig.update_xaxes(title_text="Année", tickmode="linear")
                fig.update_yaxes(title_text="Inscriptions / Heures", secondary_y=False)
                fig.update_yaxes(title_text="Recettes (€)", secondary_y=True)

                st.plotly_chart(fig, use_container_width=True, key=chart_key)

            # LEVEL 1: IFI Total
            with st.expander(f"{t('evolution_ifi')}", expanded=True):
                create_evolution_chart(df_evo, t('evolution_ifi'), "evo_ifi_chart")

            # LEVEL 2: By Antenna
            with st.expander(f"{t('evolution_by_antenna')}", expanded=True):
                antenna_cols = st.columns(2)
                for idx, antenna in enumerate(ANTENNA_ORDER):
                    df_antenna = df_evo[df_evo["Sede"] == antenna]
                    if len(df_antenna) > 0:
                        with antenna_cols[idx % 2]:
                            create_evolution_chart(df_antenna, f"{antenna}", f"evo_{antenna}_chart")

    # TAB 5: PROFITABILITY (NEW!)
    with tab5:
        st.markdown(f"### {t('profitability')}")
        st.markdown(f"*{t('revenue_per_inscr')} = ARPI (Average Revenue Per Inscription)*")

        # Year selector for this tab
        tab5_years = sorted(df_combined["Année"].unique())
        if len(tab5_years) > 1:
            selected_year_tab5 = st.selectbox(
                t("filter_by_period"), 
                tab5_years, 
                index=len(tab5_years)-1,  # Default to most recent year
                key="profit_year_filter"
            )
            df_tab5 = df_combined[df_combined["Année"] == selected_year_tab5]
        else:
            df_tab5 = df_combined

        by_sector, by_sede, by_sector_sede = calculate_profitability(df_tab5)

        col1, col2 = st.columns(2)

        with col1:
            st.markdown(f"#### {t('profitability_by_sector')}")

            fig = px.bar(
                by_sector, x="ARPI", y="Secteur", orientation="h",
                color="ARPI", color_continuous_scale="Greens",
                text="ARPI"
            )
            fig.update_traces(texttemplate="€%{text:.2f}", textposition="outside")
            fig.update_layout(
                height=450, 
                paper_bgcolor=bg_color, 
                plot_bgcolor=bg_color, 
                font=dict(color=text_color),
                yaxis=dict(categoryorder="total ascending")
            )
            st.plotly_chart(fig, use_container_width=True)

            # Top 3 most profitable
            st.markdown(f"##### {t('most_profitable')}")
            for i, row in by_sector.head(3).iterrows():
                st.success(f"**{row['Secteur']}**: €{row['ARPI']:.2f}/inscription ({row[inscr_col]:,.0f} inscr.)")

        with col2:
            st.markdown(f"#### {t('profitability_by_sede')}")

            fig = px.bar(
                by_sede, x="Sede", y="ARPI",
                color="Sede", color_discrete_map=SEDE_COLORS,
                text="ARPI"
            )
            fig.update_traces(texttemplate="€%{text:.2f}", textposition="outside")
            fig.update_layout(
                height=400, 
                paper_bgcolor=bg_color, 
                plot_bgcolor=bg_color, 
                font=dict(color=text_color),
                showlegend=False
            )
            st.plotly_chart(fig, use_container_width=True)

            # Detailed table
            st.dataframe(
                by_sede[["Sede", inscr_col, "Recettes", "ARPI"]].rename(columns={
                    inscr_col: t("inscriptions"),
                    "Recettes": t("revenue"),
                    "ARPI": "€/inscr"
                }),
                hide_index=True,
                use_container_width=True
            )

        # Heatmap ARPI by Secteur x Sede
        st.markdown(f"#### Heatmap ARPI: Secteur × Sede")
        arpi_pivot = by_sector_sede.pivot(index="Secteur", columns="Sede", values="ARPI").fillna(0)
        fig = px.imshow(
            arpi_pivot, 
            labels=dict(x="Sede", y="Secteur", color="€/inscr"),
            aspect="auto", 
            color_continuous_scale="Greens",
            text_auto=".2f"
        )
        fig.update_layout(height=500, paper_bgcolor=bg_color, plot_bgcolor=bg_color, font=dict(color=text_color))
        st.plotly_chart(fig, use_container_width=True)

    # TAB 6: MAP (NEW!)
    with tab6:
        st.markdown(f"### {t('italy_map')}")

        # Year selector for this tab
        tab6_years = sorted(df_combined["Année"].unique())
        if len(tab6_years) > 1:
            selected_year_tab6 = st.selectbox(
                t("filter_by_period"), 
                tab6_years, 
                index=len(tab6_years)-1,  # Default to most recent year
                key="map_year_filter"
            )
            df_tab6_base = df_combined[df_combined["Année"] == selected_year_tab6]
        else:
            df_tab6_base = df_combined

        # Age group filter
        st.markdown(f"#### {t('filter_by_age')}")
        age_groups = ["Tous"] + sorted(df_tab6_base["Groupe_Age"].unique().tolist())
        selected_age = st.selectbox(t("age_groups"), age_groups, key="map_age_filter")

        if selected_age != "Tous":
            df_map = df_tab6_base[df_tab6_base["Groupe_Age"] == selected_age]
        else:
            df_map = df_tab6_base

        # Map
        fig_map = create_italy_map(df_map)
        st.plotly_chart(fig_map, use_container_width=True)

        # Age distribution pie chart
        st.markdown(f"#### {t('age_distribution')}")

        age_data = df_tab6_base.groupby("Groupe_Age")[inscr_col].sum().reset_index()
        age_colors = {"Adultes": "#6366f1", "Ados": "#f59e0b", "Enfants": "#10b981"}

        col1, col2 = st.columns([1, 2])

        with col1:
            fig = px.pie(
                age_data, values=inscr_col, names="Groupe_Age",
                color="Groupe_Age", color_discrete_map=age_colors,
                hole=0.4
            )
            fig.update_traces(textposition='inside', textinfo='percent+label+value')
            fig.update_layout(
                height=300, 
                paper_bgcolor=bg_color, 
                font=dict(color=text_color),
                showlegend=True
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            # Age by sede
            age_sede = df_tab6_base.groupby(["Sede", "Groupe_Age"])[inscr_col].sum().reset_index()
            fig = px.bar(
                age_sede, x="Sede", y=inscr_col, color="Groupe_Age",
                color_discrete_map=age_colors,
                barmode="stack",
                title=f"{t('age_distribution')} {t('by_sede')}",
                text=inscr_col
            )
            fig.update_traces(texttemplate='%{text:,.0f}', textposition='inside')
            fig.update_layout(
                height=300, 
                paper_bgcolor=bg_color, 
                plot_bgcolor=bg_color,
                font=dict(color=text_color)
            )
            st.plotly_chart(fig, use_container_width=True)

    # TAB 7: COMPARAISONS (was TAB 4)
    with tab7:
        st.markdown(f"### {t('comparison_mode')}")
        comparison_type = st.radio(t("comparison_type"), [t("sede_vs_sede"), t("semester_vs_semester"), t("sector_vs_sector")], horizontal=True)

        if comparison_type == t("sede_vs_sede"):
            sedi = df_combined["Sede"].unique().tolist()
            col1, col2 = st.columns(2)
            with col1:
                sede1 = st.selectbox(t("first_sede"), sedi, key="cmp_sede1")
            with col2:
                sede2 = st.selectbox(t("second_sede"), [s for s in sedi if s != sede1], key="cmp_sede2")
            df1 = df_combined[df_combined["Sede"] == sede1]
            df2 = df_combined[df_combined["Sede"] == sede2]
            inscr1, inscr2 = df1[inscr_col].sum(), df2[inscr_col].sum()
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"#### {sede1}")
                st.metric(t("inscriptions"), f"{inscr1:,.0f}")
                st.metric(t("courses"), f"{df1['Nb. de Cours'].sum():,.0f}")
                st.metric(t("revenue"), f"€{df1['Recettes'].sum():,.0f}")
            with col2:
                diff = ((inscr2 - inscr1) / inscr1 * 100) if inscr1 > 0 else 0
                st.markdown(f"#### {sede2}")
                st.metric(t("inscriptions"), f"{inscr2:,.0f}", f"{diff:+.1f}%")
                st.metric(t("courses"), f"{df2['Nb. de Cours'].sum():,.0f}")
                st.metric(t("revenue"), f"€{df2['Recettes'].sum():,.0f}")
            compare_df = pd.DataFrame({"Sede": [sede1, sede1, sede2, sede2], "Métrique": [t("inscriptions"), t("courses")] * 2, "Valeur": [inscr1, df1["Nb. de Cours"].sum(), inscr2, df2["Nb. de Cours"].sum()]})
            fig = px.bar(compare_df, x="Métrique", y="Valeur", color="Sede", barmode="group", color_discrete_map=SEDE_COLORS, text="Valeur")
            fig.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
            fig.update_layout(paper_bgcolor=bg_color, plot_bgcolor=bg_color, font=dict(color=text_color), height=400)
            st.plotly_chart(fig, use_container_width=True)
        elif comparison_type == t("semester_vs_semester"):
            semesters = df_combined["Semestre"].unique()
            if len(semesters) >= 2:
                sem1_data = df_combined[df_combined["Semestre"] == "sem1"]
                sem2_data = df_combined[df_combined["Semestre"] == "sem2"]
                s1_total, s2_total = sem1_data[inscr_col].sum(), sem2_data[inscr_col].sum()
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"#### {t('semester1')} (jan-juil)")
                    st.metric(t("inscriptions"), f"{s1_total:,.0f}")
                with col2:
                    diff = ((s2_total - s1_total) / s1_total * 100) if s1_total > 0 else 0
                    st.markdown(f"#### {t('semester2')} (sept-déc)")
                    st.metric(t("inscriptions"), f"{s2_total:,.0f}", f"{diff:+.1f}%")
                sem_sede = df_combined.groupby(["Semestre", "Sede"])[inscr_col].sum().reset_index()
                fig = px.bar(sem_sede, x="Sede", y=inscr_col, color="Semestre", barmode="group", title=t("comparison_by_sede"), text=inscr_col)
                fig.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
                fig.update_layout(paper_bgcolor=bg_color, plot_bgcolor=bg_color, font=dict(color=text_color), height=400)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info(t("load_both_semesters"))
        else:
            secteurs = df_combined["Secteur"].unique().tolist()
            col1, col2 = st.columns(2)
            with col1:
                sector1 = st.selectbox(t("first_sector"), secteurs, key="cmp_sector1")
            with col2:
                sector2 = st.selectbox(t("second_sector"), [s for s in secteurs if s != sector1], key="cmp_sector2")
            df_s1, df_s2 = df_combined[df_combined["Secteur"] == sector1], df_combined[df_combined["Secteur"] == sector2]
            compare_data = pd.DataFrame({"Secteur": [sector1, sector2], t("inscriptions"): [df_s1[inscr_col].sum(), df_s2[inscr_col].sum()], t("courses"): [df_s1["Nb. de Cours"].sum(), df_s2["Nb. de Cours"].sum()]})
            st.dataframe(compare_data, hide_index=True, use_container_width=True)

    # TAB 8: GRAPHIQUES - With fullscreen navigation (was TAB 5)
    with tab8:
        st.markdown(f"### {t('graphs')}")

        # Year selector for this tab
        tab8_years = sorted(df_combined["Année"].unique())
        if len(tab8_years) > 1:
            selected_year_tab8 = st.selectbox(
                t("filter_by_period"), 
                tab8_years, 
                index=len(tab8_years)-1,  # Default to most recent year
                key="graphs_year_filter"
            )
            df_tab8 = df_combined[df_combined["Année"] == selected_year_tab8]
        else:
            df_tab8 = df_combined

        # Graph list for navigation
        graph_titles = [
            t("flow_sede_sector"),
            t("inscr_by_sector_sede"),
            t("treemap_title"),
            t("sunburst_title"),
            f"{t('by_sede')} + Top 6 secteurs"
        ]

        # Navigation buttons
        col_prev, col_counter, col_next = st.columns([1, 2, 1])
        with col_prev:
            if st.button(t("prev_graph"), key="prev_btn", use_container_width=True):
                st.session_state.graph_index = (st.session_state.graph_index - 1) % len(graph_titles)
        with col_counter:
            st.markdown(f'<div class="graph-counter">{t("graph_counter")} {st.session_state.graph_index + 1} {t("of")} {len(graph_titles)}: {graph_titles[st.session_state.graph_index]}</div>', unsafe_allow_html=True)
        with col_next:
            if st.button(t("next_graph"), key="next_btn", use_container_width=True):
                st.session_state.graph_index = (st.session_state.graph_index + 1) % len(graph_titles)

        st.markdown("---")

        # Display current graph (larger)
        current_graph = st.session_state.graph_index

        if current_graph == 0:
            # Sankey
            fig_sankey = create_sankey_diagram(df_tab8)
            fig_sankey.update_layout(height=700)
            st.plotly_chart(fig_sankey, use_container_width=True)
        elif current_graph == 1:
            # Bar chart by sector and sede
            sector_sede_data = df_tab8.groupby(["Sede", "Secteur"])[inscr_col].sum().reset_index()
            fig = px.bar(sector_sede_data, x="Secteur", y=inscr_col, color="Sede",
                        barmode="group", color_discrete_map=SEDE_COLORS, title=t("inscr_by_sector_sede"),
                        text=inscr_col)
            fig.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
            fig.update_layout(height=650, xaxis_tickangle=-45, paper_bgcolor=bg_color, plot_bgcolor=bg_color, font=dict(color=text_color, size=14))
            st.plotly_chart(fig, use_container_width=True)
        elif current_graph == 2:
            # Treemap
            fig = px.treemap(df_tab8.groupby(["Sede", "Secteur"])[inscr_col].sum().reset_index(), path=["Sede", "Secteur"],
                            values=inscr_col, color="Sede", color_discrete_map=SEDE_COLORS, title=t("treemap_title"))
            fig.update_layout(height=650, paper_bgcolor=bg_color, plot_bgcolor=bg_color, font=dict(color=text_color, size=14))
            st.plotly_chart(fig, use_container_width=True)
        elif current_graph == 3:
            # Sunburst
            fig = px.sunburst(df_tab8.groupby(["Sede", "Secteur"])[inscr_col].sum().reset_index(), path=["Sede", "Secteur"],
                             values=inscr_col, color="Sede", color_discrete_map=SEDE_COLORS, title=t("sunburst_title"))
            fig.update_layout(height=650, paper_bgcolor=bg_color, plot_bgcolor=bg_color, font=dict(color=text_color, size=14))
            st.plotly_chart(fig, use_container_width=True)
        elif current_graph == 4:
            # Double pie
            fig = make_subplots(rows=1, cols=2, specs=[[{"type": "pie"}, {"type": "pie"}]], subplot_titles=[t("by_sede"), "Top 6 secteurs"])
            sede_data = df_tab8.groupby("Sede")[inscr_col].sum().reset_index()
            fig.add_trace(go.Pie(labels=sede_data["Sede"], values=sede_data[inscr_col], marker_colors=[SEDE_COLORS.get(s, "#888") for s in sede_data["Sede"]]), row=1, col=1)
            sector_data = df_tab8.groupby("Secteur")[inscr_col].sum().nlargest(6).reset_index()
            fig.add_trace(go.Pie(labels=sector_data["Secteur"], values=sector_data[inscr_col]), row=1, col=2)
            fig.update_layout(height=600, paper_bgcolor=bg_color, plot_bgcolor=bg_color, font=dict(color=text_color, size=14))
            st.plotly_chart(fig, use_container_width=True)

        # Quick navigation thumbnails
        st.markdown("---")
        st.markdown(f"#### {t('graph_navigation')}")
        cols = st.columns(5)
        for i, title in enumerate(graph_titles):
            with cols[i]:
                label = f"{'→ ' if i == current_graph else ''}{i+1}. {title[:15]}..."
                if st.button(label, key=f"nav_{i}", use_container_width=True):
                    st.session_state.graph_index = i

    # TAB 9: AI ASSISTANT (was TAB 6)
    with tab9:
        st.markdown(f"### {t('ai_assistant')}")
        assistant = DataAssistant(df_combined)
        st.markdown(f"#### {t('auto_insights')}")
        for insight in assistant.get_insights():
            st.markdown(f'<div class="insight-card">{insight}</div>', unsafe_allow_html=True)
        st.markdown("---")
        st.markdown(f"#### {t('ask_question')}")
        question = st.text_input(t('ask_question'), placeholder=t('question_placeholder'), key="ai_question", label_visibility="collapsed")
        if question:
            answer = assistant.answer(question)
            st.markdown(f'<div class="ai-box">{answer}</div>', unsafe_allow_html=True)
        st.markdown(f"#### {t('suggestions')}")
        suggestions = [t("q_total_inscr"), t("q_revenue"), t("q_best_sede"), t("q_compare"), t("q_about")]
        cols = st.columns(3)
        for i, sugg in enumerate(suggestions):
            with cols[i % 3]:
                if st.button(sugg, key=f"sugg_{i}"):
                    answer = assistant.answer(sugg)
                    st.markdown(f'<div class="ai-box">{answer}</div>', unsafe_allow_html=True)

    # TAB 10: EXPORT (was TAB 7)
    with tab10:
        st.markdown(f"### {t('export_data')}")
        export_format = st.radio(t("format"), [t("excel_multi"), "CSV"], horizontal=True)
        if export_format == t("excel_multi"):
            sheets = {
                "Données_Complètes": df_combined, "Prova_Stats": create_prova_stats_format(df_combined),
                "Par_Sede": df_combined.groupby("Sede").agg({inscr_col: "sum", "Nb. de Cours": "sum", "Recettes": "sum"}).reset_index(),
                "Par_Secteur": df_combined.groupby("Secteur").agg({inscr_col: "sum", "Nb. de Cours": "sum", "Recettes": "sum"}).reset_index(),
                "IFI_Totals": create_ifi_totals(df_combined),
                "Profitabilite": calculate_profitability(df_combined)[0]  # Add profitability to export
            }
            excel_data = export_to_excel(sheets)
            st.download_button(t('download_excel'), data=excel_data, file_name=f"IFI_Stats_AEC_{default_year}.xlsx",
                              mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        else:
            csv_data = df_combined.to_csv(index=False)
            st.download_button(t('download_csv'), data=csv_data, file_name=f"IFI_Stats_AEC_{default_year}.csv", mime="text/csv")
        st.markdown("---")
        st.markdown(f"### {t('dataset_summary')}")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(t("files_loaded"), len(file_info))
        with col2:
            st.metric(t("total_rows"), len(df_combined))
        with col3:
            st.metric(t("periods"), df_combined["Période"].nunique())

    # TAB 11: CONFIGURATION
    with tab11:
        st.markdown(f"### {t('tab_config')}")

        # Category mapping table with all 4 levels
        with st.expander(f"{t('category_mapping_title')}", expanded=True):
            # Build mapping table with all 4 levels
            mapping_data = []
            for cat, levels in sorted(CATEGORY_MAPPING.items(), key=lambda x: (x[1][2], x[1][1], x[1][0], x[0])):
                mapping_data.append({
                    "Catégorie": cat, 
                    "Macro-catégorie": levels[0] if levels[0] else "MANQUANT", 
                    "Sous-secteur": levels[1] if levels[1] else "MANQUANT", 
                    "Secteur": levels[2] if levels[2] else "MANQUANT"
                })
            mapping_df = pd.DataFrame(mapping_data)

            # Use st.data_editor for editable table
            st.markdown("*Double-cliquez sur une cellule pour modifier*")
            edited_df = st.data_editor(
                mapping_df, 
                hide_index=True, 
                use_container_width=True, 
                height=500,
                column_config={
                    "Catégorie": st.column_config.TextColumn("Catégorie", disabled=True),
                    "Macro-catégorie": st.column_config.SelectboxColumn(
                        "Macro-catégorie",
                        options=sorted(list(set([levels[0] for levels in CATEGORY_MAPPING.values()]))),
                        required=True
                    ),
                    "Sous-secteur": st.column_config.SelectboxColumn(
                        "Sous-secteur",
                        options=sorted(list(set([levels[1] for levels in CATEGORY_MAPPING.values()]))),
                        required=True
                    ),
                    "Secteur": st.column_config.SelectboxColumn(
                        "Secteur",
                        options=SECTOR_ORDER,
                        required=True
                    ),
                },
                key="mapping_editor"
            )

            # Button to save edits from the main mapping table
            if st.button("Sauvegarder les modifications", type="primary", key="save_main_mappings"):
                try:
                    # Find rows that have been modified (compare with original CATEGORY_MAPPING)
                    modified_mappings = []
                    for idx, row in edited_df.iterrows():
                        cat = row["Catégorie"]
                        new_macro = row["Macro-catégorie"] if row["Macro-catégorie"] != "MANQUANT" else ""
                        new_ss = row["Sous-secteur"] if row["Sous-secteur"] != "MANQUANT" else ""
                        new_sect = row["Secteur"] if row["Secteur"] != "MANQUANT" else ""

                        # Get original values
                        original = CATEGORY_MAPPING.get(cat, ("", "", ""))
                        orig_macro, orig_ss, orig_sect = original

                        # Check if modified
                        if (new_macro != orig_macro) or (new_ss != orig_ss) or (new_sect != orig_sect):
                            modified_mappings.append({
                                "Catégorie": cat,
                                "Macro-catégorie": new_macro,
                                "Sous-secteur": new_ss,
                                "Secteur": new_sect
                            })

                    if modified_mappings:
                        # Use configurable CSV path
                        csv_path = get_csv_mapping_path()
                        csv_dir = os.path.dirname(csv_path)

                        # Create directory if it doesn't exist
                        if csv_dir:
                            os.makedirs(csv_dir, exist_ok=True)

                        # Check if file exists
                        if os.path.exists(csv_path):
                            existing_df = pd.read_csv(csv_path)
                        else:
                            existing_df = pd.DataFrame(columns=["Catégorie", "Macro-catégorie", "Sous-secteur", "Secteur"])

                        # Add modified mappings
                        new_df = pd.DataFrame(modified_mappings)
                        combined_df = pd.concat([existing_df, new_df], ignore_index=True)

                        # Remove duplicates (keep last = keep new mappings)
                        combined_df = combined_df.drop_duplicates(subset=["Catégorie"], keep="last")

                        # Sort by Secteur, Sous-secteur, Macro-catégorie, Catégorie
                        combined_df = combined_df.sort_values(["Secteur", "Sous-secteur", "Macro-catégorie", "Catégorie"])

                        # Save to CSV
                        combined_df.to_csv(csv_path, index=False)

                        # Update in-memory CATEGORY_MAPPING
                        for mapping in modified_mappings:
                            CATEGORY_MAPPING[mapping["Catégorie"]] = (
                                mapping["Macro-catégorie"],
                                mapping["Sous-secteur"],
                                mapping["Secteur"]
                            )

                        st.success(f"{len(modified_mappings)} correspondance(s) modifiée(s) sauvegardée(s) !")
                        st.balloons()
                        st.rerun()
                    else:
                        st.info("Aucune modification détectée dans le tableau.")

                except Exception as e:
                    st.error(f"Erreur lors de la sauvegarde : {str(e)}")

        # Show unlinked categories warning if any exist
        unlinked_cats = get_unknown_categories()
        if unlinked_cats:
            with st.expander(f"{t('unlinked_categories')} ({len(unlinked_cats)})", expanded=True):
                st.error(t('unlinked_cat_warning'))
                st.markdown("### Catégories détectées dans l'import mais absentes du tableau de correspondances :")
                st.markdown("*Ces catégories sont classées comme 'NON RATTACHÉ' dans les analyses.*")

                # Get unique macro-categories for dropdown
                macro_cat_options = ["-- Sélectionner --"] + sorted(list(set([levels[0] for levels in CATEGORY_MAPPING.values()]))) + ["[Créer nouvelle macro-catégorie]"]
                sous_secteur_options = ["-- Sélectionner --"] + sorted(list(set([levels[1] for levels in CATEGORY_MAPPING.values()])))
                secteur_options = ["-- Sélectionner --"] + SECTOR_ORDER

                # Header row
                col_h1, col_h2, col_h3, col_h4, col_h5 = st.columns([2.5, 2, 2, 1.5, 2])
                with col_h1:
                    st.markdown("**Catégorie (AEC)**")
                with col_h2:
                    st.markdown("**→ Macro-catégorie**")
                with col_h3:
                    st.markdown("**→ Sous-secteur**")
                with col_h4:
                    st.markdown("**→ Secteur**")
                with col_h5:
                    st.markdown("**Détail**")

                st.markdown("---")

                for cat, detail in sorted(unlinked_cats.items()):
                    col1, col2, col3, col4, col5 = st.columns([2.5, 2, 2, 1.5, 2])
                    with col1:
                        st.markdown(f"**{cat}**")
                    with col2:
                        st.selectbox(
                            "Macro", 
                            macro_cat_options, 
                            key=f"fix_macro_{cat}", 
                            label_visibility="collapsed"
                        )
                    with col3:
                        st.selectbox(
                            "Sous-secteur", 
                            sous_secteur_options, 
                            key=f"fix_ss_{cat}", 
                            label_visibility="collapsed"
                        )
                    with col4:
                        st.selectbox(
                            "Secteur", 
                            secteur_options, 
                            key=f"fix_sect_{cat}", 
                            label_visibility="collapsed"
                        )
                    with col5:
                        st.caption(detail)

                st.markdown("---")

                # Button to save new mappings
                if st.button("Sauvegarder les correspondances", type="primary", key="save_unlinked_mappings"):
                    # Collect all selected mappings (even partial ones)
                    new_mappings = []
                    partial_mappings = []
                    errors = []

                    for cat in sorted(unlinked_cats.keys()):
                        macro = st.session_state.get(f"fix_macro_{cat}", "-- Sélectionner --")
                        ss = st.session_state.get(f"fix_ss_{cat}", "-- Sélectionner --")
                        sect = st.session_state.get(f"fix_sect_{cat}", "-- Sélectionner --")

                        # Check if at least one field is filled
                        has_macro = macro != "-- Sélectionner --" and macro != "[Créer nouvelle macro-catégorie]"
                        has_ss = ss != "-- Sélectionner --"
                        has_sect = sect != "-- Sélectionner --"

                        if has_macro and has_ss and has_sect:
                            # Complete mapping
                            new_mappings.append({
                                "Catégorie": cat,
                                "Macro-catégorie": macro,
                                "Sous-secteur": ss,
                                "Secteur": sect
                            })
                        elif has_macro or has_ss or has_sect:
                            # Partial mapping - save with empty values
                            partial_mappings.append({
                                "Catégorie": cat,
                                "Macro-catégorie": macro if has_macro else "",
                                "Sous-secteur": ss if has_ss else "",
                                "Secteur": sect if has_sect else ""
                            })

                    all_mappings = new_mappings + partial_mappings

                    if all_mappings:
                        try:
                            # Use configurable CSV path
                            csv_path = get_csv_mapping_path()
                            csv_dir = os.path.dirname(csv_path)

                            # Create directory if it doesn't exist
                            if csv_dir:
                                os.makedirs(csv_dir, exist_ok=True)

                            # Check if file exists
                            if os.path.exists(csv_path):
                                existing_df = pd.read_csv(csv_path)
                            else:
                                # Create new file with headers
                                existing_df = pd.DataFrame(columns=["Catégorie", "Macro-catégorie", "Sous-secteur", "Secteur"])

                            # Add new mappings (complete + partial)
                            new_df = pd.DataFrame(all_mappings)
                            combined_df = pd.concat([existing_df, new_df], ignore_index=True)

                            # Remove duplicates (keep last = keep new mappings)
                            combined_df = combined_df.drop_duplicates(subset=["Catégorie"], keep="last")

                            # Sort by Secteur, Sous-secteur, Macro-catégorie, Catégorie
                            combined_df = combined_df.sort_values(["Secteur", "Sous-secteur", "Macro-catégorie", "Catégorie"])

                            # Save to CSV
                            combined_df.to_csv(csv_path, index=False)

                            # Also update the in-memory CATEGORY_MAPPING
                            for mapping in new_mappings:
                                CATEGORY_MAPPING[mapping["Catégorie"]] = (
                                    mapping["Macro-catégorie"],
                                    mapping["Sous-secteur"],
                                    mapping["Secteur"]
                                )

                            # Clear unknown categories from session state (only complete ones)
                            if "unknown_categories" in st.session_state:
                                for mapping in new_mappings:
                                    if mapping["Catégorie"] in st.session_state.unknown_categories:
                                        del st.session_state.unknown_categories[mapping["Catégorie"]]

                            # Show success message
                            if new_mappings:
                                st.success(f"{len(new_mappings)} correspondance(s) complète(s) sauvegardée(s) !")
                            if partial_mappings:
                                st.info(f"{len(partial_mappings)} correspondance(s) partielle(s) sauvegardée(s) (à compléter plus tard)")

                            st.balloons()

                            # Rerun to refresh the page dynamically
                            st.rerun()

                        except Exception as e:
                            st.error(f"Erreur lors de la sauvegarde : {str(e)}")
                    else:
                        st.warning("Aucun champ rempli. Sélectionnez au moins une valeur pour une catégorie.")

                    if errors:
                        for err in errors:
                            st.warning(err)
        else:
            st.success("Toutes les catégories sont reconnues dans le tableau de correspondances.")


# Render other export tabs
if _has_other_exports:
    if df_profils is not None:
        with _top_tabs[_top_labels.index("Profils")]:
            render_profils_tabs(st.session_state.profils_clients_data)
    if df_fiches is not None:
        with _top_tabs[_top_labels.index("Fiches de cours")]:
            render_fiches_tabs(st.session_state.course_fiches_data)
    if df_produits is not None:
        with _top_tabs[_top_labels.index("Produits")]:
            render_produits_tabs(st.session_state.produits_data)

# =====================================================
# FOOTER
# =====================================================
st.markdown("---")
st.caption("O.S.C.A.R. v3.0 • Institut français Italia")
