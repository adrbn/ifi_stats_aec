# OSCAR — pre-alpha (Next.js rebuild)

A **local, non-destructive** experiment that rebuilds the OSCAR UI outside Streamlit,
implementing the design system from the Claude Design handoff bundle
(`OSCAR — Wireframes & Design System.html`).

> Nothing in the original app is touched. `../dashboard_aec_v2.py`, `../aec_parser_v3.py`,
> the Streamlit deployment and the data files are all untouched. This lives entirely in
> `oscar-prealpha/`.

## Why this stack

You asked for "the best, free, better than the current UI" and named Next.js / Tailwind /
Three.js. The constraint was **reuse the existing calculation** (9,479 lines of pandas) rather
than rewrite it. So:

| Layer | Choice | Rationale |
|-------|--------|-----------|
| **Calculation** | Python / pandas (reused) | The pure data functions from `dashboard_aec_v2.py` were *copied* (not imported — the original executes Streamlit at import) into `api/oscar_core.py`, stripped of `st.*`. Zero logic rewritten. |
| **Backend** | FastAPI + uvicorn | Thin JSON API over the reused functions. Computes a real snapshot from `../data/` at startup. |
| **Frontend** | Next.js 14 (App Router) + TypeScript | Production-grade, free, full control to match the design pixel-for-pixel. |
| **Styling** | Tailwind, themed with the OSCAR design tokens | `design-system.css` ported verbatim into `web/app/globals.css` + `tailwind.config.ts`. IBM Plex Sans, slate neutrals, IFI-blue accent, 6px radius. |
| **Charts** | Recharts | SVG, themed to the design's Plotly rules (subtle grid, tabular-nums, no chart title). |
| **3D / WebGL** | react-three-fiber + drei (Three.js) | The "Carte du réseau" — 4 antennas as glowing pillars (height ∝ inscriptions) on a 3D map, linked to the IFI hub. |
| **State / data** | Zustand (filters) + TanStack Query (fetch + cache) | |
| **Motion** | Framer Motion | Micro-interactions only (the design forbids decorative animation). |

### The other options that were on the table (all free)
- **FastAPI + HTMX + Jinja** — lightest, server-rendered, no JS build. Max reuse, less "telling".
- **Plotly Dash** — pure Python, lowest migration friction, reuses Plotly directly.
- **Reflex / NiceGUI** — pure-Python reactive → React/Vue.

Next.js was chosen per your request for the highest UI ceiling (motion + WebGL).

## Navigation

Hybrid of the design's Direction **C** + **A**, picked as the most intuitive for 11+ multidimensional views:
- **Left nav rail** — domains (Cours / Profils / Produits) and their sub-views, always visible.
- **Persistent top filter bar** — year segment + antenna toggles that hold across every view, plus a breadcrumb and the Assistant button.

## Run it

Two processes. Backend first:

```bash
# 1) Backend (FastAPI) — http://localhost:8000
cd oscar-prealpha/api && ./run.sh

# 2) Frontend (Next.js) — http://localhost:3000
cd oscar-prealpha/web && npm install && npm run dev
```

Open the frontend; `/api/*` is proxied to the backend (see `web/next.config.mjs`).
If the backend is down, the frontend falls back to an embedded fixture and shows a
"données démo" badge — so it always renders.

## What's wired vs pending

**Wired with real computed data** (`source: "computed"` from `../data/` annual exports):
- KPIs (inscriptions, cours, recettes, heures, remplissage) with real YoY deltas
- By-antenna breakdown · by-sector table with TOTAL row · multi-year evolution
- 3D network map · AI assistant (answers locally from the loaded snapshot)

**Stubbed (calc exists in `oscar_core`, view not yet ported):**
- Profils → Démographie / Acquisition · Produits → Catalogue
- File-upload ingestion (the backend currently computes from preloaded `../data/`)
- Per-course `aec_parser_v3` path (the annual zips are the category-report format; see `api/README.md`)

## Layout

```
oscar-prealpha/
  api/            FastAPI backend — reuses the pandas calc, serves JSON
    oscar_core.py     pure functions copied from dashboard_aec_v2.py (no streamlit)
    aec_parser_v3.py  copied parser (future per-course path)
    build_snapshot.py computes fixtures/snapshot.json from ../../data
    main.py           endpoints: /api/health /api/snapshot /api/meta
  web/            Next.js + Tailwind + Three.js frontend
    app/                routes (welcome + dashboard shell + views)
    components/         KPI cards, charts, table, filters, nav rail, AI modal, 3D map
    lib/                types, api client, fixture fallback, formatters, store
```
