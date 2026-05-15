# SPC App — Statistical Process Control for Chemical Batch Processes

## Overview

A Streamlit web app for SPC monitoring of batch chemical processes. MVP focuses on a single adhesive batch process with 3 parameters measured daily (3 replicates each). Multi-role support: operator data entry, engineer SPC analysis, manager dashboards.

## Tech Stack

- **Frontend**: Streamlit (Python)
- **Charts**: Plotly
- **Data storage**: CSV/Excel files (swappable to PostgreSQL later via repository pattern)
- **Auth**: Simple role-based (operator / engineer / manager / admin)

## Architecture

Layered architecture with strict dependency direction:

```
UI (Streamlit pages by role)
 └─> Visualization (Plotly chart builders)
      └─> SPC Engine (pure Python — no framework deps)
           └─> Data Access (repository pattern, CSV today)
```

### Directory Structure

```
SPC/
├── app.py                  # Entry point, role routing, session state
├── config.py               # App settings, file paths, SPC constants (n=3)
├── specs.yaml              # Not used — specs live in CSV rows
├── data/
│   ├── adhesive_batches.csv  # Working data file (90 rows, 2 formulas)
│   ├── generate_samples.py   # Dummy data generator
│   └── uploads/              # Timestamped upload archive (audit trail)
├── data_access/
│   ├── base.py             # Abstract DataRepository interface
│   ├── file_reader.py      # CSV/Excel read/write
│   └── repository.py       # CsvRepository + get_formulas(), get_specs_for_formula()
├── spc_engine/
│   ├── control_limits.py   # X-bar & R limits (n=3: A2=1.023, D3=0, D4=2.574)
│   ├── capability.py       # Pp, Ppk, PPM (one-sided spec: NaN = no limit)
│   ├── rules.py            # Western Electric rules 1, 2, 4, trending
│   └── attributes.py       # Not yet implemented (future: p-chart)
├── visualization/
│   ├── control_charts.py   # Plotly X-bar & R chart (paired subplots)
│   ├── capability.py       # Plotly histogram + spec lines (one-sided aware)
│   └── attribute_charts.py # Not yet implemented
├── ui/
│   ├── common/
│   │   ├── sidebar.py      # Role selector, data summary, navigation
│   │   └── data_upload.py  # Orphaned (upload moved into operator page)
│   ├── operator/
│   │   └── data_entry.py   # Mode selector: CSV Upload (default) or Manual Entry
│   ├── engineer/
│   │   ├── chart_view.py   # Combined SPC analysis: formula selector + X-bar/R + capability
│   │   └── capability_view.py  # Orphaned (merged into chart_view.py)
│   └── manager/
│       └── dashboard.py    # Formulas count, today's uploads, 🟢🟡🔴 status table
└── tests/
    ├── test_control_limits.py
    ├── test_rules.py
    ├── test_capability.py
    └── test_integration.py
```

## MVP Scope

### Single Process
- Adhesive batch process
- One batch per day, 3 replicate measurements per test

### Parameters & Specifications

Specs live in the CSV data file — not a separate YAML. Each row carries its own `lower_spec` and `upper_spec`, so different formulas can have different limits. When an operator uploads a new formula spreadsheet, the specs come with it.

**One-sided specs**: A parameter may have only an upper spec (e.g., impurities ≤ 0.5%) or only a lower spec (e.g., purity ≥ 98%). Leave the unused column empty (NaN). The SPC engine handles this:
- Only USL: Ppk = (USL − X̄) / 3σ. Pp is N/A. Only PPM > USL is reported.
- Only LSL: Ppk = (X̄ − LSL) / 3σ. Pp is N/A. Only PPM < LSL is reported.
- Both missing: capability analysis is skipped for that parameter.
- Neither missing: full Pp, Ppk, PPM both tails.

**Upload versioning**: Every CSV file uploaded by an operator is saved to `data/uploads/` with a timestamp prefix (`20260515-143022-uploaded.csv`). This creates an audit trail without needing a database or git for data. The working data file is still `data/adhesive_batches.csv`.

| Parameter  | Example LSL | Example USL | Example Target | Units |
|------------|-------------|-------------|----------------|-------|
| pH         | 5.50        | 8.50        | 7.00           | —     |
| IV         | 0.90        | 1.10        | 1.00           | dL/g  |
| Viscosity  | 6000        | 15000       | 10500          | cP    |

### Data Format (CSV)

```
date,batch_id,formula,parameter,rep1,rep2,rep3,lower_spec,upper_spec
2025-01-02,ADH-001,Adhesive A,pH,6.82,6.91,6.78,5.50,8.50
2025-01-02,ADH-001,Adhesive A,IV,0.952,0.947,0.961,0.90,1.10
2025-01-02,ADH-001,Adhesive A,viscosity,8420,8380,8450,6000,15000
```

### SPC Features (MVP)
- **X-bar & R charts** for each parameter (subgroup n=3)
- **Western Electric rules**: Rule 1 (beyond 3σ), Rule 2 (2 of 3 beyond 2σ), Rule 4 (8 consecutive same side of CL), trending (6 up/down)
- **Pp & Ppk** using overall standard deviation (not within-subgroup)
- **PPM > USL / PPM < LSL** from normal distribution fit

### Screens (MVP)
1. **Operator: Data Entry** — mode selector (CSV Upload by default, or Manual Entry). CSV mode validates columns and imports data with append/replace. Manual mode has formula selector, 3 params with inline LSL/USL/None toggles, live X̄/R/status, save.
2. **Engineer: SPC Analysis** — single combined page. Formula selector at top, then parameter selector. X-bar & R chart with violation markers and table, capability KPIs (Pp/Ppk/σ/PPM) with 🟢🟡🔴 status, histogram with spec lines. Raw data table at bottom.
3. **Manager: Dashboard** — total formulas/batches/rows/today's uploads KPI row. Status summary cards: 🟢 Capable (Ppk≥1.33), 🟡 Marginal (1.0≤Ppk<1.33), 🔴 Not Capable (Ppk<1.0), ⚪ No Spec. Full formula×parameter status table. Recent batches.

### Future (out of MVP)
- p-chart / c-chart attribute charts
- I-MR charts for single-measurement scenarios
- Multiple processes/products
- Instrument auto-import (CSV watch folder)
- PostgreSQL backend
- Email/Slack alerts for out-of-control signals
- User management admin page

## Key Design Decisions

1. **SPC engine is pure Python** — takes DataFrames, returns dicts. No Streamlit imports. Independently testable, portable.
2. **Repository pattern for data** — `base.py` defines interface. CSV implementation today. Drop in a PostgreSQL class later without touching SPC engine or UI.
3. **Specs travel with data** — each CSV row has `lower_spec` and `upper_spec` columns. No external spec config file. Different formulas/products can have different specs. Operators upload data with specs inline.
4. **Streamlit session_state** holds current batch data, selected parameter, role, and loaded DataFrame.
5. **Pp/Ppk uses overall σ** (all X-bar values across batches), matching the company's preference.
