"""Auto-generated executive summary text for SPC reports."""

import math
import numpy as np


def build_summary(
    cap: dict,
    violations: list[dict],
    limits: dict,
    formula: str,
    parameter: str,
    date_range: tuple[str, str],
    n_batches: int,
    batch_ids: list[str] | None = None,
    dates: list[str] | None = None,
) -> dict:
    """Generate executive summary sections from SPC analysis results.

    Returns dict with keys: verdict, metrics_bullet, trend_note, ooc_summary, action_items.
    """
    ppk = cap["Ppk"]

    # --- Verdict ---
    if math.isnan(ppk):
        verdict = f"{formula} / {parameter}: no specification limits defined; capability cannot be assessed."
    elif ppk >= 1.33:
        verdict = f"{formula} / {parameter}: process is capable (Ppk = {ppk:.2f})."
    elif ppk >= 1.0:
        verdict = (f"{formula} / {parameter}: process is marginal — "
                   f"requires attention (Ppk = {ppk:.2f}).")
    else:
        verdict = (f"{formula} / {parameter}: process is NOT capable "
                   f"(Ppk = {ppk:.2f}). Corrective action recommended.")

    # --- Metrics bullet ---
    pp_str = f"{cap['Pp']:.2f}" if not math.isnan(cap["Pp"]) else "N/A"
    ppk_str = f"{ppk:.2f}" if not math.isnan(ppk) else "N/A"
    metrics_bullet = (
        f"Pp = {pp_str}, Ppk = {ppk_str}, "
        f"Mean = {cap['mean']:.3f}, σ = {cap['sigma_overall']:.3f}, "
        f"PPM = {cap['total_ppm']:.0f}, N = {n_batches} batches"
    )

    # --- Trend note ---
    trend_note = _assess_trend(limits["xbar"])

    # --- OOC summary ---
    if not violations:
        ooc_summary = "No out-of-control events detected."
        action_items = ""
    else:
        n_violations = len(violations)
        if batch_ids and dates and violations:
            viol_indices = sorted(set(v["batch_index"] for v in violations))
            valid = [i for i in viol_indices if i < len(batch_ids)]
            if valid:
                first_date = dates[valid[0]]
                last_date = dates[valid[-1]]
                first_batch = batch_ids[valid[0]]
                last_batch = batch_ids[valid[-1]]
                ooc_summary = (
                    f"{n_violations} out-of-control event(s) detected: "
                    f"{first_batch} ({first_date}) through "
                    f"{last_batch} ({last_date})."
                )
            else:
                ooc_summary = f"{n_violations} out-of-control event(s) detected."
        else:
            ooc_summary = f"{n_violations} out-of-control event(s) detected."

        action_items = "Investigate root cause of out-of-control signals and implement corrective actions."
        if ppk < 1.0:
            action_items += " Consider reviewing process parameters and specification limits."

    return {
        "verdict": verdict,
        "metrics_bullet": metrics_bullet,
        "trend_note": trend_note,
        "ooc_summary": ooc_summary,
        "action_items": action_items,
    }


def _assess_trend(xbar: np.ndarray) -> str:
    """Assess the direction of the xbar series using a simple slope check.

    Uses linear regression slope on the last min(10, len) points.
    """
    n = len(xbar)
    if n < 5:
        return "Insufficient data for trend assessment."

    window = min(10, n)
    recent = xbar[-window:]
    x = np.arange(window, dtype=float)
    y = recent.astype(float)

    x_mean = np.mean(x)
    y_mean = np.mean(y)
    slope = np.sum((x - x_mean) * (y - y_mean)) / (np.sum((x - x_mean) ** 2) + 1e-12)

    relative_slope = slope / (y_mean + 1e-12)

    if relative_slope > 0.005:
        return "Upward trend detected in recent batches."
    elif relative_slope < -0.005:
        return "Downward trend detected in recent batches."
    else:
        return "No significant trend detected."
