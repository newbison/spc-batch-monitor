# SPC App — Statistical Process Control for Chemical Batch Processes

## Overview

A Streamlit web app for SPC monitoring of batch manufacturing processes and DOE (Design of Experiments). SPC monitors 4 parameters (Metric A, Metric B, Metric C, Metric D) with variable subgroup sizes (5–15 replicates). DOE supports full/fractional factorial and Box-Behnken designs with RSM analysis and multi-response desirability optimization. Multi-role support: operator data entry, engineer SPC analysis + DOE, manager dashboards, admin data management.

## Tech Stack

- **Frontend**: Streamlit (Python)
- **Charts**: Plotly
- **DOE**: pyDOE2 (design matrices), statsmodels (RSM regression), scipy (optimization)
- **Data storage**: SQLite (via repository pattern; swappable to PostgreSQL later)
- **Auth**: Simple role-based dropdown (operator / engineer / manager / admin)

## Architecture

Layered architecture with strict dependency direction:

```
UI (Streamlit pages by role)
 └─> Visualization (Plotly chart builders)
      └─> SPC Engine (pure Python — no framework deps)
           └─> Data Access (repository pattern → SQLite today)
                └─> Validation (row-level guard before writes)
```

### Directory Structure

```
SPC/
├── app.py                       # Entry point, CSS theme, role routing
├── config.py                    # Paths, SPC constants (A2/D3/D4 by n)
├── requirements.txt             # Python deps
├── data/
│   ├── batch_data.csv          # Generated sample data (120 rows)
│   ├── generate_samples.py      # Dummy data generator
│   └── uploads/                 # Timestamped CSV upload archive (audit trail)
├── data_access/
│   ├── base.py                  # DataRepository ABC
│   ├── file_reader.py           # CSV/Excel read/write helpers
│   ├── repository.py            # CsvRepository (legacy, kept for reference)
│   ├── sqlite_repository.py     # SqliteRepository — source of truth
│   └── validation.py            # validate_rows() — rejects bad data before write
├── spc_engine/
│   ├── control_limits.py        # X-bar & R limits (dynamic n via NaN detection)
│   ├── capability.py            # Pp, Ppk, PPM (one-sided spec: NaN = no limit)
│   └── rules.py                 # Western Electric rules 1, 2, 4, trending
├── doe/
│   ├── __init__.py              # Package init, public API re-exports
│   ├── designs.py               # Full/fractional factorial + Box-Behnken via pyDOE2
│   ├── analysis.py              # Linear regression + RSM via statsmodels, curvature test
│   ├── optimization.py          # Derringer-Suich desirability, scipy multi-start optimizer
│   └── persistence.py           # SQLite CRUD for DOE sessions (JSON columns)
├── reports/
│   ├── narrative.py             # SPC narrative report generator
│   └── pptx_generator.py        # PPTX export for SPC charts
├── visualization/
│   ├── _theme.py                # Shared Plotly defaults (industrial warm palette)
│   ├── control_charts.py        # X-bar & R chart (paired subplots)
│   ├── capability.py            # Histogram + spec lines
│   ├── boxplot.py               # Batch-to-batch variation boxplot
│   ├── run_chart.py             # X̄ over time with median line
│   ├── moving_range.py          # |X̄ᵢ − X̄ᵢ₋₁| with CL/UCL
│   └── rolling_ppk.py           # Sliding-window Ppk with zone coloring
├── ui/
│   ├── common/
│   │   └── sidebar.py           # Role selector, data summary, param sync, page switch
│   ├── operator/
│   │   └── data_entry.py        # CSV Upload, Manual Entry, View & Edit tabs
│   ├── engineer/
│   │   ├── chart_view.py        # Formula+param selectors, 4 chart tabs, capability
│   │   └── doe_view.py          # DOE wizard: define→design→capture→analyze→optimize
│   ├── manager/
│   │   └── dashboard.py         # KPI cards, status table, trend expander
│   └── admin/
│       └── data_manager.py      # Filter, view, edit, delete, export, import
└── tests/
    ├── test_control_limits.py
    ├── test_rules.py
    ├── test_capability.py
    ├── test_validation.py
    ├── test_sqlite_repository.py
    ├── test_integration.py
    ├── test_doe_designs.py
    ├── test_doe_analysis.py
    ├── test_doe_optimization.py
    └── test_doe_persistence.py   # 73 tests total
```

## Current Scope

### Manufacturing Process
- 2 formulas (Grade A, Grade B), 30 batches each
- 4 parameters with variable replicates

| Parameter | Reps | LSL | USL | Units |
|-----------|------|-----|-----|-------|
| Metric A | 5 | 0.6 | 1.5 | N/mm |
| Metric B | 15 | 1000.0 | — | — |
| Metric C | 8 | 10.0 | 50.0 | mm |
| Metric D | 10 | 5.0 | 20.0 | g/inch |

### Data Format (CSV / SQLite)

```
date,batch_id,formula,parameter,lower_spec,upper_spec,rep1,...,rep15
2025-01-02,BATCH-001,Grade A,Metric A,0.6,1.5,1.118,1.157,1.201,...,NaN
```

- Specs are inline per-row (different formulas can have different limits)
- Replicates beyond actual n are padded with NaN
- Subgroup size auto-detected by counting non-NaN reps per row

### SPC Features
- **X-bar & R charts** with dynamic subgroup size (n=5–15)
- **Western Electric rules**: Rule 1 (beyond 3σ), Rule 2 (2 of 3 beyond 2σ), Rule 4 (8 consecutive same side of CL), trending (6 up/down)
- **Trend charts**: run chart, moving range, rolling Ppk (window=10)
- **Boxplot**: batch-to-batch variation with spec lines
- **Pp & Ppk** using overall standard deviation
- **One-sided spec handling**: NaN = no limit; Ppk computed from available side

### Screens
1. **Operator: Data Entry** — 3 modes: CSV Upload (validated + deduped), Manual Entry, View & Edit (today's batches only)
2. **Engineer: SPC Analysis** — formula+param selectors side-by-side, all-formulas out-of-spec banner, 4 chart tabs (X-bar & R, Run, Moving Range, Rolling Ppk), capability KPIs, histogram, boxplot, raw data
3. **Engineer: DOE** — wizard workflow: Landing → Define Factors & Responses → Generate Design Matrix → Capture Results → Analyze (regression, RSM, main effects, Pareto, contour/surface plots) → Optimize (Derringer-Suich desirability). Supports promote-to-full-factorial and session persistence.
4. **Manager: Dashboard** — KPI row, out-of-spec/marginal banners, status summary cards (🟢/🟡/🔴/⚪), full status table, trend analysis expander
5. **Admin: Data Management** — filterable data browser (date, formula, param, search), inline edit, row/batch delete, CSV export, CSV import

## Key Design Decisions

1. **SPC engine is pure Python** — takes DataFrames, returns dicts. No Streamlit imports.
2. **Repository pattern** — `base.py` defines interface. `SqliteRepository` today. Drop in PostgreSQL later.
3. **SQLite with WAL** — replaced single-file CSV. Dedup via UNIQUE(batch_id, formula, parameter).
4. **Validation gate** — `validate_rows()` rejects negative values, bad dates, non-numeric data before any write.
5. **Auto-migration** — existing `batch_data.csv` imported into SQLite on first run.
6. **Specs travel with data** — each row has `lower_spec`/`upper_spec`. Different formulas can have different limits.
7. **Upload versioning** — every uploaded CSV archived to `data/uploads/` with timestamp prefix.
8. **Pp/Ppk uses overall σ** (all X-bar values across batches).
9. **DOE engine is pure Python** — doe/ modules take DataFrames/arrays, return dicts. No Streamlit imports.
10. **pyDOE2 for design matrices** — patched `import imp` → `import importlib` for Python 3.12+ compat.
11. **statsmodels for RSM** — second-order regression with coded variables; ANOVA + significance via t-tests.
12. **Derringer-Suich desirability** — individual desirability per response (nominal-the-best, larger-the-better, smaller-the-better), geometric mean overall desirability, scipy multi-start optimization.
13. **DOE sessions persisted in SQLite** — separate `doe_sessions` table with JSON columns for factors, responses, design, results.
