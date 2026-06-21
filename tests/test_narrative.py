import math
import numpy as np
from reports.narrative import build_summary


def test_capable_process_no_violations():
    """Capable process with no OOC → positive summary."""
    cap = {"Pp": 1.8, "Ppk": 1.52, "sigma_overall": 0.93, "mean": 8.45,
           "total_ppm": 127}
    violations = []
    limits = {"xbar": np.array([8.3, 8.4, 8.5, 8.6, 8.5, 8.4, 8.3, 8.4]),
              "baseline_n": 5}
    result = build_summary(
        cap=cap, violations=violations, limits=limits,
        formula="Grade A", parameter="viscosity",
        date_range=("2025-01-01", "2025-03-15"), n_batches=40,
    )
    assert "1.52" in result["verdict"]
    assert "capable" in result["verdict"].lower()
    assert result["ooc_summary"] == "No out-of-control events detected."
    assert result["action_items"] == ""
    assert "40" in result["metrics_bullet"]


def test_marginal_process_with_violations():
    """Marginal process with OOC events → warning in summary."""
    cap = {"Pp": 1.1, "Ppk": 1.08, "sigma_overall": 1.2, "mean": 8.45,
           "total_ppm": 5500}
    violations = [
        {"batch_index": 12, "rule": 1, "description": "Point beyond 3σ"},
        {"batch_index": 18, "rule": 4, "description": "8 consecutive above CL"},
    ]
    batch_ids = [f"B-{i:03d}" for i in range(20)]
    dates = [f"2025-03-{(i % 28) + 1:02d}" for i in range(20)]
    limits = {"xbar": np.zeros(20), "baseline_n": 10}
    result = build_summary(
        cap=cap, violations=violations, limits=limits,
        formula="Grade A", parameter="viscosity",
        date_range=("2025-03-01", "2025-03-28"),
        n_batches=20, batch_ids=batch_ids, dates=dates,
    )
    assert "marginal" in result["verdict"].lower()
    assert "1.08" in result["verdict"]
    assert "2" in result["ooc_summary"]
    assert result["action_items"] != ""


def test_not_capable_process():
    """Ppk < 1.0 → not capable verdict."""
    cap = {"Pp": 0.7, "Ppk": 0.65, "sigma_overall": 2.0, "mean": 8.45,
           "total_ppm": 50000}
    violations = [
        {"batch_index": 5, "rule": 1, "description": "Point beyond 3σ"},
    ]
    batch_ids = [f"B-{i:03d}" for i in range(10)]
    dates = [f"2025-01-{(i % 28) + 1:02d}" for i in range(10)]
    limits = {"xbar": np.zeros(10), "baseline_n": 10}
    result = build_summary(
        cap=cap, violations=violations, limits=limits,
        formula="Grade A", parameter="viscosity",
        date_range=("2025-01-01", "2025-01-31"),
        n_batches=10, batch_ids=batch_ids, dates=dates,
    )
    assert "not capable" in result["verdict"].lower()
    assert "0.65" in result["verdict"]


def test_no_spec_limits():
    """No spec limits → Ppk is NaN → 'no specification' verdict."""
    cap = {"Pp": float("nan"), "Ppk": float("nan"), "sigma_overall": 0.5,
           "mean": 8.45, "total_ppm": 0}
    violations = []
    limits = {"xbar": np.zeros(5), "baseline_n": 5}
    result = build_summary(
        cap=cap, violations=violations, limits=limits,
        formula="Grade A", parameter="viscosity",
        date_range=("2025-01-01", "2025-01-31"), n_batches=5,
    )
    assert "no spec" in result["verdict"].lower() or "nan" in result["verdict"].lower()


def test_trend_detection():
    """Detect declining rolling Ppk trend."""
    cap = {"Pp": 1.3, "Ppk": 1.05, "sigma_overall": 1.0, "mean": 8.0,
           "total_ppm": 3000}
    violations = []
    xbar = np.array([8.5, 8.4, 8.3, 8.2, 8.1, 8.0, 7.9, 7.8, 7.7, 7.6,
                      7.5, 7.4, 7.3, 7.2, 7.1])
    limits = {"xbar": xbar, "baseline_n": 10}
    result = build_summary(
        cap=cap, violations=violations, limits=limits,
        formula="Grade A", parameter="viscosity",
        date_range=("2025-01-01", "2025-03-15"), n_batches=15,
    )
    assert "declin" in result["trend_note"].lower() or "downward" in result["trend_note"].lower()
