"""DOE analysis: linear regression and RSM via statsmodels.

Pure Python — no Streamlit imports.
"""

import itertools
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats


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

    return {
        "coefficients": coefficients,
        "r_squared": float(ols.rsquared) if np.isfinite(ols.rsquared) else None,
        "r_squared_adj": float(ols.rsquared_adj) if np.isfinite(ols.rsquared_adj) else None,
        "model_p_value": float(ols.f_pvalue) if np.isfinite(ols.f_pvalue) else None,
        "rmse": float(np.sqrt(ols.mse_resid)) if hasattr(ols, 'mse_resid') and np.isfinite(ols.mse_resid) else None,
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

    return {
        "coefficients": coefficients,
        "r_squared": float(ols.rsquared) if np.isfinite(ols.rsquared) else None,
        "r_squared_adj": float(ols.rsquared_adj) if np.isfinite(ols.rsquared_adj) else None,
        "model_p_value": float(ols.f_pvalue) if np.isfinite(ols.f_pvalue) else None,
        "curvature_p_value": curvature_p,
        "has_curvature": has_curv,
        "rmse": float(np.sqrt(ols.mse_resid)) if hasattr(ols, 'mse_resid') and np.isfinite(ols.mse_resid) else None,
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
