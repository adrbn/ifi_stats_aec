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

from fastapi import FastAPI, Query
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
    mode: Optional[str] = Query(default="civil"),
):
    """Live, filter-aware Cours payload (multi-year + multi-antenna + cascading
    dimension filters), computed on demand — same granularity as OSCAR Online.

    mode : "civil" (année civile) ou "school" (année scolaire)."""
    import engine

    try:
        return engine.compute(
            _parse_years(years), _parse_antennas(antennas),
            secteurs=secteurs, sousSecteurs=sousSecteurs, macros=macros, categories=categories,
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
