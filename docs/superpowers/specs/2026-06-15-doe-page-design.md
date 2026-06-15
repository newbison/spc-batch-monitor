# DOE (Design of Experiments) Page — Design Spec

**Date:** 2026-06-15
**Status:** Approved
**Scope:** End-to-end DOE workflow page for process engineers — design generation, result capture, regression/RSM analysis, and optimization

---

## Problem

Process engineers need to optimize coating process parameters (line speed, cure temp, resin supplier, etc.) to hit target response specs (peel strength, optical density, etc.). Today this work happens in Minitab, Excel, and on paper run sheets — disconnected from the SPC system that monitors the resulting process. There's no guided workflow inside the app for running a DOE from start to finish.

Two common scenarios must be supported:
1. **Full circle:** Engineer has many factors, screens to find critical 2–3, runs full factorial, models, and optimizes.
2. **Direct characterization:** Engineer already knows the critical Xs (from prior work or domain knowledge) and just needs to run a full factorial on a new machine / new raw material / new environment.

## Decisions

| Decision | Choice |
|----------|--------|
| Architecture | Pure-Python `doe/` module (designs, analysis, optimization, persistence) + Streamlit wizard UI |
| Entry model | Multi-entry: Screening / Full factorial / Analyze-only + resume saved |
| Factors | Continuous + 2-level categorical |
| Responses | Custom per DOE, with goal (min/target/max) and bounds |
| Design types | Fractional factorial (screening), Full factorial + center points (characterization), Box-Behnken (RSM phase) |
| Analysis | Linear regression + RSM via statsmodels, with curvature test |
| Visualization | Main effects, interaction, Pareto, contour, response surface, overlay |
| Optimization | Desirability function + scipy.optimize, multi-start |
| Persistence | `doe_sessions` table in spc.db (JSON columns for variable-shape data) |
| Dependencies | `pyDOE2`, `statsmodels` (scipy already installed) |
| Bridge | "Promote to full factorial" from screening analysis |

## Architecture

### New files

| File | Purpose |
|------|---------|
| `doe/__init__.py` | Package marker |
| `doe/designs.py` | Pure Python: generate factorial / fractional / Box-Behnken design matrices via `pyDOE2`. No Streamlit imports. |
| `doe/analysis.py` | Pure Python: fit linear regression (main effects, interactions, p-values) and RSM (quadratic) via `statsmodels`. No Streamlit imports. |
| `doe/optimization.py` | Pure Python: solve for optimal factor settings from a fitted model via `scipy.optimize`. No Streamlit imports. |
| `doe/persistence.py` | Pure Python: load/save DOE sessions (factors, design, results) to SQLite. No Streamlit imports. |
| `ui/engineer/doe_view.py` | Streamlit UI: the multi-entry wizard page |

### Modified files

| File | Change |
|------|--------|
| `ui/common/sidebar.py` | Engineer role radio changes from `["SPC Analysis"]` to `["SPC Analysis", "DOE"]` (two page options) |
| `app.py` | Route Engineer "DOE" selection to `render_doe_page` |
| `requirements.txt` | Add `pyDOE2`, `statsmodels` |

### No changes to

- `spc_engine/`, `visualization/`, `data_access/sqlite_repository.py`, `reports/` — DOE is a self-contained subsystem

### Data model

Single table with JSON columns for variable-shape data:

```sql
CREATE TABLE doe_sessions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    entry_type  TEXT NOT NULL,   -- 'screening' | 'full_factorial' | 'analyze_only'
    status      TEXT NOT NULL,   -- 'defined' | 'designed' | 'running' | 'analyzed' | 'optimized'
    factors     TEXT NOT NULL,   -- JSON: [{name, type, low, high}]
    responses   TEXT NOT NULL,   -- JSON: [{name, goal, target, low, high}]
    design      TEXT,            -- JSON: design matrix (null until generated)
    results     TEXT,            -- JSON: response values per run (null until captured)
    model       TEXT,            -- JSON: fitted model coefficients (null until analyzed)
    optimum     TEXT,            -- JSON: optimal factor settings (null until optimized)
    created_at  TEXT DEFAULT (datetime('now')),
    updated_at  TEXT DEFAULT (datetime('now'))
);
```

JSON shapes are defined by Python dicts in `doe/persistence.py`:

- `factors`: `[{"name": "line_speed", "type": "continuous", "low": 50, "high": 80}, ...]`
- `responses`: `[{"name": "peel_strength", "goal": "maximize", "target": null, "low": 5.0, "high": 8.0}, ...]`
- `design`: `[{"run": 1, "line_speed": -1, "cure_temp": -1, "resin_supplier": -1}, ...]` (coded −1/+1)
- `results`: `[{"run": 1, "peel_strength": 6.2, "optical_density": 1.82}, ...]`

## Wizard Workflow

### Landing — Entry Point Selection

Three radio options + a saved-DOE resume dropdown:

- **Screening** — many factors, find the critical 2–3
- **Full factorial** — known critical Xs, characterize on new setup
- **Analyze only** — have results (from Excel / another tool), want to model & optimize

Plus: **Continue existing DOE** — dropdown of saved sessions + Resume button.

### Step 1: Define (all paths)

**Factors table** — engineer adds rows dynamically:

| Factor name | Type | Low | High |
|-------------|------|-----|------|
| line_speed | Continuous | 50 | 80 |
| cure_temp | Continuous | 120 | 160 |
| resin_supplier | Categorical | Supplier A | Supplier B |

- Type options: Continuous, Categorical
- For screening: typically 4–8 factors
- For full factorial: typically 2–3 factors

**Responses table** — engineer adds rows dynamically:

| Response name | Goal | Target | Low | High |
|---------------|------|--------|-----|------|
| peel_strength | Maximize | — | 5.0 | 8.0 |
| optical_density | Target | 1.85 | 1.70 | 2.00 |

- Goal options: Minimize, Target, Maximize
- Target column only applies when Goal = Target
- Low/High define the desirability function bounds (Step 5)

### Step 2: Design (screening + full factorial paths; skipped for analyze-only)

Based on entry type:

- **Screening path:** Fractional factorial `2^(k-p)` (minimum Resolution IV) or Plackett-Burman. Engineer selects resolution from available options. App shows run count.
- **Full factorial path:** `2^k` full factorial with center points (default 3, range 3–5). Center points enable curvature detection for RSM. App shows run count.

"Generate Run Sheet" button produces a table with coded factor levels (decoded to actual values for display):

| Run | line_speed | cure_temp | resin_supplier | [response cols blank] |
|-----|-----------|-----------|----------------|------|
| 1 | 50 (-1) | 120 (-1) | Supplier A (-1) | |
| 2 | 80 (+1) | 120 (-1) | Supplier A (-1) | |
| ... | | | | |
| C1 | 65 (0) | 140 (0) | — | |

Exportable to CSV (for printing and taking to the line).

### Step 3: Capture (all paths)

Editable table matching the run sheet, with response columns now fillable:
- **Manual entry:** engineer types results into Streamlit data editor
- **CSV upload:** paste/upload a completed run sheet with response values filled in

Validation: every run must have all response values before analysis is allowed.

For analyze-only path: this is where the engineer imports existing results (CSV or manual entry of a pre-existing design matrix).

### Step 4: Analyze (all paths)

For each response, the app fits:

**Linear regression** (always):
- Encodes 2-level factors as −1 / +1
- Fits main effects + all 2-way interactions
- Uses `statsmodels.api.OLS`
- Returns coefficient table: term, estimate, std err, p-value, significant (p < 0.05)?

**RSM** (when center points present and curvature significant):
- Adds quadratic terms
- Curvature test: t-test comparing center-point response mean vs. factorial-point response mean. If p < 0.05, RSM is recommended and fitted.

Outputs:
- Coefficients table with p-values (significant factors highlighted)
- Main effects plots — one per factor, showing response at −1 vs +1
- Interaction plots — 2-way interaction matrices
- Pareto of effects — bar chart of absolute standardized effects, sorted descending
- Contour plot — for top 2 significant factors (RSM only)
- Response surface — 3D surface for top 2 factors (RSM only)

### Step 5: Optimize (all paths)

Engineer confirms response goals (carried over from Step 1, editable). The app:

1. Builds a desirability function per response (Derringer-Suich):
   - Maximize: d ramps 0 (at Low) → 1 (at High)
   - Minimize: d ramps 1 (at Low) → 0 (at High)
   - Target: d peaks at 1 at Target, ramps to 0 at Low and High
2. Computes overall desirability D = (d₁ · d₂ · ... · dₙ)^(1/n)
3. Solves for factor settings that maximize D via `scipy.optimize.minimize` with multi-start (10 random initial points)
4. Displays:
   - Optimal factor settings (decoded to actual values)
   - Predicted response values at optimum (with 95% prediction interval)
   - Overall desirability score (0–1)
   - Overlay plot — contour with shaded feasible region where all responses meet goals

Results downloadable as summary CSV.

### Promote-to-full-factorial bridge (screening path only)

After Step 4 on the screening path, a "Promote significant factors to full factorial" button appears. Clicking it:
1. Identifies the 2–3 factors with the lowest p-values from the screening analysis
2. Pre-fills a new full-factorial DOE session with those factors
3. Engineer lands on Step 1 of the new session (can adjust levels for the new characterization run)

This bridges the screening → characterization transition without manual re-entry.

## Design Library Details (`doe/designs.py`)

Uses `pyDOE2`:

- `ffactn(n, 2**(n-p))` — fractional factorial for n factors at resolution determined by p
- `fullfact([2]*n)` — full factorial 2^k (then map to coded −1/+1)
- Center points: append `n_center` rows of all-zeros in coded space
- Box-Behnken: `bbdesign(n)` — for RSM on 3+ factors without corner extremes

All design matrices are returned in coded space (−1, 0, +1). Decoding to actual factor values happens at display time in the UI layer.

## Analysis Details (`doe/analysis.py`)

Uses `statsmodels.api.OLS`:

```
fit_linear(factors, design, results, response_name) -> {
    "coefficients": [{"term": "line_speed", "estimate": 0.85, "p_value": 0.003, "significant": True}, ...],
    "r_squared": 0.94,
    "r_squared_adj": 0.91,
    "model_p_value": 0.001,
}

fit_rsm(factors, design, results, response_name) -> {
    "coefficients": [...],  # includes quadratic terms
    "r_squared": ...,
    "curvature_p_value": 0.02,  # from center-point test
    "has_curvature": True,
}
```

## Optimization Details (`doe/optimization.py`)

Uses `scipy.optimize.minimize`:

```
optimize(factors, responses, models) -> {
    "optimal_settings": {"line_speed": 72, "cure_temp": 145, "resin_supplier": "Supplier B"},
    "predicted_responses": {"peel_strength": 7.8, "optical_density": 1.84},
    "desirability": 0.87,
    "prediction_intervals": {"peel_strength": [7.2, 8.4], ...},
}
```

Multi-start: 10 random initial points within factor bounds. Returns the best solution found.

## Out of Scope (deferred)

- Mixture designs (specialized simplex-lattice)
- 3+ level categorical factors
- Taguchi orthogonal arrays
- Robustness / tolerance design (Taguchi signal-to-noise)
- Automated DOE recommendation (suggest design type based on factor count)
- Integration with SPC data (e.g., auto-import historical measurements as DOE responses)
- DOE results export to PPTX (future enhancement, after PPTX report module is stable)
