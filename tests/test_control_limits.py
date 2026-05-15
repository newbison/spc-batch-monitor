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
