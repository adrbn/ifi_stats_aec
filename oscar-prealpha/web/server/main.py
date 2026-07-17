"""main.py — FastAPI backend for the OSCAR pre-alpha dashboard.

Endpoints:
  GET /api/health           -> {"status": "ok"}
  GET /api/snapshot         -> the snapshot (optionally filtered by ?year=&antennas=)
  GET /api/meta             -> snapshot.meta

On startup we load the precomputed fixtures/snapshot.json from disk (fast, fit
for serverless cold starts). The heavy engine lazy-loads only when /api/cours is
hit. The snapshot is loaded once into memory.
"""
from __future__ import annotations

import copy
import json
import os
from typing import List, Optional

from fastapi import Body, FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

HERE = os.path.dirname(os.path.abspath(__file__))
SNAPSHOT_PATH = os.path.join(HERE, "fixtures", "snapshot.json")

app = FastAPI(title="OSCAR API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory snapshot, populated at startup.
SNAPSHOT: dict = {}


def _load_snapshot_from_disk() -> dict:
    with open(SNAPSHOT_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_snapshot() -> dict:
    """Serverless: charge la fixture pré-calculée (rapide). engine lazy à la requête."""
    return _load_snapshot_from_disk()


@app.on_event("startup")
def _startup() -> None:
    global SNAPSHOT
    SNAPSHOT = _load_snapshot()


def _parse_antennas(antennas: Optional[str]) -> Optional[List[str]]:
    if not antennas:
        return None
    codes = [a.strip().upper() for a in antennas.split(",") if a.strip()]
    return codes or None


def _parse_years(years: Optional[str]) -> Optional[List[int]]:
    if not years:
        return None
    out = []
    for y in years.split(","):
        y = y.strip()
        if y.isdigit():
            out.append(int(y))
    return out or None


@app.get("/api/cours")
def cours(
    years: Optional[str] = Query(default=None),
    antennas: Optional[str] = Query(default=None),
    secteurs: Optional[List[str]] = Query(default=None),
    sousSecteurs: Optional[List[str]] = Query(default=None),
    macros: Optional[List[str]] = Query(default=None),
    categories: Optional[List[str]] = Query(default=None),
    niveaux: Optional[List[str]] = Query(default=None),
    ages: Optional[List[str]] = Query(default=None),
    periodes: Optional[List[str]] = Query(default=None),
    matieres: Optional[List[str]] = Query(default=None),
    ues: Optional[List[str]] = Query(default=None),
    mode: Optional[str] = Query(default="civil"),
):
    """Live, filter-aware Cours payload (multi-year + multi-antenna + cascading
    dimension filters + filtres orthogonaux niveau / tranche d'âge / période /
    matière / UE), computed on demand — same granularity as OSCAR Online.

    mode : "civil" (année civile) ou "school" (année scolaire)."""
    import engine

    try:
        return engine.compute(
            _parse_years(years), _parse_antennas(antennas),
            secteurs=secteurs, sousSecteurs=sousSecteurs, macros=macros, categories=categories,
            niveaux=niveaux, ages=ages, periodes=periodes, matieres=matieres, ues=ues,
            year_mode=("school" if mode == "school" else "civil"),
        )
    except Exception as e:  # noqa: BLE001
        print(f"[main] /api/cours compute failed ({e}); serving static snapshot.")
        return SNAPSHOT


def _filter_snapshot(snapshot: dict, year: Optional[int], antennas: Optional[List[str]]) -> dict:
    """Best-effort filtering. Never raises: unfiltered fields are passed through."""
    out = copy.deepcopy(snapshot)

    # Filter byAntenna by the requested antenna codes.
    if antennas:
        try:
            out["byAntenna"] = [r for r in out.get("byAntenna", []) if r.get("code") in antennas]
        except Exception:  # noqa: BLE001
            pass
        try:
            out["evolution"]["series"] = [
                s for s in out["evolution"].get("series", []) if s.get("code") in antennas
            ]
        except Exception:  # noqa: BLE001
            pass

    # Reflect the requested filters in the filters block (transparency for the UI).
    try:
        if year is not None:
            out.setdefault("filters", {})["year"] = year
        if antennas:
            out.setdefault("filters", {})["antennas"] = antennas
    except Exception:  # noqa: BLE001
        pass

    # NOTE: year-level filtering of kpis/sectors is not implemented because the
    # in-memory snapshot is pre-aggregated for the latest year only. We return the
    # unfiltered values for those fields rather than erroring (per spec).
    return out


_DATA_CACHE: dict = {}


@app.get("/api/data/{name}")
def data(name: str) -> dict:
    """Serve fixtures/{name}.json (profils, produits, ...). Cached in memory.

    Returns {"available": false, ...} when the file is missing, so the UI can
    render an honest 'load this export' state instead of erroring.
    """
    safe = "".join(c for c in name if c.isalnum() or c in ("-", "_"))
    if safe in _DATA_CACHE:
        return _DATA_CACHE[safe]
    path = os.path.join(HERE, "fixtures", f"{safe}.json")
    if not os.path.exists(path):
        return {"available": False, "name": safe, "reason": "no source file loaded"}
    with open(path, "r", encoding="utf-8") as f:
        payload = json.load(f)
    _DATA_CACHE[safe] = payload
    return payload


def _mapping_payload() -> dict:
    """Construit le payload du tableau d'équivalences (mapping courant = base +
    overrides), avec la liste des catégories présentes dans les données mais non
    mappées, et le flag d'éditabilité."""
    import engine
    import oscar_core as core
    import mapping_store

    # Réveille le moteur ET applique les overrides (KV/fichier) sur CATEGORY_MAPPING.
    engine.sync_mapping()
    df = engine.get_df()
    overrides = mapping_store.load_overrides()
    overridden = set(overrides.keys())
    rows = [
        {"categorie": c, "macro": v[0], "sousSecteur": v[1], "secteur": v[2],
         "override": c in overridden}
        for c, v in core.CATEGORY_MAPPING.items()
    ]
    rows.sort(key=lambda r: (r["secteur"], r["sousSecteur"], r["macro"], r["categorie"]))
    present = (
        sorted(df["Catégorie de cours"].dropna().astype(str).str.strip().unique().tolist())
        if "Catégorie de cours" in df.columns else []
    )
    mapped = {str(k).strip() for k in core.CATEGORY_MAPPING}
    unmapped = [c for c in present if c not in mapped]  # → NON RATTACHÉ
    return {
        "rows": rows,
        "sectorOrder": list(core.SECTOR_ORDER),
        "sousSecteurOrder": list(core.SOUS_SECTEUR_ORDER),
        "count": len(rows),
        "present": present,
        "unmapped": unmapped,
        "csvPath": "data/category_mapping.csv",
        "editable": mapping_store.is_writable(),
        "storage": mapping_store.backend(),
        "overridesCount": len(overridden),
    }


@app.get("/api/mapping")
def mapping() -> dict:
    """Tableau des équivalences catégorie → (macro-catégorie, sous-secteur,
    secteur). Mapping = socle (dict + CSV) + overrides éditables depuis le site
    (persistés en KV en prod / fichier en local). Sert l'onglet « Paramètres »."""
    try:
        return _mapping_payload()
    except Exception as e:  # noqa: BLE001
        return {"rows": [], "sectorOrder": [], "count": 0, "present": [], "unmapped": [],
                "editable": False, "error": str(e)[:200]}


@app.post("/api/mapping")
def mapping_edit(payload: dict = Body(default={})) -> dict:
    """Édite le tableau des correspondances depuis le site (protégé par la
    session — le middleware Next bloque les requêtes non authentifiées).

    Body : {action:"upsert", categorie, macro?, sousSecteur?, secteur}
        ou {action:"delete", categorie}

    Après écriture, on ré-applique le mapping (temps réel) → le prochain
    /api/cours reflète immédiatement la modification. La persistance survit aux
    redéploiements (KV) ou reste locale (fichier)."""
    import engine
    import mapping_store

    if not mapping_store.is_writable():
        return {"ok": False, "reason": "read_only",
                "message": "Persistance non configurée (KV absent et FS en lecture seule)."}

    action = str(payload.get("action", "upsert")).strip().lower()
    categorie = str(payload.get("categorie", "")).strip()
    if not categorie:
        return {"ok": False, "reason": "empty_category", "message": "Catégorie manquante."}

    try:
        if action == "delete":
            mapping_store.remove(categorie)
        else:
            secteur = str(payload.get("secteur", "")).strip()
            if not secteur:
                return {"ok": False, "reason": "empty_sector", "message": "Secteur manquant."}
            mapping_store.upsert(
                categorie,
                str(payload.get("macro", "")).strip(),
                str(payload.get("sousSecteur", "")).strip(),
                secteur,
            )
        # Application immédiate (recalcule les colonnes Secteur du df caché).
        engine.sync_mapping(force=True)
        return {"ok": True, **_mapping_payload()}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "reason": "error", "message": str(e)[:200]}


@app.post("/api/course-mapping")
def course_mapping_edit(payload: dict = Body(default={})) -> dict:
    """Assigne une catégorie à un COURS précis (Code cours → catégorie), pour
    rattacher un cours dont la catégorie AEC est vide/erronée — sans toucher au
    tableau catégorie→secteur. Protégé par la session (middleware Next).

    Body : {action:"upsert", code, categorie} | {action:"delete", code}

    Effet immédiat : la catégorie est réassignée et les secteurs recalculés
    (temps réel). Réversible : delete rétablit la catégorie AEC d'origine."""
    import engine
    import mapping_store

    if not mapping_store.is_writable():
        return {"ok": False, "reason": "read_only",
                "message": "Persistance non configurée (KV absent et FS en lecture seule)."}

    action = str(payload.get("action", "upsert")).strip().lower()
    code = str(payload.get("code", "")).strip()
    if not code:
        return {"ok": False, "reason": "empty_code", "message": "Code cours manquant."}

    try:
        if action == "delete":
            mapping_store.remove_course_override(code)
        else:
            categorie = str(payload.get("categorie", "")).strip()
            if not categorie:
                return {"ok": False, "reason": "empty_category", "message": "Catégorie manquante."}
            mapping_store.set_course_override(code, categorie)
        engine.sync_mapping(force=True)  # application immédiate
        return {"ok": True, "courseOverrides": mapping_store.load_course_overrides()}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "reason": "error", "message": str(e)[:200]}


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/warmup")
def warmup() -> dict:
    """Préchauffe la fonction serverless : charge le moteur (DataFrame cours +
    enrôlements) en mémoire pour éviter le cold start de ~13 s au 1er vrai appel.
    Public (route exclue de l'auth) — ne renvoie aucune donnée sensible, juste
    des compteurs. Pingée par le cron Vercel toutes les 5 min."""
    try:
        import engine
        df = engine.get_df()
        el = engine.get_eleves()
        return {"ok": True, "cours": int(len(df)), "eleves": int(len(el))}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": str(e)}


# --- Assistant LLM (API Albert / OpenAI-compatible) ----------------------------
ASSISTANT_SYSTEM = (
    "Tu es OSCAR, l'assistant analyste de données de l'Institut français Italie "
    "(réseau IFI, 4 antennes : IFM = Milano, IFF = Firenze, IFN = Napoli, "
    "IFP = Palermo ; « IFI » = total réseau).\n\n"
    "RÈGLE ABSOLUE : réponds UNIQUEMENT à partir du JSON fourni. N'invente JAMAIS "
    "un chiffre. Si l'information n'est pas dans le JSON, dis-le clairement.\n\n"
    "== CE QUE REPRÉSENTE LE JSON ==\n"
    "Le bloc `perimetre` indique le périmètre EXACT actuellement filtré par "
    "l'utilisateur : `annees` (liste), `mode_annee` (civil = année civile, ou "
    "scolaire = sept→août, libellé type 2024-25), `antennes`, et les filtres de "
    "dimension actifs (secteurs, sous_secteurs, macros, categories, niveaux). "
    "`annees_disponibles` liste TOUTES les années présentes dans les données "
    "(au-delà du filtre courant). Tous les autres chiffres portent sur ce "
    "périmètre filtré, PAS sur tout l'historique.\n\n"
    "== INDICATEURS DISPONIBLES (domaine Cours) ==\n"
    "inscriptions, élèves différents (Code Client distincts), cours (nombre), "
    "Qté heures (heures enseignées), heures-élèves (heures vendues), recettes (€), "
    "remplissage (= inscriptions / cours), nouveaux inscrits, réinscrits, "
    "panier/inscription et panier/personne (€). Le bloc `dictionnaire` en donne la "
    "définition. `totaux_IFI` = ces indicateurs sur le périmètre ; `par_antenne` "
    "et `par_secteur` = leur ventilation ; `evolution_par_annee` = série "
    "pluriannuelle par antenne.\n\n"
    "== VENTILATIONS FINES ==\n"
    "`ventilation_par_dimension` détaille le périmètre par secteur, sous_secteur, "
    "macro, categorie (la catégorie AEC brute du cours), niveau (CECRL), format "
    "(présentiel / en ligne / hybride) et tranche d'âge — chaque ligne porte "
    "inscriptions, cours, recettes, remplissage. Utilise-la pour toute question "
    "sur une catégorie, un niveau, un format ou un public précis.\n\n"
    "== SECTEURS (métier IFI) ==\n"
    "PROGRAMMÉS (cours collectifs au catalogue), PLATEFORMES (apprentissage en "
    "ligne autonome/tutoré), ECOLES (public scolaire : PCTO, classes découverte, "
    "matinées…), SUR MESURE (cours particuliers/petits groupes), SOCIÉTÉS "
    "(entreprises), et NON RATTACHÉ (cours dont la catégorie AEC est vide ou "
    "inconnue du mapping — anomalie de saisie ; le détail figure dans "
    "`diagnostics.non_rattache` si présent, avec nom du cours, antenne et période).\n\n"
    "== CE QUI N'EXISTE PAS ICI ==\n"
    "Le SEMESTRE n'est pas disponible (seulement l'année entière). Le domaine "
    "Cours n'a NI âge, NI genre, NI nationalité, NI motivation, NI taux "
    "d'abandon/satisfaction/réussite : ces données sont dans les onglets "
    "« Profils » (élèves), qui ne sont PAS dans ce JSON → si on te le demande, "
    "dis-le et renvoie l'utilisateur vers les onglets Profils.\n\n"
    "== MÉTHODE ==\n"
    "(1) Comprends la question. (2) Montre brièvement ton calcul/comparaison. "
    "(3) Donne le résultat chiffré final, formaté (milliers séparés, € pour les "
    "recettes, 1 décimale pour les ratios). Si la question vise une antenne/année/"
    "sous-catégorie hors du périmètre filtré, calcule ce que tu peux ET invite à "
    "affiner via les filtres en haut de page (Antennes, Année, « Affiner par "
    "dimension »). Réponds en français, concis et structuré."
)


@app.post("/api/assistant")
def assistant(payload: dict = Body(default={})) -> dict:
    """Assistant data en langage naturel via l'API Albert (Etalab, agents publics)
    ou tout endpoint OpenAI-compatible. Le front envoie {question, context} où
    context = sous-ensemble du snapshot (KPI, par antenne/secteur, évolution…).
    Renvoie {ok:false,reason:'no_key'} si non configuré → le front bascule sur le
    moteur déterministe local."""
    import json as _json
    import urllib.request as _u

    key = os.environ.get("ALBERT_API_KEY", "").strip()
    if not key:
        return {"ok": False, "reason": "no_key"}
    base = os.environ.get("ALBERT_BASE_URL", "https://albert.api.etalab.gouv.fr/v1").rstrip("/")
    model = os.environ.get("ALBERT_MODEL", "albert-large")
    question = str(payload.get("question", "")).strip()
    context = payload.get("context", {})
    history = payload.get("history", []) or []
    if not question:
        return {"ok": False, "reason": "empty"}

    # Messages = system + historique de la conversation (pour les questions de
    # suivi type « en %age ») + le tour courant (qui porte les données JSON).
    messages = [{"role": "system", "content": ASSISTANT_SYSTEM}]
    for h in history[-10:]:
        role = "assistant" if h.get("role") in ("assistant", "bot") else "user"
        content = str(h.get("content", "")).strip()[:2000]
        if content:
            messages.append({"role": role, "content": content})
    user = f"Données (JSON) du périmètre filtré :\n{_json.dumps(context, ensure_ascii=False)}\n\nQuestion : {question}"
    messages.append({"role": "user", "content": user})

    body = _json.dumps({
        "model": model,
        "messages": messages,
        "temperature": 0.1,
        "max_tokens": 700,
    }).encode("utf-8")
    req = _u.Request(
        f"{base}/chat/completions", data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    try:
        with _u.urlopen(req, timeout=90) as r:
            data = _json.loads(r.read().decode("utf-8"))
        answer = (data.get("choices") or [{}])[0].get("message", {}).get("content", "").strip()
        if not answer:
            return {"ok": False, "reason": "empty_response"}
        return {"ok": True, "answer": answer, "model": model}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "reason": "api_error", "error": str(e)[:200]}


@app.get("/api/meta")
def meta() -> dict:
    return SNAPSHOT.get("meta", {})


@app.get("/api/snapshot")
def snapshot(
    year: Optional[int] = Query(default=None),
    antennas: Optional[str] = Query(default=None),
) -> dict:
    codes = _parse_antennas(antennas)
    if year is None and codes is None:
        return SNAPSHOT
    return _filter_snapshot(SNAPSHOT, year, codes)
