# OSCAR — parser AEC (génération « v3 »)

> ⚠️ Ici « v3 » désigne la **génération du parser AEC**, pas l'UI. Ce document
> concerne l'app **Streamlit (v2)**. Pour le vocabulaire des versions, voir le
> [README principal](README.md). La nouvelle UI Next.js (que l'on appelle « v3 »)
> est documentée dans [`oscar-prealpha/README.md`](oscar-prealpha/README.md).

L'app Streamlit utilise le **nouveau parser** qui supporte l'export
AEC « Cours > Tous les cours » (un fichier = N cours, une ligne par cours)
en plus du format historique « rapport par catégorie ».

L'ancien dashboard (sans ce parser) est **conservé dans la branche
`archive/desktop-oscar`** sous le nom `dashboard_aec_v2_legacy_backup.py`,
récupérable si besoin.

## Fichiers

| Fichier | Rôle |
|---|---|
| `dashboard_aec_v2.py` | **Production** — point d'entrée Streamlit (la logique du parser y est inlinée : `detect_export_type()`, etc.) |
| `README_V3.md` | Ce fichier |

> Note : le module autonome `aec_parser_v3.py` et `dashboard_aec_v2_legacy_backup.py`
> ont été archivés (branche `archive/desktop-oscar`) — le dashboard ne les importait pas
> (logique du parser inlinée). La v3 Next.js garde sa propre copie dans `oscar-prealpha/web/server/`.

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

## Revenir à l'ancien dashboard (si besoin)

```bash
# Récupérer l'ancien dashboard depuis la branche d'archive
git checkout archive/desktop-oscar -- dashboard_aec_v2_legacy_backup.py
mv dashboard_aec_v2_legacy_backup.py dashboard_aec_v2.py
git commit -am "revert: rollback to legacy v2 dashboard"
git push
```

## À venir (TODO)

- Filtre niveaux de cours dans l'UI
- Inscriptions journalières / mensuelles (utilise `Date début` au lieu d'agréger)
- Statut configurable depuis la sidebar
- Date floor configurable
- Validation : comparer totaux entre import v2 (rapport-par-catégorie) et v3 (tous-les-cours) sur les mêmes années
