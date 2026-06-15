import numpy as np
import pandas as pd
from doe.designs import (
    generate_full_factorial,
    generate_fractional_factorial,
    generate_box_behnken,
    decode_to_actual,
    add_center_points,
)


def test_full_factorial_2_factors():
    """2^2 full factorial = 4 runs, coded -1/+1."""
    factors = [
        {"name": "A", "type": "continuous", "low": 50, "high": 80},
        {"name": "B", "type": "continuous", "low": 120, "high": 160},
    ]
    df = generate_full_factorial(factors, n_center=0)
    assert len(df) == 4
    assert list(df.columns) == ["run", "A", "B"]
    # All combos of -1/+1
    assert set(df["A"].unique()) == {-1, 1}
    assert set(df["B"].unique()) == {-1, 1}
    # Every combination present
    assert len(df) == len(df.drop_duplicates(subset=["A", "B"]))


def test_full_factorial_with_center_points():
    """2^2 + 3 center points = 7 runs."""
    factors = [
        {"name": "A", "type": "continuous", "low": 50, "high": 80},
        {"name": "B", "type": "continuous", "low": 120, "high": 160},
    ]
    df = generate_full_factorial(factors, n_center=3)
    assert len(df) == 7
    # Center points have 0 for all continuous factors
    center_rows = df[(df["A"] == 0) & (df["B"] == 0)]
    assert len(center_rows) == 3


def test_full_factorial_with_categorical():
    """Categorical factor encoded as -1/+1."""
    factors = [
        {"name": "supplier", "type": "categorical", "low": "Alpha", "high": "Beta"},
        {"name": "temp", "type": "continuous", "low": 100, "high": 200},
    ]
    df = generate_full_factorial(factors, n_center=0)
    assert len(df) == 4
    assert set(df["supplier"].unique()) == {-1, 1}


def test_fractional_factorial_4_factors():
    """2^(4-1) Resolution IV = 8 runs."""
    factors = [{"name": f"F{i}", "type": "continuous", "low": i*10, "high": i*10+10} for i in range(4)]
    df = generate_fractional_factorial(factors, resolution=4)
    assert len(df) == 8
    assert list(df.columns)[:2] == ["run", "F0"]
    # All factors are -1/+1 coded
    for col in ["F0", "F1", "F2", "F3"]:
        assert set(df[col].unique()).issubset({-1.0, 1.0})


def test_box_behnken_3_factors():
    """Box-Behnken for 3 factors = 13 runs (12 + 1 center)."""
    factors = [
        {"name": f"F{i}", "type": "continuous", "low": i*10, "high": i*10+10} for i in range(3)
    ]
    df = generate_box_behnken(factors)
    assert len(df) == 15  # 12 edge + 3 center (bbdesign default n_center=0, we add 3)
    assert list(df.columns) == ["run", "F0", "F1", "F2"]
    # Center points exist
    center_rows = df[(df["F0"] == 0) & (df["F1"] == 0) & (df["F2"] == 0)]
    assert len(center_rows) == 3


def test_decode_to_actual():
    """Decode coded -1/0/+1 to actual factor values."""
    factors = [
        {"name": "speed", "type": "continuous", "low": 50, "high": 80},
        {"name": "supplier", "type": "categorical", "low": "Alpha", "high": "Beta"},
    ]
    coded = pd.DataFrame({"run": [1, 2, 3], "speed": [-1, 0, 1], "supplier": [-1, 0, 1]})
    decoded = decode_to_actual(coded, factors)
    assert decoded["speed"].tolist() == [50, 65, 80]
    assert decoded["supplier"].tolist() == ["Alpha", "Midpoint", "Beta"]


def test_add_center_points():
    """Add center points to a design matrix."""
    coded = pd.DataFrame({
        "run": [1, 2, 3, 4],
        "A": [-1, 1, -1, 1],
        "B": [-1, -1, 1, 1],
    })
    result = add_center_points(coded, ["A", "B"], n_center=3)
    assert len(result) == 7
    center_rows = result[(result["A"] == 0) & (result["B"] == 0)]
    assert len(center_rows) == 3
    assert result["run"].tolist() == [1, 2, 3, 4, 5, 6, 7]
