"""Generate dummy batch data for SPC development."""
import numpy as np
import pandas as pd
from pathlib import Path

np.random.seed(42)

# Each parameter can have its own replicate count
PARAM_CONFIG = {
    "viscosity":          {"reps": 5,  "target": 1.05, "sigma_between": 0.15, "sigma_within": 0.05, "lsl": 0.6, "usl": 1.5},
    "density":            {"reps": 15, "target": 1500, "sigma_between": 200,  "sigma_within": 50,   "lsl": 1000.0, "usl": float("nan")},
    "hardness":           {"reps": 8,  "target": 30,   "sigma_between": 8,    "sigma_within": 3,    "lsl": 10.0, "usl": 50.0},
    "elasticity":         {"reps": 10, "target": 12.5, "sigma_between": 3,    "sigma_within": 1,    "lsl": 5.0, "usl": 20.0},
}

FORMULAS = {
    "Grade A": {
        "viscosity":          {"reps": 5,  "target": 1.05, "sigma_between": 0.15, "sigma_within": 0.05, "lsl": 0.6, "usl": 1.5},
        "density":            {"reps": 15, "target": 1500, "sigma_between": 200,  "sigma_within": 50,   "lsl": 1000.0, "usl": float("nan")},
        "hardness":           {"reps": 8,  "target": 30,   "sigma_between": 8,    "sigma_within": 3,    "lsl": 10.0, "usl": 50.0},
        "elasticity":         {"reps": 10, "target": 12.5, "sigma_between": 3,    "sigma_within": 1,    "lsl": 5.0, "usl": 20.0},
    },
    "Grade B": {
        "viscosity":          {"reps": 5,  "target": 1.20, "sigma_between": 0.18, "sigma_within": 0.06, "lsl": 0.6, "usl": 1.5},
        "density":            {"reps": 15, "target": 1800, "sigma_between": 250,  "sigma_within": 60,   "lsl": 1000.0, "usl": float("nan")},
        "hardness":           {"reps": 8,  "target": 35,   "sigma_between": 9,    "sigma_within": 3.5,  "lsl": 10.0, "usl": 50.0},
        "elasticity":         {"reps": 10, "target": 15,   "sigma_between": 3.5,  "sigma_within": 1.2,  "lsl": 5.0, "usl": 20.0},
    },
}

N_BATCHES = 30
OUTPUT = Path(__file__).parent / "batch_data.csv"


def _rounder_for_param(param: str) -> int:
    rounding = {
        "viscosity": 3,
        "density": 0,
        "hardness": 1,
        "elasticity": 2,
    }
    return rounding.get(param, 2)


def generate_batch(batch_id: str, date: str, formula: str) -> list[dict]:
    rows = []
    cfg = FORMULAS[formula]
    max_reps = max(p["reps"] for p in cfg.values())
    for param, p in cfg.items():
        batch_mean = np.random.normal(p["target"], p["sigma_between"])
        decimals = _rounder_for_param(param)
        # Generate actual number of replicates for this parameter
        actual_reps = p["reps"]
        raw = [np.random.normal(batch_mean, p["sigma_within"]) for _ in range(actual_reps)]
        reps = [round(v, decimals) for v in raw]
        # Pad with NaN up to max_reps so all rows have the same columns
        padded = reps + [float("nan")] * (max_reps - actual_reps)
        row = {
            "date": date,
            "batch_id": batch_id,
            "formula": formula,
            "parameter": param,
            "lower_spec": p["lsl"],
            "upper_spec": p["usl"],
        }
        for i, val in enumerate(padded, start=1):
            row[f"rep{i}"] = val
        rows.append(row)
    return rows


def main():
    start = pd.Timestamp("2025-01-02")
    formulas = list(FORMULAS.keys())
    all_rows = []
    for i in range(N_BATCHES):
        batch_id = f"BATCH-{i+1:03d}"
        date = (start + pd.Timedelta(days=i)).strftime("%Y-%m-%d")
        formula = formulas[i // 15]
        all_rows.extend(generate_batch(batch_id, date, formula))

    df = pd.DataFrame(all_rows)

    # Sort columns: metadata, specs, then reps
    meta_cols = ["date", "batch_id", "formula", "parameter", "lower_spec", "upper_spec"]
    rep_cols = sorted([c for c in df.columns if c.startswith("rep")], key=lambda x: int(x[3:]))
    df = df[meta_cols + rep_cols]

    df.to_csv(OUTPUT, index=False)
    print(f"Wrote {len(df)} rows to {OUTPUT}")
    print(f"Columns: {list(df.columns)}")
    print(f"Formulas: {df['formula'].unique().tolist()}")
    print(f"Parameters: {df['parameter'].unique().tolist()}")
    print(f"Rep columns: {len(rep_cols)} (max across parameters)")
    print(f"\nPer-parameter rep counts:")
    for param in df["parameter"].unique():
        sub = df[df["parameter"] == param]
        reps = sub[[c for c in rep_cols]].values.astype(float)
        n_per_row = np.sum(~np.isnan(reps), axis=1)
        print(f"  {param:20s} n={int(n_per_row[0])}")
    print(f"\nFirst 2 rows:")
    print(df[meta_cols[:5] + ["rep1", "rep2", "rep3"]].head(2).to_string(index=False))


if __name__ == "__main__":
    main()
