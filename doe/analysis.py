"""DOE analysis: linear regression and RSM via statsmodels.

Pure Python — no Streamlit imports.
"""

import itertools
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats


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


def _is_center_row(design: pd.DataFrame, factor_names: list[str],
                   tol: float = 0.01) -> np.ndarray:
    """Return boolean array: True for rows where ALL factors are within `tol` of 0.

    Shared helper used by the internal curvature test — single
    source of truth for center-point detection.
    """
    is_center = np.ones(len(design), dtype=bool)
    for f in factor_names:
        is_center &= np.abs(design[f].values) < tol
    return is_center


def _validate_inputs(design: pd.DataFrame, results: pd.DataFrame,
                     response_name: str):
    """Guard: check response_name exists in results, and both DataFrames have a 'run' column."""
    if response_name not in results.columns:
        raise ValueError(
            f"Response '{response_name}' not found in results columns: "
            f"{list(results.columns)}"
        )
    if "run" not in design.columns:
        raise ValueError("design DataFrame must have a 'run' column")
    if "run" not in results.columns:
        raise ValueError("results DataFrame must have a 'run' column")


def _merge_and_validate(design: pd.DataFrame, results: pd.DataFrame,
                        response_name: str) -> tuple[pd.DataFrame, np.ndarray]:
    """Merge design and results on 'run', validate, return (merged_design, y)."""
    _validate_inputs(design, results, response_name)

    merged = design.merge(results[["run", response_name]], on="run", how="inner")
    if len(merged) == 0:
        raise ValueError("No matching 'run' values between design and results. "
                         "Check that run numbers align.")

    # Check for NaN/Inf in response
    y = merged[response_name].values.astype(float)
    if not np.isfinite(y).all():
        raise ValueError(
            f"Response '{response_name}' contains NaN or Inf values. "
            "Clean data before analysis."
        )

    return merged, y


def _check_parameter_count(n_obs: int, n_params: int):
    """Raise ValueError if model has more parameters than observations."""
    if n_params > n_obs:
        raise ValueError(
            f"Model has {n_params} parameters — more parameters than "
            f"observations ({n_obs}). "
            "This produces NaN p-values and R²=1.0. "
            "For screening designs with ≥4 factors, use a main-effects-only "
            "model or increase the number of runs."
        )


def fit_linear(factors: list[dict], design: pd.DataFrame, results: pd.DataFrame,
               response_name: str, alpha: float = 0.05) -> dict:
    """Fit a linear model with main effects and all 2-way interactions.

    Parameters
    ----------
    factors : list of dict
        Each dict has keys: name, type ('continuous' or 'categorical'), low, high.
    design : pd.DataFrame
        Coded design matrix (columns: run, <factor_names>).
    results : pd.DataFrame
        Response values (columns: run, <response_names>).
    response_name : str
        Name of the response column to model.
    alpha : float
        Significance level for p-value tests (default 0.05).

    Returns
    -------
    dict with keys:
        coefficients: list of dict (term, estimate, std_err, p_value, significant)
        r_squared: float
        r_squared_adj: float
        model_p_value: float
        rmse: float — root mean squared error (for prediction intervals)
    """
    factor_names = [f["name"] for f in factors]

    merged, y = _merge_and_validate(design, results, response_name)

    # Build X matrix: intercept + main effects + 2-way interactions
    X_cols = ["Intercept"] + factor_names
    X_cols += [f"{a}*{b}" for a, b in _pairwise(factor_names)]

    _check_parameter_count(len(merged), len(X_cols))

    X = np.column_stack([
        np.ones(len(merged)),  # intercept
        *[merged[f].values for f in factor_names],  # main effects
        *[(merged[a].values * merged[b].values) for a, b in _pairwise(factor_names)],  # interactions
    ])

    ols = sm.OLS(y, X).fit()

    coefficients = []
    for i, term in enumerate(X_cols):
        pv = float(ols.pvalues[i])
        coefficients.append({
            "term": term,
            "estimate": float(ols.params[i]),
            "std_err": float(ols.bse[i]) if np.isfinite(ols.bse[i]) else None,
            "p_value": pv if np.isfinite(pv) else None,
            "significant": bool(pv < alpha) if np.isfinite(pv) else False,
        })

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
        "rmse": 0.0 if (hasattr(ols, 'mse_resid') and ols.mse_resid < 1e-12) else (
            float(np.sqrt(ols.mse_resid)) if hasattr(ols, 'mse_resid') and np.isfinite(ols.mse_resid) else None
        ),
        "residuals": residuals_data,
        "lack_of_fit_p": lack_of_fit_p,
        "n_obs": len(merged),
        "n_params": len(X_cols),
    }


def fit_rsm(factors: list[dict], design: pd.DataFrame, results: pd.DataFrame,
            response_name: str, alpha: float = 0.05) -> dict:
    """Fit an RSM model (linear + interactions + quadratic terms).

    Parameters
    ----------
    factors : list of dict
        Factor definitions (name, type, low, high).
    design : pd.DataFrame
        Coded design matrix including center points.
    results : pd.DataFrame
        Response values.
    response_name : str
        Name of the response column to model.
    alpha : float
        Significance level.

    Returns
    -------
    dict with keys:
        coefficients, r_squared, r_squared_adj, model_p_value,
        curvature_p_value, has_curvature, rmse
    """
    factor_names = [f["name"] for f in factors]

    merged, y = _merge_and_validate(design, results, response_name)

    # Build X: intercept + main + 2-way interactions + quadratic
    X_cols = ["Intercept"] + factor_names
    X_cols += [f"{a}*{b}" for a, b in _pairwise(factor_names)]
    X_cols += [f"{f}^2" for f in factor_names]

    _check_parameter_count(len(merged), len(X_cols))

    X_parts = [np.ones(len(merged))]
    for f in factor_names:
        X_parts.append(merged[f].values)
    for a, b in _pairwise(factor_names):
        X_parts.append(merged[a].values * merged[b].values)
    for f in factor_names:
        X_parts.append(merged[f].values ** 2)

    X = np.column_stack(X_parts)

    ols = sm.OLS(y, X).fit()

    coefficients = []
    for i, term in enumerate(X_cols):
        pv = float(ols.pvalues[i])
        coefficients.append({
            "term": term,
            "estimate": float(ols.params[i]),
            "std_err": float(ols.bse[i]) if np.isfinite(ols.bse[i]) else None,
            "p_value": pv if np.isfinite(pv) else None,
            "significant": bool(pv < alpha) if np.isfinite(pv) else False,
        })

    # Curvature test: center points vs factorial points
    curvature_p, has_curv = _curvature_test(merged, y, factor_names)

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
        "rmse": 0.0 if (hasattr(ols, 'mse_resid') and ols.mse_resid < 1e-12) else (
            float(np.sqrt(ols.mse_resid)) if hasattr(ols, 'mse_resid') and np.isfinite(ols.mse_resid) else None
        ),
        "residuals": residuals_data,
        "lack_of_fit_p": lack_of_fit_p,
        "n_obs": len(merged),
        "n_params": len(X_cols),
    }


def has_curvature(factorial_y: np.ndarray, center_y: np.ndarray,
                  alpha: float = 0.05) -> bool:
    """Test for curvature by comparing center point mean vs factorial mean.

    Parameters
    ----------
    factorial_y : np.ndarray
        Response values at factorial (non-center) points.
    center_y : np.ndarray
        Response values at center points.
    alpha : float
        Significance level.

    Returns
    -------
    bool
        True if curvature is statistically significant.
    """
    if len(center_y) < 2:
        return False

    # Two-sample t-test (unequal variance)
    _, p_value = stats.ttest_ind(center_y, factorial_y, equal_var=False)

    return p_value < alpha


def _curvature_test(design: pd.DataFrame, y: np.ndarray,
                    factor_names: list[str]) -> tuple[float, bool]:
    """Perform curvature test using center vs factorial points.

    Returns (p_value, has_curvature).
    Uses shared _is_center_row helper.
    """
    is_center = _is_center_row(design, factor_names)

    center_y = y[is_center]
    factorial_y = y[~is_center]

    if len(center_y) < 2 or len(factorial_y) < 2:
        return 1.0, False

    _, p_value = stats.ttest_ind(center_y, factorial_y, equal_var=False)
    return float(p_value), bool(p_value < 0.05)


def _pairwise(items: list[str]) -> list[tuple[str, str]]:
    """Return all unique 2-element combinations (unordered)."""
    return list(itertools.combinations(items, 2))


def predict_from_model(model: dict, factors: list[dict], point: dict) -> float:
    """Predict response value at a given point using a fitted linear or RSM model.

    Parameters
    ----------
    model : dict
        Output from fit_linear() or fit_rsm().
    factors : list of dict
        Factor definitions.
    point : dict
        Factor values in coded space, e.g. {"A": 0.5, "B": -0.3}.

    Returns
    -------
    float
        Predicted response.
    """
    coefs = {c["term"]: c["estimate"] for c in model["coefficients"]}
    prediction = coefs.get("Intercept", 0.0)

    for f in factors:
        name = f["name"]
        if name in coefs:
            prediction += coefs[name] * point.get(name, 0.0)

    for a, b in _pairwise([f["name"] for f in factors]):
        term = f"{a}*{b}"
        if term in coefs:
            prediction += coefs[term] * point.get(a, 0.0) * point.get(b, 0.0)

    # Quadratic terms (RSM)
    for f in factors:
        term = f"{f['name']}^2"
        if term in coefs:
            prediction += coefs[term] * point.get(f["name"], 0.0) ** 2

    return prediction


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
