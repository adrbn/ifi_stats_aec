# OSCAR — Outil de Suivi des Cours et d'Analyse du Réseau

**v3.0** · Dashboard analytique pour l'Institut français Italia (données AEC)

---

## Deux modes de déploiement

### 1. Streamlit Cloud (test en ligne)

Chaque push sur `main` met automatiquement à jour l'app Streamlit Cloud.
Le dossier `DEPLOYMENT STREAMLIT/` est la source de vérité pour ce déploiement.

> **Workflow** : modifier `dashboard_aec_v2.py` → copier dans `DEPLOYMENT STREAMLIT/` → `git push origin main` → Streamlit Cloud redéploie automatiquement.

### 2. Application desktop OSCAR (distribution clients)

Builds natifs macOS / Windows / Linux générés via GitHub Actions.
Voir la section [Releases GitHub](#releases-github) ci-dessous.

---

## Fonctionnalités

- Analyse multi-années et multi-sedes (Milano, Firenze, Napoli, Palermo, Roma)
- Vues : Panoramica, IFI Global, Par secteur, Comparaisons, Assistant IA
- Upload Excel individuel ou ZIP multi-fichiers
- **Fichiers récents** : les sessions uploadées sont sauvegardées localement et réouvrables
- Interface FR/IT, mode nuit/jour
- Export PDF/Excel des graphiques
- Licence hors-ligne (RSA-2048) — pas de connexion internet requise

---

## Format des fichiers d'entrée

```
export AEC semestre 1 2024 IFM.xlsx
export AEC semestre 2 2024 IFF.xlsx
...
```

Ou une archive ZIP contenant plusieurs de ces fichiers :

```
exports_AEC_2024.zip
├── export AEC semestre 1 2024 IFM.xlsx
├── export AEC semestre 1 2024 IFF.xlsx
└── export AEC semestre 2 2024 IFM.xlsx
```

---

## Releases GitHub

### Builds automatiques (chaque push sur `main`)

GitHub Actions compile les trois plateformes à chaque push.
Les artefacts (DMG, EXE, AppImage) sont disponibles 30 jours dans l'onglet **Actions** du repo.

### Créer une Release officielle

Pour publier une release avec les installateurs en téléchargement :

```bash
git tag v3.0.1
git push origin v3.0.1
```

GitHub Actions crée automatiquement la release avec les trois fichiers attachés :
- `OSCAR-3.0.1-macOS.dmg`
- `OSCAR-3.0.1-Windows-Setup.exe`
- `OSCAR-3.0.1-Linux-x86_64.AppImage`

---

## Installation desktop (utilisateurs finaux)

### 1. Installer l'application

| Plateforme | Fichier | Procédure |
|---|---|---|
| macOS 12+ | `OSCAR-*.dmg` | Ouvrir le DMG → glisser OSCAR dans Applications |
| Windows 10/11 | `OSCAR-*-Windows-Setup.exe` | Exécuter l'installateur (admin non requis) |
| Linux x86_64 | `OSCAR-*-Linux-x86_64.AppImage` | `chmod +x OSCAR-*.AppImage && ./OSCAR-*.AppImage` |

### 2. Placer le fichier de licence

Déposez `oscar_license.lic` dans le dossier correspondant à votre OS :

| OS | Emplacement |
|---|---|
| macOS | `~/Library/Application Support/OSCAR/oscar_license.lic` |
| Windows | `%APPDATA%\OSCAR\oscar_license.lic` |
| Linux | `~/.config/oscar/oscar_license.lic` |

Sans licence valide, l'application refusera de démarrer.

---

## Gestion des licences (administrateurs)

### Générer une licence client

```bash
# Requis : oscar_private_key.pem (ne jamais committer ni distribuer)
python keygen.py \
  --customer "Institut français de Naples" \
  --org IFN \
  --email admin@ifnapoli.it \
  --expiry 2027-12-31 \
  --output licenses/ifn_2027.lic
```

Mode interactif : `python keygen.py -i`

### Générer la paire de clés RSA (une seule fois, déjà fait)

```bash
python generate_keys.py
# → oscar_private_key.pem  (PRIVÉE — ne jamais partager)
# → public key embedded in license_validator.py
```

La clé publique est embarquée dans `license_validator.py`.
La clé privée est dans `oscar_private_key.pem` (gitignorée — **ne jamais committer**).

---

## Développement local

### Lancer en mode Streamlit (sans licence)

```bash
pip install -r requirements.txt
streamlit run dashboard_aec_v2.py
```

### Lancer en mode desktop (avec licence)

```bash
pip install -r requirements.txt
python launcher.py
```

### Builder manuellement

```bash
# macOS
bash build/build_mac.sh        # → dist/OSCAR-*.dmg

# Windows (sur Windows)
build\build_windows.bat        # → dist/OSCAR-*-Windows-Setup.exe

# Linux
bash build/build_linux.sh      # → dist/OSCAR-*-Linux-x86_64.AppImage
```

Prérequis macOS : `pip install pyinstaller pillow && brew install create-dmg`

---

## Architecture

```
stats_aec_app/
├── dashboard_aec_v2.py          # App Streamlit principale (6500+ lignes)
├── launcher.py                  # Entry point desktop (licence + WebView + Streamlit)
├── license_validator.py         # Validation RSA-2048 hors-ligne
├── keygen.py                    # CLI génération de licences (dev only)
├── oscar.spec                   # PyInstaller spec (3 plateformes)
├── oscar_private_key.pem        # Clé privée RSA (gitignorée !)
├── requirements.txt             # Dépendances Python
├── DEPLOYMENT STREAMLIT/        # Snapshot pour Streamlit Cloud
│   ├── dashboard_aec_v2.py
│   ├── requirements.txt
│   └── IFI_noir_logo.png
├── build/
│   ├── build_mac.sh             # Script build macOS
│   ├── build_windows.bat        # Script build Windows
│   ├── build_linux.sh           # Script build Linux
│   ├── convert_icon.py          # PNG → ICO (Windows)
│   ├── streamlit_config/        # Config Streamlit embarquée dans le bundle
│   └── installers/windows/
│       └── oscar_installer.iss  # Script Inno Setup
└── .github/workflows/
    └── build.yml                # CI/CD GitHub Actions
```

---

## Confidentialité

L'application ne transmet aucune donnée à des serveurs externes.
Les analyses sont effectuées localement. La validation de licence est entièrement hors-ligne.

---

© Institut français Italia — Usage interne uniquement
