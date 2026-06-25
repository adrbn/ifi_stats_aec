<img src="oscar-icon.png" alt="OSCAR" width="88" />

# OSCAR — Outil de Suivi des Cours et d'Analyse du Réseau

Dashboard analytique pour l'Institut français Italia (données AEC).

---

## Vocabulaire des versions (à lire en premier)

Le repo contient **deux UIs distinctes** de la même donnée, plus une app desktop archivée.
Pour lever toute ambiguïté, voici les termes utilisés partout :

| Nom | Ce que c'est | Techno | Où ça tourne | État |
|---|---|---|---|---|
| **v2** | App Streamlit historique | Streamlit (Python) | [ifi-stats-aec.streamlit.app](https://ifi-stats-aec.streamlit.app) | ✅ **prod, déployée** |
| **v3** | Nouvelle UI (la plus aboutie) | Next.js + FastAPI | **Vercel** (serverless) | ✅ **déployée, protégée par mot de passe** |
| *(desktop)* | Ancienne app native OSCAR (licences RSA) | PyInstaller | — | 📦 **archivée** (voir plus bas) |

> ⚠️ **Piège de nommage historique** : le fichier `dashboard_aec_v2.py` était étiqueté « v3.0 »
> dans d'anciennes docs. Ce « v3 »-là désignait la **génération du parser AEC** (lecture du
> nouvel export « Tous les cours »), **pas** l'UI. Dans ce README, **v2 = l'app Streamlit**
> et **v3 = l'app Next.js déployée sur Vercel**. C'est le vocabulaire qui fait foi.

> 🛠️ **Les deux UIs sont alimentées différemment.** La v2 lit les ZIP annuels « rapport par
> catégorie » dans `data/`. La v3 lit un cache **par cours** (`cache_cours.xlsx`, format « Tous
> les cours ») et le recalcule en direct. Voir les sections dédiées.

---

## v2 — App Streamlit

Point d'entrée : **`dashboard_aec_v2.py`** (à la racine). Contient toute la logique
de calcul (pandas) et le parser AEC inliné. Données dans `data/` (ZIP annuels).

### Déploiement
Streamlit Cloud exécute `dashboard_aec_v2.py` à la racine.
**Chaque `git push origin main` redéploie automatiquement.**

### Lancer en local
```bash
pip install -r requirements.txt
streamlit run dashboard_aec_v2.py
```

### Fonctionnalités
- Analyse multi-années et multi-sedi (IFM Milano, IFF Firenze, IFN Napoli, IFP Palermo)
- Vues : Panoramica, IFI Global, par secteur, comparaisons, Assistant IA
- Upload Excel/ZIP/CSV, fichiers récents réouvrables, données pré-chargées depuis `data/`
- Interface FR/IT, mode nuit/jour, export PDF/Excel
- Double pipeline : « rapport par catégorie » (vues principales) **et** « Tous les cours »
  (onglet *Fiches de cours* séparé), + profils clients, catalogue produits, activité par période

---

## v3 — App Next.js + FastAPI (déployée sur Vercel)

Vit entièrement dans [`oscar-prealpha/web/`](oscar-prealpha/web/). C'est l'UI la plus aboutie.

### Architecture de déploiement (Vercel)
- **Frontend** : Next.js 14 (App Router) + Tailwind + Recharts + react-three-fiber.
- **Backend** : FastAPI servi comme **fonction serverless Python** via
  [`web/api/index.py`](oscar-prealpha/web/api/index.py) (importe `app` depuis
  `web/server/main.py`). Tout `/api/*` (sauf `/api/auth/*`) y est routé — voir
  [`web/vercel.json`](oscar-prealpha/web/vercel.json).
- **Même origine** en prod : pas de CORS. En dev, `/api/*` est proxifié vers
  `http://localhost:8000` (voir [`web/next.config.mjs`](oscar-prealpha/web/next.config.mjs)).
- **Auth** : middleware ([`web/middleware.ts`](oscar-prealpha/web/middleware.ts)) qui exige un
  cookie de session JWT signé sur toutes les routes sauf `/login`, `/api/auth/login`,
  `/api/warmup`. Mot de passe vérifié contre `OSCAR_PASSWORD_SHA256`, cookie signé avec
  `OSCAR_SESSION_SECRET` (voir [`web/.env.local.example`](oscar-prealpha/web/.env.local.example)).
- **Build Vercel** : [`web/vercel-build.sh`](oscar-prealpha/web/vercel-build.sh) copie `data/` →
  `server/data/` puis lance `next build`. Le backend serverless embarque `server/**`
  (`includeFiles` dans `vercel.json`), dont les caches de données.

### Comment la v3 obtient ses données (IMPORTANT)
- Le frontend appelle **`GET /api/cours`** ([`web/lib/api.ts`](oscar-prealpha/web/lib/api.ts)),
  qui **recalcule en direct** le payload pour les filtres demandés via
  [`web/server/engine.py`](oscar-prealpha/web/server/engine.py) (`engine.compute`).
- Source de vérité = **`web/server/data/new_cours/cache_cours.xlsx`** : l'export AEC
  « Cours > Tous les cours » (1 ligne = 1 cours), parsé par
  [`aec_parser_v3.py`](oscar-prealpha/web/server/aec_parser_v3.py) (statuts Ouvert / Fermé à
  l'inscription / En attente ; date début ≥ 2022-09-01 ; Sede, Année et Semestre dérivés).
  Le moteur charge ce dataframe **une fois** (cache mémoire) — un redéploiement/restart
  recharge les nouvelles données.
- Un second cache **`cache_eleves.xlsx`** (Code Client × Code cours) alimente l'indicateur
  *Élèves différents* (compte distinct) et le *Panier / personne*.
- Ces deux fichiers sont **commités** (force-trackés dans `web/server/.gitignore`) pour être
  embarqués sur Vercel.
- `web/server/fixtures/snapshot.json` est un **fallback statique** (régénérable via
  `build_snapshot.py`), servi seulement si le calcul live échoue. Les ZIP annuels de `data/`
  ne sont **plus** la source de la v3 (ils restent la source de la v2).

### Mettre à jour les données (ex. compléter l'année 25-26)
1. Exporter depuis AEC « Cours > Tous les cours » (tous centres) → un `.xlsx`.
2. **Fusionner avec l'historique** (un export ne couvre que l'année courante ; un remplacement
   brut effacerait les années précédentes) :
   ```bash
   python merge_cours.py \
     oscar-prealpha/web/server/data/new_cours/cache_cours.xlsx \
     "aec export cours 25.26.xlsx" \
     cache_cours_merged.xlsx \
     2025-09-01            # cutoff = rentrée de l'année rafraîchie
   ```
   Le script garde l'historique (< cutoff) et prend l'année courante complète (≥ cutoff).
3. Remplacer le cache puis (optionnel) régénérer le fixture de secours :
   ```bash
   cp cache_cours_merged.xlsx oscar-prealpha/web/server/data/new_cours/cache_cours.xlsx
   python oscar-prealpha/web/server/build_snapshot.py
   ```
4. `git push` → Vercel redéploie. (Pour rafraîchir *Élèves différents* / *Panier / personne*,
   il faut aussi régénérer `cache_eleves.xlsx` — voir « Outils d'export AEC ».)

### Fonctionnalités v3
- **Cours** : Synthèse, Par antenne, Secteurs, Répartition, Année vs année, Rentabilité,
  Évolutions, Graphiques, Carte 3D du réseau.
- **Profils** (données réelles) : Synthèse, Démographie, Nationalités, Motivation.
- **Produits** (données réelles) : Catalogue, Types, Tarifs.
- Sélecteur d'indicateur (inscriptions, élèves différents, cours, heures, remplissage,
  recettes, **panier / inscription**, **panier / personne**…), filtres en cascade
  (année/antenne/secteur…), bascule **année civile / scolaire**, Assistant IA (API Albert),
  copie d'un graphique en image (presse-papiers), page `/compare` (toggle v2 ⇄ v3).

### Lancer la v3 en local (deux process)
```bash
# 1) Backend FastAPI — http://localhost:8000
cd oscar-prealpha/web/server && ./run.sh

# 2) Frontend Next.js — http://localhost:3000
cd oscar-prealpha/web && npm install && npm run dev
```
Détails : [`oscar-prealpha/README.md`](oscar-prealpha/README.md) et
[`oscar-prealpha/web/server/README.md`](oscar-prealpha/web/server/README.md).

---

## Comparer v2 et v3 côte à côte

Deux options :
- **Page intégrée `/compare`** dans la v3 ([`web/app/compare/page.tsx`](oscar-prealpha/web/app/compare/page.tsx)) :
  toggle façon Apple entre la v2 (embarquée en live depuis Streamlit Cloud) et la v3.
- **Coque standalone locale** ([`oscar-prealpha/shell/index.html`](oscar-prealpha/shell/index.html)
  + `start-compare.sh`) qui sert les deux dans des iframes persistantes (chaque version garde
  son état). `cd oscar-prealpha && ./start-compare.sh` puis http://localhost:8080.

---

## Format des fichiers d'entrée AEC

- **v3** : export « Cours > Tous les cours » (1 ligne = 1 cours, ~154 colonnes), feuille `AEC`.
- **v2** : « rapport par catégorie » (un fichier par sede/année, ex. `export AEC 2024 IFM.xlsx`),
  ou ZIP annuel `exports_AEC_YYYY_annuel.zip` ; accepte aussi le format « Tous les cours »
  (onglet *Fiches de cours*), les profils clients (CSV) et le catalogue produits (XLSX).

---

## Outils d'export AEC (scraping Playwright)

Scripts à la racine qui récupèrent les exports depuis la plateforme AEC :
- [`export_eleves_par_classe.py`](export_eleves_par_classe.py) — exporte le rapport
  « Cours > Rapports > Par Classe » (1 ligne = 1 élève × 1 cours, avec Code Client), un fichier
  par année. Base de l'indicateur *Élèves différents*.
- [`merge_eleves.py`](merge_eleves.py) — fusionne les `eleves_par_classe_*.xlsx` en
  `cache_eleves.xlsx` et le copie côté serveur v3 (prod Vercel).
- [`merge_cours.py`](merge_cours.py) — fusionne un nouvel export « Tous les cours » avec
  l'historique de `cache_cours.xlsx` (voir « Mettre à jour les données »).

> ⚠️ **À savoir** : `export_eleves_par_classe.py` importe `aec_login` et `export_cours_aec`
> (login + export de base), qui **ne sont pas commités** dans ce repo. Il faut donc disposer de
> ces deux modules localement pour relancer les exports. `playwright` n'est pas non plus dans
> `requirements.txt` (à installer séparément).
>
> 💡 **Limite « +1000 résultats »** : le bandeau AEC « ce rapport contient plus de 1000
> résultats » est un avertissement **d'affichage** ; l'export, lui, contient toutes les lignes
> (vérifié : exports > 1000 lignes OK). Un export « par antenne » plutôt que « tous centres »
> n'est donc **pas nécessaire** pour éviter une troncature — une donnée incomplète vient plutôt
> d'un export pris trop tôt dans le cycle (cours pas encore tous publiés).

---

## Backups & archives (tout vit dans git)

| Réf git | Contenu |
|---|---|
| tag `backup-2026-06-25` | Snapshot de `main` avant la passe « chargement 25-26 + panier + fix copie graphiques ». |
| `archive/desktop-oscar` | App desktop OSCAR (launcher, keygen, `license_validator`, `oscar.spec`, CI), + `dashboard_aec_v2_legacy_backup.py` et l'ancien `aec_parser_v3.py` racine. |
| `backup-restore-attempt-2026-05-27` | Ancienne tentative de restauration (conservée). |

Pour ressortir un fichier archivé :
```bash
git checkout archive/desktop-oscar -- <chemin/du/fichier>
```

---

## Confidentialité

- **v2** : analyses côté serveur Streamlit ; données importées en mémoire de session, aucun
  stockage persistant.
- **v3** : déployée sur Vercel, **protégée par mot de passe** ; les données (caches AEC
  agrégés/anonymisés au niveau cours) sont recalculées côté fonction serverless. Pas de données
  nominatives exposées dans l'UI au-delà des comptes agrégés.

---

© Institut français Italia — Usage interne uniquement
