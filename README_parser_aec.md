# OSCAR — parser de l'export AEC

Documentation du parser qui transforme l'export brut **AEC « Cours > Tous les cours »**
(1 fichier = N cours, **une ligne par cours**) en schéma interne OSCAR.

> 📍 **La copie qui fait foi** : [`oscar-prealpha/web/server/aec_parser_v3.py`](oscar-prealpha/web/server/aec_parser_v3.py).
> C'est le chargeur de production : l'app lit en continu
> `oscar-prealpha/web/server/data/new_cours/cache_cours.xlsx` via ce parser, puis
> `engine.py` recalcule à la demande. Voir le [README principal](README.md).
>
> 🏷️ Le suffixe « v3 » du nom de fichier désigne la **génération du parser** (support du
> format « Tous les cours »), pas l'UI. Le badge **« v3 parser »** dans la barre latérale
> confirme qu'il est actif.

## Ce que fait le parser

- Lit le `.xlsx` brut (feuille `AEC` ou première feuille)
- Filtre par statut (par défaut : `Ouvert`, `Fermé à l'inscription`, `En attente`)
- Filtre par date de début ≥ 2022-09-01
- Dérive `Sede` depuis « Lieu du cours » (IFM / IFF / IFN / IFP)
- Dérive `Année` + `Semestre` (jan–août = S1, sep–déc = S2) depuis `Date début`
- Dérive l'**année scolaire** (sep N → août N+1) pour la bascule civile / scolaire de l'UI
- Renomme les colonnes vers le schéma OSCAR :

| Export AEC | OSCAR (interne) |
|---|---|
| `Quantité d'inscriptions ` ⚠️ *espace final* | `Nb. d'inscriptions` |
| `Total des ventes` | `Recettes` |
| `Qté heures` *ou* `Nombre total d'heures` | `Nombre d'heures prévues` |
| `Qté heures vendues` | `Nombre total d'heures vendues (heures-étudiants)` (libellé UI : « Heures-élèves ») |
| `Qté synchrones heures vendues` | `Heures synchrones vendues (heures-étudiants)` |
| `Catégorie` | `Catégorie de cours` |
| `Tranche d'âge` | `Tranche d'âge du cours` |

> ⚠️ **Piège connu** : l'export AEC nomme la colonne `Quantité d'inscriptions ` **avec un
> espace final**. Toujours faire `df.columns = [c.strip() for c in df.columns]` avant toute
> fusion / `reindex`, sinon les inscriptions passent à `NaN` silencieusement.

## Grain

Le parser sait agréger par `(Année, Semestre, Sede, Catégorie de cours)`, mais la
production l'appelle en **grain par cours** (`aggregate=False`) : `engine.py` agrège
ensuite lui-même selon les filtres. C'est ce qui permet de ventiler par niveau, format
ou tranche d'âge, et de basculer année civile / scolaire à la volée.

## Détection automatique

`detect_export_type()` reconnaît deux formats :
- **`tous_les_cours`** (actuel) : présence simultanée de `Quantité d'inscriptions`,
  `Total des ventes`, `Statut` et `Lieu du cours` / `Centre`
- **`rapport_categories`** (historique) : présence de `Catégorie de cours`

## Mapping catégorie → secteur

Le parser ne fait **pas** le rattachement aux secteurs : c'est
`oscar_core.map_category_to_levels()` (dict par défaut + surcharges CSV + overrides
éditables depuis l'onglet **Paramètres › Équivalences**, persistés en KV).

## À venir (TODO)

- Inscriptions journalières / mensuelles (exploiter `Date début` sans agréger)
- Statut et date plancher configurables depuis l'UI
