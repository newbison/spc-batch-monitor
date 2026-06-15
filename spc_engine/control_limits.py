import numpy as np
import pandas as pd
import re

from config import get_spc_constants


def _rep_columns(df: pd.DataFrame) -> list[str]:
    """Return sorted list of column names matching rep1, rep2, ..., repN."""
    return sorted(
        [c for c in df.columns if re.match(r"^rep\d+$", c)],
        key=lambda x: int(x[3:]),
    )


def subgroup_size(df: pd.DataFrame) -> int:
    """Detect subgroup size n from rep columns in the DataFrame."""
    return len(_rep_columns(df))


def compute_xbar_r(
    df: pd.DataFrame,
    n: int | None = None,
    baseline_size: int = 20,
) -> dict:
    """Compute X-bar & R statistics and control limits.

    Per-row ``xbar`` and ``r`` are computed for **every** row so charts can
    plot all batches. The grand statistics (``Xbarbar``, ``Rbar``) and the
    derived control limits are frozen to the first ``baseline_size`` rows —
    i.e. the earliest batches, assuming the caller passes the DataFrame
    sorted by date. This is standard SPC practice: limits are established
    from an in-control baseline rather than allowed to drift with the full
    series, so sustained shifts actually surface as Rule 1 violations.

    If the DataFrame has fewer than ``baseline_size`` rows, all rows are
    used (behavior is unchanged from the pre-baseline implementation).

    Parameters
    ----------
    df : DataFrame
        Measurement rows with ``rep1..repN`` columns. Expected to be sorted
        by date so "first N rows" means "earliest N batches".
    n : int, optional
        Override subgroup size for the control-limit constants. If omitted,
        the average non-NaN rep count is used.
    baseline_size : int, default 20
        Number of leading rows used to compute ``Xbarbar``/``Rbar``/limits.
        AIAG/ASTM guidance is ≥20 subgroups for a stable limit estimate.

    Returns
    -------
    dict
        ``xbar``, ``r`` (all rows); ``Xbarbar``, ``Rbar``, ``UCLx``,
        ``LCLx``, ``CLx``, ``UCLr``, ``LCLr``, ``CLr`` (from baseline);
        ``baseline_n`` (int — rows actually used for limits).
    """
    rep_cols = _rep_columns(df)
    if not rep_cols:
        raise ValueError("No rep columns found (rep1, rep2, ...).")

    reps = df[rep_cols].values.astype(float)

    # Detect per-row n from non-NaN values, or use all columns if n is fixed
    if n is None:
        # Use average n for control limit constants when n varies
        n_per_row = np.sum(~np.isnan(reps), axis=1)
        n_avg = int(round(float(np.mean(n_per_row))))
        # Fall back to detected column count if average is unreasonable
        n_used = n_avg if n_avg > 0 else len(rep_cols)
    else:
        n_used = n

    A2, D3, D4 = get_spc_constants(n_used)

    xbar = np.nanmean(reps, axis=1)
    r = np.nanmax(reps, axis=1) - np.nanmin(reps, axis=1)

    # Freeze grand statistics to the baseline window (earliest batches).
    # Falls back to all rows when the dataset is smaller than the window.
    baseline_n = min(baseline_size, len(xbar))
    Xbarbar = float(np.nanmean(xbar[:baseline_n]))
    Rbar = float(np.nanmean(r[:baseline_n]))

    return {
        "xbar": xbar,
        "r": r,
        "Xbarbar": Xbarbar,
        "Rbar": Rbar,
        "UCLx": Xbarbar + A2 * Rbar,
        "LCLx": Xbarbar - A2 * Rbar,
        "CLx": Xbarbar,
        "UCLr": D4 * Rbar,
        "LCLr": D3 * Rbar,
        "CLr": Rbar,
        "baseline_n": baseline_n,
    }
