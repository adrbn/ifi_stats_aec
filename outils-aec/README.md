# Outils AEC → OSCAR (données cours)

Chaîne qui récupère les cours depuis AEC et alimente le tableau de bord OSCAR.
Elle s'utilise par un double-clic — `Recuperer cours AEC.command` (macOS) ou
`Recuperer cours AEC.bat` (Windows) — qui ouvre une petite fenêtre avec les logs
en direct.

## La chaîne

| Étape | Script | Rôle |
|---|---|---|
| 1 | `export_cours_aec.py` | export d'AEC, **une année par tirage** (AEC tronque si on demande tout l'historique d'un coup) |
| 2 | `update_cache.py` | fusion dans `cache_cours.xlsx` : les années fraîches **remplacent** les anciennes, le reste est conservé |
| 3 | `oscar_cours.py` | indicateurs (`oscar_indicateurs_cours.xlsx`) |
| 4 | `controle_incoherences.py` | liste des cours dont la période ne correspond pas aux dates → `incoherences_dates.xlsx` |

`oscar_tool.py` est la fenêtre qui enchaîne ces quatre étapes ; `aec_login.py`
gère la connexion.

## Correction ciblée d'un cours

Corriger un cours dans AEC change souvent sa **période** — parfois d'un an. On
ne sait alors plus quelle période retirer. Ces deux scripts contournent le
problème :

```bash
python reexport_ids.py --ids 4592,9128   # ou sans --ids : reprend incoherences_dates.xlsx
python patch_cache_ids.py --dry-run      # montre les changements
python patch_cache_ids.py                # les applique
```

`reexport_ids.py` coche **tous les centres et tout l'historique des périodes**,
puis retrouve chaque cours par son n° de classe via la recherche générale — la
période n'a donc plus d'importance. `patch_cache_ids.py` remplace **uniquement
ces lignes** dans le cache (upsert sur « Classe N° »), avec sauvegarde et
garde-fous ; `--supprimer 7477` retire un cours effacé dans AEC, qui resterait
sinon en fantôme jusqu'au prochain export complet.

⚠ Ne pas utiliser `update_cache.py` pour ça : il raisonne par **année entière**,
donc un fichier d'une ligne effacerait toute l'année.

## Publication vers OSCAR

`publier_oscar_pr.py` (bouton « Publier sur OSCAR ») crée une branche depuis
`upstream/main`, y copie le cache, régénère `snapshot.json`, et ouvre une Pull
Request. Le dépôt local revient ensuite à son état initial. `--dry-run` fait
tout sauf le push et la PR.

Rien n'est codé en dur : le dépôt vient de `OSCAR_REPO`, le propriétaire du fork
est déduit du remote `origin`, et l'identité des commits est celle du poste (ou
`OSCAR_GIT_NAME` / `OSCAR_GIT_EMAIL`).

## Installation

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt      # Windows : .venv\Scripts\pip
.venv/bin/playwright install chromium
```

Chromium doit être **visible** (`headless=False`) : la connexion à AEC se fait à
la main la première fois, puis le profil persistant
(`%LOCALAPPDATA%`/`~/Library` → `aec_exporter_profil_chrome`) la mémorise. Sur
macOS, `aec_login.py` peut aussi lire les identifiants dans le Trousseau :

```bash
security add-generic-password -U -s aec-ifitalie -a "prenom.nom@exemple.fr" -w
```

Le mot de passe n'est jamais dans le code.

## Ce que produit la chaîne

Les fichiers atterrissent dans `data/new_cours/`, **à côté des scripts** — ils ne
sont pas versionnés ici (seul `cache_cours.xlsx` l'est, dans
`oscar-prealpha/web/server/data/new_cours/`, via la PR de publication).
`aec_state.json` contient une session AEC authentifiée : il est explicitement
ignoré par `.gitignore` et ne doit jamais être publié.

## Deux pièges d'AEC à connaître

**La colonne « Période » dépend du filtre actif au moment de l'export.** Un même
cours ressort « 2022-DÉCEMBRE » quand on tire l'année 2022, et « 2023-JANVIER »
quand toutes les périodes sont cochées. L'export année par année biaise donc
cette colonne vers l'année tirée — d'où des faux positifs dans le contrôle
qualité. `reexport_ids.py`, qui coche tout, donne la valeur de référence.

**Un cours peut porter plusieurs périodes** (« 2024-MARS, 2024-JUILLET ») : le
libellé complet est conservé tel quel plutôt que d'en choisir un arbitrairement.
