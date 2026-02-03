"""
🎓 Institut français Italia - Dashboard Statistiques AEC v3.0
================================================================
Dashboard interactif pour l'analyse des données AEC
- 8+ fichiers: 4 sedi × 2 semestres (multi-années supporté)
- Auto-détection sede + semestre depuis le nom du fichier
- Vue globale IFI + détails par sede
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
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from io import BytesIO
import zipfile
import re

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
    os.path.join(os.path.dirname(__file__), "2. FEUILLE DE TRAVAIL", "category_mapping.csv")
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
        "preloaded_files": "📦 Données disponibles", "load_year": "Charger l'année", "or_upload_files": "Ou importez vos propres fichiers",
        "drag_files": "Glissez vos fichiers Excel", "files_detected": "Fichiers détectés",
        "expected_structure": "Structure attendue", "you_must_load": "Vous devez charger",
        "files": "fichiers", "sede": "Sede", "semester1": "Semestre 1", "semester2": "Semestre 2",
        "recommended_format": "Format de nom recommandé",
        "load_files_sidebar": "Chargez vos fichiers AEC dans la barre latérale pour commencer l'analyse.",
        "overview": "Vue d'ensemble", "inscriptions": "Inscriptions", "courses": "Cours",
        "student_hours": "Heures-élèves", "planned_hours": "Heures prévues", "revenue": "Recettes", "students_per_course": "Élèves/cours",
        "tab_prova_stats": "Synthèse", "tab_by_sede": "Par antenne",
        "tab_by_sector": "Par secteurs", "tab_by_sous_secteur": "Par sous-secteurs", "tab_by_macro_category": "Par macro-catégories", "tab_by_category": "Par catégories", "tab_comparisons": "Comparaisons",
        "tab_graphs": "Graphiques", "tab_ai": "Assistant IA", "tab_export": "Export", "tab_config": "Configuration",
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
        "sunburst_title": "Vue en rayons de soleil", "ai_assistant": "Assistant IA",
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
        "graph_navigation": "Navigation graphiques", "prev_graph": "◀ Précédent", "next_graph": "Suivant ▶",
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
        "tab_profitability": "Rentabilité", "tab_map": "Carte",
        "increase": "hausse", "decrease": "baisse", "stable": "stable",
        "multi_year_evolution": "Évolution pluriannuelle", "need_multiple_years": "Chargez les données de plusieurs années pour voir l'évolution.",
        "arpi": "ARPI (€/inscr)", "total_years": "Années", "load_more_years": "Chargez plus d'années pour comparer",
        "default_year_help": "Utilisé si l'année n'est pas détectable dans le nom de fichier",
        "total_all_years": "TOTAL (toutes années)", "breakdown_by_year": "Répartition par année",
        "multi_year_warning": "⚠️ Plusieurs années chargées", "showing_combined": "Données combinées de",
        "welcome": "Bienvenue", "welcome_subtitle": "Analysez les statistiques de cours de français pour les 4 Instituts Français d'Italie",
        "quick_start": "Démarrage rapide", "upload_here": "Déposez vos fichiers Excel ici",
        "features": "Fonctionnalités", "feature_1": "Vue globale IFI et par antenne",
        "feature_2": "Comparaison année vs année", "feature_3": "Analyse de rentabilité (ARPI)",
        "feature_4": "Carte d'Italie interactive", "feature_5": "Export Excel multi-feuilles",
        "feature_6": "Graphiques interactifs", "how_to_export": "Comment exporter depuis AEC ?",
        "export_steps": "1. Connectez-vous à AEC\n2. Allez dans Statistiques > Inscriptions\n3. Exportez en Excel pour chaque antenne/semestre",
        "need_help": "Besoin d'aide ?", "contact_support": "Contactez le support",
        "filter_years": "Sélectionner les années", "showing_years": "Années affichées",
        "showing_all_years": "Toutes les années",
        "view_mode": "Vue", "by_sede": "Par antenne", "year": "Année",
        "calculation_details": "Détails des calculs",
        "pct_new": "% nouveaux", "pct_returning": "% réinscrits",
        "choose_indicator": "Choisissez un indicateur", "global_view": "Vue globale",
        "new_students": "Nouveaux inscrits", "returning_students": "Réinscrits",
        "ifi_total": "IFI Total",
    },
    "it": {
        "title": "Institut français Italia",
        "subtitle": "Dashboard statistiche AEC - Analisi dei corsi di francese",
        "mode": "Tema", "language": "Lingua", "default_year": "Anno predefinito",
        "load_files": "Caricare gli 8 file AEC", "sedi_semesters": "4 sedi × 2 semestri",
        "preloaded_files": "📦 Dati disponibili", "load_year": "Carica l'anno", "or_upload_files": "Oppure importa i tuoi file",
        "drag_files": "Trascina i tuoi file Excel", "files_detected": "File rilevati",
        "expected_structure": "Struttura prevista", "you_must_load": "Devi caricare",
        "files": "file", "sede": "Sede", "semester1": "Semestre 1", "semester2": "Semestre 2",
        "recommended_format": "Formato nome consigliato",
        "load_files_sidebar": "Carica i tuoi file AEC nella barra laterale per iniziare l'analisi.",
        "overview": "Panoramica", "inscriptions": "Iscrizioni", "courses": "Corsi",
        "student_hours": "Ore-studenti", "planned_hours": "Ore previste", "revenue": "Ricavi", "students_per_course": "Alunni/corso",
        "tab_prova_stats": "Sintesi", "tab_by_sede": "Per sede",
        "tab_by_sector": "Per settori", "tab_by_sous_secteur": "Per sotto-settori", "tab_by_macro_category": "Per macro-categorie", "tab_by_category": "Per categorie", "tab_comparisons": "Confronti",
        "tab_graphs": "Grafici", "tab_ai": "Assistente IA", "tab_export": "Esporta", "tab_config": "Configurazione",
        "filter_by_sede": "Filtra per sede", "filter_by_sector": "Filtra per settore", "filter_by_period": "Filtra per periodo",
        "all": "Tutti", "ifi_totals": "Totali IFI (tutte le sedi)",
        "analysis_by_sede": "Analisi per sede", "inscriptions_by_sede": "Iscrizioni per sede",
        "distribution": "Distribuzione delle iscrizioni", "detail_by_sede": "Dettaglio per sede",
        "analysis_by_sector": "Analisi per settori", "inscriptions_by_sector": "Iscrizioni per settore", "ifi_all_antennas": "IFI - totale tutte le sedi", "details_by_antenna": "Dettagli per sede",
        "analysis_by_sous_secteur": "Analisi per sotto-settori", "inscriptions_by_sous_secteur": "Iscrizioni per sotto-settore",
        "analysis_by_macro_category": "Analisi per macro-categorie", "inscriptions_by_macro_category": "Iscrizioni per macro-categoria",
        "courses_by_sector": "N. corsi per settore",
        "analysis_by_category": "Analisi per categorie", "inscriptions_by_category": "Iscrizioni per categoria",
        "courses_by_category": "N. corsi per categoria", "top_categories": "Top categorie",
        "heatmap_title": "Heatmap", "heatmap_subtitle": "Categorie per settore (per sede)", "comparison_mode": "Modalità confronti",
        "category_mapping_title": "Corrispondenze categorie → settori", "show_mapping": "Mostra tabella corrispondenze",
        "unlinked_categories": "Categorie non collegate", "unlinked_cat_warning": "Le seguenti categorie non sono collegate nella tabella di corrispondenza",
        "assign_macro_category": "Assegna una macro-categoria", "create_new_macro_category": "Crea una nuova macro-categoria",
        "filter_by_category": "Filtra per categoria", "category_view": "Vista per categoria",
        "filter_by_sous_secteur": "Filtra per sotto-settore", "filter_by_macro_category": "Filtra per macro-categoria",
        "multi_selection": "Selezione multipla", "comparison_by_antenna": "Confronto per sede",
        "comparison_type": "Tipo di confronto", "sede_vs_sede": "Sede vs sede",
        "semester_vs_semester": "Semestre vs semestre", "sector_vs_sector": "Settore vs settore",
        "first_sede": "Prima sede", "second_sede": "Seconda sede",
        "first_sector": "Primo settore", "second_sector": "Secondo settore",
        "comparison_by_sede": "Confronto per sede",
        "load_both_semesters": "Carica i dati di entrambi i semestri per confrontare.",
        "graphs": "Grafici", "flow_sede_sector": "Flusso: sede → settore",
        "inscr_by_sector_sede": "Iscrizioni per settore e sede", "treemap_title": "Ripartizione gerarchica",
        "sunburst_title": "Vista a raggiera", "ai_assistant": "Assistente IA",
        "auto_insights": "Analisi automatiche", "ask_question": "Fai una domanda",
        "question_placeholder": "Es: Qual è la sede migliore? Confronta IFM e IFF...",
        "suggestions": "Suggerimenti", "export_data": "Esporta i dati", "format": "Formato",
        "excel_multi": "Excel (multi-fogli)", "download_excel": "Scarica Excel",
        "download_csv": "Scarica CSV", "dataset_summary": "Riepilogo del dataset",
        "files_loaded": "File caricati", "total_rows": "Righe totali", "periods": "Periodi",
        "footer_mode": "Tema", "night": "scuro", "day": "chiaro",
        "dominates_with": "domina con il", "of_inscriptions": "delle iscrizioni",
        "avg_revenue_per_inscr": "Ricavo medio per iscrizione",
        "sem1_beats_sem2": "Il semestre 1 supera il S2 del",
        "sem2_beats_sem1": "Il semestre 2 supera il S1 del",
        "dominant_sector": "Settore dominante", "total_inscriptions": "Totale iscrizioni",
        "by_sede": "Per sede", "total_revenue": "Ricavi totali", "best_sede": "Sede migliore",
        "possible_questions": "Domande possibili", "q_total_inscr": "Quante iscrizioni in totale?",
        "q_revenue": "Quali sono i ricavi?", "q_best_sede": "Qual è la sede migliore?",
        "q_compare": "Confronta IFM e IFF", "q_about": "Parlami di IFN",
        "graph_navigation": "Navigazione grafici", "prev_graph": "◀ Precedente", "next_graph": "Successivo ▶",
        "graph_counter": "Grafico", "of": "di",
        # New translations for v2.8 features
        "year_comparison": "Confronto annuale", "yoy_variation": "Variazione A/A",
        "year_vs_year": "Anno vs anno", "first_year": "Primo anno", "second_year": "Secondo anno",
        "variation": "Variazione", "evolution": "Evoluzione", "profitability": "Redditività",
        "revenue_per_inscr": "€/iscrizione", "most_profitable": "Più redditizi",
        "least_profitable": "Meno redditizi", "profitability_by_sector": "Redditività per settore",
        "profitability_by_sede": "Redditività per sede", "age_groups": "Fasce d'età",
        "filter_by_age": "Filtra per età", "adults": "Adulti", "teens": "Ado", "children": "Bambini",
        "age_distribution": "Distribuzione per età", "italy_map": "Mappa d'Italia",
        "map_by_inscriptions": "Iscrizioni per città", "tab_yoy": "Per anno",
        "tab_profitability": "Redditività", "tab_map": "Mappa",
        "increase": "aumento", "decrease": "calo", "stable": "stabile",
        "multi_year_evolution": "Evoluzione pluriennale", "need_multiple_years": "Carica i dati di più anni per vedere l'evoluzione.",
        "arpi": "ARPI (€/iscr)", "total_years": "Anni", "load_more_years": "Carica più anni per confrontare",
        "default_year_help": "Usato se l'anno non è rilevabile dal nome del file",
        "total_all_years": "TOTALE (tutti gli anni)", "breakdown_by_year": "Ripartizione per anno",
        "multi_year_warning": "⚠️ Più anni caricati", "showing_combined": "Dati combinati di",
        "welcome": "Benvenuto", "welcome_subtitle": "Analizza le statistiche dei corsi di francese per i 4 Istituti Francesi d'Italia",
        "quick_start": "Avvio rapido", "upload_here": "Trascina qui i tuoi file Excel",
        "features": "Funzionalità", "feature_1": "Vista globale IFI e per sede",
        "feature_2": "Confronto anno vs anno", "feature_3": "Analisi di redditività (ARPI)",
        "feature_4": "Mappa d'Italia interattiva", "feature_5": "Export Excel multi-foglio",
        "feature_6": "Grafici interattivi", "how_to_export": "Come esportare da AEC?",
        "export_steps": "1. Accedi a AEC\n2. Vai in Statistiche > Iscrizioni\n3. Esporta in Excel per ogni sede/semestre",
        "need_help": "Hai bisogno di aiuto?", "contact_support": "Contatta il supporto",
        "filter_years": "Seleziona gli anni", "showing_years": "Anni visualizzati",
        "showing_all_years": "Tutti gli anni",
        "view_mode": "Vista", "by_sede": "Per sede", "year": "Anno",
        "calculation_details": "Dettagli dei calcoli",
        "pct_new": "% nuovi", "pct_returning": "% reiscritti",
        "choose_indicator": "Scegli un indicatore", "global_view": "Vista globale",
        "new_students": "Nuovi iscritti", "returning_students": "Reiscritti",
        "ifi_total": "IFI Totale",
    }
}

def t(key):
    lang = st.session_state.get('language', 'fr')
    return TRANSLATIONS.get(lang, TRANSLATIONS['fr']).get(key, key)

# =====================================================
# PAGE CONFIG
# =====================================================
st.set_page_config(
    page_title="IFI - Stats AEC",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =====================================================
# SESSION STATE INITIALIZATION
# =====================================================
if 'language' not in st.session_state:
    st.session_state.language = 'fr'  # French only
if 'graph_index' not in st.session_state:
    st.session_state.graph_index = 0
# Store processed data in session state to prevent loss on theme/language toggle
if 'processed_data' not in st.session_state:
    st.session_state.processed_data = None
if 'file_info' not in st.session_state:
    st.session_state.file_info = None

# =====================================================
# CUSTOM CSS
# =====================================================
def get_css():
    return """
    <style>
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
    </style>
    """

st.markdown(get_css(), unsafe_allow_html=True)

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
                 f"📚 {row[inscr_col]:,.0f} inscriptions<br>" +
                 f"🎓 {row['Nb. de Cours']:,.0f} cours<br>" +
                 f"💰 €{row['Recettes']:,.0f}<br>" +
                 f"📊 ARPI: €{row['ARPI']:.2f}",
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
        title=dict(text=f"🇮🇹 {t('italy_map')} - {t('map_by_inscriptions')}", font=dict(color=text_color, size=18)),
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
            insights.append(f"🏆 <strong>{top[0]}</strong> {t('dominates_with')} {pct:.0f}% {t('of_inscriptions')} ({top_inscr:,.0f})")
        if self.context['total_revenue'] > 0:
            rev_per = self.context['total_revenue'] / total
            insights.append(f"💰 {t('avg_revenue_per_inscr')}: <strong>€{rev_per:.0f}</strong>")
        if self.context.get('by_semester'):
            sem1 = self.context['by_semester'].get('sem1', 0)
            sem2 = self.context['by_semester'].get('sem2', 0)
            if sem1 > 0 and sem2 > 0:
                if sem1 > sem2:
                    diff = (sem1 - sem2) / sem2 * 100
                    insights.append(f"📅 {t('sem1_beats_sem2')} <strong>{diff:.0f}%</strong>")
                else:
                    diff = (sem2 - sem1) / sem1 * 100
                    insights.append(f"📅 {t('sem2_beats_sem1')} <strong>{diff:.0f}%</strong>")
        secteurs = sorted(self.context['by_sector'].items(), key=lambda x: x[1][self.inscr_col], reverse=True)
        if secteurs:
            top_sector = secteurs[0]
            pct = top_sector[1][self.inscr_col] / total * 100
            insights.append(f"📚 {t('dominant_sector')}: <strong>{top_sector[0]}</strong> ({pct:.0f}%)")
        return insights
    
    def answer(self, question):
        q = question.lower().strip()
        total = self.context['total_inscriptions']
        if any(word in q for word in ["inscri", "iscriz", "total", "combien", "quant"]):
            lines = [f"📊 <strong>{t('total_inscriptions')}</strong>: {format_number(total)}", "", f"{t('by_sede')}:"]
            for sede, data in self.context['by_sede'].items():
                inscr = data[self.inscr_col]
                pct = inscr / total * 100
                lines.append(f"• {sede}: {format_number(inscr)} ({pct:.1f}%)")
            return "<br>".join(lines)
        if any(word in q for word in ["recettes", "ricavi", "revenue", "fatturato"]):
            lines = [f"💰 <strong>{t('total_revenue')}</strong>: {format_number(self.context['total_revenue'], '€')}", "", f"{t('by_sede')}:"]
            for sede, data in self.context['by_sede'].items():
                lines.append(f"• {sede}: €{data['Recettes']:,.0f}")
            return "<br>".join(lines)
        if any(word in q for word in ["meilleur", "migliore", "best", "top"]):
            best = max(self.context['by_sede'].items(), key=lambda x: x[1][self.inscr_col])
            best_inscr = best[1][self.inscr_col]
            best_recettes = best[1]['Recettes']
            return f"🏆 <strong>{t('best_sede')}</strong>: {best[0]}<br>• {t('inscriptions')}: {format_number(best_inscr)}<br>• {t('revenue')}: €{best_recettes:,.0f}"
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
                            return f"⚖️ <strong>{s1.upper()} vs {s2.upper()}</strong><br><br>| | {s1.upper()} | {s2.upper()} |<br>|---|---|---|<br>| {t('inscriptions')} | {inscr1:,} | {inscr2:,} |<br>| {t('revenue')} | €{rec1:,.0f} | €{rec2:,.0f} |"
        for sede in ["IFM", "IFF", "IFN", "IFP"]:
            if sede.lower() in q:
                data = self.context['by_sede'].get(sede, {})
                if data:
                    inscr = data[self.inscr_col]
                    pct = inscr / total * 100
                    return f"🏛️ <strong>{sede}</strong><br>• {t('inscriptions')}: {format_number(inscr)} ({pct:.1f}%)<br>• {t('courses')}: {data['Nb. de Cours']}<br>• {t('revenue')}: €{data['Recettes']:,.0f}"
        return f"""🤖 <strong>{t('possible_questions')}:</strong><br>
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
PRELOADED_FILES = {}

if os.path.exists(DATA_DIR):
    for filename in os.listdir(DATA_DIR):
        if filename.endswith('.zip') and 'exports_AEC_' in filename:
            # Extract year from filename: exports_AEC_2024_annuel.zip -> 2024
            match = re.search(r'exports_AEC_(\d{4})_annuel\.zip', filename)
            if match:
                year = match.group(1)
                PRELOADED_FILES[year] = os.path.join(DATA_DIR, filename)

with st.sidebar:
    st.markdown("## 🇫🇷 Institut français Italia")
    st.markdown("### Dashboard Stats AEC")
    
    st.markdown("---")
    
    with st.expander(t('load_files'), expanded=True):
        # Show preloaded files section if available
        if PRELOADED_FILES:
            st.markdown(f"**{t('preloaded_files')}**")
            available_years = sorted(PRELOADED_FILES.keys(), reverse=True)
            
            # Multi-select checkboxes for years
            selected_years = []
            cols = st.columns(len(available_years))
            for idx, year in enumerate(available_years):
                with cols[idx]:
                    if st.checkbox(f"📅 {year}", key=f"check_year_{year}", value=False):
                        selected_years.append(year)
            
            # Load button - only show if at least one year selected
            if selected_years:
                if st.button(f"📥 Charger {', '.join(sorted(selected_years))}", key="load_selected_years", use_container_width=True):
                    # Load all selected years' ZIP files
                    st.session_state.stored_files = []
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
                            st.error(f"Erreur {year}: {e}")
                    # Clear processed data to force reprocessing
                    if 'processed_data' in st.session_state:
                        del st.session_state.processed_data
                    if 'file_info' in st.session_state:
                        del st.session_state.file_info
                    st.rerun()
            
            st.caption(t('or_upload_files'))
        else:
            st.caption(t('sedi_semesters'))
        
        raw_uploaded_files = st.file_uploader(
            t('drag_files'), type=['xlsx', 'xls', 'zip'], accept_multiple_files=True,
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
                        st.info(f"📦 ZIP extrait: {f.name}")
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
            st.info(f"📂 {len(uploaded_files)} fichiers restaurés depuis la session")
        
        # Button to clear stored data
        if 'stored_files' in st.session_state and st.session_state.stored_files:
            if st.button("🗑️ Effacer les données en cache", key="clear_cache"):
                del st.session_state.stored_files
                if 'processed_data' in st.session_state:
                    del st.session_state.processed_data
                if 'file_info' in st.session_state:
                    del st.session_state.file_info
                st.rerun()
    
    if uploaded_files:
        with st.expander(t('files_detected'), expanded=True):
            # Show count badge
            st.success(f"✅ {len(uploaded_files)} {t('files')}")
            
            # Build tree structure: Year > Semester > Sede
            file_tree = {}
            for f in uploaded_files:
                sede, sem, year = detect_from_filename(f.name)
                if sede and year:
                    if year not in file_tree:
                        file_tree[year] = {"sem1": [], "sem2": [], "annuel": []}
                    # sem can be None for annual files
                    sem_key = sem if sem else "annuel"
                    file_tree[year][sem_key].append(sede)
            
            # Display as tree with expanders
            for year in sorted(file_tree.keys(), reverse=True):
                st.markdown(f"**📅 {year}**")
                sem_labels = {"sem1": t('semester1'), "sem2": t('semester2'), "annuel": "Année complète"}
                for sem_key in ["sem1", "sem2", "annuel"]:
                    sedi_list = file_tree[year].get(sem_key, [])
                    if sedi_list:
                        sedi_str = " • ".join([f"✅ {s}" for s in sorted(sedi_list)])
                        st.caption(f"{sem_labels[sem_key]}: {sedi_str}")
                    elif sem_key != "annuel":  # Don't show empty annual row if using semesters
                        st.caption(f"{sem_labels[sem_key]}: ⬜ (aucun fichier)")
            
            # Show undetected files if any - only require sede and year, semester is optional (annual files)
            undetected = [f.name for f in uploaded_files if not detect_from_filename(f.name)[0] or not detect_from_filename(f.name)[2]]
            if undetected:
                st.markdown("**⚠️ Fichiers non reconnus:**")
                for fname in undetected:
                    st.caption(f"❌ {fname}")

# Default year fallback (when not detected from filename)
default_year = 2025

# =====================================================
# MAIN CONTENT
# =====================================================
# Use files from sidebar uploader
all_uploaded_files = uploaded_files if uploaded_files else []

if not all_uploaded_files:
    # Welcome screen with upload section
    st.markdown(f"## 👋 {t('welcome')}!")
    st.markdown(f"*{t('welcome_subtitle')}*")
    
    st.markdown("---")
    
    # Main upload section - prominent
    col_upload, col_features = st.columns([2, 1])
    
    with col_upload:
        st.markdown(f"### 📤 {t('quick_start')}")
        st.info(f"👆 {t('load_files_sidebar')}")
        
        # How to export from AEC
        with st.expander(f"❓ {t('how_to_export')}", expanded=False):
            st.markdown(f"""
            {t('export_steps')}
            
            **Format attendu:** `export AEC semestre X YYYY SEDE.xlsx`
            """)
    
    with col_features:
        st.markdown(f"### ✨ {t('features')}")
        st.markdown(f"""
        - 🏛️ {t('feature_1')}
        - 📅 {t('feature_2')}
        - 💶 {t('feature_3')}
        - 🗺️ {t('feature_4')}
        - 📥 {t('feature_5')}
        - 📊 {t('feature_6')}
        """)
    
    st.markdown("---")
    
    # Expected structure - less prominent, in expander
    with st.expander(f"📁 {t('expected_structure')}", expanded=False):
        st.markdown(f"""
        {t('you_must_load')} **8 {t('files')}** (4 sedi × 2 semestres):
        
        | {t('sede')} | {t('semester1')} | {t('semester2')} |
        |------|-----------|------------|
        | **IFM** (Milano) | ⬜ | ⬜ |
        | **IFF** (Firenze) | ⬜ | ⬜ |
        | **IFN** (Napoli) | ⬜ | ⬜ |
        | **IFP** (Palermo) | ⬜ | ⬜ |
        
        {t('recommended_format')}: `export AEC semestre X YYYY SEDE.xlsx`
        """)
    
    st.stop()

# Process files
files_to_process = all_uploaded_files

# Process files
all_data, file_info, errors = [], [], []
for uploaded_file in files_to_process:
    sede, semester, year = detect_from_filename(uploaded_file.name)
    year = year or default_year
    if not sede:
        errors.append(f"❌ Sede non détectée: {uploaded_file.name}")
        continue
    # semester can be None for annual files, this is handled by process_data
    df, error = load_excel(uploaded_file, uploaded_file.name)
    if error:
        errors.append(f"❌ Erreur: {uploaded_file.name}: {error}")
        continue
    processed = process_data(df, year, semester, sede)
    all_data.append(processed)
    semester_label = semester if semester else "annuel"
    file_info.append({"Fichier": uploaded_file.name, "Sede": sede, "Semestre": semester_label, "Année": year, "Lignes": len(processed)})

if errors:
    for err in errors:
        st.warning(err)
if not all_data:
    st.error("Aucune donnée valide chargée.")
    st.stop()

df_combined = pd.concat(all_data, ignore_index=True)
inscr_col = "Nb. d'inscriptions"

# Store in session state
st.session_state.processed_data = df_combined
st.session_state.file_info = file_info

# =====================================================
# KEY METRICS
# =====================================================
st.markdown(f"## 📊 {t('overview')}")

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
tab1, tab2, tab3, tab3_ss, tab3_mc, tab3b, tab4, tab5, tab6, tab7, tab8, tab9, tab10, tab11 = st.tabs([
    t("tab_prova_stats"), t("tab_by_sede"), t("tab_by_sector"), t("tab_by_sous_secteur"), t("tab_by_macro_category"), t("tab_by_category"),
    t("tab_yoy"), t("tab_profitability"), t("tab_map"),
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
        # Extract year from selection like "📅 2025 (année complète)"
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

# TAB 2: PAR SEDE
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
    
    # Custom blue scale with darker minimum for better visibility
    BLUE_SCALE_IFI = [[0, "#1e40af"], [0.25, "#3b82f6"], [0.5, "#60a5fa"], [0.75, "#93c5fd"], [1, "#dbeafe"]]
    
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
            fig_bar = px.bar(antenna_data, y="Secteur", x=value_col, orientation='h',
                            color=value_col, 
                            color_continuous_scale=[[0, color_scale[0]], [0.5, antenna_color], [1, color_scale[-1]]],
                            title=f"{title_suffix} - {antenna}",
                            text=value_col)
            fig_bar.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
            fig_bar.update_layout(height=chart_height, paper_bgcolor=bg_color, plot_bgcolor=bg_color, 
                                 font=dict(color=text_color), coloraxis_showscale=False)
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
            st.markdown(f"#### 🎯 Sélection : {filter_label}")
            
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
            
            col1, col2 = st.columns(2)
            with col1:
                fig_bar = px.bar(ss_summary, y="Sous-secteur", x=value_col, orientation='h',
                                color=value_col, color_continuous_scale="Greens",
                                title=f"{title_suffix} - Histogramme (IFI)",
                                text=value_col)
                fig_bar.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
                fig_bar.update_layout(height=500, paper_bgcolor=bg_color, plot_bgcolor=bg_color, 
                                     font=dict(color=text_color))
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
                           aspect="auto", color_continuous_scale="YlGn", text_auto=True)
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
                fig_bar = px.bar(antenna_data, y="Sous-secteur", x=value_col, orientation='h',
                                color=value_col, 
                                color_continuous_scale=[[0, color_scale[0]], [0.5, antenna_color], [1, color_scale[-1]]],
                                title=f"{title_suffix} - {antenna}",
                                text=value_col)
                fig_bar.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
                fig_bar.update_layout(height=400, paper_bgcolor=bg_color, plot_bgcolor=bg_color, 
                                     font=dict(color=text_color), coloraxis_showscale=False)
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
                st.markdown(f"#### 🎯 Sélection : {filter_label}")
                
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
            
            col1, col2 = st.columns(2)
            with col1:
                fig_bar = px.bar(mc_summary, y="Macro-catégorie", x=value_col, orientation='h',
                                color=value_col, color_continuous_scale="Purples",
                                title=f"{title_suffix} - Histogramme (IFI)",
                                text=value_col)
                fig_bar.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
                fig_bar.update_layout(height=500, paper_bgcolor=bg_color, plot_bgcolor=bg_color, 
                                     font=dict(color=text_color))
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
                           aspect="auto", color_continuous_scale="RdPu", text_auto=True)
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
                fig_bar = px.bar(antenna_data, y="Macro-catégorie", x=value_col, orientation='h',
                                color=value_col, 
                                color_continuous_scale=[[0, color_scale[0]], [0.5, antenna_color], [1, color_scale[-1]]],
                                title=f"{title_suffix} - {antenna}",
                                text=value_col)
                fig_bar.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
                fig_bar.update_layout(height=450, paper_bgcolor=bg_color, plot_bgcolor=bg_color, 
                                     font=dict(color=text_color), coloraxis_showscale=False)
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
                st.markdown(f"#### 🎯 Sélection : {filter_label}")
                
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
            
            col1, col2 = st.columns(2)
            with col1:
                fig_bar = px.bar(cat_summary, y="Catégorie de cours", x=value_col, orientation='h',
                                color=value_col, color_continuous_scale="Blues",
                                title=f"{title_suffix} - Top catégories (IFI)",
                                text=value_col)
                fig_bar.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
                fig_bar.update_layout(height=500, paper_bgcolor=bg_color, plot_bgcolor=bg_color, 
                                     font=dict(color=text_color))
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
                           aspect="auto", color_continuous_scale="YlOrRd", text_auto=True)
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
                fig_bar = px.bar(antenna_data, y="Catégorie de cours", x=value_col, orientation='h',
                                color=value_col, 
                                color_continuous_scale=[[0, antenna_color], [1, "#ffffff"]],
                                title=f"{title_suffix} - {antenna}",
                                text=value_col)
                fig_bar.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
                fig_bar.update_layout(height=350, paper_bgcolor=bg_color, plot_bgcolor=bg_color, 
                                     font=dict(color=text_color), coloraxis_showscale=False)
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
                st.markdown(f"#### 🎯 Sélection : {filter_label}")
                
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
    st.markdown("### 📅 Analyse par année")
    
    years = sorted(df_combined["Année"].unique())
    
    if len(years) < 1:
        st.warning("Aucune donnée chargée.")
    else:
        # 3 sub-levels using expanders
        
        # ============================================
        # NIVEAU 1: RÉSUMÉ DE L'ANNÉE
        # ============================================
        with st.expander("📊 Résumé de l'année", expanded=True):
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
        with st.expander("📈 Évolution pluriannuelle", expanded=True if len(years) > 1 else False):
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
        with st.expander("📊 Variations par antenne", expanded=True if len(years) > 1 else False):
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
    st.markdown(f"### ⚙️ {t('tab_config')}")
    
    # Category mapping table with all 4 levels
    with st.expander(f"📋 {t('category_mapping_title')}", expanded=True):
        # Build mapping table with all 4 levels
        mapping_data = []
        for cat, levels in sorted(CATEGORY_MAPPING.items(), key=lambda x: (x[1][2], x[1][1], x[1][0], x[0])):
            mapping_data.append({
                "Catégorie": cat, 
                "Macro-catégorie": levels[0] if levels[0] else "⚠️ MANQUANT", 
                "Sous-secteur": levels[1] if levels[1] else "⚠️ MANQUANT", 
                "Secteur": levels[2] if levels[2] else "⚠️ MANQUANT"
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
        if st.button("💾 Sauvegarder les modifications", type="primary", key="save_main_mappings"):
            try:
                # Find rows that have been modified (compare with original CATEGORY_MAPPING)
                modified_mappings = []
                for idx, row in edited_df.iterrows():
                    cat = row["Catégorie"]
                    new_macro = row["Macro-catégorie"] if row["Macro-catégorie"] != "⚠️ MANQUANT" else ""
                    new_ss = row["Sous-secteur"] if row["Sous-secteur"] != "⚠️ MANQUANT" else ""
                    new_sect = row["Secteur"] if row["Secteur"] != "⚠️ MANQUANT" else ""
                    
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
                    
                    st.success(f"✅ {len(modified_mappings)} correspondance(s) modifiée(s) sauvegardée(s) !")
                    st.balloons()
                    st.rerun()
                else:
                    st.info("ℹ️ Aucune modification détectée dans le tableau.")
                    
            except Exception as e:
                st.error(f"❌ Erreur lors de la sauvegarde : {str(e)}")
    
    # Show unlinked categories warning if any exist
    unlinked_cats = get_unknown_categories()
    if unlinked_cats:
        with st.expander(f"🚨 {t('unlinked_categories')} ({len(unlinked_cats)})", expanded=True):
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
                    st.markdown(f"🔴 **{cat}**")
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
            if st.button("💾 Sauvegarder les correspondances", type="primary", key="save_unlinked_mappings"):
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
                            st.success(f"✅ {len(new_mappings)} correspondance(s) complète(s) sauvegardée(s) !")
                        if partial_mappings:
                            st.info(f"📝 {len(partial_mappings)} correspondance(s) partielle(s) sauvegardée(s) (à compléter plus tard)")
                        
                        st.balloons()
                        
                        # Rerun to refresh the page dynamically
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"❌ Erreur lors de la sauvegarde : {str(e)}")
                else:
                    st.warning("⚠️ Aucun champ rempli. Sélectionnez au moins une valeur pour une catégorie.")
                
                if errors:
                    for err in errors:
                        st.warning(err)
    else:
        st.success("✅ Toutes les catégories sont reconnues dans le tableau de correspondances.")

# =====================================================
# FOOTER
# =====================================================
st.markdown("---")
st.caption("Dashboard Stats AEC v3.0 • Institut Français Italia")
