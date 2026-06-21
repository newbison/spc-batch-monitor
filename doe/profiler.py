"""Prediction profiler for interactive DOE exploration.

Computes predicted responses at slider positions and trace curves
showing how each response varies across each factor's range.

Pure Python — no Streamlit imports.
"""

import numpy as np
from doe.analysis import predict_from_model
from doe.optimization import desirability


def compute_profile(
    factors: list[dict],
    models: dict,
    responses: list[dict],
    slider_positions: dict[str, float],
    n_points: int = 50,
) -> dict:
    """Compute prediction profile at current slider positions.

    Parameters
    ----------
    factors : list of dict
        Factor definitions (name, type, low, high).
    models : dict
        Fitted models keyed by response name.
    responses : list of dict
        Response definitions (name, goal, low, high, target).
    slider_positions : dict
        Current coded values for each factor, e.g. {"T": 0.5, "P": -0.3}.
    n_points : int
        Number of points in each trace curve (default 50).

    Returns
    -------
    dict keyed by response name:
        {
            "predicted": float,
            "desirability": float,
            "traces": {
                factor_name: {
                    "x": [coded_values across -1..+1],
                    "y": [predicted response values],
                }
            }
        }
    """
    factor_names = [f["name"] for f in factors]
    response_map = {r["name"]: r for r in responses}

    result = {}
    for r in responses:
        rname = r["name"]
        if rname not in models:
            continue
        model = models[rname]

        # Predicted value at current positions
        pred = predict_from_model(model, factors, slider_positions)

        # Desirability
        d = desirability(
            pred,
            goal=r["goal"],
            low=r.get("low", 0),
            high=r.get("high", 1e12),
            target=r.get("target"),
        )

        # Trace curves: vary each factor across its range
        traces = {}
        for fname in factor_names:
            x_range = np.linspace(-1, 1, n_points)
            y_vals = []
            for x_val in x_range:
                point = dict(slider_positions)
                point[fname] = x_val
                y_vals.append(predict_from_model(model, factors, point))
            traces[fname] = {
                "x": [float(v) for v in x_range],
                "y": [float(v) for v in y_vals],
            }

        result[rname] = {
            "predicted": round(float(pred), 4),
            "desirability": round(float(d), 4),
            "traces": traces,
        }

    return result


def compute_overall_desirability(individual_d: list[float]) -> float:
    """Geometric mean of individual desirability values."""
    if not individual_d or any(d <= 0 for d in individual_d):
        return 0.0
    return float(np.prod(individual_d) ** (1.0 / len(individual_d)))
