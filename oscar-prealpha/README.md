# OSCAR — l'application (Next.js + FastAPI, déployée sur Vercel)

L'UI OSCAR, **déployée sur Vercel** et **protégée par mot de passe**. Tout vit dans
`oscar-prealpha/`.

> Pour le pipeline de données, voir le [README principal](../README.md).
> ℹ️ L'ancienne UI Streamlit (« v2 ») et son comparateur `/compare` ont été retirés en
> juillet 2026 : c'est désormais la seule version.

## Stack

| Couche | Choix | Notes |
|-------|--------|-------|
| **Calcul** | Python / pandas | Fonctions pures dans `web/server/oscar_core.py` (héritées de l'ancienne app Streamlit, dépouillées de `st.*`). |
| **Backend** | FastAPI | API JSON ; **recalcul en direct** par filtre via `web/server/engine.py` (`/api/cours`). En prod = **fonction serverless** `web/api/index.py`. |
| **Frontend** | Next.js 14 (App Router) + TS | |
| **Styling** | Tailwind + tokens OSCAR | IBM Plex Sans, neutres ardoise, accent bleu IFI, radius 6px. |
| **Charts** | Recharts | SVG, grille discrète, tabular-nums. |
| **3D / WebGL** | react-three-fiber + drei | « Carte du réseau » : 4 antennes en piliers (hauteur ∝ inscriptions). |
| **State / data** | Zustand (filtres) + TanStack Query (fetch/cache) | |
| **Motion** | Framer Motion | Micro-interactions. |

## Déploiement (Vercel)

- `web/vercel.json` — fonction Python `api/index.py` (`includeFiles: server/**`) + rewrite de
  `/api/*` (sauf `/api/auth/*`) vers la fonction. Auth via `web/middleware.ts` (cookie JWT).
- `web/vercel-build.sh` — copie `../../data` → `server/data/` puis `next build`.
- Variables d'env : `OSCAR_PASSWORD_SHA256`, `OSCAR_SESSION_SECRET`, et l'assistant
  (`ALBERT_API_KEY` / `ALBERT_BASE_URL` / `ALBERT_MODEL`). Voir `web/.env.local.example`.

## Données

Le frontend appelle **`/api/cours`** → `engine.compute()` recalcule à la volée depuis
**`web/server/data/new_cours/cache_cours.xlsx`** (export « Tous les cours » parsé par
`aec_parser_v3.py`) + **`cache_eleves.xlsx`** (élèves différents). `fixtures/snapshot.json` est
un **fallback statique** ; si le calcul live échoue, le frontend renvoie un état « hors-ligne »
(aucune donnée — pas de « données démo »). Détails : `web/server/README.md` et le
[README principal](../README.md).

## Navigation

- **Rail de navigation** à gauche — domaines (Cours / Profils / Produits) et sous-vues.
- **Barre de filtres** persistante en haut — année (civile/scolaire), antennes, fil d'Ariane,
  bouton Assistant.

## Lancer en local

Deux process, backend d'abord :

```bash
# 1) Backend (FastAPI) — http://localhost:8000
cd oscar-prealpha/web/server && ./run.sh

# 2) Frontend (Next.js) — http://localhost:3000
cd oscar-prealpha/web && npm install && npm run dev
```
En dev, `/api/*` est proxifié vers le backend (`web/next.config.mjs`).

## Ce qui est en place (données réelles)

- **Cours** : Synthèse, Par antenne, Secteurs, Répartition, Année vs année, Rentabilité,
  Évolutions, Graphiques, Carte 3D. KPI (inscriptions, élèves différents, cours, heures,
  remplissage, recettes, **panier/inscription**, **panier/personne**) avec deltas N-1.
- **Profils** : Synthèse, Démographie, Nationalités, Motivation (`build_profils.py` →
  `fixtures/profils.json`).
- **Produits** : Catalogue, Types, Tarifs (`build_produits.py` → `fixtures/produits.json`).
- **Paramètres › Équivalences** : table catégorie → secteur éditable en direct (persistée en KV).
- Assistant IA (API Albert, repli local déterministe), mode année civile/scolaire,
  **mode confidentiel** (masque les recettes, actif par défaut), et sur chaque panneau un
  menu **⋮** : copier l'image · export PNG · export CSV · plein écran.

## Arborescence

```
oscar-prealpha/
  web/
    api/index.py         point d'entrée serverless Vercel (importe server/main.py:app)
    server/              backend FastAPI
      oscar_core.py        fonctions pandas pures + mapping catégorie → secteur
      aec_parser_v3.py     parser « Tous les cours » (chargeur de prod)
      engine.py            recalcul live par filtre (/api/cours)
      mapping_store.py     overrides des équivalences (KV en prod, fichier en dev)
      build_snapshot.py    (re)génère fixtures/snapshot.json (fallback)
      build_profils.py     → fixtures/profils.json
      build_produits.py    → fixtures/produits.json
      main.py              endpoints: /api/cours /api/mapping /api/course-mapping
                                       /api/data/{name} /api/meta /api/snapshot
                                       /api/assistant /api/warmup /api/health
      data/new_cours/      cache_cours.xlsx, cache_eleves.xlsx (embarqués Vercel)
      fixtures/            snapshot.json, profils.json, produits.json
    app/                 routes (welcome + dashboard + paramètres + login + vues)
    components/          KPI, charts, table, filtres, rail, modal IA, carte 3D
    lib/                 types, client API, fallback, formatters, store
```
