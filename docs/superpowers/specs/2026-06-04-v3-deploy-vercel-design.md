# Déploiement v3 en ligne sur Vercel — Design

**Date :** 2026-06-04
**Statut :** spec à valider
**Sujet :** mettre la v3 (nouvelle UI) en ligne sur Vercel, avec upload de fichiers
comme la v2, auth par mot de passe partagé, et le comparateur v2/v3 sur le même site.

---

## 1. Contexte & vocabulaire

- **v2** = app Streamlit en production (`ifi-stats-aec.streamlit.app`). Gate par login
  bricolé. Données IFI internes.
- **v3** = nouvelle UI `oscar-prealpha/` : front **Next.js** + backend **FastAPI**
  (pandas réutilisé via `oscar_core.py`). Aujourd'hui **locale uniquement**, lecture
  seule sur des données pré-calculées, **sans upload ni auth**.

Objectif : un **seul site Vercel** servant la v3 (native) + un **comparateur** qui
embarque la v2 (en iframe, le temps de la transition). Endgame : la v3 atteint la
parité, on retire la v2 et l'iframe.

## 2. Objectifs (cette spec)

1. v3 en ligne sur Vercel (front + backend Python serverless), **un seul projet**.
2. **Upload** d'un fichier AEC (.xlsx/.zip) comme la v2 → calcul → affichage.
3. **Auth** : mot de passe partagé unique protégeant tout le site (données internes).
4. **Comparateur** v2/v3 hébergé sur le même site, derrière l'auth.

Hors scope (futur, mentionné pour cohérence) : auth fine (Google/email), persistance
des fichiers uploadés côté serveur, PWA/app native, parité totale puis retrait v2.

## 3. Architecture cible

Un projet Vercel unique :

```
Vercel (un seul domaine)
├── Next.js (front)                     ← UI v3 + page login + comparateur
│   └── middleware d'auth (cookie signé) ← protège pages + /api/*
└── Python serverless (FastAPI)  /api/* ← même origine, pas de CORS
    ├── GET  /api/cours|snapshot|meta    ← filtre le snapshot pré-calculé (léger)
    └── POST /api/upload   (NOUVEAU)     ← pandas sur le fichier déposé
```

- **Même origine** front ↔ API (`/api/*` sur le domaine Vercel) → plus de CORS, plus
  de variable `OSCAR_API_URL` en prod (le `rewrites` localhost reste pour le dev).
- FastAPI packagé en **fonction serverless Python** (pattern Vercel `api/index.py`
  exposant l'app ASGI).

## 4. Stratégie données (clé de la perf serverless)

Le serverless est **sans état entre requêtes**. On exploite le fait que l'API filtre
déjà un snapshot pré-calculé :

- **Données historiques** : `fixtures/snapshot.json` (31 Ko) est **embarqué** dans la
  fonction. Chaque `/api/cours` le charge (trivial) et le **filtre** → rapide, **aucun
  pandas** à la requête. Mêmes fixtures pour `produits.json` / `profils.json`.
- **Régénération** : `build_snapshot.py` (déjà existant) recalcule ces JSON depuis
  `data/`. Exécuté **hors-ligne** (localement ou via une étape de build CI) quand les
  données changent, puis committé. **pandas ne tourne donc jamais pour l'historique.**
- **Upload** : seul endroit où pandas s'exécute à la requête (sur le fichier de
  l'utilisateur). Voir §5.

→ Conséquence : la fonction « lecture » est légère ; seule la fonction « upload » embarque
pandas. (On peut les séparer en deux fonctions pour garder la lecture rapide/légère.)

## 5. Upload (nouveau, front + back)

**Backend — `POST /api/upload`** (fonction serverless avec pandas+openpyxl) :
1. Reçoit le fichier en multipart (.xlsx ou .zip).
2. `detect_export_type()` + parsing via la logique existante (`oscar_core` /
   `aec_parser_v3`) → DataFrame normalisé.
3. Construit un **Snapshot** (même schéma que `snapshot.json`).
4. Renvoie le Snapshot en JSON (traitement **en mémoire**, pas de persistance en M2).

**Frontend** : composant d'import (drag-drop / file input) → POST → met le Snapshot
retourné dans le store (TanStack Query / Zustand) → les vues s'affichent comme pour
l'historique. État « en cours / erreur / succès » géré explicitement.

**Persistance « fichiers sur serveur »** (demandée « à terme ») → **phase ultérieure** :
Vercel Blob (tier gratuit) ou stockage objet ; on stocke le fichier + le snapshot
dérivé, réouvrables (équivalent « fichiers récents » de la v2).

## 6. Auth — mot de passe partagé unique

- **Page de login** (Next.js) : un champ mot de passe.
- **Vérification** côté serveur (route handler Next) : compare au hash d'un secret
  stocké en **variable d'environnement Vercel** (`OSCAR_SHARED_PASSWORD_HASH`).
  Jamais de mot de passe en clair dans le repo.
- Sur succès : pose un **cookie httpOnly signé** (session). 
- **Middleware Next.js** : protège toutes les pages **et** les routes `/api/*`
  (les données ne sont jamais accessibles sans cookie valide).
- Déconnexion : efface le cookie.

> Évolution prévue (hors scope ici) : remplacer par Auth.js (Google restreint ou
> email+mot de passe) sans toucher au reste — le middleware reste le point d'entrée.

## 7. Comparateur v2/v3 sur le site

La coque existante (`oscar-prealpha/shell/index.html`) devient une **route Next**
(ex. `/compare`) déployée sur Vercel, **derrière l'auth** :
- onglet **v3** → l'app v3 (même domaine Vercel) ;
- onglet **v2** → iframe vers la v2 Streamlit live (inchangée).

> Ride UX connu : la v2 en iframe a **sa propre** page de login (Streamlit). L'utilisateur
> se connecte au site Vercel, puis re-saisit le login v2 dans l'onglet v2. Acceptable en
> transition ; disparaît quand la v2 est retirée.

## 8. Config & déploiement

- `vercel.json` : routage `/api/*` → fonction Python ; le reste → Next.js.
- `api/index.py` : point d'entrée ASGI exposant l'app FastAPI existante.
- `api/requirements.txt` : fastapi, pandas, numpy, openpyxl (pour `/api/upload`).
- Variables d'env Vercel : `OSCAR_SHARED_PASSWORD_HASH`, secret de signature de cookie.
- Front : en prod l'API est same-origin (`/api`) ; le `rewrites` vers `localhost:8000`
  reste pour le dev local.

**Ce que fait l'utilisateur (toi)** : créer un compte Vercel (gratuit), connecter le
repo `adrbn/ifi_stats_aec`, choisir `oscar-prealpha/web` comme racine, coller les 2
variables d'env, cliquer Deploy. Tout le reste est préparé dans le repo.

## 9. Jalons

- **M1 — En ligne + auth + historique** : v3 déployée sur Vercel, protégée par mot de
  passe, données historiques (snapshot pré-calculé), comparateur intégré. *Site public,
  sécurisé, utilisable.*
- **M2 — Upload** : `/api/upload` + composant d'import → parité « comme la v2 » sur
  l'analyse d'un fichier déposé.
- **M3 — Persistance** : stockage des fichiers/snapshots (Vercel Blob) → « fichiers
  récents ».
- **M4 — Parité & retrait v2** : la v3 couvre tout ; on supprime l'iframe et on retire
  la v2 Streamlit.

(Auth fine, PWA/app native : à planifier après, l'architecture les permet.)

## 10. Risques & mitigations

| Risque | Mitigation |
|---|---|
| Taille du bundle pandas sur fonction serverless (limite Vercel 250 Mo) | pandas+numpy+openpyxl ≈ bien < 250 Mo ; isoler l'upload dans sa propre fonction pour ne pas alourdir la lecture. À **vérifier au 1er déploiement**. |
| Durée d'exécution serverless (Hobby ~10–60 s) | L'upload d'un xlsx = quelques s ; régler `maxDuration`. Historique = filtrage léger, sans risque. |
| Cold start de la fonction upload | Acceptable (action ponctuelle, l'utilisateur attend comme en v2). |
| Snapshot pré-calculé qui se périme quand `data/` change | `build_snapshot.py` rejoué + committé (manuel, ou étape de build CI). |
| Données exposées sans auth | Middleware protège pages **et** `/api/*` dès M1. |
| Double login v2 (iframe) | Transitoire ; résolu au retrait de la v2 (M4). |

## 11. Coût

Vercel **Hobby = gratuit** (suffisant pour l'usage interne). Surveiller les limites de
fonctions ; passage Pro seulement si besoin (durées plus longues, protection de
déploiement intégrée).

## 12. Décisions actées

- Hébergement : **tout Vercel** (front + Python serverless). Pas de Render.
- Auth : **mot de passe partagé unique** (env var hashée) pour M1.
- v2 : **reste sur Streamlit Cloud**, embarquée en iframe ; retirée à terme (M4).
- Données : **snapshot pré-calculé embarqué** ; pandas uniquement à l'upload.
