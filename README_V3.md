# OSCAR v3 — parser pour le nouvel export AEC

OSCAR utilise désormais le **nouveau parser v3** qui supporte l'export
AEC « Cours > Tous les cours » (un fichier = N cours, une ligne par cours)
en plus du format historique « rapport par catégorie ».

L'ancienne version est **conservée dans git** comme `dashboard_aec_v2_legacy_backup.py`
pour pouvoir y revenir si besoin (`git log` + `git checkout`).

## Fichiers

| Fichier | Rôle |
|---|---|
| `dashboard_aec_v2.py` | **Production** — point d'entrée Streamlit (contient le code v3) |
| `aec_parser_v3.py` | Module parseur pour le nouvel export AEC |
| `dashboard_aec_v2_legacy_backup.py` | Backup de l'ancien dashboard (sans le parser v3) — non déployé |
| `README_V3.md` | Ce fichier |

## Ce que fait `aec_parser_v3.py`

- Lit le fichier `.xlsx` brut (feuille `AEC` ou première feuille)
- Filtre par statut (par défaut : `Ouvert`, `Fermé à l'inscription`, `En attente`)
- Filtre par date début ≥ 2022-09-01
- Dérive `Sede` depuis « Lieu du cours » (IFM/IFF/IFN/IFP)
- Dérive `Année` + `Semestre` (Jan–Aug = S1, Sep–Dec = S2) depuis `Date début`
- Renomme les colonnes vers le schéma OSCAR :

| Nouvel export AEC | OSCAR (interne) |
|---|---|
| `Quantité d'inscriptions ` | `Nb. d'inscriptions` |
| `Total des ventes` | `Recettes` |
| `Qté heures` *ou* `Nombre total d'heures` | `Nombre d'heures prévues` |
| `Qté heures vendues` | `Nombre total d'heures vendues (heures-étudiants)` (libellé UI : « Heures-élèves ») |
| `Qté synchrones heures vendues` | `Heures synchrones vendues (heures-étudiants)` |
| `Catégorie` | `Catégorie de cours` |
| `Tranche d'âge` | `Tranche d'âge du cours` |

- Agrège par `(Année, Semestre, Sede, Catégorie de cours)` → schéma 100% compatible avec le dashboard existant

## Détection automatique

`detect_export_type()` reconnaît l'ancien et le nouveau format :
- Nouveau (`tous_les_cours`) : présence simultanée de `Quantité d'inscriptions`, `Total des ventes`, `Statut` et `Lieu du cours`/`Centre`
- Ancien (`rapport_categories`) : présence de `Catégorie de cours`

Tu peux charger les deux formats en même temps si besoin (mais en pratique on en charge un seul à la fois).

## Repère visuel

Petit badge gris **« v3 parser »** dans la sidebar à côté du logo IFI pour confirmer que le parser v3 est actif.

## Déploiement Streamlit Cloud

**Aucun changement nécessaire** côté Streamlit Cloud — l'app pointait déjà
sur `dashboard_aec_v2.py`, qui contient maintenant le code v3.

Au prochain push, Streamlit Cloud redéploie automatiquement.

## Revenir à l'ancienne version (si besoin)

```bash
cd stats_aec_app
git mv dashboard_aec_v2.py dashboard_aec_v3_active.py
git mv dashboard_aec_v2_legacy_backup.py dashboard_aec_v2.py
git commit -m "revert: rollback to legacy v2 dashboard"
git push
```

## À venir (TODO)

- Filtre niveaux de cours dans l'UI
- Inscriptions journalières / mensuelles (utilise `Date début` au lieu d'agréger)
- Statut configurable depuis la sidebar
- Date floor configurable
- Validation : comparer totaux entre import v2 (rapport-par-catégorie) et v3 (tous-les-cours) sur les mêmes années
