# SPC App — Statistical Process Control for Chemical Batch Processes

## Overview

A Streamlit web app for SPC monitoring of batch coating processes. Monitors 4 parameters (adhesion, cohesion, rolling_ball_tack, liner_release) with variable subgroup sizes (5–15 replicates). Multi-role support: operator data entry, engineer SPC analysis, manager dashboards, admin data management.

## Tech Stack

- **Frontend**: Streamlit (Python)
- **Charts**: Plotly
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
│   ├── coating_batches.csv      # Generated sample data (120 rows)
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
│   │   └── sidebar.py           # Role selector, data summary, param sync
│   ├── operator/
│   │   └── data_entry.py        # CSV Upload, Manual Entry, View & Edit tabs
│   ├── engineer/
│   │   └── chart_view.py        # Formula+param selectors, 4 chart tabs, capability
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
    └── test_integration.py      # 38 tests total
```

## Current Scope

### Coating Process
- 2 formulas (Coating A, Coating B), 30 batches each
- 4 parameters with variable replicates

| Parameter | Reps | LSL | USL | Units |
|-----------|------|-----|-----|-------|
| adhesion | 5 | 0.6 | 1.5 | N/mm |
| cohesion | 15 | 1000.0 | — | — |
| rolling_ball_tack | 8 | 10.0 | 50.0 | mm |
| liner_release | 10 | 5.0 | 20.0 | g/inch |

### Data Format (CSV / SQLite)

```
date,batch_id,formula,parameter,lower_spec,upper_spec,rep1,...,rep15
2025-01-02,COAT-001,Coating A,adhesion,0.6,1.5,1.118,1.157,1.201,...,NaN
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
3. **Manager: Dashboard** — KPI row, out-of-spec/marginal banners, status summary cards (🟢/🟡/🔴/⚪), full status table, trend analysis expander
4. **Admin: Data Management** — filterable data browser (date, formula, param, search), inline edit, row/batch delete, CSV export, CSV import

## Key Design Decisions

1. **SPC engine is pure Python** — takes DataFrames, returns dicts. No Streamlit imports.
2. **Repository pattern** — `base.py` defines interface. `SqliteRepository` today. Drop in PostgreSQL later.
3. **SQLite with WAL** — replaced single-file CSV. Dedup via UNIQUE(batch_id, formula, parameter).
4. **Validation gate** — `validate_rows()` rejects negative values, bad dates, non-numeric data before any write.
5. **Auto-migration** — existing `coating_batches.csv` imported into SQLite on first run.
6. **Specs travel with data** — each row has `lower_spec`/`upper_spec`. Different formulas can have different limits.
7. **Upload versioning** — every uploaded CSV archived to `data/uploads/` with timestamp prefix.
8. **Pp/Ppk uses overall σ** (all X-bar values across batches).
