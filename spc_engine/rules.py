import numpy as np


def check_rules(xbar: np.ndarray, ucl: float, lcl: float, cl: float) -> list[dict]:
    n = len(xbar)
    sigma = (ucl - cl) / 3.0
    violations = []

    for i in range(n):
        # Rule 1: single point beyond 3-sigma
        if xbar[i] > ucl or xbar[i] < lcl:
            violations.append({
                "batch_index": i, "rule": 1,
                "description": f"Point beyond 3σ (x̄={xbar[i]:.3f})",
            })

    for i in range(n - 2):
        # Rule 2: 2 of 3 consecutive beyond 2-sigma (same side)
        window = xbar[i:i + 3]
        above_2sigma = np.sum(window > cl + 2 * sigma) >= 2
        below_2sigma = np.sum(window < cl - 2 * sigma) >= 2
        if above_2sigma or below_2sigma:
            violations.append({
                "batch_index": i + 2, "rule": 2,
                "description": "2 of 3 points beyond 2σ",
            })

    for i in range(n - 7):
        # Rule 4: 7 consecutive on same side of centerline
        window = xbar[i:i + 8]
        if np.all(window > cl) or np.all(window < cl):
            violations.append({
                "batch_index": i + 7, "rule": 4,
                "description": "8 consecutive points on same side of centerline",
            })

    for i in range(n - 5):
        # Trending: 6 consecutive increasing or decreasing
        window = xbar[i:i + 6]
        diffs = np.diff(window)
        if np.all(diffs > 0):
            violations.append({
                "batch_index": i + 5, "rule": 5,
                "description": "6 consecutive points trending up",
            })
        if np.all(diffs < 0):
            violations.append({
                "batch_index": i + 5, "rule": 5,
                "description": "6 consecutive points trending down",
            })

    return _dedup_violations(violations)


def _dedup_violations(violations: list[dict]) -> list[dict]:
    """Merge overlapping same-rule violations reported at nearby indices.

    Rule 2 (and similar sliding-window rules) can flag the same underlying
    shift multiple times as the window advances by one.  We collapse any
    consecutive same-rule violations whose batch indices are within a
    tolerance of 2 into a single violation (keeping the earliest).
    """
    if not violations:
        return violations

    deduped = []
    prev = None
    TOLERANCE = 2

    for v in violations:
        if (
            prev is not None
            and v["rule"] == prev["rule"]
            and abs(v["batch_index"] - prev["batch_index"]) <= TOLERANCE
        ):
            # Overlapping — skip this duplicate
            continue
        deduped.append(v)
        prev = v

    return deduped
