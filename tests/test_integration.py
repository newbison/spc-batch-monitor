import pandas as pd
import numpy as np
from pathlib import Path
import tempfile

from data_access.sqlite_repository import SqliteRepository
from spc_engine.control_limits import compute_xbar_r
from spc_engine.rules import check_rules
from spc_engine.capability import compute_capability


def test_full_pipeline_n10():
    """Full SPC pipeline with n=10 replicates (coating process)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        repo = SqliteRepository(db_path, auto_migrate=False)

        np.random.seed(99)
        for i in range(20):
            date = f"2025-{(i // 28) + 1:02d}-{(i % 28) + 1:02d}"
            measurements = {}
            for param, (target, lsl, usl, sigma_between, sigma_within) in [
                ("adhesion", (8.5, 5.0, 12.0, 1.0, 0.3)),
                ("cohesion", (5.0, 2.0, 8.0, 0.6, 0.2)),
            ]:
                batch_mean = np.random.normal(target, sigma_between)
                reps = [round(np.random.normal(batch_mean, sigma_within), 2)
                        for _ in range(10)]
                measurements[param] = {"reps": reps, "lower_spec": lsl, "upper_spec": usl}
            repo.append_batch(f"B-{i:03d}", date, "Coating A", measurements)

        df = repo.load_all()
        assert len(df) == 40  # 20 batches × 2 params

        adh_df = repo.get_for_parameter("adhesion")
        limits = compute_xbar_r(adh_df)
        assert len(limits["xbar"]) == 20
        assert limits["UCLx"] > limits["CLx"] > limits["LCLx"]

        violations = check_rules(limits["xbar"], limits["UCLx"], limits["LCLx"], limits["CLx"])
        assert isinstance(violations, list)

        cap = compute_capability(limits["xbar"], lsl=5.0, usl=12.0)
        assert cap["Pp"] > 0
        assert cap["Ppk"] > 0


def test_sqlite_full_pipeline():
    """Full SPC pipeline with SqliteRepository."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        repo = SqliteRepository(db_path, auto_migrate=False)

        np.random.seed(99)
        for i in range(10):
            date_str = f"2025-{(i // 28) + 1:02d}-{(i % 28) + 1:02d}"
            measurements = {}
            for param, (target, lsl, usl, sigma_between, sigma_within) in [
                ("adhesion", (1.05, 0.6, 1.5, 0.15, 0.05)),
            ]:
                batch_mean = np.random.normal(target, sigma_between)
                reps = [round(np.random.normal(batch_mean, sigma_within), 3)
                        for _ in range(5)]
                measurements[param] = {"reps": reps, "lower_spec": lsl, "upper_spec": usl}
            repo.append_batch(f"B-{i:03d}", date_str, "Coating A", measurements)

        df = repo.load_all()
        assert len(df) == 10  # 10 batches x 1 param

        # SPC engine should work with the loaded data
        adh_df = repo.get_for_parameter("adhesion")
        limits = compute_xbar_r(adh_df, n=5)
        assert len(limits["xbar"]) == 10
        assert limits["UCLx"] > limits["CLx"] > limits["LCLx"]

        violations = check_rules(limits["xbar"], limits["UCLx"], limits["LCLx"], limits["CLx"])
        assert isinstance(violations, list)

        cap = compute_capability(limits["xbar"], lsl=0.6, usl=1.5)
        assert cap["Ppk"] > 0

        # Dedup test: append same batch again
        repo.append_batch("B-001", date_str, "Coating A", measurements)
        df2 = repo.load_all()
        assert len(df2) == 10  # still 10, no duplicate
