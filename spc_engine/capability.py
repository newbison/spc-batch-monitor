import numpy as np
import math
from scipy import stats


def compute_capability(xbar: np.ndarray, lsl: float, usl: float) -> dict:
    mean = float(np.mean(xbar))
    sigma_overall = float(np.std(xbar, ddof=1))

    has_lsl = not math.isnan(lsl)
    has_usl = not math.isnan(usl)

    if sigma_overall == 0:
        return {
            "sigma_overall": 0.0,
            "Pp": float("inf") if (has_lsl and has_usl) else float("nan"),
            "Ppk": float("inf"),
            "mean": mean, "ppm_usl": 0.0, "ppm_lsl": 0.0, "total_ppm": 0.0,
        }

    # Pp: needs both limits
    if has_lsl and has_usl:
        Pp = (usl - lsl) / (6 * sigma_overall)
    else:
        Pp = float("nan")

    # Ppk: uses whichever limit(s) are available
    pk_candidates = []
    if has_usl:
        pk_candidates.append((usl - mean) / (3 * sigma_overall))
    if has_lsl:
        pk_candidates.append((mean - lsl) / (3 * sigma_overall))
    Ppk = min(pk_candidates) if pk_candidates else float("nan")

    # PPM
    ppm_usl = (1 - stats.norm.cdf(usl, loc=mean, scale=sigma_overall)) * 1_000_000 if has_usl else 0.0
    ppm_lsl = stats.norm.cdf(lsl, loc=mean, scale=sigma_overall) * 1_000_000 if has_lsl else 0.0

    return {
        "sigma_overall": sigma_overall,
        "Pp": Pp,
        "Ppk": Ppk,
        "mean": mean,
        "ppm_usl": ppm_usl,
        "ppm_lsl": ppm_lsl,
        "total_ppm": ppm_usl + ppm_lsl,
    }
