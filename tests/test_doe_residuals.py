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
