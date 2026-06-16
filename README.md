# SPC Batch Monitor

Statistical Process Control (SPC) web app for monitoring chemical batch coating processes, with integrated Design of Experiments (DOE) for process optimization. Tracks 4 quality parameters per batch with variable subgroup sizes (5–15 replicates) across multiple formulas.

![1778922140812](image/README/1778922140812.png)


![1778922162913](image/README/1778922162913.png)


![1778922204098](image/README/1778922204098.png)



## Features

### SPC

- **X-bar & R control charts** with dynamic subgroup sizes and ASTM E2587 constants
- **Western Electric rules** — Rule 1 (beyond 3σ), Rule 2 (2 of 3 beyond 2σ), Rule 4 (8 consecutive same side), trending (6 up/down)
- **Trend analysis** — run chart, moving range chart, rolling Ppk
- **Process capability** — Pp, Ppk, PPM with histogram and spec lines (supports one-sided specs)
- **Batch-to-batch boxplots** with spec line overlays
- **PPTX report export** — auto-generated SPC reports with charts and narrative summaries

### DOE (Design of Experiments)

- **Screening & full factorial designs** — 2^k full factorial, 2^(k-p) fractional factorial (Resolution IV/V), and Box-Behnken RSM designs via pyDOE2
- **Regression analysis** — linear models with main effects + 2-way interactions, plus RSM quadratic models via statsmodels
- **Curvature detection** — automatic two-sample t-test comparing center vs. factorial points
- **Visualization** — main effects plots, Pareto of effects, contour plots, 3D response surfaces
- **Derringer-Suich optimization** — multi-response desirability with multi-start scipy optimization
- **Session persistence** — save, resume, and iterate on DOE experiments across sessions

### Platform

- **Role-based UI** — Operator, Engineer, Manager, Admin
- **SQLite storage** with repository pattern (swappable to PostgreSQL)

## Tech Stack

| Layer         | Technology                              |
| ------------- | --------------------------------------- |
| UI            | Streamlit                               |
| Charts        | Plotly                                  |
| SPC Engine    | Pure Python (NumPy/SciPy)               |
| DOE Engine    | pyDOE2, statsmodels, scipy.optimize     |
| Reports       | python-pptx, Kaleido                    |
| Database      | SQLite (WAL mode)                       |
| Testing       | Pytest (90 tests)                       |

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

| Role     | Screen          | Capabilities                                                              |
| -------- | --------------- | ------------------------------------------------------------------------- |
| Operator | Data Entry      | CSV upload, manual entry, view/edit today's batches                       |
| Engineer | SPC Analysis    | Control charts, capability analysis, trend charts, boxplots, PPTX export  |
| Engineer | DOE             | Design wizard: define → design → capture → analyze → optimize             |
| Manager  | Dashboard       | KPI cards, out-of-spec banners, status table, trend expander              |
| Admin    | Data Management | Filter, edit, delete, export CSV, import CSV                              |

## Monitored Parameters

| Parameter         | Replicates | LSL    | USL  | Units  |
| ----------------- | ---------- | ------ | ---- | ------ |
| Adhesion          | 5          | 0.6    | 1.5  | N/mm   |
| Cohesion          | 15         | 1000.0 | —   | —     |
| Rolling Ball Tack | 8          | 10.0   | 50.0 | mm     |
| Liner Release     | 10         | 5.0    | 20.0 | g/inch |

## Architecture

```
UI (Streamlit pages by role)
 └─> Visualization (Plotly chart builders)
      └─> SPC Engine (pure Python — no framework deps)
           └─> Data Access (repository pattern → SQLite)
                └─> Validation (row-level guard before writes)

DOE (Design of Experiments)
 └─> doe/designs.py     — factorial & Box-Behnken matrices (pyDOE2)
 └─> doe/analysis.py    — linear + RSM regression (statsmodels)
 └─> doe/optimization.py — Derringer-Suich desirability (scipy)
 └─> doe/persistence.py — SQLite session CRUD
```

The SPC and DOE engines are framework-agnostic — they take DataFrames, return dicts. The repository pattern abstracts storage so SQLite can be swapped for PostgreSQL without touching UI or business logic.

## Testing

```bash
pytest tests/ -v
```

90 tests covering control limits, Western Electric rules, capability calculations, validation, repository operations, integration, design generation, regression analysis, desirability optimization, and DOE persistence.
