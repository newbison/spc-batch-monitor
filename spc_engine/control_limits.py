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

    n_detected = len(rep_cols)
    if n is None:
        n = n_detected
    elif n != n_detected:
        raise ValueError(f"Expected n={n} but found {n_detected} rep columns.")

    A2, D3, D4 = get_spc_constants(n)

    reps = df[rep_cols].values.astype(float)
    xbar = np.mean(reps, axis=1)
    r = np.max(reps, axis=1) - np.min(reps, axis=1)

    Xbarbar = float(np.mean(xbar))
    Rbar = float(np.mean(r))

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
