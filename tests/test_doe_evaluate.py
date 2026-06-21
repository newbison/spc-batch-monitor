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
