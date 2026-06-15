import numpy as np
import pandas as pd
from doe.optimization import desirability, optimize, overall_desirability


def test_desirability_maximize():
    """Maximize: d=0 at low, d=1 at high."""
    d = desirability(8.0, goal="maximize", low=5.0, high=10.0)
    assert 0.5 < d < 0.7  # 8 is 60% of the way from 5 to 10

    d_high = desirability(10.0, goal="maximize", low=5.0, high=10.0)
    assert d_high == 1.0

    d_low = desirability(5.0, goal="maximize", low=5.0, high=10.0)
    assert d_low == 0.0


def test_desirability_minimize():
    """Minimize: d=1 at low, d=0 at high."""
    d = desirability(7.0, goal="minimize", low=5.0, high=10.0)
    assert 0.3 < d < 0.7

    d_high = desirability(10.0, goal="minimize", low=5.0, high=10.0)
    assert d_high == 0.0

    d_low = desirability(5.0, goal="minimize", low=5.0, high=10.0)
    assert d_low == 1.0


def test_desirability_target():
    """Target: d=1 at target, d=0 at low and high."""
    d = desirability(8.0, goal="target", low=5.0, high=10.0, target=8.0)
    assert abs(d - 1.0) < 0.01

    d_low = desirability(5.0, goal="target", low=5.0, high=10.0, target=8.0)
    assert d_low == 0.0

    d_high = desirability(10.0, goal="target", low=5.0, high=10.0, target=8.0)
    assert d_high == 0.0

    d_mid = desirability(7.0, goal="target", low=5.0, high=10.0, target=8.0)
    assert 0.0 < d_mid < 1.0


def test_overall_desirability():
    """Geometric mean of individual desirabilities."""
    individual = [1.0, 0.8, 0.5]
    od = overall_desirability(individual)
    # (1.0 * 0.8 * 0.5)^(1/3) = 0.4^0.333
    assert 0.7 < od < 0.8  # roughly (0.4)^(1/3) ≈ 0.737

    od_zero = overall_desirability([1.0, 0.0, 0.8])
    assert od_zero == 0.0


def test_optimize_simple():
    """Optimize a simple linear model: Y = 10 + 2*A + 3*B (maximize Y)."""
    factors = [
        {"name": "A", "type": "continuous", "low": 50, "high": 80},
        {"name": "B", "type": "continuous", "low": 120, "high": 160},
    ]
    responses = [
        {"name": "Y", "goal": "maximize", "target": None, "low": 5.0, "high": 25.0},
    ]
    models = {
        "Y": {
            "coefficients": [
                {"term": "Intercept", "estimate": 10.0, "std_err": 0.5, "p_value": 0.001, "significant": True},
                {"term": "A", "estimate": 2.0, "std_err": 0.5, "p_value": 0.01, "significant": True},
                {"term": "B", "estimate": 3.0, "std_err": 0.5, "p_value": 0.001, "significant": True},
                {"term": "A*B", "estimate": 0.0, "std_err": 0.5, "p_value": 0.5, "significant": False},
            ],
            "r_squared": 0.99,
            "r_squared_adj": 0.98,
            "model_p_value": 0.001,
        }
    }

    result = optimize(factors, responses, models, n_starts=5)

    assert result["desirability"] >= 0.5
    # Should push A and B to their high settings
    assert result["optimal_settings"]["A"] >= 70
    assert result["optimal_settings"]["B"] >= 140


def test_optimize_multi_response():
    """Two responses with conflicting goals."""
    factors = [
        {"name": "temp", "type": "continuous", "low": 100, "high": 200},
    ]
    responses = [
        {"name": "yield", "goal": "maximize", "target": None, "low": 50, "high": 100},
        {"name": "impurity", "goal": "minimize", "target": None, "low": 0, "high": 10},
    ]
    # yield increases with temp, impurity increases with temp → tradeoff
    models = {
        "yield": {
            "coefficients": [
                {"term": "Intercept", "estimate": 50.0, "std_err": 1.0, "p_value": 0.001, "significant": True},
                {"term": "temp", "estimate": 20.0, "std_err": 1.0, "p_value": 0.001, "significant": True},
            ],
            "r_squared": 0.95,
        },
        "impurity": {
            "coefficients": [
                {"term": "Intercept", "estimate": 1.0, "std_err": 0.5, "p_value": 0.001, "significant": True},
                {"term": "temp", "estimate": 4.0, "std_err": 0.5, "p_value": 0.001, "significant": True},
            ],
            "r_squared": 0.90,
        },
    }

    result = optimize(factors, responses, models, n_starts=5)

    assert result["desirability"] > 0.0
    # Optimal temp should be a compromise
    assert 100 <= result["optimal_settings"]["temp"] <= 200
    assert "yield" in result["predicted_responses"]
    assert "impurity" in result["predicted_responses"]
