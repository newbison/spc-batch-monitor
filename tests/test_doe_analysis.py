import numpy as np
import pandas as pd
from doe.analysis import fit_linear, fit_rsm, has_curvature


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
