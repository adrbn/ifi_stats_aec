"""mapping_store.py — persistance des OVERRIDES du tableau de correspondances
(catégorie → macro / sous-secteur / secteur), éditables depuis le site.

Deux back-ends, choisis automatiquement :

  • PRODUCTION (Vercel, FS en lecture seule) → magasin KV REST compatible
    Upstash / Vercel KV, via les variables d'environnement :
        KV_REST_API_URL   (ex. https://xxx.upstash.io)
        KV_REST_API_TOKEN
    Lecture à chaque requête (fusionnée au mapping) → effet TEMPS RÉEL ;
    écriture durable → survit aux redéploiements.

  • DÉVELOPPEMENT / local (FS accessible en écriture) → fichier JSON
        server/data/mapping_overrides.json

Format des overrides (identique dans les deux back-ends) :
    { "NOM CATEGORIE": {"macro": "...", "sousSecteur": "...", "secteur": "..."}, ... }

Toutes les fonctions sont tolérantes aux pannes : en cas d'erreur (KV
indisponible, JSON corrompu…) elles renvoient un dict vide plutôt que de lever,
pour que l'app continue de tourner sur le mapping par défaut.
"""
from __future__ import annotations

import hashlib
import json
import os
import urllib.request

_HERE = os.path.dirname(os.path.abspath(__file__))
_LOCAL_PATH = os.path.join(_HERE, "data", "mapping_overrides.json")
_KV_KEY = "oscar:mapping_overrides"
# Overrides au niveau d'un COURS précis (Code cours → Catégorie de cours) : sert
# à rattacher un cours dont la catégorie AEC est vide/erronée, sans toucher au
# tableau catégorie→secteur.
_COURSE_LOCAL_PATH = os.path.join(_HERE, "data", "course_overrides.json")
_COURSE_KEY = "oscar:course_overrides"


# ---------------------------------------------------------------------------
# Back-end selection
# ---------------------------------------------------------------------------

def _kv() -> tuple[str, str] | None:
    """(base_url, token) si un KV REST est configuré, sinon None."""
    url = os.environ.get("KV_REST_API_URL", "").strip().rstrip("/")
    token = os.environ.get("KV_REST_API_TOKEN", "").strip()
    return (url, token) if url and token else None


def backend() -> str:
    return "kv" if _kv() else "file"


def is_writable() -> bool:
    """Vrai si l'on peut persister des modifications (KV configuré, ou dossier
    local accessible en écriture)."""
    if _kv():
        return True
    d = os.path.dirname(_LOCAL_PATH)
    try:
        return os.path.isdir(d) and os.access(d, os.W_OK)
    except OSError:
        return False


# ---------------------------------------------------------------------------
# KV REST (commandes Upstash-compatibles : POST body = ["CMD", ...args])
# ---------------------------------------------------------------------------

def _kv_command(args: list[str]) -> object:
    conf = _kv()
    if not conf:
        raise RuntimeError("KV non configuré")
    base, token = conf
    body = json.dumps(args).encode("utf-8")
    req = urllib.request.Request(
        base, data=body,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=8) as r:
        payload = json.loads(r.read().decode("utf-8"))
    return payload.get("result")


def _kv_get(key: str = _KV_KEY) -> dict:
    raw = _kv_command(["GET", key])
    if not raw:
        return {}
    try:
        data = json.loads(raw) if isinstance(raw, str) else raw
        return data if isinstance(data, dict) else {}
    except (ValueError, TypeError):
        return {}


def _kv_set(overrides: dict, key: str = _KV_KEY) -> None:
    _kv_command(["SET", key, json.dumps(overrides, ensure_ascii=False)])


# ---------------------------------------------------------------------------
# Fichier local
# ---------------------------------------------------------------------------

def _file_get(path: str = _LOCAL_PATH) -> dict:
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _file_set(overrides: dict, path: str = _LOCAL_PATH) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(overrides, fh, ensure_ascii=False, indent=2)
    os.replace(tmp, path)  # écriture atomique


# ---------------------------------------------------------------------------
# API publique
# ---------------------------------------------------------------------------

def _clean(v: object) -> str:
    return str(v).strip() if v is not None else ""


def load_overrides() -> dict:
    """Renvoie le dict des overrides {catégorie: {macro, sousSecteur, secteur}}."""
    try:
        raw = _kv_get() if _kv() else _file_get()
    except Exception:  # noqa: BLE001 — jamais bloquant
        return {}
    out: dict = {}
    for cat, val in (raw or {}).items():
        if isinstance(val, dict):
            out[str(cat)] = {
                "macro": _clean(val.get("macro")),
                "sousSecteur": _clean(val.get("sousSecteur")),
                "secteur": _clean(val.get("secteur")),
            }
    return out


def save_overrides(overrides: dict) -> None:
    if _kv():
        _kv_set(overrides)
    else:
        _file_set(overrides)


def upsert(categorie: str, macro: str, sous_secteur: str, secteur: str) -> dict:
    """Ajoute ou met à jour une correspondance. Renvoie le dict complet à jour."""
    cat = _clean(categorie)
    if not cat:
        raise ValueError("catégorie vide")
    overrides = load_overrides()
    overrides[cat] = {
        "macro": _clean(macro) or _clean(secteur),
        "sousSecteur": _clean(sous_secteur) or _clean(secteur),
        "secteur": _clean(secteur) or "NON RATTACHÉ",
    }
    save_overrides(overrides)
    return overrides


def remove(categorie: str) -> dict:
    """Supprime une correspondance override (retour au mapping par défaut).
    Renvoie le dict complet à jour."""
    cat = _clean(categorie)
    overrides = load_overrides()
    overrides.pop(cat, None)
    save_overrides(overrides)
    return overrides


def version_of(overrides: dict) -> str:
    """Empreinte stable des overrides → sert à détecter un changement et
    déclencher le recalcul des secteurs (temps réel)."""
    blob = json.dumps(overrides or {}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha1(blob.encode("utf-8")).hexdigest()


def to_tuples(overrides: dict) -> dict:
    """Convertit {cat:{macro,sousSecteur,secteur}} → {cat:(macro,sous,secteur)}
    pour injection dans oscar_core.CATEGORY_MAPPING."""
    return {
        cat: (v.get("macro", ""), v.get("sousSecteur", ""), v.get("secteur", ""))
        for cat, v in (overrides or {}).items()
    }


# ---------------------------------------------------------------------------
# Overrides au niveau d'un COURS (Code cours → Catégorie de cours)
# ---------------------------------------------------------------------------

def load_course_overrides() -> dict:
    """Renvoie {code_cours: catégorie} — assigne une catégorie à un cours précis
    (utile quand la catégorie AEC est vide/erronée)."""
    try:
        raw = _kv_get(_COURSE_KEY) if _kv() else _file_get(_COURSE_LOCAL_PATH)
    except Exception:  # noqa: BLE001
        return {}
    return {str(k): _clean(v) for k, v in (raw or {}).items() if _clean(v)}


def save_course_overrides(overrides: dict) -> None:
    if _kv():
        _kv_set(overrides, _COURSE_KEY)
    else:
        _file_set(overrides, _COURSE_LOCAL_PATH)


def set_course_override(code: str, categorie: str) -> dict:
    """Assigne (ou met à jour) la catégorie d'un cours précis. Renvoie le dict."""
    c = _clean(code)
    cat = _clean(categorie)
    if not c:
        raise ValueError("code cours vide")
    if not cat:
        raise ValueError("catégorie vide")
    ovr = load_course_overrides()
    ovr[c] = cat
    save_course_overrides(ovr)
    return ovr


def remove_course_override(code: str) -> dict:
    ovr = load_course_overrides()
    ovr.pop(_clean(code), None)
    save_course_overrides(ovr)
    return ovr
