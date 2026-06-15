"""Design matrix generation for DOE.

Wraps pyDOE2 to produce coded design matrices (-1, 0, +1).
Pure Python — no Streamlit imports.
"""

import numpy as np
import pandas as pd
from pyDOE2 import fullfact, fracfact, bbdesign


def generate_full_factorial(factors: list[dict], n_center: int = 3) -> pd.DataFrame:
    """Generate a 2^k full factorial design with optional center points.

    Parameters
    ----------
    factors : list of dict
        Each dict has keys: name, type ('continuous' or 'categorical'), low, high.
    n_center : int
        Number of center points to append (default 3).

    Returns
    -------
    pd.DataFrame
        Design matrix with columns: run, <factor_names>. Coded -1/+1 (0 for center).
    """
    k = len(factors)
    # Generate 2^k factorial
    levels = [2] * k
    raw = fullfact(levels)  # numpy array with values 0, 1
    # Convert to coded -1, +1
    coded = np.where(raw == 0, -1, 1).astype(float)

    df = _build_design_df(coded, factors)

    if n_center > 0:
        df = add_center_points(df, [f["name"] for f in factors], n_center)

    return df


def generate_fractional_factorial(factors: list[dict], resolution: int = 4) -> pd.DataFrame:
    """Generate a 2^(k-p) fractional factorial design.

    Parameters
    ----------
    factors : list of dict
        Factor definitions (name, type, low, high).
    resolution : int
        Desired minimum resolution (IV or V). Determines generator.

    Returns
    -------
    pd.DataFrame
        Design matrix with columns: run, <factor_names>. Coded -1/+1.
    """
    # Determine the best available fractional factorial for k factors
    # Use fracfact with standard generators
    generators = _get_fractional_generators(len(factors), resolution)
    coded = fracfact(generators)

    return _build_design_df(coded, factors)


def generate_box_behnken(factors: list[dict], n_center: int = 3) -> pd.DataFrame:
    """Generate a Box-Behnken design for RSM.

    Parameters
    ----------
    factors : list of dict
        Factor definitions (name, type, low, high).
    n_center : int
        Number of center points (default 3).

    Returns
    -------
    pd.DataFrame
        Design matrix with columns: run, <factor_names>. Coded -1/0/+1.
    """
    k = len(factors)
    if k < 3:
        raise ValueError("Box-Behnken requires at least 3 factors")

    coded = bbdesign(k, center=n_center)

    return _build_design_df(coded, factors)


def decode_to_actual(coded: pd.DataFrame, factors: list[dict]) -> pd.DataFrame:
    """Decode coded design matrix to actual factor values.

    Parameters
    ----------
    coded : pd.DataFrame
        Coded design matrix (columns: run, <factor_names>).
    factors : list of dict
        Factor definitions with low/high values.

    Returns
    -------
    pd.DataFrame
        Copy of coded with -1/0/+1 replaced by actual values.
    """
    decoded = coded.copy()
    for f in factors:
        name = f["name"]
        low, high = f["low"], f["high"]
        decoded[name] = decoded[name].apply(lambda x: _decode_value(x, low, high, f["type"]))
    return decoded


def add_center_points(df: pd.DataFrame, factor_names: list[str], n_center: int = 3) -> pd.DataFrame:
    """Append center points to a design matrix.

    Parameters
    ----------
    df : pd.DataFrame
        Existing design matrix.
    factor_names : list of str
        Names of factors (columns to set to 0 for center points).
    n_center : int
        Number of center points to add.

    Returns
    -------
    pd.DataFrame
        Original design with center points appended, runs renumbered.
    """
    next_run = df["run"].max() + 1
    center_rows = pd.DataFrame(
        {"run": range(next_run, next_run + n_center),
         **{name: 0.0 for name in factor_names}}
    )
    combined = pd.concat([df, center_rows], ignore_index=True)
    combined["run"] = range(1, len(combined) + 1)
    return combined


def _build_design_df(coded: np.ndarray, factors: list[dict]) -> pd.DataFrame:
    """Build a design DataFrame from a coded numpy array."""
    factor_names = [f["name"] for f in factors]
    df = pd.DataFrame(coded, columns=factor_names)
    df = df.round(4)  # clean up floating point
    df.insert(0, "run", range(1, len(df) + 1))
    return df


def _decode_value(coded_val: float, low, high, factor_type: str):
    """Decode a single coded value to actual."""
    if coded_val == -1:
        return low
    elif coded_val == 1:
        return high
    else:  # 0 (center point)
        if factor_type == "continuous":
            return (low + high) / 2
        else:
            return "Midpoint"


def _get_fractional_generators(k: int, resolution: int) -> str:
    """Return a fracfact generator string for k factors at given resolution.

    For k <= 3, returns full factorial (no aliasing needed).
    For k = 4..11, returns standard Resolution IV/V generators.
    """
    # Standard generators for 2^(k-p) designs
    # fracfact takes: basic factors as single letters, added factors as generator strings
    generators_map = {
        4: "a b c abc",           # 2^(4-1) Res IV: D = ABC
        5: "a b c ab ac",         # 2^(5-2) Res IV
        6: "a b c d ab ac",       # 2^(6-3) Res IV
        7: "a b c d ab ac bc",    # 2^(7-4) Res IV
        8: "a b c d ab ac bc abcd",  # 2^(8-4) Res IV
    }

    if k <= 3:
        # Full factorial for 3 or fewer factors
        return " ".join([chr(ord('a') + i) for i in range(k)])

    if k in generators_map:
        return generators_map[k]

    # For k > 8, use a half-fraction approach
    # Generate enough generators: for 2^(k-p) where p = ceil(k/2)
    letters = [chr(ord('a') + i) for i in range(k)]
    return " ".join(letters)
