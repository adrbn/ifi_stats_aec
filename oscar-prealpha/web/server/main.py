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
    mode: Optional[str] = Query(default="civil"),
):
    """Live, filter-aware Cours payload (multi-year + multi-antenna + cascading
    dimension filters + filtre niveau orthogonal), computed on demand — same
    granularity as OSCAR Online.

    mode : "civil" (année civile) ou "school" (année scolaire)."""
    import engine

    try:
        return engine.compute(
            _parse_years(years), _parse_antennas(antennas),
            secteurs=secteurs, sousSecteurs=sousSecteurs, macros=macros, categories=categories,
            niveaux=niveaux,
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


@app.get("/api/mapping")
def mapping() -> dict:
    """Tableau des équivalences catégorie → (macro-catégorie, sous-secteur,
    secteur). LECTURE SEULE (le FS serverless est en lecture seule) : la source
    éditable reste data/category_mapping.csv (dict + override CSV). Sert l'onglet
    « Paramètres » de la v3."""
    try:
        import engine
        import oscar_core as core
        # Réveille le moteur → applique les overrides CSV sur CATEGORY_MAPPING.
        df = engine.get_df()
        rows = [
            {"categorie": c, "macro": v[0], "sousSecteur": v[1], "secteur": v[2]}
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
            "count": len(rows),
            "present": present,
            "unmapped": unmapped,
            "csvPath": "data/category_mapping.csv",
            "editable": False,
        }
    except Exception as e:  # noqa: BLE001
        return {"rows": [], "sectorOrder": [], "count": 0, "present": [], "unmapped": [], "error": str(e)[:200]}


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
    "(réseau IFI : IFM Milano, IFF Firenze, IFN Napoli, IFP Palermo). Tu réponds "
    "UNIQUEMENT à partir des données JSON fournies, qui correspondent au PÉRIMÈTRE "
    "ACTUELLEMENT FILTRÉ par l'utilisateur (années + antennes sélectionnées). "
    "Procède ainsi : (1) comprends la question, (2) montre brièvement tes étapes de "
    "calcul / comparaison, (3) donne le résultat chiffré final. "
    "Le JSON contient : totaux_IFI, par_antenne, par_secteur, evolution_par_annee, "
    "et 'ventilation_par_dimension' = le détail du périmètre filtré par secteur, "
    "sous_secteur, macro, categorie (ex. type de cours / français général…), niveau, "
    "format (présentiel/en ligne) et tranche d'âge — chaque ligne a inscriptions, "
    "cours, recettes, remplissage. Utilise cette ventilation pour les questions sur "
    "une catégorie / un niveau / un type de cours précis. "
    "IMPORTANT — si la question vise une antenne précise, une année précise ou une "
    "sous-catégorie, et que le périmètre filtré ne correspond pas exactement, "
    "calcule ce que tu peux à partir des données ET invite l'utilisateur à affiner "
    "via les filtres en haut de page (boutons Antennes, Année, et « Affiner par "
    "dimension ») puis à reposer la question. "
    "Le SEMESTRE n'est pas disponible (seulement l'année entière — civile ou "
    "scolaire) : signale-le si on te le demande. "
    "Si une métrique n'existe pas (taux d'abandon, satisfaction, âge, nationalité…), "
    "dis-le et liste les indicateurs disponibles. N'invente JAMAIS de chiffre. "
    "Réponds en français, concis et structuré."
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
