"""Tests for doe/profiler.py — prediction profiler computation."""
import numpy as np
import pandas as pd
from doe.profiler import compute_profile, compute_overall_desirability


def test_compute_profile_basic():
    """compute_profile returns predictions and traces for all responses."""
    factors = [
        {"name": "T", "type": "continuous", "low": 80, "high": 120},
        {"name": "P", "type": "continuous", "low": 2, "high": 4},
    ]
    class FakeModel:
        pass

    # Simple linear model for response "y": y = 10 + 2*T + 1*P
    model_y = {
        "model_type": "linear",
        "coefficients": [
            {"term": "Intercept", "estimate": 10.0},
            {"term": "T", "estimate": 2.0},
            {"term": "P", "estimate": 1.0},
            {"term": "T*P", "estimate": 0.0},
        ],
    }

    models = {"y": model_y}
    responses = [{"name": "y", "goal": "maximize", "low": 5.0, "high": 20.0}]
    positions = {"T": 0.0, "P": 0.0}

    result = compute_profile(factors, models, responses, positions, n_points=10)

    assert "y" in result
    assert "predicted" in result["y"]
    assert "desirability" in result["y"]
    assert "traces" in result["y"]
    assert "T" in result["y"]["traces"]
    assert "P" in result["y"]["traces"]

    # At center point (T=0, P=0), predicted = intercept = 10.0
    assert abs(result["y"]["predicted"] - 10.0) < 0.01

    # Trace for T should have correct x and y lengths
    t_trace = result["y"]["traces"]["T"]
    assert len(t_trace["x"]) == 10
    assert len(t_trace["y"]) == 10
    # x range should be -1 to 1
    assert abs(t_trace["x"][0] - (-1.0)) < 0.01
    assert abs(t_trace["x"][-1] - 1.0) < 0.01


def test_compute_profile_at_corner():
    """At T=+1, P=-1 with model y = 10 + 2*T + 1*P, predicted = 10 + 2 - 1 = 11."""
    factors = [
        {"name": "T", "type": "continuous", "low": 80, "high": 120},
        {"name": "P", "type": "continuous", "low": 2, "high": 4},
    ]
    model = {
        "model_type": "linear",
        "coefficients": [
            {"term": "Intercept", "estimate": 10.0},
            {"term": "T", "estimate": 2.0},
            {"term": "P", "estimate": 1.0},
        ],
    }
    models = {"y": model}
    responses = [{"name": "y", "goal": "maximize", "low": 0, "high": 20}]
    positions = {"T": 1.0, "P": -1.0}

    result = compute_profile(factors, models, responses, positions, n_points=10)

    assert abs(result["y"]["predicted"] - 11.0) < 0.01


def test_compute_profile_traces_vary_correctly():
    """When varying T, the trace curve for response y should reflect 2*T slope."""
    factors = [
        {"name": "A", "type": "continuous", "low": 0, "high": 10},
        {"name": "B", "type": "continuous", "low": 0, "high": 10},
    ]
    model = {
        "model_type": "linear",
        "coefficients": [
            {"term": "Intercept", "estimate": 5.0},
            {"term": "A", "estimate": 3.0},
            {"term": "B", "estimate": 0.0},
        ],
    }
    models = {"r": model}
    responses = [{"name": "r", "goal": "maximize", "low": 0, "high": 15}]
    positions = {"A": 0.0, "B": 0.0}

    result = compute_profile(factors, models, responses, positions, n_points=20)

    trace_a = result["r"]["traces"]["A"]
    # At A=-1: pred = 5 - 3 = 2, at A=+1: pred = 5 + 3 = 8
    assert abs(trace_a["y"][0] - 2.0) < 0.1
    assert abs(trace_a["y"][-1] - 8.0) < 0.1


def test_compute_profile_desirability():
    """Maximize goal: predicted=10 with low=0, high=20 -> d = (10-0)/(20-0) = 0.5."""
    factors = [{"name": "X", "type": "continuous", "low": 0, "high": 100}]
    model = {
        "model_type": "linear",
        "coefficients": [
            {"term": "Intercept", "estimate": 10.0},
            {"term": "X", "estimate": 0.0},
        ],
    }
    models = {"y": model}
    responses = [{"name": "y", "goal": "maximize", "low": 0.0, "high": 20.0}]
    positions = {"X": 0.0}

    result = compute_profile(factors, models, responses, positions, n_points=10)

    assert abs(result["y"]["desirability"] - 0.5) < 0.01


def test_compute_overall_desirability():
    """Geometric mean of [0.8, 0.5] = (0.8 * 0.5)^(1/2) = 0.632."""
    d = compute_overall_desirability([0.8, 0.5])
    assert abs(d - 0.632) < 0.01


def test_compute_overall_desirability_zero():
    """Geometric mean with a zero should be zero."""
    d = compute_overall_desirability([0.9, 0.0, 0.7])
    assert d == 0.0
