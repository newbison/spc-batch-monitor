import pytest
import numpy as np
import pandas as pd
from doe.analysis import fit_linear, fit_rsm, has_curvature, predict_from_model, _is_center_row


def test_fit_linear_perfect_model():
    """Y = 10 + 2*A + 3*B — exact linear fit."""
    factors = [
        {"name": "A", "type": "continuous", "low": 50, "high": 80},
        {"name": "B", "type": "continuous", "low": 120, "high": 160},
    ]
    design = pd.DataFrame({
        "run": [1, 2, 3, 4],
        "A": [-1, 1, -1, 1],
        "B": [-1, -1, 1, 1],
    })
    # Y = 10 + 2*A + 3*B
    # run1: 10 + 2*(-1) + 3*(-1) = 5
    # run2: 10 + 2*(1) + 3*(-1) = 9
    # run3: 10 + 2*(-1) + 3*(1) = 11
    # run4: 10 + 2*(1) + 3*(1) = 15
    results = pd.DataFrame({
        "run": [1, 2, 3, 4],
        "Y": [5, 9, 11, 15],
    })

    model = fit_linear(factors, design, results, "Y")

    assert model["r_squared"] > 0.99
    # Check coefficients
    coefs = {c["term"]: c["estimate"] for c in model["coefficients"]}
    assert abs(coefs["Intercept"] - 10.0) < 0.5
    assert abs(coefs["A"] - 2.0) < 0.5
    assert abs(coefs["B"] - 3.0) < 0.5


def test_fit_linear_with_interaction():
    """Y = 10 + 2*A + 3*B + 4*A*B — includes significant interaction."""
    factors = [
        {"name": "A", "type": "continuous", "low": 50, "high": 80},
        {"name": "B", "type": "continuous", "low": 120, "high": 160},
    ]
    design = pd.DataFrame({
        "run": [1, 2, 3, 4],
        "A": [-1, 1, -1, 1],
        "B": [-1, -1, 1, 1],
    })
    # Y = 10 + 2*A + 3*B + 4*A*B
    results = pd.DataFrame({
        "run": [1, 2, 3, 4],
        "Y": [10 - 2 - 3 + 4, 10 + 2 - 3 - 4, 10 - 2 + 3 - 4, 10 + 2 + 3 + 4],
    })

    model = fit_linear(factors, design, results, "Y")

    assert model["r_squared"] > 0.99
    coefs = {c["term"]: c["estimate"] for c in model["coefficients"]}
    assert abs(coefs["A*B"] - 4.0) < 0.5


def test_fit_linear_noisy_data():
    """Linear fit with noise — R² should be reasonable but not perfect."""
    np.random.seed(42)
    factors = [
        {"name": "A", "type": "continuous", "low": 50, "high": 80},
        {"name": "B", "type": "continuous", "low": 120, "high": 160},
        {"name": "C", "type": "continuous", "low": 10, "high": 20},
    ]
    # 2^3 = 8 runs
    coded = np.array([
        [-1, -1, -1], [1, -1, -1], [-1, 1, -1], [1, 1, -1],
        [-1, -1, 1], [1, -1, 1], [-1, 1, 1], [1, 1, 1],
    ], dtype=float)
    design = pd.DataFrame(coded, columns=["A", "B", "C"])
    design.insert(0, "run", range(1, 9))
    # Y = 20 + 5*A + noise
    y = 20 + 5 * coded[:, 0] + np.random.normal(0, 1, 8)
    results = pd.DataFrame({"run": range(1, 9), "Y": y})

    model = fit_linear(factors, design, results, "Y")

    assert model["r_squared"] > 0.7
    # A should be significant, B and C should not
    coefs = {c["term"]: c for c in model["coefficients"]}
    assert coefs["A"]["significant"]
    assert not coefs["B"]["significant"]


def test_fit_rsm_with_curvature():
    """RSM fit on data with curvature — should detect curvature."""
    np.random.seed(10)
    factors = [
        {"name": "A", "type": "continuous", "low": 50, "high": 80},
        {"name": "B", "type": "continuous", "low": 120, "high": 160},
    ]
    # 2^2 factorial + 5 center points
    coded = np.array([
        [-1, -1], [1, -1], [-1, 1], [1, 1],
        [0, 0], [0, 0], [0, 0], [0, 0], [0, 0],
    ], dtype=float)
    design = pd.DataFrame(coded, columns=["A", "B"])
    design.insert(0, "run", range(1, 10))
    # Y = 20 + 2*A + 3*B + 4*A^2 (curvature)
    y = 20 + 2*coded[:, 0] + 3*coded[:, 1] + 4*coded[:, 0]**2 + np.random.normal(0, 0.3, 9)
    results = pd.DataFrame({"run": range(1, 10), "Y": y})

    model = fit_rsm(factors, design, results, "Y")

    assert model["r_squared"] > 0.8
    # Should have quadratic terms
    terms = [c["term"] for c in model["coefficients"]]
    assert "A^2" in terms or "A²" in terms


def test_has_curvature_true():
    """Curvature test detects real curvature."""
    np.random.seed(42)
    factorial_y = np.array([10, 20, 15, 25], dtype=float)  # factorial points
    center_y = np.array([100, 101, 100], dtype=float)  # center points far from linear prediction
    assert has_curvature(factorial_y, center_y) == True


def test_has_curvature_false():
    """No curvature when center matches linear model prediction."""
    np.random.seed(42)
    factorial_y = np.array([10, 20, 15, 25], dtype=float)
    # Predicted center = mean of factorial = 17.5
    center_y = np.array([17, 18, 17.5], dtype=float)
    assert has_curvature(factorial_y, center_y) == False


def test_fit_linear_missing_response():
    """fit_linear raises ValueError when response_name not in results."""
    factors = [{"name": "A", "type": "continuous", "low": 50, "high": 80}]
    design = pd.DataFrame({"run": [1, 2], "A": [-1.0, 1.0]})
    results = pd.DataFrame({"run": [1, 2], "wrong_name": [5.0, 7.0]})
    with pytest.raises(ValueError, match="not found in results"):
        fit_linear(factors, design, results, "Y")


def test_fit_linear_nan_in_response():
    """fit_linear raises ValueError when response contains NaN."""
    factors = [{"name": "A", "type": "continuous", "low": 50, "high": 80}]
    design = pd.DataFrame({"run": [1, 2], "A": [-1.0, 1.0]})
    results = pd.DataFrame({"run": [1, 2], "Y": [5.0, float("nan")]})
    with pytest.raises(ValueError, match="NaN or Inf"):
        fit_linear(factors, design, results, "Y")


def test_fit_linear_overparameterized():
    """fit_linear raises ValueError when n_params > n_obs."""
    factors = [{"name": f"F{i}", "type": "continuous", "low": 0, "high": 10} for i in range(5)]
    # 5 factors -> 1 + 5 + 10 = 16 params, only 8 rows in fractional factorial
    design = pd.DataFrame({
        "run": list(range(1, 9)),
        "F0": [-1, 1, -1, 1, -1, 1, -1, 1],
        "F1": [-1, -1, 1, 1, -1, -1, 1, 1],
        "F2": [-1, -1, -1, -1, 1, 1, 1, 1],
        "F3": [1, -1, 1, -1, -1, 1, -1, 1],
        "F4": [-1, 1, 1, -1, 1, -1, -1, 1],
    })
    results = pd.DataFrame({"run": list(range(1, 9)),
                            "Y": [10.0, 12.0, 11.0, 13.0, 9.0, 14.0, 10.0, 15.0]})
    with pytest.raises(ValueError, match="more parameters"):
        fit_linear(factors, design, results, "Y")


def test_fit_linear_merges_on_run():
    """fit_linear merges on 'run' -- results in different order still works."""
    factors = [{"name": "A", "type": "continuous", "low": 50, "high": 80}]
    design = pd.DataFrame({"run": [2, 1], "A": [1.0, -1.0]})
    # Results in opposite run order -- should still work after merge
    results = pd.DataFrame({"run": [1, 2], "Y": [5.0, 7.0]})
    # Y = 6 + 1*A -> run1 (A=-1): Y=5, run2 (A=1): Y=7
    model = fit_linear(factors, design, results, "Y")
    coefs = {c["term"]: c["estimate"] for c in model["coefficients"]}
    assert abs(coefs["A"] - 1.0) < 0.5


def test_predict_from_model_linear():
    """predict_from_model recovers known linear model predictions."""
    factors = [{"name": "A", "type": "continuous", "low": 50, "high": 80},
               {"name": "B", "type": "continuous", "low": 100, "high": 200}]
    model = {
        "coefficients": [
            {"term": "Intercept", "estimate": 10.0},
            {"term": "A", "estimate": 2.0},
            {"term": "B", "estimate": 3.0},
            {"term": "A*B", "estimate": 1.5},
        ],
    }
    # Y = 10 + 2*A + 3*B + 1.5*A*B
    pred = predict_from_model(model, factors, {"A": 1.0, "B": -1.0})
    assert abs(pred - (10 + 2 - 3 - 1.5)) < 0.01


def test_predict_from_model_rsm():
    """predict_from_model includes quadratic terms."""
    factors = [{"name": "A", "type": "continuous", "low": 50, "high": 80}]
    model = {
        "coefficients": [
            {"term": "Intercept", "estimate": 20.0},
            {"term": "A", "estimate": 5.0},
            {"term": "A^2", "estimate": 4.0},
        ],
    }
    # Y = 20 + 5*A + 4*A^2; A=0.5 -> 20 + 2.5 + 1.0 = 23.5
    pred = predict_from_model(model, factors, {"A": 0.5})
    assert abs(pred - 23.5) < 0.01


def test_is_center_row():
    """_is_center_row identifies rows where all factors are near 0."""
    design = pd.DataFrame({"A": [-1.0, 0.0, 1.0, 0.001], "B": [-1.0, 0.0, 0.0, 0.0]})
    result = _is_center_row(design, ["A", "B"], tol=0.01)
    assert result.tolist() == [False, True, False, True]  # row 4: A=0.001 < 0.01 -> True


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
