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


def compute_xbar_r(df: pd.DataFrame, n: int | None = None) -> dict:
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

    Xbarbar = float(np.nanmean(xbar))
    Rbar = float(np.nanmean(r))

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
    }
