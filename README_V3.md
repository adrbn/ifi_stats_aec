# OSCAR v3 — copie de travail (coexiste avec v2)

`dashboard_aec_v3.py` est une **copie de travail** de `dashboard_aec_v2.py`
avec en plus le support du **nouvel export AEC** « Cours > Tous les cours »
(un fichier = N cours, une ligne par cours).

**`dashboard_aec_v2.py` reste intact et fonctionne comme avant.** Tu peux
lancer l'un ou l'autre selon tes besoins, et les déployer comme deux apps
Streamlit Cloud distinctes.

## Ce qui change dans v3

### Nouveau module
- **`aec_parser_v3.py`** — parseur du nouvel export AEC :
  - Lit le fichier brut
  - Filtre par statut (par défaut : `Ouvert`, `Fermé à l'inscription`, `En attente`)
  - Filtre par date début ≥ 2022-09-01
  - Dérive `Sede` depuis « Lieu du cours » (IFM/IFF/IFN/IFP)
  - Dérive `Année` + `Semestre` (Jan–Aug = S1, Sep–Dec = S2) depuis `Date début`
  - Renomme les colonnes vers le schéma OSCAR v2 :
    | Nouvel export AEC | OSCAR v3 (interne) |
    |---|---|
    | `Quantité d'inscriptions ` | `Nb. d'inscriptions` |
    | `Total des ventes` | `Recettes` |
    | `Qté heures` *ou* `Nombre total d'heures` | `Nombre d'heures prévues` |
    | `Qté heures vendues` | `Nombre total d'heures vendues (heures-étudiants)` (libellé UI : « Heures-élèves ») |
    | `Qté synchrones heures vendues` | `Heures synchrones vendues (heures-étudiants)` |
    | `Catégorie` | `Catégorie de cours` |
    | `Tranche d'âge` | `Tranche d'âge du cours` |
  - Agrège par `(Année, Semestre, Sede, Catégorie de cours)` → schéma 100% compatible avec le dashboard v2

### Modifications dans `dashboard_aec_v3.py`
- `detect_export_type()` reconnaît un type supplémentaire **`tous_les_cours`** (signature : `Quantité d'inscriptions` + `Total des ventes` + `Statut` + `Lieu du cours`/`Centre`)
- Le routeur d'imports appelle `parse_aec_export()` quand ce type est détecté
- Le mapping `Catégorie de cours → (Macro-catégorie, Sous-secteur, Secteur)` du fichier `category_mapping.csv` continue de s'appliquer
- Bandeau **« OSCAR v3 • NEW PARSER »** dans la sidebar pour identifier la version
- Title : **« OSCAR v3 »**

## Lancer localement

```bash
# v2 (production)
cd stats_aec_app
streamlit run dashboard_aec_v2.py

# v3 (test du nouveau parser)
cd stats_aec_app
streamlit run dashboard_aec_v3.py
```

## Déployer sur Streamlit Cloud

Crée une **deuxième app** Streamlit Cloud à partir du même repo, en pointant
sur **`dashboard_aec_v3.py`** (au lieu de `dashboard_aec_v2.py`). L'app v2
reste déployée séparément.

| App Streamlit | Fichier d'entrée |
|---|---|
| OSCAR (v2) | `dashboard_aec_v2.py` |
| OSCAR v3 (test) | `dashboard_aec_v3.py` |

## Tester le parser en CLI

```bash
cd stats_aec_app
python3 -c "
from aec_parser_v3 import parse_aec_export
df, stats = parse_aec_export(open('/path/to/export.xlsx', 'rb').read())
print(df.head())
print('Stats:', stats)
"
```

## À venir (TODO)

- Filtre niveaux de cours dans l'UI
- Inscriptions journalières / mensuelles (utilise `Date début` au lieu d'agréger)
- Statut configurable depuis la sidebar
- Date floor configurable
- Validation : comparer totaux entre import v2 (rapport-par-catégorie) et v3 (tous-les-cours) sur les mêmes années
