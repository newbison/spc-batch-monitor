# DOE Platform Redesign — Design Spec

**Date:** 2026-06-21
**Status:** Spec — awaiting user review
**Scope:** Complete DOE overhaul — architecture, analysis, design types, UI

---

## 1. Overview

### 1.1 Why This Exists

A chemist or materials engineer designing experiments needs:
- The right design for the task (factorial, CCD, mixture, etc.)
- Statistical rigor they can trust (ANOVA, residuals, diagnostics)
- A fluid interface that doesn't break their flow

The current DOE is a 6-step linear wizard with coefficient-only analysis and no design evaluation. It's functional but too shallow for real R&D work — it covers the basics but stops where actual DOE practice begins.

### 1.2 Goals

| Goal | How |
|------|-----|
| Trust the model | Full ANOVA (SS, MS, F, p), residual diagnostics, curvature detection |
| Explore predictions interactively | Drag-to-predict profiler with desirability ramp |
| Evaluate designs before running | Power, VIF, G-efficiency, alias structure |
| Cover the design space | Factorial, fractional, CCD, Box-Behnken, mixture, D-optimal, split-plot |
| Reduce friction | 2 rich tabs instead of 6 wizard pages |

### 1.3 Non-Goals

- Replacing JMP/Design-Expert/Minitab — this is a companion tool for rapid iteration, not a full enterprise stats package
- Bayesian DOE or space-filling designs (Latin hypercube, etc.) — out of scope
- Real-time collaboration — single-user tool
- Automated experiment execution (no lab instrument integration)

---

## 2. Architecture

### 2.1 Tab Structure

```
┌─────────────────────────────────────────────────────────────┐
│  DOE SIDEBAR                                                │
│  ┌─────────┐  Session name, status, quick nav               │
│  │ DESIGN  │  ─── TAB 1                                     │
│  │ ANALYZE │  ─── TAB 2                                     │
│  └─────────┘                                                │
│  [New DOE] [Export]                                         │
├─────────────────────────────────────────────────────────────┤
│  MAIN CONTENT: SCROLLABLE TAB WITH COLLAPSIBLE SECTIONS     │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Layer Architecture (unchanged from current)

```
UI (Streamlit tabs + sections)
 └─> Visualization (Plotly: ANOVA tables as styled DataFrames, plots for residuals/profiler)
      └─> DOE Engine (pure Python — design generation, analysis, optimization)
           └─> Persistence (DoeRepository → SQLite doe_sessions table)
```

All new modules follow the existing pattern: pure Python, take DataFrames/arrays/dicts, return dicts. No Streamlit imports in the engine layer.

### 2.3 Module Map

| File | Purpose | Status |
|------|---------|--------|
| `doe/designs.py` | Factorial, fractional, BB + new CCD, mixture | Expand |
| `doe/evaluate.py` | Power, VIF, G-efficiency, alias | **New** |
| `doe/analysis.py` | ANOVA + linear/RSM models | Rewrite |
| `doe/residuals.py` | Residual diagnostics (normality, plots) | **New** |
| `doe/profiler.py` | Interactive prediction + desirability ramp data | **New** |
| `doe/optimization.py` | Derringer-Suich multi-start (keep, minor tweaks) | Keep |
| `doe/persistence.py` | SQLite CRUD (keep, add analysis_json column) | Extend |
| `doe/_factorial.py` | Self-contained factorial generators | Keep |
| `ui/engineer/doe_view.py` | Full UI rewrite: 2 tabs + sections | Rewrite |

---

## 3. Data Model

### 3.1 doe_sessions Table (extended)

```sql
CREATE TABLE doe_sessions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    entry_type      TEXT NOT NULL,        -- 'screening', 'full_factorial', 'rsm', 'mixture', 'd_optimal', 'split_plot', 'analyze_only'
    status          TEXT DEFAULT 'defined', -- 'defined', 'designed', 'running', 'analyzed', 'optimized'
    factors         TEXT NOT NULL,        -- JSON: list of factor dicts
    responses       TEXT NOT NULL,        -- JSON: list of response dicts
    design          TEXT,                 -- JSON: list of run dicts (coded design matrix)
    results         TEXT,                 -- JSON: list of run dicts with response values
    analysis        TEXT,                 -- JSON: {response_name: {anova, coefficients, residuals, model_type}}
    optimum         TEXT,                 -- JSON: {optimal_settings, predicted_responses, desirability, ...}
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now'))
);
```

Key change: `model` column renamed to `analysis` and now stores ANOVA + coefficients + residuals per response.

### 3.2 analysis JSON Structure

```python
{
    "Metric A": {
        "model_type": "rsm",          # 'linear' | 'rsm' | 'mixture'
        "anova": {
            "source": ["Model", "A-Temperature", "B-Pressure", "A*B", "Residual", "Total"],
            "ss": [0.8472, 0.3120, 0.2105, 0.1247, 0.0349, 0.8821],
            "df": [5, 1, 1, 1, 5, 10],
            "ms": [0.1694, 0.3120, 0.2105, 0.1247, 0.0070, None],
            "f": [24.31, 44.75, 30.19, 17.88, None, None],
            "p": [0.001, 0.001, 0.003, 0.008, None, None]
        },
        "r_squared": 0.9604,
        "r_squared_adj": 0.9208,
        "rmse": 0.0836,
        "lack_of_fit_p": 0.872,
        "coefficients": [...],
        "residuals": {
            "run": [1, 2, 3, ...],
            "predicted": [1.12, 0.98, ...],
            "residual": [0.03, -0.02, ...],
            "studentized": [0.41, -0.28, ...]
        }
    }
}
```

### 3.3 Factor JSON (extended)

Mixture factors add constraints:

```python
{
    "name": "Monomer A",
    "type": "mixture",           # new type
    "low": 0.20,                 # 20% minimum
    "high": 0.40,                # 40% maximum
    # Mixture constraint: sum of all mixture factors = 1.0 (enforced by design type)
}
```

---

## 4. Tab 1: DESIGN

### 4.1 Layout

A single scrollable page with 4 collapsible sections. Only the current section is expanded; completed sections collapse to a summary line.

```
▸ SETUP (expanded)
    Factor rows: name | type | low | high | constraints
    Response rows: name | goal | low | target | high
    [+ Add Factor]  [+ Add Response]

▸ DESIGN TYPE (collapsed when setup incomplete)
    ┌──────────────────────────────────────────────────────────┐
    │ [Factorial] [Fractional] [CCD] [Box-Behnken]             │
    │ [Mixture] [D-Optimal] [Split-Plot]                       │
    │                                                          │
    │ Config: n_center=[3]  alpha=[rotatable]  replicates=[1] │
    └──────────────────────────────────────────────────────────┘

▸ DESIGN DIAGNOSTICS (shown after design generated)
    Power | VIF | G-efficiency | Alias structure
    Warning banners: "VIF > 5 detected", "Power < 0.8 for small effects"

▸ RUN SHEET (shown after design generated)
    Interactive table: run | factor1 | factor2 | ... | response1 | response2 | ...
    [Download CSV] [Randomize Order] [Copy to Clipboard]
```

### 4.2 Design Type Selection

Design type radio buttons in a horizontal layout. Each selection shows:
- Estimated run count
- When to use (one-line tooltip)
- Configuration options specific to that type

| Design Type | Config | Runs Formula | Phase |
|------------|--------|-------------|-------|
| Full Factorial | n_center, replicates | 2^k + cp | 1 (exists) |
| Fractional Factorial | resolution (IV/V), n_center | 2^(k-p) + cp | 1 (exists) |
| CCD | alpha (rotatable/orthogonal/face-centered), n_center | 2k + 2k + cp | 1 (new) |
| Box-Behnken | n_center | per k combinatorics | 1 (exists) |
| Mixture Simplex Lattice | degree (m) | (k+m-1 choose m) | 2 (new) |
| Mixture Simplex Centroid | none | 2^k - 1 + cp | 2 (new) |
| D-Optimal | n_runs, model_order | user-specified | 3 (new) |
| Split-Plot | whole_plot_factors, subplot_factors | product of sub-designs | 3 (new) |

### 4.3 Design Diagnostics (evaluate.py)

Computed immediately after design generation and displayed before the user exports the run sheet.

| Metric | What It Means | Threshold |
|--------|--------------|-----------|
| **Power** | Probability of detecting a real effect of size δ | > 0.80 for δ=1σ |
| **VIF (max)** | Variance Inflation Factor — multicollinearity | < 5 OK, > 10 bad |
| **G-efficiency** | Max prediction variance / average prediction variance | > 0.50 acceptable |
| **Alias structure** | Which effects are confounded with which | Res IV/V display |

Power is computed per effect: `power = 1 - F_cdf(F_crit - ncp) + F_cdf(-F_crit - ncp)` where ncp depends on effect size, sample size, and error df.

VIF = diagonal of `(X'X)^-1` scaled by MSE. For factorial designs with center points, computed from the model matrix.

### 4.4 Run Sheet

After design generation: the full design matrix (both coded and actual) with empty response columns. The user can:
- Toggle between coded/actual display
- Randomize run order (Fisher-Yates, seeded)
- Download as CSV
- Optionally enter response data directly in the run sheet (bridges to Tab 2)

---

## 5. Tab 2: ANALYZE

### 5.1 Layout

One scrollable page with 5 sections. Section visibility depends on data availability.

```
▸ DATA ENTRY (always expanded until data exists)
    [Upload completed run sheet CSV]  or  enter inline
    After data: collapsed summary "11 runs, 2 responses — all complete ✓"

▸ ANOVA (shown after analysis runs)
    Full ANOVA table per response.
    Model summary line: R², Adj R², RMSE, Lack-of-fit p

▸ RESIDUAL DIAGNOSTICS (shown after analysis runs)
    2×2 grid: Normal Q-Q | Residuals vs Predicted | Residuals vs Run Order | Histogram

▸ EFFECTS & PLOTS (shown after analysis runs)
    Pareto chart | Main effects plot | Interaction plot (if 2FIs present)
    Contour + Surface plots (RSM/mixture models only)

▸ PREDICTION PROFILER (shown after model fitted)
    Interactive factor sliders | Response trace curves | Desirability ramp | [Find Optimum]
```

### 5.2 ANOVA Table (analysis.py rewrite)

The `fit_linear()` and `fit_rsm()` functions return an expanded dict that now includes the full ANOVA decomposition:

```python
def fit_linear(factors, design, results, response_name, alpha=0.05) -> dict:
    """Returns: {
        'model_type': 'linear',
        'coefficients': [...],
        'anova': {source, ss, df, ms, f, p},
        'r_squared': float,
        'r_squared_adj': float,
        'rmse': float,
        'residuals': {run, predicted, residual, studentized},
        'lack_of_fit_p': float or None,
        'n_obs': int,
        'n_params': int,
    }
    """
```

ANOVA decomposition uses Type III SS (statsmodels OLS). The lack-of-fit test groups replicated runs and compares pure error vs. model error.

### 5.3 Residual Diagnostics (residuals.py)

Four diagnostic plots using Plotly, generated as a 2×2 subplot grid:

| Plot | What It Checks | Bad Pattern |
|------|---------------|-------------|
| **Normal Q-Q** | Normality of residuals | S-curve or outliers off the line |
| **Residuals vs Predicted** | Constant variance (homoscedasticity) | Fan shape, curvature |
| **Residuals vs Run Order** | Time trends, drift | Upward/downward trend |
| **Histogram + KDE** | Distribution shape | Severe skew, bimodal |

Studentized residuals (externally studentized) are used throughout. Points with |studentized residual| > 2 are highlighted in the plots.

An interpretive summary line appears below the plots:
- ✅ "No issues detected" if all checks pass
- ⚠️ "Mild non-normality detected (Shapiro-Wilk p = 0.03)" 
- ❌ "Strong heteroscedasticity — consider transformation"

### 5.4 Prediction Profiler (profiler.py + Plotly)

The profiler is the centerpiece of the Analyze tab. It's a Plotly-based interactive widget rendered inline.

**Layout:**
```
┌─────────────────────────────────────────────────────┐
│  Factor Panels (one row per continuous factor)       │
│  Temperature  ===●======= [95°C marked on -1..+1]  │
│  Pressure     =====●===== [3.2 bar]                 │
│  Speed        ======●==== [1850 rpm]                │
├─────────────────────────────────────────────────────┤
│  Response Trace Columns (one per response)           │
│  Metric A  ┌──────────────┐  Metric B  ┌──────────┐│
│  (visc.)   │ trace curve  │  (density) │ trace    ││
│            │ across Temp  │             │ curve    ││
│            └──────────────┘             └──────────┘│
│  1.27                   1850                       │
│  desirability ████████░░ 0.82   desir. ██████░░  0.71│
├─────────────────────────────────────────────────────┤
│  Overall Desirability D = 0.85  [Find Optimum]     │
└─────────────────────────────────────────────────────┘
```

**Interaction model:**
- Each factor has a slider. Dragging a slider updates ALL response predictions and ALL trace curves in real time.
- The trace curve for response R shows predicted R across the full range of that factor, holding all OTHER factors at their current slider positions.
- Below each response prediction, a desirability bar shows d_i (0-1). Red (<0.3), yellow (0.3-0.7), green (>0.7).
- Overall D = geometric mean of d_i.

**Implementation approach:**
Streamlit sliders trigger reruns. On each rerun, `profiler.py` computes:
1. Predicted responses at current slider positions
2. Trace data: 50 points across each factor's range with other factors held
3. Desirability values for each response

The trace curves are rendered as small Plotly line charts (one per factor-response pair in a grid layout).

**[Find Optimum]** runs `doe_optimize()` from the current slider positions as the starting point (warm start), then updates the sliders to the optimal values. The optimization uses the same Derringer-Suich multi-start approach as today.

### 5.5 Effects & Plots

Same Pareto and main effects plots as today, plus:
- **Interaction plot:** Two-factor interaction lines. For factors A and B: show response vs A at low B, center B, high B.
- Contour and surface plots shown for significant factors in RSM and mixture models.

---

## 6. Engine Modules — Detailed Specs

### 6.1 doe/analysis.py — Rewrite

**Public API (backward-compatible):**
- `fit_linear(factors, design, results, response_name, alpha=0.05) -> dict` — expanded return value
- `fit_rsm(factors, design, results, response_name, alpha=0.05) -> dict` — expanded return value
- `has_curvature(factorial_y, center_y, alpha=0.05) -> bool` — unchanged
- `predict_from_model(model, factors, point) -> float` — unchanged
- `anova_table(model_dict) -> pd.DataFrame` — **new**: extract ANOVA as a display-ready DataFrame

**Internal:**
- `_compute_anova(ols_result, X_cols) -> dict` — decompose OLS output into ANOVA components
- `_lack_of_fit(design, y, y_pred, factor_names, n_params) -> tuple[float, float]` — pure error vs model error F-test
- `_compute_studentized_residuals(ols_result) -> np.ndarray` — externally studentized

### 6.2 doe/residuals.py — New

**Public API:**
- `compute_residuals(y, y_pred, run_order=None) -> dict` — residuals, studentized residuals, predicted values
- `build_residual_plots(residuals_dict) -> go.Figure` — 2×2 Plotly subplot grid

**Internal:**
- `_shapiro_wilk_test(residuals) -> float` — normality p-value
- `_breusch_pagan_test(design_matrix, residuals) -> float` — heteroscedasticity p-value (optional, can skip for simplicity)
- `_durbin_watson(residuals) -> float` — autocorrelation in run order

### 6.3 doe/profiler.py — New

**Public API:**
- `compute_profile(factors, models, responses, slider_positions) -> dict`
    - Returns: `{responses: {response_name: {predicted, desirability, traces: {factor_name: [x_vals], [y_vals]}}}}`
- `compute_overall_desirability(individual_d) -> float` — re-export from optimization.py

**Internal:**
- `_trace_curve(factors, model, response, varying_factor, fixed_positions, n_points=50) -> tuple[list, list]`
- `_desirability_ramp_color(d) -> str` — hex color for desirability level

### 6.4 doe/evaluate.py — New

**Public API:**
- `evaluate_design(design_df, factors, model_order='linear') -> dict`
    - Returns: `{power: {effect_size_1sigma: float}, vif: {factor: float}, g_efficiency: float, alias_structure: str, warnings: [str]}`

**Internal:**
- `_compute_power(n_runs, n_params, effect_size, alpha=0.05) -> float`
- `_compute_vif(design_matrix) -> dict`
- `_compute_g_efficiency(design_matrix) -> float`

### 6.5 doe/designs.py — Extend

Add:
- `generate_ccd(factors, alpha='rotatable', n_center=3) -> pd.DataFrame` — Central Composite Design
    - alpha = 'rotatable' (default), 'orthogonal', 'face-centered' (α=1), or custom float
- `generate_simplex_lattice(factors, degree, n_center=0) -> pd.DataFrame` — Simplex lattice mixture (Phase 2)
- `generate_simplex_centroid(factors, n_center=0) -> pd.DataFrame` — Simplex centroid mixture (Phase 2)

Keep existing:
- `generate_full_factorial(factors, n_center=3) -> pd.DataFrame`
- `generate_fractional_factorial(factors, resolution=4) -> pd.DataFrame`
- `generate_box_behnken(factors, n_center=3) -> pd.DataFrame`
- `decode_to_actual(coded, factors) -> pd.DataFrame`
- `add_center_points(df, factor_names, n_center=3) -> pd.DataFrame`

### 6.6 doe/persistence.py — Extend

- Add `analysis` to `ALLOWED_COLUMNS` and `JSON_COLUMNS`
- Existing API unchanged

---

## 7. UI: doe_view.py — Rewrite

### 7.1 Entry Point

```python
def render_doe_page(repo: DataRepository):
    # Sidebar: session list, active session info, DESIGN/ANALYZE tabs
    # Main: render_design_tab() or render_analyze_tab()
```

### 7.2 Sidebar

```
┌─────────────────────┐
│ DOE SESSIONS         │
│ ┌──────────────────┐ │
│ │ [DESIGN] ANALYZE │ │   ← Tab buttons, primary=active
│ └──────────────────┘ │
│                       │
│ Active: "My DOE #3"   │
│ Status: analyzed      │
│ Type: RSM             │
│                       │
│ ───────────────────── │
│ Saved Sessions ▼      │
│ • My DOE #3 (today)   │
│ • Screening Run 1     │
│ • Formulation Test    │
│                       │
│ [+ New DOE] [Export]  │
└─────────────────────┘
```

### 7.3 State Management

```python
# Session state keys
"doe_active_tab"          # "design" | "analyze"
"doe_session_id"          # int — active session DB ID
"doe_session"             # dict — active session data (cached)
"doe_design_generated"    # bool — design matrix exists
"doe_results_entered"     # bool — response data entered
"doe_analysis_run"        # bool — analysis completed
"doe_profiler_positions"  # dict — {factor_name: coded_value} for profiler sliders
```

### 7.4 Design Tab Implementation

```python
def _render_design_tab(doe_repo):
    # Section 1: Setup (always visible)
    with st.expander("▸ SETUP", expanded=not design_exists):
        _render_factor_rows()
        _render_response_rows()

    # Section 2: Design Type
    with st.expander("▸ DESIGN TYPE", expanded=not design_exists):
        design_type = _render_design_type_selector()
        st.session_state["doe_design_type"] = design_type
        _render_design_config(design_type)

    if st.button("Generate Design", type="primary"):
        coded_df = _generate_design(...)
        diagnostics = evaluate_design(coded_df, factors)
        decoded_df = decode_to_actual(coded_df, factors)
        st.session_state["doe_design_generated"] = True
        # Save to DB
        doe_repo.update(sid, {"design": coded_df.to_dict("records"), "status": "designed"})

    if design_exists:
        # Section 3: Diagnostics
        with st.expander("▸ DESIGN DIAGNOSTICS"):
            _render_diagnostics(diagnostics)

        # Section 4: Run Sheet
        with st.expander("▸ RUN SHEET", expanded=True):
            _render_run_sheet(decoded_df, responses)
            # Download + Randomize buttons
```

### 7.5 Analyze Tab Implementation

```python
def _render_analyze_tab(doe_repo):
    # Section 1: Data Entry
    with st.expander("▸ DATA ENTRY", expanded=not results_exist):
        _render_data_entry(uploaded_csv, inline_table)

    if results_exist:
        if st.button("Run Analysis", type="primary"):
            for response in responses:
                model = fit_linear(factors, design, results, response["name"])
                anova[response["name"]] = model
                residuals[response["name"]] = compute_residuals(...)
            st.session_state["doe_analysis_run"] = True

    if analysis_run:
        # Section 2: ANOVA
        with st.expander("▸ ANOVA", expanded=True):
            _render_anova_tables(analysis_results)

        # Section 3: Residuals
        with st.expander("▸ RESIDUAL DIAGNOSTICS"):
            for response_name in response_names:
                fig = build_residual_plots(analysis[response_name]["residuals"])
                st.plotly_chart(fig)

        # Section 4: Effects & Plots
        with st.expander("▸ EFFECTS & PLOTS"):
            _render_pareto(...)
            _render_main_effects(...)
            _render_contour_surface(...)

        # Section 5: Profiler
        with st.expander("▸ PREDICTION PROFILER", expanded=True):
            _render_profiler(factors, responses, models)
```

### 7.6 Profiler UI

```python
def _render_profiler(factors, responses, models):
    # Initialize slider positions at center
    positions = st.session_state.get("doe_profiler_positions", {f["name"]: 0.0 for f in factors})

    # Row of factor sliders
    cols = st.columns(len(factors))
    for i, f in enumerate(factors):
        if f["type"] != "continuous":
            continue
        with cols[i]:
            positions[f["name"]] = st.slider(
                f["name"],
                min_value=-1.0, max_value=1.0, value=positions[f["name"]],
                step=0.01, key=f"profiler_{f['name']}"
            )

    # Compute profiles at current positions
    profile = compute_profile(factors, models, responses, positions)

    # Response trace columns
    resp_cols = st.columns(len(responses))
    for i, r in enumerate(responses):
        with resp_cols[i]:
            st.metric(r["name"], f"{profile[r['name']]['predicted']:.3f}")
            d = profile[r["name"]]["desirability"]
            st.progress(d, text=f"D = {d:.2f}")
            # Mini trace plots
            for f in factors:
                if f["type"] == "continuous":
                    trace = profile[r["name"]]["traces"][f["name"]]
                    fig = go.Figure(go.Scatter(x=trace["x"], y=trace["y"], mode="lines"))
                    fig.update_layout(height=120, margin=dict(l=20,r=20,t=10,b=30))
                    st.plotly_chart(fig, use_container_width=True)

    # Overall desirability + optimize button
    overall_d = compute_overall_desirability([profile[r["name"]]["desirability"] for r in responses])
    st.metric("Overall Desirability", f"D = {overall_d:.3f}")

    if st.button("Find Optimum", type="primary"):
        result = doe_optimize(factors, responses, models, n_starts=10)
        # Update slider positions to optimum
        for f in factors:
            opt_val = result["optimal_settings"].get(f["name"])
            # Map actual back to coded
            coded = (2 * (opt_val - f["low"]) / (f["high"] - f["low"])) - 1
            positions[f["name"]] = max(-1.0, min(1.0, coded))
        st.rerun()
```

---

## 8. Phase Plan

### Phase 1 (this implementation cycle): Core Platform + CCD

| Deliverable | Files |
|------------|-------|
| 2-tab architecture + sidebar | `doe_view.py` (rewrite) |
| ANOVA tables + lack-of-fit | `analysis.py` (rewrite) |
| Residual diagnostics (2×2) | `residuals.py` (new) |
| Prediction profiler | `profiler.py` (new) |
| Design diagnostics | `evaluate.py` (new) |
| CCD generation | `designs.py` (extend) |
| Improved factorial/BB (keep, add diagnostics) | `designs.py` (extend) |
| Persistence: analysis column | `persistence.py` (extend) |

**Phase 1 covers:** factorial, fractional, CCD, Box-Behnken — all with full ANOVA, residuals, and profiler.

### Phase 2: Mixture Designs

| Deliverable | Files |
|------------|-------|
| Simplex lattice generator | `designs.py` |
| Simplex centroid generator | `designs.py` |
| Mixture model fitting (Scheffé polynomials) | `analysis.py` |
| Ternary plot visualization | Visualization layer |

### Phase 3: D-Optimal + Split-Plot

| Deliverable | Files |
|------------|-------|
| D-optimal candidate-set exchange | `doptimal.py` (new) |
| Split-plot design | `splitplot.py` (new) |
| Mixed-model analysis (whole-plot + subplot error) | `analysis.py` |

---

## 9. Migration from Current DOE

### 9.1 Backward Compatibility

Existing `doe_sessions` rows in the DB remain valid. The new code:
- Reads old sessions (no `analysis` column, old `model` column) and maps them:
  - If `model` exists but `analysis` doesn't → construct basic `analysis` dict with coefficients only (no ANOVA, no residuals) → show a note: "Re-run analysis for full diagnostics"
  - If neither exists → show as "defined" or "designed" as before

### 9.2 What Gets Deleted

- The 6-step wizard flow (landing, separate define/design/capture/analyze/optimize pages) — replaced by 2 tabs
- `entry_type` 'screening' → renamed to 'fractional_factorial'
- Old `model` column → becomes `analysis` (auto-migrated on DB read)

### 9.3 What Stays

- `DoeRepository` SQLite pattern
- `_factorial.py` self-contained generators
- `optimization.py` Derringer-Suich multi-start
- `decode_to_actual()`, `add_center_points()`
- SPC data separate from DOE data (same db, different tables)

---

## 10. Testing Strategy

### 10.1 New Tests

| Module | Tests | What |
|--------|-------|------|
| `test_doe_anova.py` | ~8 | ANOVA decomposition, lack-of-fit, SS types |
| `test_doe_residuals.py` | ~6 | Studentized residuals, normality, plot builders |
| `test_doe_profiler.py` | ~5 | Trace curves, desirability ramp, profile computation |
| `test_doe_evaluate.py` | ~6 | Power, VIF, G-efficiency, alias display |
| `test_doe_ccd.py` | ~4 | CCD generation: rotatable, orthogonal, face-centered |
| `test_doe_mixture.py` | ~6 | Phase 2 — lattice, centroid, Scheffé models |
| `test_doe_analysis.py` | extend | Add ANOVA assertions to existing linear/RSM tests |

### 10.2 Updated Tests

- `test_doe_designs.py` — add CCD, mixture design tests
- `test_doe_persistence.py` — add `analysis` column CRUD
- `test_doe_integration.py` — full pipeline through profiler

**Target:** ~60+ DOE tests (up from today's ~24)

---

## 11. Risks & Trade-offs

| Risk | Mitigation |
|------|-----------|
| **Streamlit rerun overhead on profiler sliders** | Profiler is 50-point traces across factors — computationally cheap. If slow, debounce sliders with `st.session_state` |
| **Mixture designs are mathematically different** | Factor sum-to-1 constraint changes everything: design space is a simplex, models are Scheffé polynomials. Separate code paths in analysis.py |
| **D-optimal exchange algorithm complexity** | Federov or k-exchange is ~200 lines of NumPy. Build candidate set → greedy add → exchange to improve D-criterion |
| **Too many features, too little focus** | Phase gating. Phase 1 ships when ANOVA + residuals + profiler + CCD work. Mixture and D-optimal are separate phases |
| **Screen real estate on smaller monitors** | Each section is collapsible. The profiler has inline mini-charts. Full-width layout by default |

---

## 12. Spec Self-Review

- [x] No TBDs or TODOs — all module APIs specified
- [x] Architecture consistent with existing layered pattern
- [x] Data model changes specified (analysis JSON column)
- [x] Phase boundaries clear — Phase 1 is self-contained and shippable
- [x] Backward compatibility handled (old `model` → `analysis` migration)
- [x] Testing scope defined per module
- [x] Risk mitigations identified

---

*Spec written 2026-06-21. Review and approve before transitioning to implementation plan.*
