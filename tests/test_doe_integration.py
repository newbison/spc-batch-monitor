"""Integration tests for the full DOE pipeline: design -> capture -> analyze -> optimize."""

import numpy as np
import pandas as pd
from doe.designs import generate_full_factorial, decode_to_actual
from doe.analysis import fit_linear, fit_rsm, predict_from_model, _is_center_row
from doe.optimization import optimize


def test_full_pipeline_2_factor():
    """End-to-end: generate 2^2 design, create responses with known coefficients,
    fit model, verify coefficient recovery, and optimize."""
    # --- Define ---
    factors = [
        {"name": "temp", "type": "continuous", "low": 100, "high": 200},
        {"name": "speed", "type": "continuous", "low": 50, "high": 80},
    ]
    responses = [
        {"name": "strength", "goal": "maximize", "target": None, "low": 5.0, "high": 25.0},
        {"name": "waste", "goal": "minimize", "target": None, "low": 0.0, "high": 10.0},
    ]

    # --- Design ---
    coded = generate_full_factorial(factors, n_center=3)
    assert len(coded) == 7  # 4 factorial + 3 center

    # --- Simulate real process ---
    np.random.seed(123)
    # strength = 15 + 4*temp + 2*speed + noise
    coded["strength"] = (
        15.0
        + 4.0 * coded["temp"]
        + 2.0 * coded["speed"]
        + np.random.normal(0, 0.3, len(coded))
    )
    # waste = 3 - 1*temp + 0.5*speed + noise (less waste at higher temp)
    coded["waste"] = (
        3.0
        - 1.0 * coded["temp"]
        + 0.5 * coded["speed"]
        + np.random.normal(0, 0.1, len(coded))
    )
    results = coded[["run", "strength", "waste"]]
    design = coded[["run", "temp", "speed"]]

    # --- Analyze: strength ---
    model_s = fit_linear(factors, design, results, "strength")
    coefs_s = {c["term"]: c["estimate"] for c in model_s["coefficients"]}
    assert model_s["r_squared"] > 0.9
    assert abs(coefs_s["Intercept"] - 15.0) < 1.0
    assert abs(coefs_s["temp"] - 4.0) < 1.0
    assert abs(coefs_s["speed"] - 2.0) < 1.0
    assert model_s["rmse"] is not None
    assert model_s["rmse"] < 1.0

    # --- Analyze: waste ---
    model_w = fit_linear(factors, design, results, "waste")
    coefs_w = {c["term"]: c["estimate"] for c in model_w["coefficients"]}
    assert model_w["r_squared"] > 0.8
    assert abs(coefs_w["Intercept"] - 3.0) < 1.0
    assert abs(coefs_w["temp"] + 1.0) < 1.0  # temp should be negative
    assert model_w["rmse"] is not None

    # --- Check curvature (should be False for pure linear) ---
    is_center = _is_center_row(design, ["temp", "speed"])
    assert is_center.sum() == 3
    from doe.analysis import has_curvature
    assert not has_curvature(
        results.loc[~is_center, "strength"].values,
        results.loc[is_center, "strength"].values,
    )

    # --- Optimize ---
    models = {"strength": model_s, "waste": model_w}
    opt = optimize(factors, responses, models, n_starts=10)

    assert opt["desirability"] > 0.3  # conflicting objectives -> compromise
    assert 100 <= opt["optimal_settings"]["temp"] <= 200
    assert 50 <= opt["optimal_settings"]["speed"] <= 80

    # Prediction intervals computed from RMSE
    pi_s = opt["prediction_intervals"]["strength"]
    assert pi_s[0] < pi_s[1]
    half_w = (pi_s[1] - pi_s[0]) / 2
    assert 0.1 < half_w < 5.0  # reasonable range for +-2*RMSE

    # --- predict_from_model at optimum ---
    coded_point = {"temp": 1.0, "speed": 1.0}  # both at high
    pred_high = predict_from_model(model_s, factors, coded_point)
    assert pred_high > 17.0  # both at high should give high strength


def test_pipeline_with_center_curvature():
    """RSM pipeline: data with curvature should trigger RSM, and quadratic
    terms should improve fit over linear-only model."""
    factors = [
        {"name": "temp", "type": "continuous", "low": 100, "high": 200},
        {"name": "speed", "type": "continuous", "low": 50, "high": 80},
    ]
    responses = [
        {"name": "yield", "goal": "maximize", "target": None, "low": 0.0, "high": 50.0},
    ]

    coded = generate_full_factorial(factors, n_center=5)
    np.random.seed(99)
    # yield = 30 + 1*temp - 10*temp^2 + 1*speed + noise  (strong quadratic curvature)
    # Small main effects keep factorial-point variance low so the
    # Welch t-test (used by _curvature_test) can detect curvature.
    coded["yield"] = (
        30.0
        + 1.0 * coded["temp"]
        - 10.0 * coded["temp"] ** 2
        + 1.0 * coded["speed"]
        + np.random.normal(0, 0.3, len(coded))
    )
    results = coded[["run", "yield"]]
    design = coded[["run", "temp", "speed"]]

    # RSM should detect curvature
    model = fit_rsm(factors, design, results, "yield")
    assert model["has_curvature"] is True
    assert model["r_squared"] > 0.8

    # Quadratic term for temp should be significant and negative
    coefs = {c["term"]: c for c in model["coefficients"]}
    assert "temp^2" in coefs
    assert coefs["temp^2"]["significant"] is True
    assert coefs["temp^2"]["estimate"] < 0  # negative curvature
