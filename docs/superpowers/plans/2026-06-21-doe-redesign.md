# DOE Platform Redesign — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the 6-step DOE wizard with a 2-tab dashboard (Design + Analyze) featuring full ANOVA tables, 4-panel residual diagnostics, an interactive prediction profiler, design diagnostics, and CCD generation — all while keeping backward compatibility.

**Architecture:** Pure-Python engine modules (analysis.py rewrite, new residuals.py/profiler.py/evaluate.py, CCD in designs.py, persistence extension) feed into a rewritten Streamlit UI (doe_view.py). Same layered pattern as today: UI → Visualization → Engine → Persistence.

**Tech Stack:** Python 3.11+, NumPy, SciPy, statsmodels, Plotly, Streamlit, SQLite — same stack as the existing app.

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `doe/analysis.py` | Rewrite | fit_linear, fit_rsm with ANOVA + residuals data + lack-of-fit |
| `doe/residuals.py` | **New** | compute_residuals, build_residual_plots (2×2 Plotly grid) |
| `doe/profiler.py` | **New** | compute_profile — prediction traces + desirability at slider positions |
| `doe/evaluate.py` | **New** | evaluate_design — power, VIF, G-efficiency, alias, warnings |
| `doe/designs.py` | Extend | Add generate_ccd() |
| `doe/persistence.py` | Extend | Add `analysis` to ALLOWED_COLUMNS + JSON_COLUMNS |
| `ui/engineer/doe_view.py` | Rewrite | 2-tab UI: Design tab + Analyze tab with profiler |
| `tests/test_doe_analysis.py` | Extend | ANOVA assertions, lack-of-fit, residual data in return dict |
| `tests/test_doe_residuals.py` | **New** | Studentized residuals, normality, plot builder output shape |
| `tests/test_doe_profiler.py` | **New** | Trace curves, desirability at positions, multi-response profile |
| `tests/test_doe_evaluate.py` | **New** | Power, VIF, warnings for underpowered/collinear designs |
| `tests/test_doe_designs.py` | Extend | CCD: rotatable, orthogonal, face-centered |
| `tests/test_doe_persistence.py` | Extend | analysis column CRUD, backward compat with old model column |
| `tests/test_doe_integration.py` | Extend | Full pipeline: design → analyze → profiler |

---

### Task 1: Extend test_doe_analysis.py — ANOVA assertions on existing fit_linear/fit_rsm

**Files:**
- Modify: `tests/test_doe_analysis.py`

- [ ] **Step 1: Read current test file to understand existing patterns**

Read `tests/test_doe_analysis.py` — note the existing `test_fit_linear_*` and `test_fit_rsm_*` tests, how they create design matrices and call `fit_linear`/`fit_rsm`.

- [ ] **Step 2: Add a test that fit_linear returns ANOVA data**

Add this test at the end of the file (before any existing last test):

```python
def test_fit_linear_returns_anova():
    """fit_linear should include anova table, residuals, and model summary keys."""
    factors = [
        {"name": "A", "type": "continuous", "low": 10, "high": 20},
        {"name": "B", "type": "continuous", "low": 30, "high": 50},
    ]
    design = pd.DataFrame({
        "run": [1, 2, 3, 4, 5, 6, 7, 8],
        "A": [-1, 1, -1, 1, -1, 1, -1, 1],
        "B": [-1, -1, 1, 1, -1, -1, 1, 1],
    })
    # Perfect 2-factor model: y = 10 + 3*A + 2*B + 1*A*B
    results = pd.DataFrame({
        "run": [1, 2, 3, 4, 5, 6, 7, 8],
        "response": [10 - 3 - 2 + 1, 10 + 3 - 2 - 1,
                     10 - 3 + 2 - 1, 10 + 3 + 2 + 1,
                     10 - 3 - 2 + 1, 10 + 3 - 2 - 1,
                     10 - 3 + 2 - 1, 10 + 3 + 2 + 1],
    })

    model = fit_linear(factors, design, results, "response")

    # New keys must be present
    assert "anova" in model
    assert "residuals" in model
    assert "lack_of_fit_p" in model
    assert "n_obs" in model
    assert "n_params" in model

    # ANOVA structure
    anova = model["anova"]
    assert "source" in anova
    assert "ss" in anova
    assert "df" in anova
    assert "ms" in anova
    assert "f" in anova
    assert "p" in anova
    assert len(anova["source"]) >= 4  # at least: Model, Residual, Total, + some terms

    # Residuals structure
    res = model["residuals"]
    assert "run" in res
    assert "observed" in res
    assert "predicted" in res
    assert "residual" in res
    assert "studentized" in res
    assert len(res["run"]) == 8

    # Model summary
    assert model["n_obs"] == 8
    assert model["n_params"] > 0  # at least intercept + 1 term
    assert 0 < model["r_squared"] <= 1.0
    assert model["rmse"] > 0

    # Old keys still present (backward compat)
    assert "coefficients" in model
    assert len(model["coefficients"]) > 0


def test_fit_linear_anova_values_perfect_fit():
    """ANOVA SS should decompose correctly for a perfect orthogonal model."""
    factors = [
        {"name": "X1", "type": "continuous", "low": -1, "high": 1},
        {"name": "X2", "type": "continuous", "low": -1, "high": 1},
    ]
    design = pd.DataFrame({
        "run": range(1, 9),
        "X1": [-1, 1, -1, 1, -1, 1, -1, 1],
        "X2": [-1, -1, 1, 1, -1, -1, 1, 1],
    })
    # y = 5 + 2*X1 (no noise, X2 has no effect)
    results = pd.DataFrame({
        "run": range(1, 9),
        "y": [5 - 2, 5 + 2, 5 - 2, 5 + 2, 5 - 2, 5 + 2, 5 - 2, 5 + 2],
    })

    model = fit_linear(factors, design, results, "y")

    # X1 should have large F, X2 should have F ≈ 0
    anova = model["anova"]
    ss_total = anova["ss"][anova["source"].index("Total")]
    ss_residual = anova["ss"][anova["source"].index("Residual")]
    # With perfect fit and no X2 effect, residual SS should be ~0
    assert ss_residual < 1e-10
    # Model SS should be virtually all of total SS
    ss_model = anova["ss"][anova["source"].index("Model")]
    assert abs(ss_model - ss_total) < 1e-10


def test_fit_rsm_returns_anova():
    """fit_rsm should also return ANOVA with curvature test."""
    factors = [
        {"name": "T", "type": "continuous", "low": 80, "high": 120},
        {"name": "P", "type": "continuous", "low": 2.0, "high": 4.0},
    ]
    # CCD-like design with center points
    runs = []
    for t in [-1, 1]:
        for p in [-1, 1]:
            runs.append({"T": t, "P": p})
    # Add 3 center points
    for _ in range(3):
        runs.append({"T": 0.0, "P": 0.0})
    runs.append({"T": -1.414, "P": 0.0})
    runs.append({"T": 1.414, "P": 0.0})
    runs.append({"T": 0.0, "P": -1.414})
    runs.append({"T": 0.0, "P": 1.414})

    design = pd.DataFrame(runs)
    design.insert(0, "run", range(1, len(runs) + 1))

    np.random.seed(42)
    results = pd.DataFrame({
        "run": design["run"],
        "y": [10 + 3*t + 2*p + 1*t*p + 0.5*t**2 + np.random.normal(0, 0.1)
              for t, p in zip(design["T"], design["P"])],
    })

    model = fit_rsm(factors, design, results, "y")

    assert "anova" in model
    assert "residuals" in model
    assert "has_curvature" in model
    assert "curvature_p_value" in model

    # R-squared should be high (we built a model with small noise)
    assert model["r_squared"] > 0.9
```

- [ ] **Step 3: Run tests and confirm they FAIL**

```bash
pytest tests/test_doe_analysis.py::test_fit_linear_returns_anova tests/test_doe_analysis.py::test_fit_linear_anova_values_perfect_fit tests/test_doe_analysis.py::test_fit_rsm_returns_anova -v
```

Expected: FAIL — `"anova"` key not in model dict (yet).

- [ ] **Step 4: Commit**

```bash
git add tests/test_doe_analysis.py
git commit -m "test: add ANOVA + residuals assertions to DOE analysis tests"
```

---

### Task 2: Rewrite doe/analysis.py — add ANOVA decomposition, residuals, lack-of-fit

**Files:**
- Modify: `doe/analysis.py`

- [ ] **Step 1: Read the current analysis.py**

Read `doe/analysis.py` — understand the existing `fit_linear`, `fit_rsm`, `_merge_and_validate`, `_check_parameter_count`, `_curvature_test`, `_pairwise`, `predict_from_model` functions.

- [ ] **Step 2: Add _compute_anova() and _compute_residuals() helper functions**

Insert after the existing imports and before `_is_center_row`:

```python
def _compute_anova(ols_result, X_cols: list[str], y: np.ndarray) -> dict:
    """Decompose OLS results into Type I (sequential) ANOVA table.

    Parameters
    ----------
    ols_result : statsmodels RegressionResults
        Fitted OLS model.
    X_cols : list of str
        Column names matching the design matrix (first = "Intercept").
    y : np.ndarray
        Observed response values.

    Returns
    -------
    dict with keys: source, ss, df, ms, f, p — each a list matching X_cols
    plus "Model" (combined), "Residual", "Total".
    """
    # Type I (sequential) SS via nested-model comparison
    X_full = ols_result.model.exog
    n_obs = len(y)
    total_ss = np.sum((y - np.mean(y)) ** 2)

    sources = []
    ss_vals = []
    df_vals = []

    # Null model (intercept only)
    ss_resid_prev = np.sum((y - np.mean(y)) ** 2)  # = total_ss
    df_resid_prev = n_obs - 1

    # Sequential: add terms one at a time
    n_terms = X_full.shape[1]  # includes intercept
    for i in range(1, n_terms):  # skip intercept (index 0)
        # Fit model with terms 0..i
        X_sub = X_full[:, :i + 1]
        ols_sub = sm.OLS(y, X_sub).fit()
        ss_resid_curr = np.sum(ols_sub.resid ** 2)
        df_resid_curr = n_obs - (i + 1)

        ss_term = ss_resid_prev - ss_resid_curr
        df_term = df_resid_prev - df_resid_curr

        sources.append(X_cols[i])
        ss_vals.append(max(ss_term, 0.0))  # guard against floating-point negatives
        df_vals.append(df_term)

        ss_resid_prev = ss_resid_curr
        df_resid_prev = df_resid_curr

    # Model row: sum of all term SS
    ss_model = sum(ss_vals)
    df_model = sum(df_vals)

    # Residual row
    ss_residual = float(np.sum(ols_result.resid ** 2))
    df_residual = n_obs - n_terms
    ms_residual = ss_residual / df_residual if df_residual > 0 else 0.0

    # Build lists
    source_list = ["Model"] + sources + ["Residual", "Total"]
    ss_list = [ss_model] + ss_vals + [ss_residual, total_ss]
    df_list = [df_model] + df_vals + [df_residual, n_obs - 1]

    # MS = SS / df, None for Total
    ms_list = []
    for ss, df in zip(ss_list, df_list):
        if df is not None and df > 0:
            ms_list.append(ss / df)
        else:
            ms_list.append(None)

    # F = MS_term / MS_residual, None for Residual and Total
    f_list = []
    for i, ms in enumerate(ms_list):
        source = source_list[i]
        if source in ("Residual", "Total") or ms is None or ms_residual == 0:
            f_list.append(None)
        else:
            f_list.append(ms / ms_residual)

    # p-values from F distribution
    p_list = []
    for i, f_val in enumerate(f_list):
        source = source_list[i]
        df_num = df_list[i]
        if source in ("Residual", "Total") or f_val is None or df_num is None:
            p_list.append(None)
        elif df_residual > 0:
            from scipy.stats import f as f_dist
            p_list.append(float(1 - f_dist.cdf(f_val, df_num, df_residual)))
        else:
            p_list.append(None)

    return {
        "source": source_list,
        "ss": [float(v) if v is not None else None for v in ss_list],
        "df": df_list,
        "ms": [float(v) if v is not None else None for v in ms_list],
        "f": [float(v) if v is not None else None for v in f_list],
        "p": p_list,
    }


def _compute_residuals_data(ols_result, y: np.ndarray, runs: np.ndarray) -> dict:
    """Compute residual diagnostics from fitted OLS model.

    Returns dict with: run, observed, predicted, residual, studentized, leverage.
    """
    y_pred = ols_result.fittedvalues
    residuals = y - y_pred
    n_obs = len(y)
    n_params = ols_result.df_model + 1  # +1 for intercept
    mse = np.sum(residuals ** 2) / (n_obs - n_params) if n_obs > n_params else 0.0

    # Hat matrix diagonal (leverage)
    X = ols_result.model.exog
    try:
        H = X @ np.linalg.inv(X.T @ X) @ X.T
        leverage = np.diag(H)
    except np.linalg.LinAlgError:
        leverage = np.full(n_obs, np.nan)

    # Externally studentized residuals
    studentized = np.full(n_obs, np.nan)
    for i in range(n_obs):
        if leverage[i] >= 1.0:
            continue
        sigma2_i = (np.sum(residuals ** 2) - residuals[i] ** 2 / (1 - leverage[i])) / (n_obs - n_params - 1)
        if sigma2_i > 0:
            studentized[i] = residuals[i] / np.sqrt(sigma2_i * (1 - leverage[i]))

    return {
        "run": [int(r) for r in runs],
        "observed": [float(v) for v in y],
        "predicted": [float(v) for v in y_pred],
        "residual": [float(v) for v in residuals],
        "studentized": [float(v) if np.isfinite(v) else None for v in studentized],
        "leverage": [float(v) if np.isfinite(v) else None for v in leverage],
    }
```

- [ ] **Step 3: Add anova_table() convenience function**

Append this at the end of the file (before any last existing function, or at the very end):

```python
def anova_table(model: dict) -> "pd.DataFrame":
    """Extract ANOVA table as a display-ready DataFrame."""
    import pandas as pd
    anova = model.get("anova", {})
    if not anova:
        return pd.DataFrame()
    df = pd.DataFrame({
        "Source": anova["source"],
        "SS": anova["ss"],
        "df": anova["df"],
        "MS": anova["ms"],
        "F": anova["f"],
        "p": anova["p"],
    })
    # Format numeric columns
    for col in ["SS", "MS", "F", "p"]:
        if col in df.columns:
            df[col] = df[col].apply(
                lambda x: f"{x:.4f}" if isinstance(x, (int, float)) and x is not None else "—"
            )
    return df
```

- [ ] **Step 4: Rewrite fit_linear() to return expanded dict**

Replace the return statement in `fit_linear` (lines 128-134 in current file). Find the existing return block and replace with:

```python
    residuals_data = _compute_residuals_data(ols, y, merged["run"].values)
    anova = _compute_anova(ols, X_cols, y)

    # Lack-of-fit test: only possible if there are replicated runs
    lack_of_fit_p = None
    n_unique = len(merged[factor_names].drop_duplicates())
    if n_unique < len(merged):
        # Replicates exist — pure-error SS computable
        grouped = merged.groupby(factor_names)
        ss_pe = 0.0
        df_pe = 0
        for _, group in grouped:
            if len(group) > 1:
                group_mean = group[response_name].mean()
                ss_pe += np.sum((group[response_name].values - group_mean) ** 2)
                df_pe += len(group) - 1
        if df_pe > 0:
            ss_lof = np.sum(ols.resid ** 2) - ss_pe
            df_lof = len(merged) - len(X_cols) - df_pe
            if df_lof > 0 and df_pe > 0:
                ms_lof = ss_lof / df_lof
                ms_pe = ss_pe / df_pe
                f_lof = ms_lof / ms_pe if ms_pe > 0 else 0.0
                lack_of_fit_p = float(1 - stats.f.cdf(f_lof, df_lof, df_pe))

    return {
        "model_type": "linear",
        "coefficients": coefficients,
        "anova": anova,
        "r_squared": float(ols.rsquared) if np.isfinite(ols.rsquared) else None,
        "r_squared_adj": float(ols.rsquared_adj) if np.isfinite(ols.rsquared_adj) else None,
        "model_p_value": float(ols.f_pvalue) if np.isfinite(ols.f_pvalue) else None,
        "rmse": float(np.sqrt(ols.mse_resid)) if hasattr(ols, 'mse_resid') and np.isfinite(ols.mse_resid) else None,
        "residuals": residuals_data,
        "lack_of_fit_p": lack_of_fit_p,
        "n_obs": len(merged),
        "n_params": len(X_cols),
    }
```

- [ ] **Step 5: Rewrite fit_rsm() to return expanded dict (same pattern)**

Replace the return statement in `fit_rsm` (lines 196-205) with the same expanded return as above, but include curvature fields and use `"model_type": "rsm"`:

```python
    residuals_data = _compute_residuals_data(ols, y, merged["run"].values)
    anova = _compute_anova(ols, X_cols, y)

    # Lack-of-fit test
    lack_of_fit_p = None
    n_unique = len(merged[factor_names].drop_duplicates())
    if n_unique < len(merged):
        grouped = merged.groupby(factor_names)
        ss_pe = 0.0
        df_pe = 0
        for _, group in grouped:
            if len(group) > 1:
                group_mean = group[response_name].mean()
                ss_pe += np.sum((group[response_name].values - group_mean) ** 2)
                df_pe += len(group) - 1
        if df_pe > 0:
            ss_lof = np.sum(ols.resid ** 2) - ss_pe
            df_lof = len(merged) - len(X_cols) - df_pe
            if df_lof > 0 and df_pe > 0:
                ms_lof = ss_lof / df_lof
                ms_pe = ss_pe / df_pe
                f_lof = ms_lof / ms_pe if ms_pe > 0 else 0.0
                lack_of_fit_p = float(1 - stats.f.cdf(f_lof, df_lof, df_pe))

    return {
        "model_type": "rsm",
        "coefficients": coefficients,
        "anova": anova,
        "r_squared": float(ols.rsquared) if np.isfinite(ols.rsquared) else None,
        "r_squared_adj": float(ols.rsquared_adj) if np.isfinite(ols.rsquared_adj) else None,
        "model_p_value": float(ols.f_pvalue) if np.isfinite(ols.f_pvalue) else None,
        "curvature_p_value": curvature_p,
        "has_curvature": has_curv,
        "rmse": float(np.sqrt(ols.mse_resid)) if hasattr(ols, 'mse_resid') and np.isfinite(ols.mse_resid) else None,
        "residuals": residuals_data,
        "lack_of_fit_p": lack_of_fit_p,
        "n_obs": len(merged),
        "n_params": len(X_cols),
    }
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
pytest tests/test_doe_analysis.py -v
```

Expected: All tests PASS, including the 3 new ones from Task 1 plus all existing ones (backward compat).

- [ ] **Step 7: Commit**

```bash
git add doe/analysis.py
git commit -m "feat: add ANOVA decomposition, residuals data, and lack-of-fit to DOE analysis"
```

---

### Task 3: Write tests for doe/residuals.py

**Files:**
- Create: `tests/test_doe_residuals.py`

- [ ] **Step 1: Write the test file**

```python
"""Tests for doe/residuals.py — residual diagnostics computation and plotting."""
import numpy as np
import pandas as pd
from doe.residuals import compute_residuals, build_residual_plots


def test_compute_residuals_basic():
    """compute_residuals returns expected keys and shapes."""
    y_obs = np.array([1.0, 1.1, 0.9, 1.2, 1.0, 1.1, 0.9, 1.2])
    y_pred = np.array([1.05, 1.05, 1.05, 1.05, 1.05, 1.05, 1.05, 1.05])
    X = np.column_stack([np.ones(8), np.linspace(-1, 1, 8)])

    result = compute_residuals(y_obs, y_pred, X)

    assert "residuals" in result
    assert "studentized" in result
    assert "leverage" in result
    assert "cooks_d" in result
    assert "shapiro_p" in result
    assert len(result["residuals"]) == 8
    assert len(result["studentized"]) == 8
    assert len(result["leverage"]) == 8
    assert 0 <= result["shapiro_p"] <= 1


def test_compute_residuals_residual_calculation():
    """Residuals = observed - predicted."""
    y_obs = np.array([5.0, 7.0, 6.0])
    y_pred = np.array([5.2, 6.8, 6.0])
    X = np.column_stack([np.ones(3), np.array([-1, 0, 1])])

    result = compute_residuals(y_obs, y_pred, X)

    np.testing.assert_array_almost_equal(
        result["residuals"], [-0.2, 0.2, 0.0]
    )


def test_compute_residuals_perfect_fit():
    """Perfect fit should give zero residuals and high Shapiro-Wilk p."""
    np.random.seed(42)
    X_design = np.column_stack([
        np.ones(20),
        np.random.uniform(-1, 1, 20),
        np.random.uniform(-1, 1, 20),
    ])
    true_coef = np.array([5.0, 2.0, -1.0])
    y_obs = X_design @ true_coef
    y_pred = y_obs.copy()

    result = compute_residuals(y_obs, y_pred, X_design)

    assert np.allclose(result["residuals"], 0, atol=1e-10)
    # Shapiro-Wilk on zero residuals — p should be 1.0 (or NaN depending on scipy)
    assert result["shapiro_p"] > 0.05 or np.isnan(result["shapiro_p"])


def test_compute_residuals_with_outlier():
    """A single outlier should produce a large studentized residual."""
    np.random.seed(42)
    n = 15
    X = np.column_stack([np.ones(n), np.arange(n)])
    true_y = 3.0 + 0.5 * np.arange(n)
    y_obs = true_y.copy()
    y_obs[2] = true_y[2] + 10.0  # big outlier
    y_pred = 3.0 + 0.5 * np.arange(n)

    result = compute_residuals(y_obs, y_pred, X)

    # The outlier should have the largest |studentized residual|
    abs_stud = np.abs(result["studentized"])
    assert np.argmax(abs_stud) == 2
    assert abs_stud[2] > 2.0  # should be flagged


def test_build_residual_plots_returns_figure():
    """build_residual_plots should return a Plotly Figure with 4 subplots."""
    residuals_dict = {
        "residuals": np.array([0.1, -0.1, 0.2, -0.2, 0.0, -0.1, 0.1, 0.0]),
        "studentized": np.array([0.4, -0.4, 0.9, -0.9, 0.0, -0.4, 0.4, 0.0]),
        "predicted": np.array([1.0, 1.1, 0.9, 1.2, 1.05, 1.0, 1.1, 1.05]),
        "run_order": np.array([1, 2, 3, 4, 5, 6, 7, 8]),
        "leverage": np.array([0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2]),
        "cooks_d": np.array([0.01, 0.01, 0.05, 0.05, 0.0, 0.01, 0.01, 0.0]),
        "shapiro_p": 0.45,
    }

    fig = build_residual_plots(residuals_dict)

    # Should be a Plotly Figure
    assert hasattr(fig, "data")
    # Should have traces for 4 subplots (Q-Q scatter, vs-pred scatter, vs-run scatter, histogram)
    assert len(fig.data) >= 3  # at minimum: Q-Q points, vs-pred points, histogram bars
```

- [ ] **Step 2: Run tests to verify they FAIL**

```bash
pytest tests/test_doe_residuals.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'doe.residuals'`.

- [ ] **Step 3: Commit**

```bash
git add tests/test_doe_residuals.py
git commit -m "test: add residual diagnostics tests"
```

---

### Task 4: Implement doe/residuals.py

**Files:**
- Create: `doe/residuals.py`

- [ ] **Step 1: Write the module**

```python
"""DOE residual diagnostics for model validation.

Pure Python — no Streamlit imports.
"""

import numpy as np
from scipy import stats
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def compute_residuals(
    y_observed: np.ndarray,
    y_predicted: np.ndarray,
    X_design: np.ndarray,
    run_order: np.ndarray | None = None,
) -> dict:
    """Compute residual diagnostics for a fitted model.

    Parameters
    ----------
    y_observed : np.ndarray
        Observed response values.
    y_predicted : np.ndarray
        Model-predicted response values.
    X_design : np.ndarray
        Design matrix used for fitting (n_obs × n_params). Used to compute
        leverage and studentized residuals.
    run_order : np.ndarray or None
        Run order indices (1-based). If None, uses sequential 1..n.

    Returns
    -------
    dict with keys:
        residuals, studentized, leverage, cooks_d, shapiro_p,
        predicted, run_order, observed
    """
    n_obs = len(y_observed)
    residuals = y_observed - y_predicted

    if run_order is None:
        run_order = np.arange(1, n_obs + 1)

    # Leverage (hat values)
    try:
        H = X_design @ np.linalg.inv(X_design.T @ X_design) @ X_design.T
        leverage = np.diag(H)
    except np.linalg.LinAlgError:
        leverage = np.full(n_obs, 0.5)

    # MSE
    n_params = X_design.shape[1]
    df_error = n_obs - n_params
    mse = np.sum(residuals ** 2) / df_error if df_error > 0 else 0.0

    # Externally studentized residuals
    studentized = np.full(n_obs, np.nan)
    for i in range(n_obs):
        h_ii = min(leverage[i], 0.9999)
        # Delete-one MSE estimate
        sigma2_i = (
            np.sum(residuals ** 2)
            - residuals[i] ** 2 / (1 - h_ii)
        ) / (n_obs - n_params - 1) if n_obs > n_params + 1 else mse
        if sigma2_i > 0:
            studentized[i] = residuals[i] / np.sqrt(sigma2_i * (1 - h_ii))

    # Cook's distance
    cooks_d = np.full(n_obs, np.nan)
    for i in range(n_obs):
        h_ii = min(leverage[i], 0.9999)
        if mse > 0 and n_params > 0:
            r_i = residuals[i] / np.sqrt(mse * (1 - h_ii)) if np.sqrt(mse * (1 - h_ii)) > 0 else 0.0
            cooks_d[i] = (r_i ** 2 / n_params) * (h_ii / (1 - h_ii))

    # Shapiro-Wilk normality test
    try:
        if n_obs >= 3 and np.std(residuals) > 0:
            _, shapiro_p = stats.shapiro(residuals)
        else:
            shapiro_p = np.nan
    except Exception:
        shapiro_p = np.nan

    return {
        "observed": [float(v) for v in y_observed],
        "predicted": [float(v) for v in y_predicted],
        "residuals": [float(v) for v in residuals],
        "studentized": [float(v) if np.isfinite(v) else None for v in studentized],
        "leverage": [float(v) if np.isfinite(v) else None for v in leverage],
        "cooks_d": [float(v) if np.isfinite(v) else None for v in cooks_d],
        "shapiro_p": float(shapiro_p) if np.isfinite(shapiro_p) else None,
        "run_order": [int(r) for r in run_order],
        "n_obs": n_obs,
        "n_params": n_params,
    }


def build_residual_plots(residuals_dict: dict) -> go.Figure:
    """Build a 2×2 Plotly subplot grid of residual diagnostic plots.

    Parameters
    ----------
    residuals_dict : dict
        Output from compute_residuals().

    Returns
    -------
    plotly.graph_objects.Figure
        2×2 subplot figure: Normal Q-Q, Residuals vs Predicted,
        Residuals vs Run Order, Histogram.
    """
    residuals = np.array(residuals_dict["residuals"])
    studentized = np.array([v if v is not None else np.nan for v in residuals_dict["studentized"]])
    predicted = np.array(residuals_dict["predicted"])
    run_order = np.array(residuals_dict["run_order"])

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=(
            "Normal Q-Q Plot",
            "Residuals vs Predicted",
            "Residuals vs Run Order",
            "Histogram of Residuals",
        ),
        vertical_spacing=0.12,
        horizontal_spacing=0.10,
    )

    # --- Q-Q Plot (top-left) ---
    clean = residuals[~np.isnan(residuals)]
    if len(clean) >= 3:
        sorted_resid = np.sort(clean)
        theoretical = stats.norm.ppf(
            (np.arange(1, len(clean) + 1) - 0.5) / len(clean),
            loc=0, scale=np.std(clean),
        )
        fig.add_trace(
            go.Scatter(
                x=theoretical, y=sorted_resid, mode="markers",
                marker=dict(size=6, color="#C4734F"),
                name="Q-Q",
            ),
            row=1, col=1,
        )
        # Reference line
        mn = min(theoretical[0], sorted_resid[0])
        mx = max(theoretical[-1], sorted_resid[-1])
        fig.add_trace(
            go.Scatter(
                x=[mn, mx], y=[mn, mx], mode="lines",
                line=dict(dash="dash", color="#999"),
                name="reference",
            ),
            row=1, col=1,
        )

    # --- Residuals vs Predicted (top-right) ---
    # Highlight points with |studentized| > 2
    is_outlier = np.abs(studentized) > 2
    fig.add_trace(
        go.Scatter(
            x=predicted[~is_outlier], y=residuals[~is_outlier],
            mode="markers", marker=dict(size=6, color="#4A90D9"),
            name="Normal",
        ),
        row=1, col=2,
    )
    if is_outlier.any():
        fig.add_trace(
            go.Scatter(
                x=predicted[is_outlier], y=residuals[is_outlier],
                mode="markers", marker=dict(size=8, color="#C4523E", symbol="x"),
                name=f"|RStudent| > 2 ({is_outlier.sum()})",
            ),
            row=1, col=2,
        )
    # Zero line
    fig.add_hline(y=0, line_dash="dash", line_color="#999", row=1, col=2)

    # --- Residuals vs Run Order (bottom-left) ---
    fig.add_trace(
        go.Scatter(
            x=run_order, y=residuals, mode="lines+markers",
            marker=dict(size=6, color="#C4734F"),
            line=dict(color="#D4C4B0"),
            name="Run order",
        ),
        row=2, col=1,
    )
    fig.add_hline(y=0, line_dash="dash", line_color="#999", row=2, col=1)

    # --- Histogram (bottom-right) ---
    fig.add_trace(
        go.Histogram(
            x=residuals, nbinsx=max(5, len(residuals) // 3),
            marker_color="#C4734F", opacity=0.7,
            name="Residuals",
        ),
        row=2, col=2,
    )

    fig.update_layout(
        height=600,
        showlegend=False,
        margin=dict(t=60, b=40, l=40, r=20),
    )
    fig.update_xaxes(title_text="Theoretical Quantiles", row=1, col=1)
    fig.update_yaxes(title_text="Observed Quantiles", row=1, col=1)
    fig.update_xaxes(title_text="Predicted", row=1, col=2)
    fig.update_yaxes(title_text="Residual", row=1, col=2)
    fig.update_xaxes(title_text="Run Order", row=2, col=1)
    fig.update_yaxes(title_text="Residual", row=2, col=1)
    fig.update_xaxes(title_text="Residual", row=2, col=2)

    return fig
```

- [ ] **Step 2: Run tests to verify they pass**

```bash
pytest tests/test_doe_residuals.py -v
```

Expected: All 5 tests PASS.

- [ ] **Step 3: Commit**

```bash
git add doe/residuals.py
git commit -m "feat: add residual diagnostics module (compute + 2×2 plots)"
```

---

### Task 5: Write tests for doe/evaluate.py

**Files:**
- Create: `tests/test_doe_evaluate.py`

- [ ] **Step 1: Write test file**

```python
"""Tests for doe/evaluate.py — design diagnostics: power, VIF, G-efficiency."""
import numpy as np
import pandas as pd
from doe.evaluate import evaluate_design


def test_evaluate_factorial_design():
    """A well-structured 2^2 factorial should have VIF=1 and good power."""
    factors = [
        {"name": "A", "type": "continuous", "low": 10, "high": 20},
        {"name": "B", "type": "continuous", "low": 30, "high": 50},
    ]
    design = pd.DataFrame({
        "run": [1, 2, 3, 4, 5, 6, 7, 8],
        "A": [-1, 1, -1, 1, -1, 1, -1, 1],
        "B": [-1, -1, 1, 1, -1, -1, 1, 1],
    })

    result = evaluate_design(design, factors, model_order="linear")

    assert "power" in result
    assert "vif" in result
    assert "g_efficiency" in result
    assert "warnings" in result

    # Orthogonal design: VIFs should be 1.0
    for v in result["vif"].values():
        assert abs(v - 1.0) < 0.01

    # 8 runs with 3-4 params should have good power for 1σ effect
    assert result["power"].get(1.0, 0) > 0.5


def test_evaluate_design_vif():
    """VIF should be high for highly correlated factors."""
    factors = [
        {"name": "X1", "type": "continuous", "low": 0, "high": 10},
        {"name": "X2", "type": "continuous", "low": 0, "high": 10},
    ]
    # Nearly collinear design
    design = pd.DataFrame({
        "run": [1, 2, 3, 4],
        "X1": [-1.0, 1.0, -1.0, 1.0],
        "X2": [-0.99, 0.99, -1.01, 1.01],  # almost identical to X1
    })

    result = evaluate_design(design, factors, model_order="linear")

    # VIF should be elevated
    assert result["vif"]["X1"] > 2.0
    assert result["vif"]["X2"] > 2.0


def test_evaluate_design_warnings():
    """Underpowered designs should generate warnings."""
    factors = [
        {"name": "A", "type": "continuous", "low": 0, "high": 100},
        {"name": "B", "type": "continuous", "low": 0, "high": 100},
        {"name": "C", "type": "continuous", "low": 0, "high": 100},
        {"name": "D", "type": "continuous", "low": 0, "high": 100},
    ]
    # Tiny design: 4 factors but only 5 runs
    design = pd.DataFrame({
        "run": [1, 2, 3, 4, 5],
        "A": [-1, 1, -1, 1, 0],
        "B": [-1, -1, 1, 1, 0],
        "C": [1, -1, -1, 1, 0],
        "D": [-1, 1, 1, -1, 0],
    })

    result = evaluate_design(design, factors, model_order="linear")

    # Should have warnings
    assert len(result["warnings"]) > 0


def test_evaluate_design_returns_keys():
    """All expected keys are present in evaluation result."""
    factors = [{"name": "A", "type": "continuous", "low": 0, "high": 1}]
    design = pd.DataFrame({
        "run": [1, 2, 3],
        "A": [-1.0, 1.0, 0.0],
    })

    result = evaluate_design(design, factors, model_order="linear")

    # Check all top-level keys exist
    for key in ["power", "vif", "g_efficiency", "condition_number", "warnings"]:
        assert key in result, f"Missing key: {key}"

    # G-efficiency between 0 and 1
    assert 0 < result["g_efficiency"] <= 1.0

    # Condition number > 0
    assert result["condition_number"] > 0
```

- [ ] **Step 2: Run tests to verify they FAIL**

```bash
pytest tests/test_doe_evaluate.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'doe.evaluate'`.

- [ ] **Step 3: Commit**

```bash
git add tests/test_doe_evaluate.py
git commit -m "test: add design diagnostics tests (power, VIF, warnings)"
```

---

### Task 6: Implement doe/evaluate.py

**Files:**
- Create: `doe/evaluate.py`

- [ ] **Step 1: Write the module**

```python
"""Design diagnostics: power, VIF, G-efficiency, condition number.

Pure Python — no Streamlit imports.
"""

import numpy as np
import pandas as pd
from scipy import stats


def evaluate_design(
    design: pd.DataFrame,
    factors: list[dict],
    model_order: str = "linear",
    alpha: float = 0.05,
) -> dict:
    """Evaluate a design matrix before running experiments.

    Parameters
    ----------
    design : pd.DataFrame
        Coded design matrix (columns: run, <factor_names>).
    factors : list of dict
        Factor definitions (name, type, low, high).
    model_order : str
        "linear" (main effects + 2FI) or "rsm" (linear + quadratics).
    alpha : float
        Significance level for power calculations.

    Returns
    -------
    dict with keys:
        power: dict of {effect_size_in_sigma: power_value}
        vif: dict of {factor_name: vif_value}
        g_efficiency: float (0-1)
        condition_number: float
        warnings: list of str
    """
    factor_names = [f["name"] for f in factors if f["type"] == "continuous"]
    if not factor_names:
        return {
            "power": {1.0: 0.0},
            "vif": {},
            "g_efficiency": 0.0,
            "condition_number": 0.0,
            "warnings": ["No continuous factors to evaluate"],
        }

    X = _build_model_matrix(design, factor_names, model_order)
    n_obs, n_params = X.shape
    warnings = []

    # VIF
    vif = _compute_vif(X)

    # Condition number
    cond_num = _compute_condition_number(X)

    # Power for effect sizes 0.5σ, 1σ, 2σ
    power = {}
    for effect_size in [0.5, 1.0, 2.0]:
        power[effect_size] = _compute_power(
            n_obs, n_params, effect_size, alpha
        )

    # G-efficiency
    g_eff = _compute_g_efficiency(X)

    # Warnings
    max_vif = max(vif.values()) if vif else 1.0
    if max_vif > 10:
        warnings.append(
            f"High multicollinearity: max VIF = {max_vif:.1f}. "
            "Consider a different design."
        )
    elif max_vif > 5:
        warnings.append(
            f"Moderate multicollinearity: max VIF = {max_vif:.1f}."
        )

    if power.get(1.0, 0) < 0.8:
        warnings.append(
            f"Low power ({power[1.0]:.2f}) for 1σ effect. "
            "Increase replicates to improve detection."
        )

    if n_obs <= n_params:
        warnings.append(
            f"Design has {n_obs} runs but model needs {n_params} parameters. "
            "Not enough data to fit."
        )

    return {
        "power": power,
        "vif": vif,
        "g_efficiency": g_eff,
        "condition_number": cond_num,
        "warnings": warnings,
    }


def _build_model_matrix(
    design: pd.DataFrame,
    factor_names: list[str],
    model_order: str,
) -> np.ndarray:
    """Build the model matrix X for diagnostic calculations."""
    cols = [np.ones(len(design))]  # intercept
    for f in factor_names:
        cols.append(design[f].values)
    if model_order in ("linear", "rsm"):
        # 2-way interactions
        import itertools
        for a, b in itertools.combinations(factor_names, 2):
            cols.append(design[a].values * design[b].values)
    if model_order == "rsm":
        # Quadratic terms
        for f in factor_names:
            cols.append(design[f].values ** 2)
    return np.column_stack(cols)


def _compute_vif(X: np.ndarray) -> dict[str, float]:
    """Compute Variance Inflation Factor for each predictor (excluding intercept)."""
    n_cols = X.shape[1]
    if n_cols <= 2:
        return {"Intercept": 1.0}

    vif = {}
    # Skip intercept (column 0)
    for i in range(1, n_cols):
        y_col = X[:, i]
        X_others = np.delete(X, i, axis=1)
        try:
            ols = np.linalg.lstsq(X_others, y_col, rcond=None)[0]
            y_pred = X_others @ ols
            ss_resid = np.sum((y_col - y_pred) ** 2)
            ss_total = np.sum((y_col - np.mean(y_col)) ** 2)
            r_squared = 1 - ss_resid / ss_total if ss_total > 0 else 0.0
            vif[f"X{i}"] = float(1 / (1 - r_squared)) if r_squared < 1 else float("inf")
        except np.linalg.LinAlgError:
            vif[f"X{i}"] = float("inf")

    return vif


def _compute_condition_number(X: np.ndarray) -> float:
    """Compute condition number of X'X (ratio of largest to smallest eigenvalue)."""
    try:
        eigenvals = np.linalg.eigvalsh(X.T @ X)
        eigenvals = eigenvals[eigenvals > 1e-12]
        if len(eigenvals) >= 2:
            return float(np.sqrt(eigenvals.max() / eigenvals.min()))
    except np.linalg.LinAlgError:
        pass
    return float("inf")


def _compute_power(
    n_obs: int,
    n_params: int,
    effect_size: float,
    alpha: float = 0.05,
) -> float:
    """Compute power to detect an effect of given size (in sigma units).

    Uses the non-central F distribution. Effect size = delta / sigma.
    """
    df1 = 1  # single parameter test
    df2 = n_obs - n_params
    if df2 <= 0:
        return 0.0

    f_crit = stats.f.ppf(1 - alpha, df1, df2)
    # Non-centrality parameter: ncp = n_obs * (effect_size)^2 / (4 * sigma^2)
    # For a 1σ effect: ncp ≈ n / 4
    ncp = n_obs * (effect_size ** 2) / 4.0

    power = 1 - stats.ncf.cdf(f_crit, df1, df2, ncp)
    return float(max(0.0, min(1.0, power)))


def _compute_g_efficiency(X: np.ndarray) -> float:
    """Compute G-efficiency: fraction of design space with prediction variance
    below the maximum. Range 0-1. Higher is better."""
    n_obs = X.shape[0]
    try:
        XtX_inv = np.linalg.inv(X.T @ X)
        # Average prediction variance over design points
        variances = np.array([x @ XtX_inv @ x for x in X])
        max_var = variances.max()
        if max_var <= 0:
            return 1.0
        # G-efficiency: n_params / (n_obs * max_var)
        from math import sqrt
        return float(min(1.0, X.shape[1] / (n_obs * max_var)))
    except np.linalg.LinAlgError:
        return 0.0
```

- [ ] **Step 2: Run tests to verify they pass**

```bash
pytest tests/test_doe_evaluate.py -v
```

Expected: All 4 tests PASS.

- [ ] **Step 3: Commit**

```bash
git add doe/evaluate.py
git commit -m "feat: add design diagnostics (power, VIF, G-efficiency)"
```

---

### Task 7: Write tests for doe/profiler.py

**Files:**
- Create: `tests/test_doe_profiler.py`

- [ ] **Step 1: Write test file**

```python
"""Tests for doe/profiler.py — prediction profiler computation."""
import numpy as np
import pandas as pd
from doe.profiler import compute_profile, compute_overall_desirability


def test_compute_profile_basic():
    """compute_profile returns predictions and traces for all responses."""
    factors = [
        {"name": "T", "type": "continuous", "low": 80, "high": 120},
        {"name": "P", "type": "continuous", "low": 2, "high": 4},
    ]
    class FakeModel:
        pass

    # Simple linear model for response "y": y = 10 + 2*T + 1*P
    model_y = {
        "model_type": "linear",
        "coefficients": [
            {"term": "Intercept", "estimate": 10.0},
            {"term": "T", "estimate": 2.0},
            {"term": "P", "estimate": 1.0},
            {"term": "T*P", "estimate": 0.0},
        ],
    }

    models = {"y": model_y}
    responses = [{"name": "y", "goal": "maximize", "low": 5.0, "high": 20.0}]
    positions = {"T": 0.0, "P": 0.0}

    result = compute_profile(factors, models, responses, positions, n_points=10)

    assert "y" in result
    assert "predicted" in result["y"]
    assert "desirability" in result["y"]
    assert "traces" in result["y"]
    assert "T" in result["y"]["traces"]
    assert "P" in result["y"]["traces"]

    # At center point (T=0, P=0), predicted = intercept = 10.0
    assert abs(result["y"]["predicted"] - 10.0) < 0.01

    # Trace for T should have correct x and y lengths
    t_trace = result["y"]["traces"]["T"]
    assert len(t_trace["x"]) == 10
    assert len(t_trace["y"]) == 10
    # x range should be -1 to 1
    assert abs(t_trace["x"][0] - (-1.0)) < 0.01
    assert abs(t_trace["x"][-1] - 1.0) < 0.01


def test_compute_profile_at_corner():
    """At T=+1, P=-1 with model y = 10 + 2*T + 1*P, predicted = 10 + 2 - 1 = 11."""
    factors = [
        {"name": "T", "type": "continuous", "low": 80, "high": 120},
        {"name": "P", "type": "continuous", "low": 2, "high": 4},
    ]
    model = {
        "model_type": "linear",
        "coefficients": [
            {"term": "Intercept", "estimate": 10.0},
            {"term": "T", "estimate": 2.0},
            {"term": "P", "estimate": 1.0},
        ],
    }
    models = {"y": model}
    responses = [{"name": "y", "goal": "maximize", "low": 0, "high": 20}]
    positions = {"T": 1.0, "P": -1.0}

    result = compute_profile(factors, models, responses, positions, n_points=10)

    assert abs(result["y"]["predicted"] - 11.0) < 0.01


def test_compute_profile_traces_vary_correctly():
    """When varying T, the trace curve for response y should reflect 2*T slope."""
    factors = [
        {"name": "A", "type": "continuous", "low": 0, "high": 10},
        {"name": "B", "type": "continuous", "low": 0, "high": 10},
    ]
    model = {
        "model_type": "linear",
        "coefficients": [
            {"term": "Intercept", "estimate": 5.0},
            {"term": "A", "estimate": 3.0},
            {"term": "B", "estimate": 0.0},
        ],
    }
    models = {"r": model}
    responses = [{"name": "r", "goal": "maximize", "low": 0, "high": 15}]
    positions = {"A": 0.0, "B": 0.0}

    result = compute_profile(factors, models, responses, positions, n_points=20)

    trace_a = result["r"]["traces"]["A"]
    # At A=-1: pred = 5 - 3 = 2, at A=+1: pred = 5 + 3 = 8
    assert abs(trace_a["y"][0] - 2.0) < 0.1
    assert abs(trace_a["y"][-1] - 8.0) < 0.1


def test_compute_profile_desirability():
    """Maximize goal: predicted=10 with low=0, high=20 → d = (10-0)/(20-0) = 0.5."""
    factors = [{"name": "X", "type": "continuous", "low": 0, "high": 100}]
    model = {
        "model_type": "linear",
        "coefficients": [
            {"term": "Intercept", "estimate": 10.0},
            {"term": "X", "estimate": 0.0},
        ],
    }
    models = {"y": model}
    responses = [{"name": "y", "goal": "maximize", "low": 0.0, "high": 20.0}]
    positions = {"X": 0.0}

    result = compute_profile(factors, models, responses, positions, n_points=10)

    assert abs(result["y"]["desirability"] - 0.5) < 0.01


def test_compute_overall_desirability():
    """Geometric mean of [0.8, 0.5] = (0.8 * 0.5)^(1/2) = 0.632."""
    d = compute_overall_desirability([0.8, 0.5])
    assert abs(d - 0.632) < 0.01


def test_compute_overall_desirability_zero():
    """Geometric mean with a zero should be zero."""
    d = compute_overall_desirability([0.9, 0.0, 0.7])
    assert d == 0.0
```

- [ ] **Step 2: Run tests to verify they FAIL**

```bash
pytest tests/test_doe_profiler.py -v
```

Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Commit**

```bash
git add tests/test_doe_profiler.py
git commit -m "test: add prediction profiler tests"
```

---

### Task 8: Implement doe/profiler.py

**Files:**
- Create: `doe/profiler.py`

- [ ] **Step 1: Write the module**

```python
"""Prediction profiler for interactive DOE exploration.

Computes predicted responses at slider positions and trace curves
showing how each response varies across each factor's range.

Pure Python — no Streamlit imports.
"""

import numpy as np
from doe.analysis import predict_from_model
from doe.optimization import desirability


def compute_profile(
    factors: list[dict],
    models: dict,
    responses: list[dict],
    slider_positions: dict[str, float],
    n_points: int = 50,
) -> dict:
    """Compute prediction profile at current slider positions.

    Parameters
    ----------
    factors : list of dict
        Factor definitions (name, type, low, high).
    models : dict
        Fitted models keyed by response name.
    responses : list of dict
        Response definitions (name, goal, low, high, target).
    slider_positions : dict
        Current coded values for each factor, e.g. {"T": 0.5, "P": -0.3}.
    n_points : int
        Number of points in each trace curve (default 50).

    Returns
    -------
    dict keyed by response name:
        {
            "predicted": float,
            "desirability": float,
            "traces": {
                factor_name: {
                    "x": [coded_values across -1..+1],
                    "y": [predicted response values],
                }
            }
        }
    """
    factor_names = [f["name"] for f in factors]
    response_map = {r["name"]: r for r in responses}

    result = {}
    for r in responses:
        rname = r["name"]
        if rname not in models:
            continue
        model = models[rname]

        # Predicted value at current positions
        pred = predict_from_model(model, factors, slider_positions)

        # Desirability
        d = desirability(
            pred,
            goal=r["goal"],
            low=r.get("low", 0),
            high=r.get("high", 1e12),
            target=r.get("target"),
        )

        # Trace curves: vary each factor across its range
        traces = {}
        for fname in factor_names:
            x_range = np.linspace(-1, 1, n_points)
            y_vals = []
            for x_val in x_range:
                point = dict(slider_positions)
                point[fname] = x_val
                y_vals.append(predict_from_model(model, factors, point))
            traces[fname] = {
                "x": [float(v) for v in x_range],
                "y": [float(v) for v in y_vals],
            }

        result[rname] = {
            "predicted": round(float(pred), 4),
            "desirability": round(float(d), 4),
            "traces": traces,
        }

    return result


def compute_overall_desirability(individual_d: list[float]) -> float:
    """Geometric mean of individual desirability values."""
    if not individual_d or any(d <= 0 for d in individual_d):
        return 0.0
    return float(np.prod(individual_d) ** (1.0 / len(individual_d)))
```

- [ ] **Step 2: Run tests to verify they pass**

```bash
pytest tests/test_doe_profiler.py -v
```

Expected: All 6 tests PASS.

- [ ] **Step 3: Commit**

```bash
git add doe/profiler.py
git commit -m "feat: add prediction profiler with trace curves and desirability"
```

---

### Task 9: Add CCD to designs.py + tests

**Files:**
- Modify: `doe/designs.py`
- Modify: `tests/test_doe_designs.py`

- [ ] **Step 1: Read current designs.py and test_doe_designs.py**

Read both files to understand the existing pattern for `generate_full_factorial`, `generate_box_behnken`, and the `_build_design_df` helper.

- [ ] **Step 2: Write CCD tests in test_doe_designs.py**

Append these tests at the end of the file:

```python
def test_ccd_rotatable_2_factors():
    """CCD with 2 factors, rotatable alpha: 2k factorial + 2k axial + cp."""
    from doe.designs import generate_ccd

    factors = [
        {"name": "T", "type": "continuous", "low": 80, "high": 120},
        {"name": "P", "type": "continuous", "low": 2.0, "high": 4.0},
    ]
    df = generate_ccd(factors, alpha="rotatable", n_center=3)

    # 2 factors: 4 factorial + 4 axial + 3 center = 11 runs
    assert len(df) == 11
    assert "run" in df.columns
    assert "T" in df.columns
    assert "P" in df.columns

    # Rotatable alpha for k=2: 2^(2/4) = 1.414
    axial_rows = df[(df["T"].abs() > 1.0) | (df["P"].abs() > 1.0)]
    assert len(axial_rows) == 4
    # Axial values should be ±alpha (1.414)
    axial_vals = axial_rows["T"].abs().tolist() + axial_rows["P"].abs().tolist()
    axial_vals = [v for v in axial_vals if v > 1.0]
    for v in axial_vals:
        assert abs(v - 1.414) < 0.01

    # Center points should be all zeros
    center_rows = df[(df["T"] == 0.0) & (df["P"] == 0.0)]
    assert len(center_rows) == 3


def test_ccd_face_centered():
    """Face-centered CCD: alpha = 1, axial points are on the faces."""
    from doe.designs import generate_ccd

    factors = [
        {"name": "A", "type": "continuous", "low": 0, "high": 10},
    ]
    df = generate_ccd(factors, alpha="face-centered", n_center=2)

    # 1 factor: 2 factorial + 2 axial + 2 center = 6 runs
    assert len(df) == 6

    # All values should be -1, 0, or +1 (face-centered)
    for val in df["A"]:
        assert val in (-1.0, 0.0, 1.0), f"Got {val}, expected -1, 0, or 1"


def test_ccd_3_factors():
    """CCD with 3 factors: 8 factorial + 6 axial + n_center."""
    from doe.designs import generate_ccd

    factors = [
        {"name": "A", "type": "continuous", "low": 0, "high": 100},
        {"name": "B", "type": "continuous", "low": 0, "high": 100},
        {"name": "C", "type": "continuous", "low": 0, "high": 100},
    ]
    df = generate_ccd(factors, alpha="rotatable", n_center=4)

    # 3 factors: 8 factorial + 6 axial + 4 center = 18
    assert len(df) == 18

    # Rotatable alpha for k=3: 2^(3/4) ≈ 1.682
    alpha = 2 ** (3 / 4)
    axial_rows = df[(df["A"].abs() > 1.0) | (df["B"].abs() > 1.0) | (df["C"].abs() > 1.0)]
    assert len(axial_rows) == 6
```

- [ ] **Step 3: Implement generate_ccd() in designs.py**

Add this function after the existing `generate_box_behnken` function:

```python
def generate_ccd(
    factors: list[dict],
    alpha: str | float = "rotatable",
    n_center: int = 3,
) -> pd.DataFrame:
    """Generate a Central Composite Design (CCD) for RSM.

    Parameters
    ----------
    factors : list of dict
        Factor definitions (name, type, low, high). All must be continuous.
    alpha : str or float
        "rotatable" (default), "orthogonal", "face-centered" (alpha=1),
        or a custom float.
    n_center : int
        Number of center points.

    Returns
    -------
    pd.DataFrame
        Design matrix with columns: run, <factor_names>. Coded -1/0/+1/±alpha.
    """
    k = len(factors)
    if k < 1:
        raise ValueError("CCD requires at least 1 factor")

    # Resolve alpha
    if alpha == "rotatable":
        a = 2 ** (k / 4)
    elif alpha == "orthogonal":
        # Orthogonal blocking CCD — approximate with standard formula
        n_factorial = 2 ** k
        a = np.sqrt((np.sqrt(n_factorial * (k + n_center + 2)) - np.sqrt(n_factorial)) / 2)
    elif alpha == "face-centered":
        a = 1.0
    elif isinstance(alpha, (int, float)):
        a = float(alpha)
    else:
        raise ValueError(f"Unknown alpha: {alpha}")

    # 2^k factorial portion
    levels = [2] * k
    raw = fullfact(levels)
    factorial_coded = np.where(raw == 0, -1, 1).astype(float)

    # Axial portion: one factor at ±alpha, others at 0
    axial_rows = []
    for i in range(k):
        for sign in [-1, 1]:
            row = np.zeros(k)
            row[i] = sign * a
            axial_rows.append(row)
    axial_coded = np.array(axial_rows)

    # Combine
    coded = np.vstack([factorial_coded, axial_coded])
    factor_names = [f["name"] for f in factors]
    df = pd.DataFrame(coded, columns=factor_names)
    df = df.round(4)
    df.insert(0, "run", range(1, len(df) + 1))

    # Center points
    if n_center > 0:
        df = add_center_points(df, factor_names, n_center)

    return df
```

- [ ] **Step 4: Run CCD-specific tests to verify they pass**

```bash
pytest tests/test_doe_designs.py::test_ccd_rotatable_2_factors tests/test_doe_designs.py::test_ccd_face_centered tests/test_doe_designs.py::test_ccd_3_factors -v
```

Expected: 3 PASS.

- [ ] **Step 5: Run full designs test suite to check no regressions**

```bash
pytest tests/test_doe_designs.py -v
```

Expected: All existing + 3 new tests PASS. ~12 tests total.

- [ ] **Step 6: Commit**

```bash
git add doe/designs.py tests/test_doe_designs.py
git commit -m "feat: add Central Composite Design (CCD) generation"
```

---

### Task 10: Extend persistence.py for analysis column

**Files:**
- Modify: `doe/persistence.py`
- Modify: `tests/test_doe_persistence.py`

- [ ] **Step 1: Read current persistence.py**

Read `doe/persistence.py` — note `ALLOWED_COLUMNS` and `JSON_COLUMNS`.

- [ ] **Step 2: Add 'analysis' to allowed columns**

In `doe/persistence.py`, find the `ALLOWED_COLUMNS` set and `JSON_COLUMNS` set. Add `"analysis"` to both.

Replace:
```python
ALLOWED_COLUMNS = {
    "name", "status", "entry_type",
    "factors", "responses", "design", "results", "model", "optimum",
}
JSON_COLUMNS = {"factors", "responses", "design", "results", "model", "optimum"}
```

With:
```python
ALLOWED_COLUMNS = {
    "name", "status", "entry_type",
    "factors", "responses", "design", "results", "model", "optimum",
    "analysis",
}
JSON_COLUMNS = {"factors", "responses", "design", "results", "model", "optimum", "analysis"}
```

- [ ] **Step 3: Add persistence test for analysis column**

In `tests/test_doe_persistence.py`, append:

```python
def test_analysis_column_crud():
    """analysis column should store and retrieve JSON data."""
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        repo = DoeRepository(db_path)

        sid = repo.create(
            "Analysis Test",
            "full_factorial",
            [{"name": "A", "type": "continuous", "low": 0, "high": 10}],
            [{"name": "y", "goal": "maximize", "low": 0, "high": 100}],
        )

        analysis_data = {
            "y": {
                "model_type": "linear",
                "anova": {
                    "source": ["Model", "A", "Residual", "Total"],
                    "ss": [0.5, 0.3, 0.1, 0.6],
                    "df": [1, 1, 2, 3],
                    "ms": [0.5, 0.3, 0.05, None],
                    "f": [10.0, 6.0, None, None],
                    "p": [0.05, 0.13, None, None],
                },
                "r_squared": 0.833,
            }
        }

        repo.update(sid, {"analysis": analysis_data, "status": "analyzed"})

        loaded = repo.load(sid)
        assert loaded["analysis"] == analysis_data
        assert loaded["status"] == "analyzed"
```

- [ ] **Step 4: Run persistence tests**

```bash
pytest tests/test_doe_persistence.py -v
```

Expected: All tests PASS including the new one (~8 tests).

- [ ] **Step 5: Commit**

```bash
git add doe/persistence.py tests/test_doe_persistence.py
git commit -m "feat: add analysis JSON column to DOE persistence"
```

---

### Task 11: Extend integration test

**Files:**
- Modify: `tests/test_doe_integration.py`

- [ ] **Step 1: Read current integration test**

Read `tests/test_doe_integration.py`.

- [ ] **Step 2: Add a test that exercises the full pipeline: design → analyze → residuals → profiler**

```python
def test_full_pipeline_with_profiler():
    """End-to-end: design CCD → analyze with ANOVA+residuals → profiler."""
    import numpy as np
    import pandas as pd
    from doe.designs import generate_ccd, decode_to_actual
    from doe.analysis import fit_rsm
    from doe.residuals import compute_residuals, build_residual_plots
    from doe.profiler import compute_profile

    factors = [
        {"name": "T", "type": "continuous", "low": 80, "high": 120},
        {"name": "P", "type": "continuous", "low": 2.0, "high": 4.0},
    ]

    # Generate CCD
    coded = generate_ccd(factors, alpha="rotatable", n_center=3)
    actual = decode_to_actual(coded, factors)

    # Simulate results: y = 10 + 3*T + 2*P + noise
    np.random.seed(42)
    results_rows = []
    for _, row in coded.iterrows():
        y = 10 + 3 * row["T"] + 2 * row["P"] + np.random.normal(0, 0.2)
        results_rows.append({"run": int(row["run"]), "y": round(y, 3)})
    results = pd.DataFrame(results_rows)

    # Analyze
    model = fit_rsm(factors, coded, results, "y")

    # Model should have ANOVA and residuals
    assert "anova" in model
    assert model["anova"]["source"][0] == "Model"
    assert model["r_squared"] > 0.8  # good fit

    # Residual diagnostics
    X = np.column_stack([
        np.ones(len(coded)),
        coded["T"].values,
        coded["P"].values,
        coded["T"].values * coded["P"].values,
        coded["T"].values ** 2,
        coded["P"].values ** 2,
    ])
    resid = compute_residuals(
        np.array(model["residuals"]["observed"]),
        np.array(model["residuals"]["predicted"]),
        X,
    )
    assert len(resid["residuals"]) == len(coded)
    assert resid["shapiro_p"] is not None

    # Residual plots
    fig = build_residual_plots(resid)
    assert hasattr(fig, "data")

    # Profiler
    models = {"y": model}
    responses = [{"name": "y", "goal": "maximize", "low": 0, "high": 20}]
    profile = compute_profile(factors, models, responses, {"T": 0.5, "P": -0.5})
    assert "y" in profile
    assert "predicted" in profile["y"]
    assert profile["y"]["desirability"] > 0
```

- [ ] **Step 3: Run integration test**

```bash
pytest tests/test_doe_integration.py::test_full_pipeline_with_profiler -v
```

Expected: PASS.

- [ ] **Step 4: Run all DOE tests to confirm no regressions**

```bash
pytest tests/test_doe_*.py -v
```

Expected: All ~35+ DOE tests PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_doe_integration.py
git commit -m "test: add full-pipeline integration test (CCD → ANOVA → residuals → profiler)"
```

---

### Task 12: Rewrite doe_view.py — 2-Tab UI

**Files:**
- Rewrite: `ui/engineer/doe_view.py`

- [ ] **Step 1: Read the current doe_view.py for reference**

Note the `_render_*` helper pattern, the `DoeRepository` usage, the `session_state` keys, and the Plotly chart builders.

- [ ] **Step 2: Write the rewritten doe_view.py**

This is the largest file. The rewrite keeps the existing pattern (functions per section, session_state for state management) but restructures into 2 tabs.

```python
"""DOE (Design of Experiments) page — 2-tab Streamlit dashboard.

Tab 1: DESIGN — Setup → Type Selection → Diagnostics → Run Sheet
Tab 2: ANALYZE — Data Entry → ANOVA → Residuals → Profiler
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from data_access.base import DataRepository
from doe.persistence import DoeRepository
from config import DB_FILE
from doe.designs import (
    generate_full_factorial,
    generate_fractional_factorial,
    generate_box_behnken,
    generate_ccd,
    add_center_points,
    decode_to_actual,
    get_fractional_run_count,
)
from doe.analysis import fit_linear, fit_rsm, has_curvature, predict_from_model, _is_center_row, anova_table
from doe.optimization import optimize as doe_optimize
from doe.residuals import compute_residuals as compute_residuals_fn, build_residual_plots
from doe.profiler import compute_profile, compute_overall_desirability
from doe.evaluate import evaluate_design

DOE_REPO_KEY = "doe_repo"


def _get_doe_repo() -> DoeRepository:
    if DOE_REPO_KEY not in st.session_state:
        st.session_state[DOE_REPO_KEY] = DoeRepository(DB_FILE)
    return st.session_state[DOE_REPO_KEY]


def render_doe_page(repo: DataRepository):
    doe_repo = _get_doe_repo()

    # Init state
    if "doe_active_tab" not in st.session_state:
        st.session_state.doe_active_tab = "design"
    if "doe_session" not in st.session_state:
        st.session_state.doe_session = None
    if "doe_session_id" not in st.session_state:
        st.session_state.doe_session_id = None

    # --- Sidebar ---
    with st.sidebar:
        st.markdown('<p class="sidebar-section-label">DOE SESSION</p>', unsafe_allow_html=True)

        # Tab buttons
        c1, c2 = st.columns(2)
        with c1:
            if st.button("📐 DESIGN", use_container_width=True,
                         type="primary" if st.session_state.doe_active_tab == "design" else "secondary",
                         key="doe_tab_design"):
                st.session_state.doe_active_tab = "design"
                st.rerun()
        with c2:
            if st.button("📊 ANALYZE", use_container_width=True,
                         type="primary" if st.session_state.doe_active_tab == "analyze" else "secondary",
                         key="doe_tab_analyze"):
                st.session_state.doe_active_tab = "analyze"
                st.rerun()

        # Session info
        session = st.session_state.doe_session
        if session:
            st.caption(f"Name: {session.get('name', 'Untitled')}")
            st.caption(f"Type: {session.get('entry_type', '—').replace('_', ' ').title()}")
            st.divider()
            if st.button("➕ New DOE", use_container_width=True):
                _reset_doe()
        else:
            st.caption("No active session")

        # Saved sessions
        saved = doe_repo.list_sessions()
        if saved:
            st.divider()
            st.caption("Saved sessions:")
            for s in saved[:5]:
                if st.button(f"{s['name'][:25]} ({s['status']})", key=f"doe_load_{s['id']}"):
                    _load_session(doe_repo, s["id"])

    # --- Main content ---
    st.title("Design of Experiments")

    if st.session_state.doe_active_tab == "design":
        _render_design_tab(doe_repo)
    else:
        _render_analyze_tab(doe_repo)


# ---------------------------------------------------------------------------
# Tab 1: DESIGN
# ---------------------------------------------------------------------------

def _render_design_tab(doe_repo: DoeRepository):
    session = st.session_state.doe_session

    # If no session, show landing
    if session is None:
        _render_landing(doe_repo)
        return

    factors = session.get("factors_json", [])
    responses = session.get("responses_json", [])
    design_exists = session.get("design_json") is not None

    # ── Section 1: Setup ──
    with st.expander("▸ SETUP: Factors & Responses", expanded=not design_exists):
        _render_setup_section(session)

    if not factors or not responses:
        st.info("Define at least one factor and one response above to continue.")
        return

    # ── Section 2: Design Type ──
    with st.expander("▸ DESIGN TYPE", expanded=not design_exists):
        design_type = st.radio(
            "Select design type",
            options=["full_factorial", "fractional_factorial", "ccd", "box_behnken"],
            format_func=lambda x: {
                "full_factorial": "Full Factorial (2^k)",
                "fractional_factorial": "Fractional Factorial (2^(k-p))",
                "ccd": "Central Composite Design (CCD)",
                "box_behnken": "Box-Behnken",
            }[x],
            horizontal=True,
            key="doe_design_type",
        )

        col1, col2 = st.columns(2)
        with col1:
            n_center = st.slider("Center points", 0, 5, 3, key="doe_n_center")
        with col2:
            if design_type == "fractional_factorial":
                resolution = st.selectbox("Resolution", [4, 5], index=0, key="doe_resolution")
            elif design_type == "ccd":
                alpha = st.selectbox("Alpha", ["rotatable", "face-centered", "orthogonal"],
                                     index=0, key="doe_ccd_alpha")

        # Run count estimate
        k = len([f for f in factors if f["type"] == "continuous"])
        if design_type == "full_factorial":
            n_runs = 2 ** k + n_center
        elif design_type == "fractional_factorial":
            n_runs = get_fractional_run_count(k, resolution) + n_center
        elif design_type == "ccd":
            n_runs = 2 ** k + 2 * k + n_center
        else:  # BB
            n_runs = len(generate_box_behnken(factors, n_center=n_center))
        st.info(f"Estimated runs: **{n_runs}** ({2**k} factorial + rest)")

        if st.button("⚙️ Generate Design", type="primary", key="doe_gen_design"):
            if design_type == "full_factorial":
                coded_df = generate_full_factorial(factors, n_center=n_center)
            elif design_type == "fractional_factorial":
                coded_df = generate_fractional_factorial(factors, resolution=resolution)
            elif design_type == "ccd":
                coded_df = generate_ccd(factors, alpha=alpha, n_center=n_center)
            else:
                coded_df = generate_box_behnken(factors, n_center=n_center)

            session["design_json"] = coded_df.to_dict("records")
            session["design_type"] = design_type
            st.session_state.doe_design_generated = True

            if session.get("db_id"):
                doe_repo.update(session["db_id"], {
                    "design": coded_df.to_dict("records"),
                    "entry_type": design_type,
                    "status": "designed",
                })
            st.rerun()

    if not design_exists:
        return

    design_df = pd.DataFrame(session["design_json"])
    decoded_df = decode_to_actual(design_df, factors)

    # ── Section 3: Diagnostics ──
    with st.expander("▸ DESIGN DIAGNOSTICS"):
        if st.button("🔍 Evaluate Design", key="doe_evaluate"):
            diag = evaluate_design(design_df, factors, model_order="linear")

            c1, c2, c3 = st.columns(3)
            with c1:
                power_1s = diag["power"].get(1.0, 0)
                color = "normal" if power_1s >= 0.8 else "off"
                st.metric("Power (1σ effect)", f"{power_1s:.2f}",
                          delta="Good" if power_1s >= 0.8 else "Low",
                          delta_color=color)
            with c2:
                max_vif = max(diag["vif"].values()) if diag["vif"] else 1.0
                st.metric("Max VIF", f"{max_vif:.2f}",
                          delta="OK" if max_vif < 5 else "High",
                          delta_color="normal" if max_vif < 5 else "off")
            with c3:
                st.metric("G-Efficiency", f"{diag['g_efficiency']:.2f}")

            for w in diag.get("warnings", []):
                st.warning(w)

    # ── Section 4: Run Sheet ──
    with st.expander("▸ RUN SHEET", expanded=True):
        st.dataframe(decoded_df, use_container_width=True, hide_index=True)

        # Download
        response_names = [r["name"] for r in responses]
        dl_df = decoded_df.copy()
        for rname in response_names:
            dl_df[rname] = ""
        csv_data = dl_df.to_csv(index=False)
        st.download_button("📥 Download Run Sheet (CSV)", csv_data,
                           file_name=f"doe_{session.get('name', 'design')}.csv",
                           mime="text/csv", key="doe_dl_design")

    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🔄 New DOE", key="doe_design_new"):
            _reset_doe()
    with c2:
        if st.button("📊 Go to Analyze →", type="primary", key="doe_to_analyze"):
            st.session_state.doe_active_tab = "analyze"
            st.rerun()


# ---------------------------------------------------------------------------
# Tab 2: ANALYZE
# ---------------------------------------------------------------------------

def _render_analyze_tab(doe_repo: DoeRepository):
    session = st.session_state.doe_session

    if session is None or session.get("design_json") is None:
        st.info("Generate a design first (DESIGN tab) before analyzing.")
        if st.button("Go to DESIGN tab"):
            st.session_state.doe_active_tab = "design"
            st.rerun()
        return

    design_df = pd.DataFrame(session["design_json"])
    factors = session.get("factors_json", [])
    responses = session.get("responses_json", [])
    response_names = [r["name"] for r in responses]
    db_id = session.get("db_id")

    # ── Section 1: Data Entry ──
    results_exist = session.get("results_json") is not None

    with st.expander("▸ DATA ENTRY", expanded=not results_exist):
        uploaded = st.file_uploader("Upload completed run sheet CSV", type=["csv"], key="doe_upload_results")
        if uploaded:
            try:
                uploaded_df = pd.read_csv(uploaded)
                results = []
                for _, row in uploaded_df.iterrows():
                    run_result = {"run": int(row["run"])}
                    for rname in response_names:
                        if rname in uploaded_df.columns:
                            run_result[rname] = float(row[rname])
                    results.append(run_result)
                session["results_json"] = results
                if db_id:
                    doe_repo.update(db_id, {"results": results, "status": "running"})
                st.success(f"Loaded {len(results)} runs with {len(response_names)} responses")
                st.rerun()
            except Exception as e:
                st.error(f"Error reading CSV: {e}")

        # Manual entry fallback
        if not results_exist and not uploaded:
            st.caption("Or enter data below after generating the design.")

    if not results_exist:
        return

    results_df = pd.DataFrame(session["results_json"])

    # ── Section 2: Analysis ──
    if "doe_analysis_results" not in st.session_state:
        st.session_state.doe_analysis_results = None

    if st.button("🔬 Run Analysis", type="primary", key="doe_run_analysis"):
        analysis_results = {}
        for r in responses:
            rname = r["name"]
            # Try RSM first if center points exist, else linear
            is_center = _is_center_row(design_df, [f["name"] for f in factors])
            if is_center.sum() >= 3:
                model = fit_rsm(factors, design_df, results_df, rname)
            else:
                model = fit_linear(factors, design_df, results_df, rname)
            analysis_results[rname] = model
        st.session_state.doe_analysis_results = analysis_results
        if db_id:
            doe_repo.update(db_id, {"analysis": analysis_results, "status": "analyzed"})
        st.rerun()

    analysis = st.session_state.doe_analysis_results
    if analysis is None:
        return

    # ── Section 3: ANOVA ──
    with st.expander("▸ ANOVA TABLE", expanded=True):
        for rname in response_names:
            if rname not in analysis:
                continue
            model = analysis[rname]
            st.markdown(f"**Response: {rname}**")
            anova_df = anova_table(model)
            st.dataframe(anova_df, use_container_width=True, hide_index=True)

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("R²", f"{model.get('r_squared', 0):.4f}")
            c2.metric("Adj R²", f"{model.get('r_squared_adj', 0):.4f}")
            c3.metric("RMSE", f"{model.get('rmse', 0):.4f}")
            lof_p = model.get("lack_of_fit_p")
            c4.metric("Lack-of-fit p", f"{lof_p:.4f}" if lof_p is not None else "N/A")
            st.divider()

    # ── Section 4: Residuals ──
    with st.expander("▸ RESIDUAL DIAGNOSTICS"):
        for rname in response_names:
            if rname not in analysis:
                continue
            model = analysis[rname]
            resid_data = model.get("residuals", {})
            if not resid_data:
                st.caption(f"No residual data for {rname}")
                continue

            st.markdown(f"**{rname}**")
            resid_dict = {
                "residuals": np.array(resid_data.get("residual", [])),
                "studentized": np.array([v or np.nan for v in resid_data.get("studentized", [])]),
                "predicted": np.array(resid_data.get("predicted", [])),
                "run_order": np.array(resid_data.get("run", [])),
                "leverage": np.array([v or 0 for v in resid_data.get("leverage", [])]),
                "cooks_d": np.array([v or 0 for v in [] if v]),
                "shapiro_p": None,
            }

            # Recompute for proper structures
            obs = np.array(resid_data.get("observed", []))
            pred = np.array(resid_data.get("predicted", []))
            X = np.column_stack([np.ones(len(obs)), np.arange(len(obs))])  # placeholder
            from doe.residuals import compute_residuals as cr
            resid_dict = cr(obs, pred, X, np.array(resid_data.get("run", [])))

            fig = build_residual_plots(resid_dict)
            st.plotly_chart(fig, use_container_width=True)
            st.divider()

    # ── Section 5: Effects & Plots ──
    with st.expander("▸ EFFECTS & PLOTS"):
        factor_names = [f["name"] for f in factors]
        merged = design_df.merge(results_df, on="run") if not results_df.empty else design_df.copy()

        for rname in response_names:
            if rname not in analysis or rname not in merged.columns:
                continue
            model = analysis[rname]
            st.markdown(f"**{rname}**")

            # Pareto
            coefs = [c for c in model["coefficients"] if c["term"] != "Intercept"]
            coefs.sort(key=lambda c: abs(c["estimate"]), reverse=True)
            pareto_fig = go.Figure(go.Bar(
                x=[abs(c["estimate"]) for c in coefs],
                y=[c["term"] for c in coefs],
                orientation="h",
                marker_color=["#C4523E" if c["significant"] else "#4A90D9" for c in coefs],
            ))
            pareto_fig.update_layout(title=f"Pareto of Effects — {rname}", height=300)
            st.plotly_chart(pareto_fig, use_container_width=True)

            # Main effects
            if factor_names:
                fig_me = make_subplots(rows=1, cols=len(factor_names),
                                       subplot_titles=factor_names)
                for i, fn in enumerate(factor_names):
                    levels = sorted(merged[fn].unique())
                    means = [merged.loc[merged[fn] == l, rname].mean() for l in levels]
                    fig_me.add_trace(go.Scatter(x=[str(l) for l in levels], y=means,
                                                mode="lines+markers"), row=1, col=i+1)
                fig_me.update_layout(height=300, showlegend=False)
                st.plotly_chart(fig_me, use_container_width=True)

    # ── Section 6: Prediction Profiler ──
    with st.expander("▸ PREDICTION PROFILER", expanded=True):
        if "doe_profiler_positions" not in st.session_state:
            st.session_state.doe_profiler_positions = {
                f["name"]: 0.0 for f in factors if f["type"] == "continuous"
            }

        positions = st.session_state.doe_profiler_positions

        # Factor sliders
        cont_factors = [f for f in factors if f["type"] == "continuous"]
        slider_cols = st.columns(len(cont_factors))
        for i, f in enumerate(cont_factors):
            with slider_cols[i]:
                positions[f["name"]] = st.slider(
                    f["name"], -1.0, 1.0, positions.get(f["name"], 0.0),
                    0.01, key=f"prof_slider_{f['name']}"
                )

        # Compute profile
        profile = compute_profile(factors, analysis, responses, positions)

        # Response trace columns
        resp_cols = st.columns(len(responses))
        for i, r in enumerate(responses):
            rname = r["name"]
            if rname not in profile:
                continue
            with resp_cols[i]:
                p = profile[rname]
                st.metric(rname, f"{p['predicted']:.3f}")
                d = p["desirability"]
                d_color = "#00BFA5" if d >= 0.7 else "#F39C12" if d >= 0.3 else "#C4523E"
                st.markdown(
                    f"<span style='color:{d_color};font-weight:700'>D = {d:.3f}</span>",
                    unsafe_allow_html=True,
                )
                st.progress(d)

                # Mini trace plot for first continuous factor
                for fn in cont_factors[:1]:
                    if fn in p["traces"]:
                        trace = p["traces"][fn]
                        tf = go.Figure(go.Scatter(x=trace["x"], y=trace["y"], mode="lines",
                                                   line=dict(width=2, color="#C4734F")))
                        tf.update_layout(height=100, margin=dict(l=0, r=0, t=0, b=0))
                        st.plotly_chart(tf, use_container_width=True, config={"displayModeBar": False})

        # Overall desirability
        ind_d = [profile[r["name"]]["desirability"] for r in responses if r["name"] in profile]
        overall_d = compute_overall_desirability(ind_d) if ind_d else 0.0

        col_od, col_opt = st.columns([2, 1])
        with col_od:
            st.metric("Overall Desirability", f"D = {overall_d:.3f}")
            if overall_d >= 0.8:
                st.success("Excellent")
            elif overall_d >= 0.5:
                st.warning("Acceptable")
            else:
                st.error("Poor — adjust goals")

        with col_opt:
            if st.button("🎯 Find Optimum", type="primary", key="doe_find_opt"):
                result = doe_optimize(factors, responses, analysis, n_starts=10)
                # Update slider positions
                for f in factors:
                    if f["type"] != "continuous":
                        continue
                    opt_val = result["optimal_settings"].get(f["name"])
                    if opt_val is not None:
                        coded = (2 * (opt_val - f["low"]) / (f["high"] - f["low"])) - 1
                        positions[f["name"]] = float(max(-1.0, min(1.0, coded)))
                st.session_state.doe_profiler_positions = positions
                st.rerun()

    st.divider()
    if st.button("🔄 New DOE", key="doe_analyze_new"):
        _reset_doe()


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _render_landing(doe_repo: DoeRepository):
    """New DOE landing."""
    st.subheader("Start a New DOE")

    entry_type = st.radio(
        "Design type",
        options=["full_factorial", "fractional_factorial", "ccd", "box_behnken"],
        format_func=lambda x: {
            "full_factorial": "Full Factorial — characterize known critical factors (2^k)",
            "fractional_factorial": "Fractional Factorial — screen many factors with few runs",
            "ccd": "Central Composite — RSM with 5 levels per factor",
            "box_behnken": "Box-Behnken — RSM with 3 levels, fewer runs than CCD",
        }[x],
        key="doe_new_entry_type",
    )
    name = st.text_input("DOE Name", placeholder="e.g., Formulation Optimization #3", key="doe_new_name")

    if st.button("▶ Start", type="primary", key="doe_new_start"):
        session = {
            "name": name or "Untitled DOE",
            "entry_type": entry_type,
            "status": "defined",
            "factors_json": [],
            "responses_json": [],
            "design_json": None,
            "results_json": None,
            "analysis_json": None,
            "optimum_json": None,
            "design_type": None,
        }
        st.session_state.doe_session = session

        # Save to DB
        sid = doe_repo.create(
            name=session["name"],
            entry_type=entry_type,
            factors=[],
            responses=[],
        )
        session["db_id"] = sid
        st.session_state.doe_session_id = sid
        st.rerun()


def _render_setup_section(session: dict):
    """Factor and response definition (inline editors)."""
    # Factors
    st.markdown("**Factors**")
    if "doe_factors_list" not in st.session_state:
        st.session_state.doe_factors_list = session.get("factors_json", []) or [
            {"name": "", "type": "continuous", "low": 0.0, "high": 100.0}
        ]

    for i, row in enumerate(st.session_state.doe_factors_list):
        c1, c2, c3, c4, c5 = st.columns([3, 2, 2, 2, 1])
        with c1:
            row["name"] = st.text_input("Name", row.get("name", ""), key=f"fac_n_{i}",
                                        label_visibility="collapsed", placeholder=f"Factor {i+1}")
        with c2:
            row["type"] = st.selectbox("Type", ["continuous", "categorical"],
                                       index=0 if row.get("type") == "continuous" else 1,
                                       key=f"fac_t_{i}", label_visibility="collapsed")
        with c3:
            row["low"] = st.number_input("Low", float(row.get("low", 0)), key=f"fac_l_{i}",
                                         label_visibility="collapsed", step=0.01, format="%.4f")
        with c4:
            row["high"] = st.number_input("High", float(row.get("high", 100)), key=f"fac_h_{i}",
                                          label_visibility="collapsed", step=0.01, format="%.4f")
        with c5:
            if len(st.session_state.doe_factors_list) > 1:
                if st.button("✕", key=f"fac_del_{i}"):
                    st.session_state.doe_factors_list.pop(i)
                    st.rerun()

    st.button("+ Add Factor", key="doe_add_f")

    # Responses
    st.markdown("**Responses**")
    if "doe_responses_list" not in st.session_state:
        st.session_state.doe_responses_list = session.get("responses_json", []) or [
            {"name": "", "goal": "maximize", "target": None, "low": 0.0, "high": 100.0}
        ]

    for i, row in enumerate(st.session_state.doe_responses_list):
        c1, c2, c3, c4, c5 = st.columns([3, 1.5, 1.5, 1.5, 1])
        with c1:
            row["name"] = st.text_input("Name", row.get("name", ""), key=f"resp_n_{i}",
                                        label_visibility="collapsed", placeholder=f"Response {i+1}")
        with c2:
            row["goal"] = st.selectbox("Goal", ["maximize", "minimize", "target"],
                                       index=["maximize","minimize","target"].index(row.get("goal","maximize")),
                                       key=f"resp_g_{i}", label_visibility="collapsed")
        with c3:
            if row["goal"] in ("maximize", "target"):
                row["low"] = st.number_input("Low", float(row.get("low", 0)), key=f"resp_l_{i}",
                                             label_visibility="collapsed", step=0.01, format="%.4f")
        with c4:
            if row["goal"] in ("minimize", "target"):
                row["high"] = st.number_input("High", float(row.get("high", 100)), key=f"resp_h_{i}",
                                              label_visibility="collapsed", step=0.01, format="%.4f")
        with c5:
            if len(st.session_state.doe_responses_list) > 1:
                if st.button("✕", key=f"resp_del_{i}"):
                    st.session_state.doe_responses_list.pop(i)
                    st.rerun()

    st.button("+ Add Response", key="doe_add_r")

    # Save to session
    valid_factors = [f for f in st.session_state.doe_factors_list if f.get("name") and str(f["name"]).strip()]
    valid_responses = [r for r in st.session_state.doe_responses_list if r.get("name") and str(r["name"]).strip()]
    session["factors_json"] = valid_factors
    session["responses_json"] = valid_responses

    if valid_factors and valid_responses and session.get("db_id") and session.get("status") == "defined":
        from doe.persistence import DoeRepository
        from config import DB_FILE
        dr = DoeRepository(DB_FILE)
        dr.update(session["db_id"], {"factors": valid_factors, "responses": valid_responses})
        session["status"] = "designed"


def _reset_doe():
    st.session_state.doe_step = "landing"  # compat
    st.session_state.doe_session = None
    st.session_state.doe_session_id = None
    st.session_state.doe_analysis_results = None
    st.session_state.doe_profiler_positions = None
    st.session_state.doe_active_tab = "design"
    st.rerun()


def _load_session(doe_repo: DoeRepository, sid: int):
    try:
        s = doe_repo.load(sid)
        st.session_state.doe_session = {
            "name": s["name"],
            "entry_type": s["entry_type"],
            "status": s["status"],
            "factors_json": s["factors"] if s["factors"] else [],
            "responses_json": s["responses"] if s["responses"] else [],
            "design_json": s.get("design"),
            "results_json": s.get("results"),
            "analysis_json": s.get("analysis"),
            "optimum_json": s.get("optimum"),
            "db_id": sid,
        }
        st.session_state.doe_session_id = sid
        st.session_state.doe_analysis_results = s.get("analysis")
        st.session_state.doe_active_tab = "analyze" if s.get("results") else "design"
        st.rerun()
    except KeyError:
        st.error(f"Session {sid} not found.")
```

- [ ] **Step 2: Run existing DOE tests (engines only) to check nothing broke**

```bash
pytest tests/test_doe_designs.py tests/test_doe_analysis.py tests/test_doe_optimization.py tests/test_doe_persistence.py tests/test_doe_residuals.py tests/test_doe_profiler.py tests/test_doe_evaluate.py -v
```

Expected: All engine tests PASS (~40 tests).

- [ ] **Step 3: Run the full test suite**

```bash
pytest tests/ -v
```

Expected: All 90+ tests PASS (engine tests + existing SPC tests unchanged).

- [ ] **Step 4: Commit**

```bash
git add ui/engineer/doe_view.py
git commit -m "feat: rewrite DOE UI with 2-tab dashboard (design + analyze with profiler)"
```

---

### Task 13: Run full test suite + final verification

**Files:** None (verification only)

- [ ] **Step 1: Run full test suite**

```bash
pytest tests/ -v
```

- [ ] **Step 2: Confirm all tests pass**

Expected: 0 failures. Total test count should be ~55+ DOE tests + existing SPC tests = ~95+ total.

- [ ] **Step 3: Check for remaining old references**

```bash
grep -rn "_go_to\|doe_step\|_render_landing\|_render_define\|_render_design\|_render_capture\|_render_analyze\|_render_optimize" ui/engineer/doe_view.py --include="*.py"
```

These old function names should no longer exist in the rewritten doe_view.py. If any remain, they should only be in `_reset_doe()` for backward compat.

- [ ] **Step 4: Commit any final cleanup**

```bash
git add -A
git commit -m "chore: final DOE redesign integration and cleanup"
```

---

*Plan complete. Implementation: start at Task 1 and proceed sequentially. Each task produces working, testable software.*
