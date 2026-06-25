# OSCAR v3 — backend FastAPI

Backend de la v3. Il **recalcule en direct** la donnée statistique depuis le cache AEC
« Tous les cours » et la sert via une petite API JSON. En production il tourne comme
**fonction serverless Vercel** (`../api/index.py` importe `main:app`).

## Lancer en local

```bash
./run.sh
```
Crée un `.venv`, installe `requirements.txt`, lance `uvicorn main:app --reload --port 8000`.

Endpoints (base `http://localhost:8000`) :

| Méthode | Chemin | Description |
|--------|--------|-------------|
| GET | `/api/cours` | **Payload live** recalculé pour les filtres (`years`, `antennas`, `secteurs`…, `yearMode=civil\|school`). C'est ce que consomme l'UI. |
| GET | `/api/data/{name}` | Domaines Profils / Produits (`fixtures/{name}.json`). |
| GET | `/api/meta` | Bloc `meta` (années, antennes, mode). |
| GET | `/api/snapshot` | Fixture statique `fixtures/snapshot.json` (legacy / fallback). |
| GET | `/api/assistant` `POST` | Assistant IA (API Albert, repli local déterministe). |
| GET | `/api/warmup` | Préchauffage (cold start serverless). |
| GET | `/api/health` | `{"status": "ok"}`. |

**Démarrage** : `main.py` charge `fixtures/snapshot.json` du disque au boot (fallback). Le
calcul réel est **paresseux** : au premier `/api/cours`, `engine.py` charge le dataframe une
fois (`build_snapshot.load_all_years()`) et le met en cache mémoire (`_DF`). Un restart/redeploy
recharge les données.

Pour (re)générer le fixture de secours :
```bash
python3 build_snapshot.py        # → fixtures/snapshot.json
python3 build_profils.py         # → fixtures/profils.json
python3 build_produits.py        # → fixtures/produits.json
```

## Source de données (à jour)

- **Cours** : `data/new_cours/cache_cours.xlsx` — export AEC « Cours > Tous les cours »
  (1 ligne = 1 cours), parsé par `aec_parser_v3.parse_aec_export` (statuts Ouvert / Fermé à
  l'inscription / En attente ; `Date début` ≥ 2022-09-01 ; Sede/Année/Semestre dérivés ;
  `Année scolaire` ajoutée pour le mode scolaire). **Remplace** l'ancien pipeline « ZIP annuels
  rapport-par-catégorie » (le dict `ANNUAL_ZIPS` est du code mort).
- **Élèves différents** : `data/new_cours/cache_eleves.xlsx` (Code Client × Code cours), joint
  sur « Code cours ». Absent ⇒ l'indicateur (et *Panier / personne*) sont masqués/0.
- **Profils** : `../../data/export_417433918_clients_nat_23_24_25_26.csv` (`build_profils.py`).
- **Produits** : les 4 `../../data/export_*_produits_IF*.xlsx` (`build_produits.py`).
- `category_mapping.csv` : mapping catégorie → (Macro, Sous-secteur, Secteur).

Les caches `cache_cours.xlsx` / `cache_eleves.xlsx` sont **force-trackés** (`.gitignore`) pour
être embarqués sur Vercel.

## Réutilisé vs nouveau

- `oscar_core.py` — fonctions pandas copiées de `../../dashboard_aec_v2.py` (sans `st.*`).
  Mapping catégories, ordre secteurs, couleurs/coords antennes, pipeline d'agrégation,
  rentabilité (ARPI), etc.
- `aec_parser_v3.py` — parser « Tous les cours » ; **chargeur de production** de la v3.
- `engine.py` — recalcul live par filtre (KPI, par antenne, secteurs, évolution, YoY,
  rentabilité, indicateurs par secteur/antenne, heatmap, flux). Registre des indicateurs :
  `INDICATORS` (dont `panier_inscr` et `panier_pers`, ratios non additifs).
- `build_snapshot.py` — agrège le fixture statique de secours dans le schéma du dashboard.
- `main.py` — app FastAPI (CORS permissif pour `localhost:3000` en dev ; même origine en prod).

## À noter

- `meta.source == "computed"` ; `meta.years` reflète les années réellement présentes dans la
  donnée (actuellement 2022→2026).
- Indicateurs « ratio » (remplissage, paniers) : non additifs → le total IFI n'est pas la somme
  des antennes mais la valeur KPI globale (géré côté front).
- Le mode `yearMode=school` remplace la colonne `Année` par `Année scolaire` dans tout le
  pipeline (filtres, KPI, évolution, YoY, ventilations).
