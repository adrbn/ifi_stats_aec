# OSCAR pre-alpha — FastAPI backend

Self-contained backend for the OSCAR dashboard rebuild. It computes a real
statistical snapshot from the IFI annual AEC exports and serves it over a small
JSON API.

## How to run

```bash
./run.sh
```

This creates a `.venv`, installs `requirements.txt`, and starts
`uvicorn main:app --reload --port 8000`.

Endpoints (base `http://localhost:8000`):

| Method | Path             | Description |
|--------|------------------|-------------|
| GET    | `/api/health`    | `{"status": "ok"}` |
| GET    | `/api/snapshot`  | Full snapshot JSON. Optional `?year=&antennas=IFM,IFF` filters `byAntenna` / `evolution`. |
| GET    | `/api/meta`      | The `meta` block of the snapshot. |

The snapshot is loaded once at startup. On startup the app *recomputes* the
snapshot from real data via `build_snapshot.build()`; if that fails it serves
`fixtures/snapshot.json` from disk.

To (re)generate the on-disk snapshot manually:

```bash
python3 build_snapshot.py
```

## Reused vs new

**Reused / ported from the original Streamlit app**
- `oscar_core.py` — pure pandas functions copied out of
  `../../dashboard_aec_v2.py`, with all `streamlit` / `st.*` / `t()` calls
  removed. Includes the category mapping, sector ordering, antenna colors and
  coordinates, and the processing pipeline (`load_excel`, `process_data`,
  `aggregate_by_sector`, `create_ifi_totals`, `calculate_yoy_by_sede`, etc.).
  The original `st.session_state` "unknown categories" tracking was replaced
  with a module-level dict so the functions stay pure. The original Streamlit
  app is untouched.
- `aec_parser_v3.py` — copied verbatim from `../../aec_parser_v3.py` so the
  backend is self-contained. (Targets the newer per-course export format with a
  `Date début` column; not used by the annual-zip pipeline below, but available
  for future per-course features.)

**New**
- `build_snapshot.py` — loads the 2023/2024/2025 annual zip exports +
  `category_mapping.csv` from `../../data/`, runs the `oscar_core` pipeline, and
  writes `fixtures/snapshot.json` in the exact dashboard schema.
- `main.py` — FastAPI app (permissive CORS for `http://localhost:3000`).
- `run.sh`, `requirements.txt`.

## Computed vs mocked

The current snapshot is **fully computed** (`meta.source == "computed"`) from the
real annual AEC exports:

- `kpis`, `byAntenna`, `sectors`, `evolution` are all derived from the parsed
  data for the latest available year (2025) with year-over-year deltas.
- `meta.years` reflects the years actually present in the data (2023–2025).

Per-field fallback: if any single field fails to compute, `build_snapshot`
substitutes the value from the pristine fixture (`fixtures/snapshot.fixture.json`)
for that field and sets `meta.source = "partial"`. If the data cannot be loaded
at all, the existing `fixtures/snapshot.json` is left in place and served as-is.

### Known limitations / left to wire

- The annual zip exports are the classic AEC *category-report* format. The
  newer per-course exports (handled by `aec_parser_v3.parse_aec_export`, which
  needs a `Date début` column) are **not** wired into the snapshot yet; the
  parser is included for future use.
- The `sectors` table maps internal sector codes to fixture display labels;
  `SUR MESURE` is surfaced under the fixture's `INTENSIFS` column and `SOCIÉTÉS`
  under `ENTREPRISES` (see `SECTOR_LABELS` in `build_snapshot.py`).
- API-side filtering: `?antennas=` filters `byAntenna` and `evolution.series`.
  `?year=` is reflected in the `filters` block but does **not** re-aggregate
  `kpis`/`sectors` (the in-memory snapshot is pre-aggregated for the latest
  year). Unfiltered fields are returned rather than erroring, per spec.
- The `kpis` "Heures prévues" delta is reported as `0 / stable` (the prior-year
  planned-hours baseline is not tracked separately).
