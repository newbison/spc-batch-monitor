from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"
DATA_FILE = DATA_DIR / "batch_data.csv"
DB_FILE = DATA_DIR / "spc.db"

# SPC constants for X-bar & R charts: A2, D3, D4 by subgroup size n
# Source: ASTM E2587 / ISO 7870-2 / AIAG SPC manual
_SPC_CONSTANTS = {
    2:  (1.880, 0.000, 3.267),
    3:  (1.023, 0.000, 2.574),
    4:  (0.729, 0.000, 2.282),
    5:  (0.577, 0.000, 2.114),
    6:  (0.483, 0.000, 2.004),
    7:  (0.419, 0.076, 1.924),
    8:  (0.373, 0.136, 1.864),
    9:  (0.337, 0.184, 1.816),
    10: (0.308, 0.223, 1.777),
    11: (0.285, 0.256, 1.744),
    12: (0.266, 0.283, 1.717),
    13: (0.249, 0.307, 1.693),
    14: (0.235, 0.328, 1.672),
    15: (0.223, 0.347, 1.653),
    16: (0.212, 0.363, 1.637),
    17: (0.203, 0.378, 1.622),
    18: (0.194, 0.391, 1.608),
    19: (0.187, 0.403, 1.597),
    20: (0.180, 0.415, 1.585),
    21: (0.173, 0.425, 1.575),
    22: (0.167, 0.434, 1.566),
    23: (0.162, 0.443, 1.557),
    24: (0.157, 0.451, 1.548),
    25: (0.153, 0.459, 1.541),
}


def get_spc_constants(n: int) -> tuple[float, float, float]:
    """Return (A2, D3, D4) for subgroup size n."""
    if n not in _SPC_CONSTANTS:
        raise ValueError(f"No SPC constants for n={n}. Supported: {sorted(_SPC_CONSTANTS.keys())}")
    return _SPC_CONSTANTS[n]
