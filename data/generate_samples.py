"""Generate dummy coating batch data for SPC development."""
import numpy as np
import pandas as pd
from pathlib import Path

np.random.seed(42)

N_REPS = 10
FORMULAS = {
    "Coating A": {
        "adhesion":     {"target": 8.5, "sigma_between": 1.0, "sigma_within": 0.3, "lsl": 5.0, "usl": 12.0},
        "cohesion":     {"target": 5.0, "sigma_between": 0.6, "sigma_within": 0.2, "lsl": 2.0, "usl": 8.0},
        "tack":         {"target": 6.0, "sigma_between": 0.8, "sigma_within": 0.25, "lsl": 3.0, "usl": 9.0},
        "liner_release": {"target": 0.4, "sigma_between": 0.08, "sigma_within": 0.02, "lsl": 0.1, "usl": 0.8},
    },
    "Coating B": {
        "adhesion":     {"target": 10.0, "sigma_between": 1.2, "sigma_within": 0.35, "lsl": 6.0, "usl": 14.0},
        "cohesion":     {"target": 6.0, "sigma_between": 0.7, "sigma_within": 0.22, "lsl": 3.0, "usl": 9.0},
        "tack":         {"target": 7.5, "sigma_between": 0.9, "sigma_within": 0.28, "lsl": 4.0, "usl": 11.0},
        "liner_release": {"target": 0.5, "sigma_between": 0.10, "sigma_within": 0.03, "lsl": 0.15, "usl": 1.0},
    },
}

N_BATCHES = 30
OUTPUT = Path(__file__).parent / "coating_batches.csv"


def generate_batch(batch_id: str, date: str, formula: str) -> list[dict]:
    rows = []
    cfg = FORMULAS[formula]
    for param, p in cfg.items():
        batch_mean = np.random.normal(p["target"], p["sigma_between"])
        reps = [
            round(np.random.normal(batch_mean, p["sigma_within"]),
                  3 if param == "liner_release" else 2)
            for _ in range(N_REPS)
        ]
        row = {
            "date": date,
            "batch_id": batch_id,
            "formula": formula,
            "parameter": param,
            "lower_spec": p["lsl"],
            "upper_spec": p["usl"],
        }
        for i, val in enumerate(reps, start=1):
            row[f"rep{i}"] = val
        rows.append(row)
    return rows


def main():
    start = pd.Timestamp("2025-01-02")
    formulas = list(FORMULAS.keys())
    all_rows = []
    for i in range(N_BATCHES):
        batch_id = f"COAT-{i+1:03d}"
        date = (start + pd.Timedelta(days=i)).strftime("%Y-%m-%d")
        formula = formulas[i // 15]
        all_rows.extend(generate_batch(batch_id, date, formula))

    df = pd.DataFrame(all_rows)
    df.to_csv(OUTPUT, index=False)
    print(f"Wrote {len(df)} rows ({N_BATCHES} batches × {len(FORMULAS)} formulas × {len(FORMULAS['Coating A'])} params) to {OUTPUT}")
    print(f"N replicates per measurement: {N_REPS}")
    print(f"Formulas: {df['formula'].unique().tolist()}")
    print(f"Parameters: {df['parameter'].unique().tolist()}")
    print(df.head(5))


if __name__ == "__main__":
    main()
