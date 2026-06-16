"""Self-contained factorial design generators.

Replaces pyDOE2 to avoid the ``import imp`` issue on Python ≥ 3.12.
Provides the three functions we use: fullfact, fracfact, bbdesign.
"""

import itertools
import numpy as np


def fullfact(levels: list[int]) -> np.ndarray:
    """Full factorial design matrix.

    Parameters
    ----------
    levels : list of int
        Number of levels for each factor, e.g. ``[2, 2, 2]`` for a 2^3 design.

    Returns
    -------
    np.ndarray
        Design matrix of shape ``(product(levels), len(levels))`` with values
        0, 1, …, level−1 for each factor.
    """
    return np.array(list(itertools.product(*[range(l) for l in levels])))


def fracfact(generators: str) -> np.ndarray:
    """Fractional factorial design from a generator string.

    Parses the pyDOE2-compatible generator format: single-letter tokens are
    base factors (enumerated fully at ±1); multi-letter tokens define
    additional factors as products of the base letters they contain.

    Examples
    --------
    ``"a b c abc"`` → 3 base factors (a, b, c) + 1 generated (abc)
    → 2^3 = 8 runs × 4 factors.

    ``"a b c ab ac"`` → 3 base + 2 generated → 8 runs × 5 factors.

    Parameters
    ----------
    generators : str
        Space-separated tokens.  Single letters = base factors;
        multi-letter tokens = generated factors as products of base letters.

    Returns
    -------
    np.ndarray
        Coded design matrix of shape ``(2^n_base, n_factors)`` with values
        −1 / +1.
    """
    tokens = generators.strip().split()
    if not tokens:
        raise ValueError("generators string must not be empty")

    # Map each single-letter token to its index in the factor list
    # Multi-letter tokens define the relations for generated factors
    base_count = 0
    gen_exprs: list[list[int]] = []
    factor_letters: list[str] = []

    for token in tokens:
        factor_letters.append(token)
        if len(token) == 1:
            base_count += 1
        else:
            # "abc" → this factor = product of a * b * c
            gen_exprs.append([ord(c) - ord('a') for c in token])

    if base_count == 0:
        raise ValueError(
            f"generators string '{generators}' has no single-letter "
            "(base) factors"
        )

    n_runs = 2 ** base_count
    n_factors = len(tokens)

    # Enumerate ±1 combinations for the base factors only
    base_design = np.array(
        list(itertools.product([-1, 1], repeat=base_count)),
        dtype=float,
    )

    # Allocate full matrix
    design = np.ones((n_runs, n_factors), dtype=float)

    # Fill columns: base factors first (in order they appear), then generated
    col = 0
    for token in tokens:
        if len(token) == 1:
            base_idx = ord(token) - ord('a')
            # Find which base column this corresponds to
            # Base factors appear in alphabetical order in the base design
            design[:, col] = base_design[:, base_idx % base_count]
        else:
            # Compute product of constituent base factors
            design[:, col] = np.ones(n_runs)
            for letter_idx in [ord(c) - ord('a') for c in token]:
                if letter_idx < base_count:
                    design[:, col] *= base_design[:, letter_idx]
        col += 1

    return design


def bbdesign(k: int, center: int = 1) -> np.ndarray:
    """Box-Behnken design for *k* continuous factors.

    Generates the standard Box-Behnken matrix of edge-midpoint runs plus
    *center* centre points.  Each factor takes values −1, 0, +1.

    Parameters
    ----------
    k : int
        Number of factors (≥ 3).
    center : int
        Number of centre-point replicates to append (default 1).

    Returns
    -------
    np.ndarray
        Coded design matrix of shape ``(n_runs, k)``.
    """
    if k < 3:
        raise ValueError("Box-Behnken requires at least 3 factors")

    # Generate all 2-factor combinations
    factor_pairs = list(itertools.combinations(range(k), 2))

    # Each pair contributes 4 runs: the 2^2 factorial on those two factors
    # while the other k−2 factors are held at 0
    n_edge = len(factor_pairs) * 4
    design = np.zeros((n_edge, k), dtype=float)

    row = 0
    for i, j in factor_pairs:
        # 2^2 full factorial on factors i and j
        for vi, vj in itertools.product([-1, 1], repeat=2):
            design[row, i] = vi
            design[row, j] = vj
            row += 1

    # Append centre points
    if center > 0:
        centre_block = np.zeros((center, k), dtype=float)
        design = np.vstack([design, centre_block])

    return design
