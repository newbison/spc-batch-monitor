import pytest
import pandas as pd
import math
import tempfile
from pathlib import Path
from data_access.sqlite_repository import SqliteRepository


def test_repository_init_creates_db():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        repo = SqliteRepository(db_path, auto_migrate=False)
        assert db_path.exists()
        df = repo.load_all()
        assert isinstance(df, pd.DataFrame)


def test_append_and_load():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        repo = SqliteRepository(db_path, auto_migrate=False)

        repo.append_batch("B-001", "2025-06-01", "Grade A", {
            "viscosity": {"reps": [1.05, 1.10, 1.02], "lower_spec": 0.6, "upper_spec": 1.5},
            "density": {"reps": [1500, 1520, 1490], "lower_spec": 1000.0, "upper_spec": float("nan")},
        })

        df = repo.load_all()
        assert len(df) == 2  # 2 parameters
        assert df["batch_id"].iloc[0] == "B-001"


def test_get_for_parameter():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        repo = SqliteRepository(db_path, auto_migrate=False)

        repo.append_batch("B-001", "2025-06-01", "Grade A", {
            "viscosity": {"reps": [1.05, 1.10, 1.02], "lower_spec": 0.6, "upper_spec": 1.5},
            "density": {"reps": [1500, 1520, 1490], "lower_spec": 1000.0, "upper_spec": float("nan")},
        })

        adh = repo.get_for_parameter("viscosity")
        assert len(adh) == 1
        assert "rep1" in adh.columns


def test_get_formulas():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        repo = SqliteRepository(db_path, auto_migrate=False)

        repo.append_batch("B-001", "2025-06-01", "Grade A", {
            "viscosity": {"reps": [1.0], "lower_spec": float("nan"), "upper_spec": float("nan")},
        })
        repo.append_batch("B-002", "2025-06-02", "Grade B", {
            "viscosity": {"reps": [1.0], "lower_spec": float("nan"), "upper_spec": float("nan")},
        })

        formulas = repo.get_formulas()
        assert sorted(formulas) == ["Grade A", "Grade B"]


def test_get_parameters():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        repo = SqliteRepository(db_path, auto_migrate=False)

        repo.append_batch("B-001", "2025-06-01", "Grade A", {
            "viscosity": {"reps": [1.0], "lower_spec": float("nan"), "upper_spec": float("nan")},
            "density": {"reps": [1500], "lower_spec": float("nan"), "upper_spec": float("nan")},
        })

        params = repo.get_parameters()
        assert sorted(params) == ["density", "viscosity"]


def test_append_batch_dedup():
    """Same batch_id+formula+parameter should not create duplicates."""
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        repo = SqliteRepository(db_path, auto_migrate=False)

        repo.append_batch("B-001", "2025-06-01", "Grade A", {
            "viscosity": {"reps": [1.05, 1.10, 1.02], "lower_spec": 0.6, "upper_spec": 1.5},
        })

        # Same batch+formula+param — should be ignored
        repo.append_batch("B-001", "2025-06-01", "Grade A", {
            "viscosity": {"reps": [9.99, 9.99, 9.99], "lower_spec": 0.6, "upper_spec": 1.5},
        })

        df = repo.load_all()
        match = df[(df["batch_id"] == "B-001") & (df["parameter"] == "viscosity")]
        assert len(match) == 1  # not 2
        # Original values preserved
        assert abs(float(match["rep1"].iloc[0]) - 1.05) < 0.01


def test_upload_csv_dedup():
    """upload_csv should skip existing rows and count correctly."""
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        repo = SqliteRepository(db_path, auto_migrate=False)

        repo.append_batch("B-001", "2025-06-01", "Grade A", {
            "viscosity": {"reps": [1.0], "lower_spec": float("nan"), "upper_spec": float("nan")},
        })

        new_df = pd.DataFrame({
            "date": ["2025-06-01", "2025-06-02"],
            "batch_id": ["B-001", "B-002"],
            "formula": ["Grade A", "Grade A"],
            "parameter": ["viscosity", "viscosity"],
            "rep1": [9.99, 1.1],
            "lower_spec": [float("nan"), float("nan")],
            "upper_spec": [float("nan"), float("nan")],
        })

        result = repo.upload_csv(new_df)
        assert result["skipped"] == 1  # B-001 already exists
        assert result["inserted"] >= 1  # B-002 is new
        assert len(result["errors"]) == 0

        df = repo.load_all()
        assert len(df) == 2  # original 1 + new 1


def test_upload_csv_rejects_invalid():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        repo = SqliteRepository(db_path, auto_migrate=False)

        bad_df = pd.DataFrame({
            "date": ["2025-06-01"],
            "batch_id": ["B-001"],
            "formula": ["Grade A"],
            "parameter": ["viscosity"],
            "rep1": [-1.0],  # negative — reject
            "lower_spec": [float("nan")],
            "upper_spec": [float("nan")],
        })

        result = repo.upload_csv(bad_df)
        assert len(result["errors"]) > 0
        assert result["inserted"] == 0


def test_auto_migration_from_csv():
    """SqliteRepository should import existing CSV on first run."""
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        csv_path = Path(tmpdir) / "test_data.csv"
        df_in = pd.DataFrame({
            "date": ["2025-06-01", "2025-06-01"],
            "batch_id": ["B-001", "B-001"],
            "formula": ["Grade A", "Grade A"],
            "parameter": ["viscosity", "density"],
            "rep1": [1.05, 1500.0],
            "rep2": [1.10, 1520.0],
            "rep3": [1.02, 1490.0],
            "lower_spec": [0.6, 1000.0],
            "upper_spec": [1.5, float("nan")],
        })
        df_in.to_csv(csv_path, index=False)

        import config
        original_data_file = config.DATA_FILE
        config.DATA_FILE = csv_path

        try:
            db_path = Path(tmpdir) / "test.db"
            repo = SqliteRepository(db_path)  # auto_migrate defaults to True
            df = repo.load_all()
            assert len(df) == 2
            assert set(df["parameter"].tolist()) == {"viscosity", "density"}
        finally:
            config.DATA_FILE = original_data_file


def test_auto_migration_skips_if_db_has_data():
    """If DB already has data, don't migrate CSV again."""
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        csv_path = Path(tmpdir) / "test_data.csv"
        df_in = pd.DataFrame({
            "date": ["2025-06-01"],
            "batch_id": ["B-001"],
            "formula": ["Grade A"],
            "parameter": ["viscosity"],
            "rep1": [1.05],
            "lower_spec": [float("nan")],
            "upper_spec": [float("nan")],
        })
        df_in.to_csv(csv_path, index=False)

        import config
        original_data_file = config.DATA_FILE
        config.DATA_FILE = csv_path

        try:
            db_path = Path(tmpdir) / "test.db"
            repo = SqliteRepository(db_path)
            assert len(repo.load_all()) == 1

            repo2 = SqliteRepository(db_path)
            assert len(repo2.load_all()) == 1
        finally:
            config.DATA_FILE = original_data_file


def test_get_batch():
    """get_batch should return all params for a batch_id."""
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        repo = SqliteRepository(db_path, auto_migrate=False)

        repo.append_batch("B-001", "2025-06-01", "Grade A", {
            "viscosity": {"reps": [1.05, 1.10, 1.02], "lower_spec": 0.6, "upper_spec": 1.5},
            "density": {"reps": [1500, 1520, 1490], "lower_spec": 1000.0, "upper_spec": float("nan")},
        })

        batch_df = repo.get_batch("B-001")
        assert len(batch_df) == 2  # 2 parameters
        assert set(batch_df["parameter"].tolist()) == {"viscosity", "density"}


def test_get_batch_not_found():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        repo = SqliteRepository(db_path, auto_migrate=False)
        batch_df = repo.get_batch("NONEXISTENT")
        assert len(batch_df) == 0


def test_update_batch():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        repo = SqliteRepository(db_path, auto_migrate=False)

        repo.append_batch("B-001", "2025-06-01", "Grade A", {
            "viscosity": {"reps": [1.05, 1.10, 1.02], "lower_spec": 0.6, "upper_spec": 1.5},
        })

        # Update viscosity values
        ok = repo.update_batch("B-001", "Grade A", "viscosity", {
            "reps": [2.0, 2.1, 2.2], "lower_spec": 0.6, "upper_spec": 1.5,
        })
        assert ok is True

        df = repo.get_for_parameter("viscosity")
        assert abs(float(df["rep1"].iloc[0]) - 2.0) < 0.01


def test_update_batch_not_found():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        repo = SqliteRepository(db_path, auto_migrate=False)
        ok = repo.update_batch("NOPE", "Grade A", "viscosity", {
            "reps": [1.0], "lower_spec": float("nan"), "upper_spec": float("nan"),
        })
        assert ok is False


def test_update_batch_rejects_invalid():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        repo = SqliteRepository(db_path, auto_migrate=False)

        repo.append_batch("B-001", "2025-06-01", "Grade A", {
            "viscosity": {"reps": [1.05, 1.10, 1.02], "lower_spec": 0.6, "upper_spec": 1.5},
        })

        with pytest.raises(ValueError, match="Validation failed"):
            repo.update_batch("B-001", "Grade A", "viscosity", {
                "reps": [-1.0], "lower_spec": 0.6, "upper_spec": 1.5,
            })


def test_delete_batch():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        repo = SqliteRepository(db_path, auto_migrate=False)

        repo.append_batch("B-001", "2025-06-01", "Grade A", {
            "viscosity": {"reps": [1.0], "lower_spec": float("nan"), "upper_spec": float("nan")},
            "density": {"reps": [1500], "lower_spec": float("nan"), "upper_spec": float("nan")},
        })

        deleted = repo.delete_batch("B-001", "Grade A", "density")
        assert deleted is True

        df = repo.load_all()
        assert len(df) == 1  # only viscosity left


def test_delete_all_for_batch():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        repo = SqliteRepository(db_path, auto_migrate=False)

        repo.append_batch("B-001", "2025-06-01", "Grade A", {
            "viscosity": {"reps": [1.0], "lower_spec": float("nan"), "upper_spec": float("nan")},
            "density": {"reps": [1500], "lower_spec": float("nan"), "upper_spec": float("nan")},
        })

        count = repo.delete_all_for_batch("B-001")
        assert count == 2

        df = repo.load_all()
        assert len(df) == 0
