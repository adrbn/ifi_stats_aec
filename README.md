# OSCAR — Outil de Suivi des Cours et d'Analyse du Réseau

Dashboard analytique pour l'Institut français Italia (données AEC).

---

## Vocabulaire des versions (à lire en premier)

Le repo contient **deux UIs distinctes** de la même donnée, plus une app desktop archivée.
Pour lever toute ambiguïté, voici les termes utilisés partout :

| Nom | Ce que c'est | Techno | Où ça tourne | État |
|---|---|---|---|---|
| **v2** | L'app actuelle, en production | Streamlit (Python) | [ifi-stats-aec.streamlit.app](https://ifi-stats-aec.streamlit.app) | ✅ **prod, déployée** |
| **v3** | Nouvelle UI (test d'un nouvel UI) | Next.js + FastAPI | local seulement (`:3000` web / `:8000` api) | 🧪 **pré-alpha, locale** |
| *(desktop)* | Ancienne app native OSCAR (licences RSA) | PyInstaller | — | 📦 **archivée** (voir plus bas) |

> ⚠️ **Piège de nommage historique** : le fichier `dashboard_aec_v2.py` était étiqueté « v3.0 »
> dans d'anciennes docs. Ce « v3 »-là désignait la **génération du parser AEC** (lecture du
> nouvel export « Tous les cours »), **pas** l'UI. Dans ce README, **v2 = l'app Streamlit**
> et **v3 = la nouvelle app Next.js**. C'est le vocabulaire qui fait foi.

---

## v2 — App Streamlit (production)

Point d'entrée : **`dashboard_aec_v2.py`** (à la racine). Contient toute la logique
de calcul (pandas) et le parser AEC inliné. Données dans `data/`.

### Déploiement
Streamlit Cloud est configuré pour exécuter `dashboard_aec_v2.py` à la racine.
**Chaque `git push origin main` redéploie automatiquement.** Aucun dossier ou étape
de copie intermédiaire (l'ancien `DEPLOYMENT STREAMLIT/` a été supprimé — il était vide
et périmé).

### Lancer en local
```bash
pip install -r requirements.txt
streamlit run dashboard_aec_v2.py
```

### Fonctionnalités
- Analyse multi-années et multi-sedes (Milano, Firenze, Napoli, Palermo, Roma)
- Vues : Panoramica, IFI Global, Par secteur, Comparaisons, Assistant IA
- Upload Excel individuel ou ZIP multi-fichiers ; fichiers récents réouvrables
- Interface FR/IT, mode nuit/jour, export PDF/Excel
- Parser AEC : voir [`README_V3.md`](README_V3.md) pour le détail du mapping de colonnes

---

## v3 — Nouvelle UI Next.js (pré-alpha, locale)

Expérience locale et **non destructive** qui reconstruit l'UI hors de Streamlit.
Vit entièrement dans [`oscar-prealpha/`](oscar-prealpha/). Ne touche rien de la v2.

- `oscar-prealpha/web/` — Next.js 14 + Tailwind + Recharts + react-three-fiber
- `oscar-prealpha/api/` — FastAPI qui **réutilise** la logique pandas (`oscar_core.py`,
  copiée du dashboard et nettoyée des appels `st.*`)

### Lancer en local (deux process)
```bash
# 1) Backend FastAPI — http://localhost:8000
cd oscar-prealpha/api && ./run.sh

# 2) Frontend Next.js — http://localhost:3000
cd oscar-prealpha/web && npm install && npm run dev
```
Détails et choix de stack : [`oscar-prealpha/README.md`](oscar-prealpha/README.md).

> 🚧 La v3 n'est pas encore déployée en ligne. Son architecture d'upload/import et de
> déploiement public est un chantier ouvert (sujet de design dédié à venir).

---

## Format des fichiers d'entrée AEC

```
export AEC semestre 1 2024 IFM.xlsx
export AEC semestre 2 2024 IFF.xlsx
```
Ou une archive ZIP contenant plusieurs de ces fichiers (`exports_AEC_2024.zip`).

---

## Backups & archives (tout vit dans git, plus aucun fichier `_backup`)

| Branche | Contenu |
|---|---|
| `archive/desktop-oscar` | Snapshot complet pré-nettoyage : app desktop OSCAR (launcher, keygen, `license_validator`, `oscar.spec`, `build/`, CI `build.yml`), + l'ancien `dashboard_aec_v2_legacy_backup.py` et le module orphelin `aec_parser_v3.py`. Tout y est récupérable. |
| `backup-restore-attempt-2026-05-27` | Ancienne tentative de restauration (conservée). |

Pour ressortir un fichier archivé :
```bash
git checkout archive/desktop-oscar -- <chemin/du/fichier>
```

> L'app desktop native a été sortie du tronc actif pour clarifier le repo. Elle n'est
> plus maintenue mais reste intégralement récupérable via la branche ci-dessus.

---

## Confidentialité

Les analyses v2 sont effectuées côté serveur Streamlit ; aucune donnée n'est transmise
à des serveurs tiers au-delà de l'hébergement de l'app.

---

© Institut français Italia — Usage interne uniquement
