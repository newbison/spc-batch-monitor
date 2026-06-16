"""DOE multi-response optimization via Derringer-Suich desirability.

Pure Python — no Streamlit imports.
"""

import numpy as np
from scipy.optimize import minimize
from doe.analysis import predict_from_model


def desirability(value: float, goal: str, low: float, high: float,
                 target: float | None = None, weight: float = 1.0) -> float:
    """Compute individual desirability for a single response.

    Parameters
    ----------
    value : float
        The response value.
    goal : str
        One of 'maximize', 'minimize', 'target'.
    low : float
        Lower bound for desirability (d=0 below this for maximize, d=0 above for minimize).
    high : float
        Upper bound for desirability (d=1 above this for maximize, d=1 below for minimize).
    target : float or None
        Required when goal='target'. The ideal value.
    weight : float
        Shape parameter (1 = linear, >1 = more selective, <1 = more lenient).

    Returns
    -------
    float
        Desirability value between 0 and 1.
    """
    d = 0.0

    if goal == "maximize":
        if value <= low:
            d = 0.0
        elif value >= high:
            d = 1.0
        else:
            d = ((value - low) / (high - low)) ** weight

    elif goal == "minimize":
        if value <= low:
            d = 1.0
        elif value >= high:
            d = 0.0
        else:
            d = ((high - value) / (high - low)) ** weight

    elif goal == "target":
        if target is None:
            raise ValueError("target is required when goal='target'")
        if value <= low or value >= high:
            d = 0.0
        elif value == target:
            d = 1.0
        elif value < target:
            d = ((value - low) / (target - low)) ** weight
        else:
            d = ((high - value) / (high - target)) ** weight

    return d


def overall_desirability(individual_desirabilities: list[float]) -> float:
    """Compute overall desirability as geometric mean.

    Parameters
    ----------
    individual_desirabilities : list of float
        Individual desirability values (one per response).

    Returns
    -------
    float
        Geometric mean. Returns 0 if any d_i is 0.
    """
    if any(d <= 0 for d in individual_desirabilities):
        return 0.0
    return np.prod(individual_desirabilities) ** (1.0 / len(individual_desirabilities))


def optimize(
    factors: list[dict],
    responses: list[dict],
    models: dict,
    n_starts: int = 10,
) -> dict:
    """Find optimal factor settings using Derringer-Suich desirability.

    Uses multi-start optimization (random initial points within factor bounds)
    to maximize overall desirability.

    Parameters
    ----------
    factors : list of dict
        Factor definitions (name, type, low, high).
    responses : list of dict
        Response definitions (name, goal, target, low, high).
    models : dict
        Fitted models keyed by response name. Each value is the output
        from fit_linear() or fit_rsm().
    n_starts : int
        Number of random starting points for optimization.

    Returns
    -------
    dict with keys:
        optimal_settings: dict of factor name -> actual optimal value
        predicted_responses: dict of response name -> predicted value
        desirability: float (overall desirability 0-1)
        prediction_intervals: dict of response name -> [lower, upper]
        warnings: list of str — non-fatal warnings (e.g., fallback used)
    """
    factor_names = [f["name"] for f in factors]
    bounds = [(-1.0, 1.0) for _ in factors]
    warnings = []

    def negative_desirability(coded_point: np.ndarray) -> float:
        """Negative overall desirability (for minimization)."""
        point = {name: coded_point[i] for i, name in enumerate(factor_names)}

        individual_d = []
        for resp in responses:
            pred = predict_from_model(models[resp["name"]], factors, point)
            d = desirability(
                pred, goal=resp["goal"],
                low=resp["low"], high=resp["high"],
                target=resp.get("target"),
            )
            individual_d.append(d)

        od = overall_desirability(individual_d)
        return -od  # minimize negative = maximize

    # Multi-start optimization
    best_result = None
    best_fun = np.inf
    failure_count = 0

    rng = np.random.RandomState(42)
    for _ in range(n_starts):
        x0 = rng.uniform(-1, 1, len(factors))
        try:
            result = minimize(
                negative_desirability,
                x0=x0,
                method="L-BFGS-B",
                bounds=bounds,
            )
            if result.fun < best_fun:
                best_fun = result.fun
                best_result = result
        except Exception:
            failure_count += 1
            continue

    if failure_count > 0:
        warnings.append(f"{failure_count}/{n_starts} optimization starts failed "
                        "(non-fatal)")

    if best_result is None:
        warnings.append("All optimization starts failed. Returning midpoint "
                        "estimate — results are NOT reliable.")
        return {
            "optimal_settings": {f["name"]: (f["low"] + f["high"]) / 2 for f in factors},
            "predicted_responses": {r["name"]: 0.0 for r in responses},
            "desirability": 0.0,
            "prediction_intervals": {r["name"]: [0.0, 0.0] for r in responses},
            "warnings": warnings,
        }

    # Decode optimal coded point to actual values
    coded_point = best_result.x
    point = {name: coded_point[i] for i, name in enumerate(factor_names)}

    optimal_settings = {}
    for f in factors:
        coded_val = point[f["name"]]
        if f["type"] == "continuous":
            actual = f["low"] + (coded_val + 1) / 2 * (f["high"] - f["low"])
            # Clamp to bounds
            actual = max(f["low"], min(f["high"], actual))
            optimal_settings[f["name"]] = round(actual, 2)
        else:
            # Categorical: round to nearest endpoint
            optimal_settings[f["name"]] = f["low"] if coded_val < 0 else f["high"]

    # Predict responses at optimum with proper prediction intervals
    predicted_responses = {}
    prediction_intervals = {}
    for resp in responses:
        pred = predict_from_model(models[resp["name"]], factors, point)
        predicted_responses[resp["name"]] = round(float(pred), 3)

        # Use model RMSE for proper prediction interval (±2 × RMSE approximation)
        model_rmse = models[resp["name"]].get("rmse")
        if model_rmse is not None and np.isfinite(model_rmse) and model_rmse > 0:
            half_width = 2.0 * model_rmse
        else:
            # Fallback: 10% of predicted value (flagged as approximate)
            half_width = max(abs(pred) * 0.1, 0.1)
            warnings.append(
                f"Response '{resp['name']}': no RMSE available; "
                "prediction interval is approximate (±10%)."
            )
        prediction_intervals[resp["name"]] = [
            round(float(pred - half_width), 3),
            round(float(pred + half_width), 3),
        ]

    return {
        "optimal_settings": optimal_settings,
        "predicted_responses": predicted_responses,
        "desirability": round(-best_fun, 4),
        "prediction_intervals": prediction_intervals,
        "warnings": warnings,
    }
