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
# CONFIGURATION & MAPPING - CORRECT from user's list
# =====================================================

# This is the CORRECT mapping from Catégorie de cours → Type
CATEGORY_MAPPING = {
    # CORSI PER SCUOLE (Ecoles)
    "ECOLES - Matinée": "CORSI PER SCUOLE",
    "ECOLES - GRL": "CORSI PER SCUOLE",
    "ECOLES - Classes Découverte": "CORSI PER SCUOLE",
    "ECOLES - Ateliers": "CORSI PER SCUOLE",
    "ECOLES - SPE": "CORSI PER SCUOLE",
    "ECOLES - PCTO Au Travail": "CORSI PER SCUOLE",
    "ECOLES - PCTO Au Travail ": "CORSI PER SCUOLE",
    "ECOLES - PCTO Prim'Aria": "CORSI PER SCUOLE",
    "ECOLES - PON": "CORSI PER SCUOLE",
    "ECOLES - immersion (GRL)": "CORSI PER SCUOLE",
    "ECOLES - PCTO Ciné": "CORSI PER SCUOLE",
    
    # CORSI AZIENDALI (Entreprises)
    "SOC-GEN": "CORSI AZIENDALI",
    "SOC-SPE": "CORSI AZIENDALI",
    
    # CORSI PRIVATI (Cours particuliers / Sur mesure)
    "PART-FR GRL<20": "CORSI PRIVATI",
    "PART-FR GRL>=20": "CORSI PRIVATI",
    "PART-FR SPE<20": "CORSI PRIVATI",
    "PART-FR SPE>=20": "CORSI PRIVATI",
    "PART-DUO": "CORSI PRIVATI",
    "PART-TRIO": "CORSI PRIVATI",
    "PART-FR GRL": "CORSI PRIVATI",
    "PART-FR SPE": "CORSI PRIVATI",
    "PART-GP": "CORSI PRIVATI",
    "PART-ITA": "CORSI PRIVATI",
    
    # COURS COLL EXTENSIFS (Cours collectifs adultes extensifs)
    "GRL-45H (D) ": "COURS COLL EXTENSIFS",
    "GRL-45H (D)": "COURS COLL EXTENSIFS",
    "GRL-20H (D)": "COURS COLL EXTENSIFS",
    "GRL-60H (P)": "COURS COLL EXTENSIFS",
    "GRL-UEL 20H": "COURS COLL EXTENSIFS",
    "GRL-30H (P)": "COURS COLL EXTENSIFS",
    "GRL-45h (P)": "COURS COLL EXTENSIFS",
    "GRL-60H (D) ": "COURS COLL EXTENSIFS",
    "GRL-60H (D)": "COURS COLL EXTENSIFS",
    "GRL-30H (D)": "COURS COLL EXTENSIFS",
    "GRL-15H (P)": "COURS COLL EXTENSIFS",
    "GRL-90H (P)": "COURS COLL EXTENSIFS",
    "GRL-90H (D)": "COURS COLL EXTENSIFS",
    "GRL-90H": "COURS COLL EXTENSIFS",
    "GRL-20H (P)": "COURS COLL EXTENSIFS",
    "GRL-20H": "COURS COLL EXTENSIFS",
    "GRL-30H (BASE)": "COURS COLL EXTENSIFS",
    "GRL-30H (BASE) - V": "COURS COLL EXTENSIFS",
    "GRL-30H (MAJ)": "COURS COLL EXTENSIFS",
    "GRL-30H (MAJ) - V": "COURS COLL EXTENSIFS",
    "GRL-45H (BASE)": "COURS COLL EXTENSIFS",
    "GRL-45H (MAJ)": "COURS COLL EXTENSIFS",
    "GRL-45H (P)": "COURS COLL EXTENSIFS",
    "GRL-45h (D)": "COURS COLL EXTENSIFS",
    "GRL-60H (45+15) (BASE)": "COURS COLL EXTENSIFS",
    "GRL-60H (45+15) (MAJ)": "COURS COLL EXTENSIFS",
    "GRL-60H (50+10)": "COURS COLL EXTENSIFS",
    "GRL-60H (BASE)": "COURS COLL EXTENSIFS",
    "GRL-60H (BASE) - V": "COURS COLL EXTENSIFS",
    "GRL-60H (MAJ)": "COURS COLL EXTENSIFS",
    "GRL-60H (MAJ) - V": "COURS COLL EXTENSIFS",
    
    # COURS COLL INT (Cours intensifs)
    "INT-30H (P)": "COURS COLL INT",
    "INT-30H (D)": "COURS COLL INT",
    "INT-16H (P)": "COURS COLL INT",
    "INT-16h (P)": "COURS COLL INT",
    "INT-30H (BASE)": "COURS COLL INT",
    "INT-30H (MAJ)": "COURS COLL INT",
    "INT-30H (VIRT)": "COURS COLL INT",
    
    # COLLECTIFS ADOS/ENFANTS
    "ENFANTS 25H": "COLLECTIFS ADOS/ENFANTS",
    "ADOS/ENFANTS CAMPUS 20H": "COLLECTIFS ADOS/ENFANTS",
    "ENFANTS 18H": "COLLECTIFS ADOS/ENFANTS",
    "ADOS/ENFANTS ATELIERS": "COLLECTIFS ADOS/ENFANTS",
    "ADOS-EXT-IFN": "COLLECTIFS ADOS/ENFANTS",
    "ADOS-EXT-IFM": "COLLECTIFS ADOS/ENFANTS",
    "ADOS-EXT-IFP": "COLLECTIFS ADOS/ENFANTS",
    "ADOS-EXT": "COLLECTIFS ADOS/ENFANTS",
    "ADOS  16H": "COLLECTIFS ADOS/ENFANTS",
    "ADOS-CAMP": "COLLECTIFS ADOS/ENFANTS",
    "ADOS-INT": "COLLECTIFS ADOS/ENFANTS",
    "ADOS/ENFANTS CAMPUS 15H": "COLLECTIFS ADOS/ENFANTS",
    "ADOS/ENFANTS CAMPUS 30H": "COLLECTIFS ADOS/ENFANTS",
    "ENFANTS": "COLLECTIFS ADOS/ENFANTS",
    
    # ATELIERS COLL (Ateliers collectifs spécialisés)
    "Ateliers thématiques": "ATELIERS COLL",
    "SPE-DELF B2 EXPRESS (6+10)": "ATELIERS COLL",
    "SPE-DALF EXPRESS (10+10)": "ATELIERS COLL",
    "SPE-CONV-30H": "ATELIERS COLL",
    "SPE-CONV-21H (D)": "ATELIERS COLL",
    "SPE-CONV-21H (P)": "ATELIERS COLL",
    "SPE-THÉÂTRE": "ATELIERS COLL",
    "SPE-CONV-15H": "ATELIERS COLL",
    "SPE-CONV-15H ": "ATELIERS COLL",
    "SPE-LECT-6H": "ATELIERS COLL",
    "SPE-LECT-6H ": "ATELIERS COLL",
    "SPE-DALF EXT": "ATELIERS COLL",
    "SPE-CONV-28H": "ATELIERS COLL",
    "SPE-CONV-SENIOR-28H": "ATELIERS COLL",
    "SPE-CONV-MINIGP": "ATELIERS COLL",
    "CONVERSATION": "ATELIERS COLL",
    "DALF EXPRESS (10+10)": "ATELIERS COLL",
    "DALF EXT": "ATELIERS COLL",
    "DELF B2 EXPRESS (6+10)": "ATELIERS COLL",
    "DELF B2 EXT": "ATELIERS COLL",
    "SPE/PRO": "ATELIERS COLL",
    "SPE/TRAD": "ATELIERS COLL",
    "THÉMATIQUES": "ATELIERS COLL",
    "UEL 20H": "ATELIERS COLL",
    
    # CORSI ONLINE PIATT (Plateforme en ligne)
    "PLAT-MCEL-INDIV": "CORSI ONLINE PIATT",
    "PLAT-RIPASSO-GRAM": "CORSI ONLINE PIATT",
    "PLAT-MCEL-AUTONOMIE": "CORSI ONLINE PIATT",
    "PLAT-ABCDELFB2+4": "CORSI ONLINE PIATT",
    "PLAT-MCEL-DUO": "CORSI ONLINE PIATT",
    "PLAT-ABCDELFB1+3": "CORSI ONLINE PIATT",
    "MCEL-12": "CORSI ONLINE PIATT",
    "MCEL-12-DUO": "CORSI ONLINE PIATT",
    "MCEL-8": "CORSI ONLINE PIATT",
    "MCEL-AUTONOMIE": "CORSI ONLINE PIATT",
    "ABC DELF AUTONOMIE": "CORSI ONLINE PIATT",
    "ABC DELF SCUOLE": "CORSI ONLINE PIATT",
    "ABCDELFB2-4": "CORSI ONLINE PIATT",
    "Cours en ligne Apolearn": "CORSI ONLINE PIATT",
}

SECTOR_ORDER = [
    "COURS COLL EXTENSIFS", "COURS COLL INT", "ATELIERS COLL",
    "CORSI PRIVATI", "CORSI ONLINE PIATT", "CORSI AZIENDALI",
    "CORSI PER SCUOLE", "COLLECTIFS ADOS/ENFANTS", "AUTRE"
]

SEDE_COLORS = {
    "IFM": "#FFB347", "IFF": "#87CEEB", "IFN": "#90EE90",
    "IFP": "#DDA0DD", "IFI": "#4169E1"
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
        "drag_files": "Glissez vos fichiers Excel", "files_detected": "Fichiers détectés",
        "expected_structure": "Structure attendue", "you_must_load": "Vous devez charger",
        "files": "fichiers", "sede": "Sede", "semester1": "Semestre 1", "semester2": "Semestre 2",
        "recommended_format": "Format de nom recommandé",
        "load_files_sidebar": "Chargez vos fichiers AEC dans la barre latérale pour commencer l'analyse.",
        "overview": "Vue d'ensemble", "inscriptions": "Inscriptions", "courses": "Cours",
        "student_hours": "Heures-élèves", "planned_hours": "Heures prévues", "revenue": "Recettes", "students_per_course": "Élèves/cours",
        "tab_prova_stats": "Synthèse", "tab_by_sede": "Par antenne",
        "tab_by_sector": "Par secteur", "tab_by_category": "Par catégorie", "tab_comparisons": "Comparaisons",
        "tab_graphs": "Graphiques", "tab_ai": "Assistant IA", "tab_export": "Export",
        "filter_by_sede": "Filtrer par antenne", "filter_by_period": "Filtrer par période",
        "all": "Tous", "ifi_totals": "Totaux IFI (toutes sedi)",
        "analysis_by_sede": "Analyse par antenne", "inscriptions_by_sede": "Inscriptions par antenne",
        "distribution": "Répartition des inscriptions", "detail_by_sede": "Détail par antenne",
        "analysis_by_sector": "Analyse par secteur", "inscriptions_by_sector": "Inscriptions par secteur",
        "courses_by_sector": "Nb de cours par secteur",
        "analysis_by_category": "Analyse par catégorie", "inscriptions_by_category": "Inscriptions par catégorie",
        "courses_by_category": "Nb de cours par catégorie", "top_categories": "Top catégories",
        "heatmap_title": "Heatmap : secteur × antenne", "comparison_mode": "Mode comparaisons",
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
        "map_by_inscriptions": "Inscriptions par ville", "tab_yoy": "Année vs Année",
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
        "drag_files": "Trascina i tuoi file Excel", "files_detected": "File rilevati",
        "expected_structure": "Struttura prevista", "you_must_load": "Devi caricare",
        "files": "file", "sede": "Sede", "semester1": "Semestre 1", "semester2": "Semestre 2",
        "recommended_format": "Formato nome consigliato",
        "load_files_sidebar": "Carica i tuoi file AEC nella barra laterale per iniziare l'analisi.",
        "overview": "Panoramica", "inscriptions": "Iscrizioni", "courses": "Corsi",
        "student_hours": "Ore-studenti", "planned_hours": "Ore previste", "revenue": "Ricavi", "students_per_course": "Alunni/corso",
        "tab_prova_stats": "Sintesi", "tab_by_sede": "Per sede",
        "tab_by_sector": "Per settore", "tab_by_category": "Per categoria", "tab_comparisons": "Confronti",
        "tab_graphs": "Grafici", "tab_ai": "Assistente IA", "tab_export": "Esporta",
        "filter_by_sede": "Filtra per sede", "filter_by_period": "Filtra per periodo",
        "all": "Tutti", "ifi_totals": "Totali IFI (tutte le sedi)",
        "analysis_by_sede": "Analisi per sede", "inscriptions_by_sede": "Iscrizioni per sede",
        "distribution": "Distribuzione delle iscrizioni", "detail_by_sede": "Dettaglio per sede",
        "analysis_by_sector": "Analisi per settore", "inscriptions_by_sector": "Iscrizioni per settore",
        "courses_by_sector": "N. corsi per settore",
        "analysis_by_category": "Analisi per categoria", "inscriptions_by_category": "Iscrizioni per categoria",
        "courses_by_category": "N. corsi per categoria", "top_categories": "Top categorie",
        "heatmap_title": "Heatmap: settore × sede", "comparison_mode": "Modalità confronti",
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
        "map_by_inscriptions": "Iscrizioni per città", "tab_yoy": "Année vs Année",
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
            padding: 10px 20px !important;
            font-size: 14px !important;
            min-width: 100px !important;
            border-radius: 8px !important;
            transition: all 0.2s ease !important;
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

def map_category_to_sector(category):
    if pd.isna(category):
        return "AUTRE"
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
    # Fallback patterns
    cat_upper = cat_str.upper()
    if "ECOLES" in cat_upper:
        return "CORSI PER SCUOLE"
    if "GRL-" in cat_upper or "INT-" in cat_upper:
        return "COURS COLL EXTENSIFS"
    if "SPE-" in cat_upper or "CONV" in cat_upper or "ATELIER" in cat_upper:
        return "ATELIERS COLL"
    if "PART-" in cat_upper:
        return "CORSI PRIVATI"
    if "SOC-" in cat_upper:
        return "CORSI AZIENDALI"
    if "MCEL" in cat_upper or "PLAT-" in cat_upper:
        return "CORSI ONLINE PIATT"
    if "ADOS" in cat_upper or "ENFANTS" in cat_upper:
        return "COLLECTIFS ADOS/ENFANTS"
    return "AUTRE"

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
        df["Secteur"] = df["Catégorie de cours"].apply(map_category_to_sector)
    else:
        df["Secteur"] = "AUTRE"
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
    # Column order matching IFI totals table
    desired_cols = [
        "Année", "Période", "Sede", "Secteur", "Nb. de Cours", "Nb. d'inscriptions",
        "Nouveaux inscrits", "Réinscrits", "Nombre d'heures prévues",
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
with st.sidebar:
    st.markdown("## 🇫🇷 Institut français Italia")
    st.markdown("### Dashboard Stats AEC")
    
    st.markdown("---")
    
    with st.expander(t('load_files'), expanded=True):
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
tab1, tab2, tab3, tab3b, tab4, tab5, tab6, tab7, tab8, tab9, tab10 = st.tabs([
    t("tab_prova_stats"), t("tab_by_sede"), t("tab_by_sector"), t("tab_by_category"),
    t("tab_yoy"), t("tab_profitability"), t("tab_map"),
    t("tab_comparisons"), t("tab_graphs"), t("tab_ai"), t("tab_export")
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
            t('pct_new'): pct_new,
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
            t('pct_new'): total_pct_new,
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
        df_display[t('pct_new')] = df_display[t('pct_new')].apply(lambda x: f"{x:.1f}%")
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
                    color="Sede", color_discrete_map=SEDE_COLORS, title=t('inscriptions_by_sede'))
        fig.update_layout(showlegend=False, height=350, paper_bgcolor=bg_color, plot_bgcolor=bg_color, font=dict(color=text_color))
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        fig = px.pie(sede_summary, values=inscr_col, names="Sede", color="Sede", color_discrete_map=SEDE_COLORS, title=t('distribution'))
        fig.update_layout(height=350, paper_bgcolor=bg_color, plot_bgcolor=bg_color, font=dict(color=text_color))
        st.plotly_chart(fig, use_container_width=True)
    st.markdown(f"#### {t('detail_by_sede')}")
    sede_summary[t("students_per_course")] = (sede_summary[inscr_col] / sede_summary["Nb. de Cours"]).round(2)
    st.dataframe(sede_summary, hide_index=True, use_container_width=True)

# TAB 3: PAR SECTEUR
with tab3:
    st.markdown(f"### {t('analysis_by_sector')}")
    
    # Year selector for this tab
    tab3_years = sorted(df_combined["Année"].unique())
    if len(tab3_years) > 1:
        selected_year_tab3 = st.selectbox(
            t("filter_by_period"), 
            tab3_years, 
            index=len(tab3_years)-1,  # Default to most recent year
            key="sector_year_filter"
        )
        df_tab3 = df_combined[df_combined["Année"] == selected_year_tab3]
    else:
        df_tab3 = df_combined
    
    # Get list of antennas
    antennas = sorted(df_tab3["Sede"].unique().tolist())
    
    # Text above sub-tabs
    st.markdown(f"**{t('choose_indicator')}**")
    
    # Sub-tabs for indicators
    indicator_tabs = st.tabs([t('global_view'), t('inscriptions'), t('planned_hours'), t('courses'), t('revenue')])
    
    # Function to create 5-graph layout (IFI total + 4 antennas in 2x2)
    def create_sector_graphs(df_data, value_col, title_suffix, color_scale):
        # IFI Total (full width)
        st.markdown(f"##### {t('ifi_total')}")
        ifi_summary = df_data.groupby("Secteur").agg({value_col: "sum"}).reset_index()
        ifi_summary = ifi_summary.sort_values(value_col, ascending=False)
        fig_ifi = px.bar(ifi_summary, y="Secteur", x=value_col, orientation='h',
                        color=value_col, color_continuous_scale=color_scale, 
                        title=f"{title_suffix} - IFI ({t('ifi_total')})")
        fig_ifi.update_layout(height=400, paper_bgcolor=bg_color, plot_bgcolor=bg_color, font=dict(color=text_color))
        st.plotly_chart(fig_ifi, use_container_width=True)
        
        # 4 antennas in 2x2 layout
        if len(antennas) >= 4:
            row1_col1, row1_col2 = st.columns(2)
            row2_col1, row2_col2 = st.columns(2)
            antenna_cols = [row1_col1, row1_col2, row2_col1, row2_col2]
            
            for i, antenna in enumerate(antennas[:4]):
                with antenna_cols[i]:
                    antenna_data = df_data[df_data["Sede"] == antenna].groupby("Secteur").agg({value_col: "sum"}).reset_index()
                    antenna_data = antenna_data.sort_values(value_col, ascending=False)
                    fig = px.bar(antenna_data, y="Secteur", x=value_col, orientation='h',
                                color=value_col, color_continuous_scale=color_scale,
                                title=f"{title_suffix} - {antenna}")
                    fig.update_layout(height=350, paper_bgcolor=bg_color, plot_bgcolor=bg_color, font=dict(color=text_color),
                                     showlegend=False, coloraxis_showscale=False)
                    st.plotly_chart(fig, use_container_width=True)
        elif len(antennas) > 0:
            # Less than 4 antennas: show what we have in columns
            cols = st.columns(len(antennas))
            for i, antenna in enumerate(antennas):
                with cols[i]:
                    antenna_data = df_data[df_data["Sede"] == antenna].groupby("Secteur").agg({value_col: "sum"}).reset_index()
                    antenna_data = antenna_data.sort_values(value_col, ascending=False)
                    fig = px.bar(antenna_data, y="Secteur", x=value_col, orientation='h',
                                color=value_col, color_continuous_scale=color_scale,
                                title=f"{title_suffix} - {antenna}")
                    fig.update_layout(height=350, paper_bgcolor=bg_color, plot_bgcolor=bg_color, font=dict(color=text_color),
                                     showlegend=False, coloraxis_showscale=False)
                    st.plotly_chart(fig, use_container_width=True)
    
    # Tab: Global view (same as before, but no sub-indicator)
    with indicator_tabs[0]:
        create_sector_graphs(df_tab3, inscr_col, t('inscriptions'), "Blues")
    
    # Tab: Inscriptions
    with indicator_tabs[1]:
        create_sector_graphs(df_tab3, inscr_col, t('inscriptions'), "Blues")
    
    # Tab: Heures prévues
    with indicator_tabs[2]:
        if "Nombre d'heures prévues" in df_tab3.columns:
            create_sector_graphs(df_tab3, "Nombre d'heures prévues", t('planned_hours'), "Purples")
        else:
            st.warning("Colonne 'Nombre d'heures prévues' non disponible")
    
    # Tab: Cours
    with indicator_tabs[3]:
        create_sector_graphs(df_tab3, "Nb. de Cours", t('courses'), "Greens")
    
    # Tab: Recettes
    with indicator_tabs[4]:
        if "Recettes" in df_tab3.columns:
            create_sector_graphs(df_tab3, "Recettes", t('revenue'), "Oranges")
        else:
            st.warning("Colonne 'Recettes' non disponible")
    
    # Heatmap (always visible, after the tabs)
    st.markdown(f"#### {t('heatmap_title')}")
    heatmap_data = df_tab3.groupby(["Secteur", "Sede"])[inscr_col].sum().unstack(fill_value=0)
    fig = px.imshow(heatmap_data, labels=dict(x="Sede", y="Secteur", color=t("inscriptions")), aspect="auto", color_continuous_scale="YlOrRd", text_auto=True)
    fig.update_layout(height=550, paper_bgcolor=bg_color, plot_bgcolor=bg_color, font=dict(color=text_color))
    st.plotly_chart(fig, use_container_width=True)

# TAB 3B: PAR CATÉGORIE (granular view)
with tab3b:
    st.markdown(f"### {t('analysis_by_category')}")
    
    # Year selector for this tab
    tab3b_years = sorted(df_combined["Année"].unique())
    if len(tab3b_years) > 1:
        selected_year_tab3b = st.selectbox(
            t("filter_by_period"), 
            tab3b_years, 
            index=len(tab3b_years)-1,
            key="category_year_filter"
        )
        df_tab3b = df_combined[df_combined["Année"] == selected_year_tab3b]
    else:
        df_tab3b = df_combined
    
    # Check if "Catégorie de cours" column exists
    if "Catégorie de cours" in df_tab3b.columns:
        cat_summary = df_tab3b.groupby("Catégorie de cours").agg({inscr_col: "sum", "Nb. de Cours": "sum", "Recettes": "sum"}).reset_index()
        cat_summary = cat_summary.sort_values(inscr_col, ascending=False)
        
        # Show top 20 categories
        st.markdown(f"#### {t('top_categories')}")
        top_cats = cat_summary.head(20)
        
        col1, col2 = st.columns(2)
        with col1:
            fig = px.bar(top_cats, y="Catégorie de cours", x=inscr_col, orientation='h',
                        color=inscr_col, color_continuous_scale="Blues", title=t('inscriptions_by_category'))
            fig.update_layout(height=600, paper_bgcolor=bg_color, plot_bgcolor=bg_color, font=dict(color=text_color))
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            fig = px.bar(top_cats, y="Catégorie de cours", x="Nb. de Cours", orientation='h',
                        color="Nb. de Cours", color_continuous_scale="Greens", title=t('courses_by_category'))
            fig.update_layout(height=600, paper_bgcolor=bg_color, plot_bgcolor=bg_color, font=dict(color=text_color))
            st.plotly_chart(fig, use_container_width=True)
        
        # Full table
        cat_summary[t("students_per_course")] = (cat_summary[inscr_col] / cat_summary["Nb. de Cours"].replace(0, pd.NA)).round(2)
        st.dataframe(cat_summary, hide_index=True, use_container_width=True, height=500)
    else:
        st.warning("La colonne 'Catégorie de cours' n'est pas disponible dans les données.")

# TAB 4: YEAR VS YEAR (NEW!)
with tab4:
    st.markdown(f"### {t('year_comparison')}")
    
    years = sorted(df_combined["Année"].unique())
    
    if len(years) < 2:
        st.warning(t('need_multiple_years'))
        st.info(f"""
        **{t('load_more_years')}**
        
        Actuellement chargé : **{', '.join(map(str, years))}**
        
        Pour comparer les années, chargez les exports AEC de plusieurs années (ex: 2024 + 2025).
        """)
    else:
        # Year-over-year comparison
        comparison_df, _ = calculate_yoy_comparison(df_combined)
        
        if comparison_df is not None:
            st.markdown(f"#### {t('evolution')} {min(years)} → {max(years)}")
            
            # Show metrics with variations
            col1, col2, col3, col4 = st.columns(4)
            
            latest = comparison_df.iloc[-1]
            previous = comparison_df.iloc[-2]
            
            def get_delta_color(val):
                return "normal" if val >= 0 else "inverse"
            
            with col1:
                var = latest.get("Inscriptions_var", 0)
                st.metric(
                    t('inscriptions'), 
                    f"{latest['Inscriptions']:,.0f}",
                    f"{var:+.1f}%" if not pd.isna(var) else None,
                    delta_color=get_delta_color(var) if not pd.isna(var) else "off"
                )
            with col2:
                var = latest.get("Cours_var", 0)
                st.metric(
                    t('courses'), 
                    f"{latest['Cours']:,.0f}",
                    f"{var:+.1f}%" if not pd.isna(var) else None,
                    delta_color=get_delta_color(var) if not pd.isna(var) else "off"
                )
            with col3:
                var = latest.get("Recettes_var", 0)
                st.metric(
                    t('revenue'), 
                    f"€{latest['Recettes']:,.0f}",
                    f"{var:+.1f}%" if not pd.isna(var) else None,
                    delta_color=get_delta_color(var) if not pd.isna(var) else "off"
                )
            with col4:
                var = latest.get("Heures_var", 0)
                st.metric(
                    t('student_hours'), 
                    f"{latest['Heures']:,.0f}",
                    f"{var:+.1f}%" if not pd.isna(var) else None,
                    delta_color=get_delta_color(var) if not pd.isna(var) else "off"
                )
            
            # Evolution chart
            st.markdown(f"#### {t('multi_year_evolution')}")
            
            fig = make_subplots(rows=2, cols=2, subplot_titles=[
                t("inscriptions"), t("courses"), t("revenue"), t("student_hours")
            ])
            
            metrics = ["Inscriptions", "Cours", "Recettes", "Heures"]
            positions = [(1, 1), (1, 2), (2, 1), (2, 2)]
            colors = ["#6366f1", "#10b981", "#f59e0b", "#ef4444"]
            
            for metric, pos, color in zip(metrics, positions, colors):
                fig.add_trace(
                    go.Bar(
                        x=comparison_df["Année"].astype(str),
                        y=comparison_df[metric],
                        marker_color=color,
                        name=metric,
                        text=comparison_df[metric].apply(lambda x: f"{x:,.0f}"),
                        textposition="outside"
                    ),
                    row=pos[0], col=pos[1]
                )
            
            fig.update_layout(
                height=550,
                showlegend=False,
                paper_bgcolor=bg_color,
                plot_bgcolor=bg_color,
                font=dict(color=text_color),
                margin=dict(t=80, b=40, l=40, r=40)  # More top margin for labels
            )
            # Ensure y-axes have enough room for text labels
            fig.update_yaxes(automargin=True)
            st.plotly_chart(fig, use_container_width=True)
            
            # Year comparison by sede
            st.markdown(f"#### {t('yoy_variation')} {t('by_sede')}")
            yoy_sede = calculate_yoy_by_sede(df_combined)
            
            if yoy_sede is not None:
                pivot_inscr = yoy_sede.pivot(index="Sede", columns="Année", values="Inscriptions").reset_index()
                
                # Calculate variation
                if len(years) >= 2:
                    y1, y2 = years[-2], years[-1]
                    pivot_inscr["Variation"] = ((pivot_inscr[y2] - pivot_inscr[y1]) / pivot_inscr[y1] * 100).round(1)
                    
                    # Format with colors using HTML/markdown style for streamlit
                    def format_variation_with_color(val):
                        if val > 0:
                            return f"+{val:.1f}%"
                        elif val < 0:
                            return f"{val:.1f}%"
                        else:
                            return f"{val:.1f}%"
                    
                    pivot_inscr["Variation"] = pivot_inscr["Variation"].apply(format_variation_with_color)
                
                st.dataframe(pivot_inscr, hide_index=True, use_container_width=True)
                
                # Chart
                fig = px.bar(
                    yoy_sede, x="Sede", y="Inscriptions", color="Année",
                    barmode="group", color_discrete_sequence=px.colors.qualitative.Set2,
                    title=f"{t('inscriptions_by_sede')} - {t('year_comparison')}"
                )
                fig.update_layout(height=400, paper_bgcolor=bg_color, plot_bgcolor=bg_color, font=dict(color=text_color))
                st.plotly_chart(fig, use_container_width=True)

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
            title=f"{t('age_distribution')} {t('by_sede')}"
        )
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
        fig = px.bar(compare_df, x="Métrique", y="Valeur", color="Sede", barmode="group", color_discrete_map=SEDE_COLORS)
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
            fig = px.bar(sem_sede, x="Sede", y=inscr_col, color="Semestre", barmode="group", title=t("comparison_by_sede"))
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
        fig = px.bar(df_tab8.groupby(["Sede", "Secteur"])[inscr_col].sum().reset_index(), x="Secteur", y=inscr_col, color="Sede",
                    barmode="group", color_discrete_map=SEDE_COLORS, title=t("inscr_by_sector_sede"))
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

# =====================================================
# FOOTER
# =====================================================
st.markdown("---")
st.caption("Dashboard Stats AEC v3.0 • Institut Français Italia")
