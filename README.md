# 📊 Dashboard Statistiques AEC - Institut français Italia

Dashboard interactif pour l'analyse des données AEC.

## 🚀 Fonctionnalités

- 📈 **Analyse multi-années** : Comparez les données sur plusieurs années
- 🏢 **Vue par sede** : Milano, Firenze, Napoli, Palermo
- 📅 **Analyse par semestre** : Semestre 1 et 2
- 🔄 **Comparaisons** : Sede vs Sede, Année vs Année, Type de cours
- 🌍 **Bilingue** : Interface FR/IT
- 🌓 **Mode nuit/jour**
- 💬 **Assistant IA** pour l'analyse des données

## 📋 Format des fichiers

Le dashboard accepte :
- **Fichiers Excel individuels** nommés : `export AEC semestre [1/2] [ANNÉE] [CODE_SEDE].xlsx`
- **Archives ZIP** contenant plusieurs fichiers Excel (organisés par année)

### Structure des fichiers ZIP recommandée :
```
exports_AEC_2024_S1-S2.zip
├── export AEC semestre 1 2024 IFM.xlsx
├── export AEC semestre 1 2024 IFF.xlsx
├── export AEC semestre 2 2024 IFM.xlsx
└── export AEC semestre 2 2024 IFF.xlsx
```

## 🛠️ Installation locale

```bash
# Installer les dépendances
pip install -r requirements.txt

# Lancer le dashboard
streamlit run dashboard_aec_v2.py
```

## 📊 Utilisation

1. **Uploader vos données** : Glissez-déposez vos fichiers Excel ou ZIP dans la zone de téléchargement
2. **Sélectionner l'année de référence** : Choisissez l'année principale à analyser
3. **Explorer les onglets** :
   - 🌍 **Panoramica** : Vue d'ensemble multi-années
   - 🎯 **Vue Globale IFI** : Statistiques agrégées
   - 🏢 **Détails par Sede** : Analyse détaillée par établissement
   - 📊 **Comparaisons** : Comparaisons croisées
   - 💬 **Assistant IA** : Aide à l'analyse

## 🔒 Confidentialité

Ce dashboard ne stocke **aucune donnée** en ligne. Toutes les analyses sont effectuées localement dans votre navigateur.

## 📝 Licence

© Institut français Italia - Usage interne uniquement
