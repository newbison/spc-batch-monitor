# SPC Batch Monitor

Statistical Process Control (SPC) web app for monitoring chemical batch coating processes. Tracks 4 quality parameters per batch with variable subgroup sizes (5–15 replicates) across multiple formulas.

## Features

- **X-bar & R control charts** with dynamic subgroup sizes and ASTM E2587 constants
- **Western Electric rules** — Rule 1 (beyond 3σ), Rule 2 (2 of 3 beyond 2σ), Rule 4 (8 consecutive same side), trending (6 up/down)
- **Trend analysis** — run chart, moving range chart, rolling Ppk
- **Process capability** — Pp, Ppk, PPM with histogram and spec lines (supports one-sided specs)
- **Batch-to-batch boxplots** with spec line overlays
- **Role-based UI** — Operator, Engineer, Manager, Admin
- **SQLite storage** with repository pattern (swappable to PostgreSQL)

## Tech Stack

| Layer | Technology |
|-------|-----------|
| UI | Streamlit |
| Charts | Plotly |
| SPC Engine | Pure Python (NumPy/SciPy) |
| Database | SQLite (WAL mode) |
| Testing | Pytest |

## Installation

```bash
git clone https://github.com/newbison/spc-batch-monitor.git
cd spc-batch-monitor
pip install -r requirements.txt
```

## Usage

```bash
streamlit run app.py
```

Sample data is auto-generated on first run if the database is empty. Select a role from the sidebar to access different screens.

## Roles & Screens

| Role | Screen | Capabilities |
|------|--------|-------------|
| Operator | Data Entry | CSV upload, manual entry, view/edit today's batches |
| Engineer | SPC Analysis | Control charts, capability analysis, trend charts, boxplots |
| Manager | Dashboard | KPI cards, out-of-spec banners, status table, trend expander |
| Admin | Data Management | Filter, edit, delete, export CSV, import CSV |

## Monitored Parameters

| Parameter | Replicates | LSL | USL | Units |
|-----------|-----------|-----|-----|-------|
| Adhesion | 5 | 0.6 | 1.5 | N/mm |
| Cohesion | 15 | 1000.0 | — | — |
| Rolling Ball Tack | 8 | 10.0 | 50.0 | mm |
| Liner Release | 10 | 5.0 | 20.0 | g/inch |

## Architecture

```
UI (Streamlit pages by role)
 └─> Visualization (Plotly chart builders)
      └─> SPC Engine (pure Python — no framework deps)
           └─> Data Access (repository pattern → SQLite)
                └─> Validation (row-level guard before writes)
```

The SPC engine is framework-agnostic — takes DataFrames, returns dicts. The repository pattern abstracts storage so SQLite can be swapped for PostgreSQL without touching UI or SPC logic.

## Testing

```bash
pytest tests/ -v
```

38 tests covering control limits, Western Electric rules, capability calculations, validation, repository operations, and integration.