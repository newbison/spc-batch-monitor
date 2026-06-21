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
        elif mse > 0:
            # Fall back to ordinary studentized residual (using full MSE)
            # when delete-one estimate fails (extreme outlier case).
            studentized[i] = residuals[i] / np.sqrt(mse * (1 - h_ii))

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
        "studentized": [float(v) if np.isfinite(v) else float("nan") for v in studentized],
        "leverage": [float(v) if np.isfinite(v) else float("nan") for v in leverage],
        "cooks_d": [float(v) if np.isfinite(v) else float("nan") for v in cooks_d],
        "shapiro_p": float(shapiro_p) if np.isfinite(shapiro_p) else float("nan"),
        "run_order": [int(r) for r in run_order],
        "n_obs": n_obs,
        "n_params": n_params,
    }


def build_residual_plots(residuals_dict: dict) -> go.Figure:
    """Build a 2x2 Plotly subplot grid of residual diagnostic plots.

    Parameters
    ----------
    residuals_dict : dict
        Output from compute_residuals().

    Returns
    -------
    plotly.graph_objects.Figure
        2x2 subplot figure: Normal Q-Q, Residuals vs Predicted,
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
