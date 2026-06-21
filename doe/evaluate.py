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

    # Power for effect sizes 0.5sigma, 1sigma, 2sigma
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
            f"Low power ({power[1.0]:.2f}) for 1sigma effect. "
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
    # Non-centrality parameter: ncp = n_obs * (effect_size)^2 / sigma^2
    # Effect_size is the regression coefficient in sigma units.
    ncp = n_obs * (effect_size ** 2)

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
        return float(min(1.0, X.shape[1] / (n_obs * max_var)))
    except np.linalg.LinAlgError:
        return 0.0
