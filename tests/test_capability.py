import numpy as np
import math
from spc_engine.capability import compute_capability


def test_capability_centered_perfect():
    np.random.seed(1)
    xbar = np.random.normal(7.0, 0.15, 100)
    result = compute_capability(xbar, lsl=5.5, usl=8.5)

    assert result["Pp"] > 1.0
    assert result["Ppk"] > 1.0
    assert abs(result["Pp"] - result["Ppk"]) < 0.5
    assert "sigma_overall" in result
    assert result["ppm_usl"] >= 0
    assert result["ppm_lsl"] >= 0


def test_capability_off_center():
    # Mean shifted toward USL with small variance
    np.random.seed(2)
    xbar = np.random.normal(7.5, 0.05, 50)
    result = compute_capability(xbar, lsl=5.5, usl=8.5)

    assert result["Ppk"] < result["Pp"]  # Ppk penalizes off-center
    assert abs(result["mean"] - 7.5) < 0.01


def test_capability_usl_only():
    # Only upper spec — e.g., impurity ≤ 0.5%
    xbar = np.array([0.3, 0.35, 0.32, 0.38, 0.33])
    result = compute_capability(xbar, lsl=float("nan"), usl=0.5)

    assert math.isnan(result["Pp"])       # Pp needs both limits
    assert result["Ppk"] > 0              # Ppk uses USL only
    assert result["ppm_lsl"] == 0         # no LSL → no ppm below
    assert result["ppm_usl"] > 0


def test_capability_lsl_only():
    # Only lower spec — e.g., purity ≥ 98%
    xbar = np.array([98.5, 99.0, 98.8, 99.2, 98.7])
    result = compute_capability(xbar, lsl=98.0, usl=float("nan"))

    assert math.isnan(result["Pp"])
    assert result["Ppk"] > 0              # Ppk uses LSL only
    assert result["ppm_usl"] == 0         # no USL → no ppm above
    assert result["ppm_lsl"] > 0


def test_capability_no_specs():
    xbar = np.array([1.0, 2.0, 3.0])
    result = compute_capability(xbar, lsl=float("nan"), usl=float("nan"))

    assert math.isnan(result["Pp"])
    assert math.isnan(result["Ppk"])
    assert result["ppm_usl"] == 0
    assert result["ppm_lsl"] == 0
