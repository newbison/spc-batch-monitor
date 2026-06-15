import numpy as np
import pandas as pd
from spc_engine.control_limits import compute_xbar_r


def test_compute_xbar_r_known_data_n10():
    # 5 batches, n=10, constant values
    data = {f"rep{i+1}": [6.0 + i * 0.5 + j * 0.02 for j in range(5)]
            for i in range(10)}
    df = pd.DataFrame(data)
    result = compute_xbar_r(df)

    assert len(result["xbar"]) == 5
    assert len(result["r"]) == 5
    assert result["UCLx"] > result["CLx"] > result["LCLx"]
    assert result["UCLr"] >= result["CLr"] >= result["LCLr"]


def test_xbar_r_all_same_values_n10():
    data = {f"rep{i+1}": [5.0, 5.0, 5.0] for i in range(10)}
    df = pd.DataFrame(data)
    result = compute_xbar_r(df)

    assert result["Xbarbar"] == 5.0
    assert result["Rbar"] == 0.0
    assert result["UCLx"] == 5.0
    assert result["LCLx"] == 5.0
    assert result["UCLr"] == 0.0


def test_auto_detect_subgroup_size():
    # 3 rows, 10 reps — should auto-detect n=10
    data = {f"rep{i+1}": [7.0, 7.5, 8.0] for i in range(10)}
    df = pd.DataFrame(data)
    result = compute_xbar_r(df)
    assert len(result["xbar"]) == 3
    # A2 for n=10 is 0.308 — UCLx should be close to CLx for small range
    assert abs(result["UCLx"] - result["CLx"]) < 1.0


def test_baseline_freezes_limits():
    """Limits come from the first `baseline_size` rows; a later shift shows
    up as out-of-control points instead of inflating the limits."""
    np.random.seed(7)
    n_reps = 5
    # 20 baseline rows: tight process centered at 10.0
    base_rows = [
        [float(np.round(np.random.normal(10.0, 0.05), 3)) for _ in range(n_reps)]
        for _ in range(20)
    ]
    # 5 shifted rows: process mean jumps to 12.0 — should breach frozen UCL
    shifted_rows = [
        [float(np.round(np.random.normal(12.0, 0.05), 3)) for _ in range(n_reps)]
        for _ in range(5)
    ]
    all_rows = base_rows + shifted_rows
    data = {f"rep{i+1}": [r[i] for r in all_rows] for i in range(n_reps)}
    df = pd.DataFrame(data)

    result = compute_xbar_r(df)

    # baseline window honored
    assert result["baseline_n"] == 20
    # x̄/r still computed for all 25 rows (chart plots everything)
    assert len(result["xbar"]) == 25
    assert len(result["r"]) == 25

    # Centerline reflects only the baseline
    assert abs(result["Xbarbar"] - 10.0) < 0.1
    # Tight baseline → narrow control band
    assert result["UCLx"] - result["LCLx"] < 1.0

    # The shifted points must breach the frozen UCL (this is the whole point)
    shifted_xbars = result["xbar"][20:]
    assert np.all(shifted_xbars > result["UCLx"])


def test_baseline_falls_back_when_fewer_rows():
    """With fewer than baseline_size rows, all rows define the limits."""
    data = {f"rep{i+1}": [6.0, 7.0, 8.0] for i in range(5)}
    df = pd.DataFrame(data)  # 3 rows
    result = compute_xbar_r(df)
    assert result["baseline_n"] == 3  # min(20, 3)
