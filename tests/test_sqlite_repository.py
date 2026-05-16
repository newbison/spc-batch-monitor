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

        repo.append_batch("B-001", "2025-06-01", "Coating A", {
            "adhesion": {"reps": [1.05, 1.10, 1.02], "lower_spec": 0.6, "upper_spec": 1.5},
            "cohesion": {"reps": [1500, 1520, 1490], "lower_spec": 1000.0, "upper_spec": float("nan")},
        })

        df = repo.load_all()
        assert len(df) == 2  # 2 parameters
        assert df["batch_id"].iloc[0] == "B-001"


def test_get_for_parameter():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        repo = SqliteRepository(db_path, auto_migrate=False)

        repo.append_batch("B-001", "2025-06-01", "Coating A", {
            "adhesion": {"reps": [1.05, 1.10, 1.02], "lower_spec": 0.6, "upper_spec": 1.5},
            "cohesion": {"reps": [1500, 1520, 1490], "lower_spec": 1000.0, "upper_spec": float("nan")},
        })

        adh = repo.get_for_parameter("adhesion")
        assert len(adh) == 1
        assert "rep1" in adh.columns


def test_get_formulas():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        repo = SqliteRepository(db_path, auto_migrate=False)

        repo.append_batch("B-001", "2025-06-01", "Coating A", {
            "adhesion": {"reps": [1.0], "lower_spec": float("nan"), "upper_spec": float("nan")},
        })
        repo.append_batch("B-002", "2025-06-02", "Coating B", {
            "adhesion": {"reps": [1.0], "lower_spec": float("nan"), "upper_spec": float("nan")},
        })

        formulas = repo.get_formulas()
        assert sorted(formulas) == ["Coating A", "Coating B"]


def test_get_parameters():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        repo = SqliteRepository(db_path, auto_migrate=False)

        repo.append_batch("B-001", "2025-06-01", "Coating A", {
            "adhesion": {"reps": [1.0], "lower_spec": float("nan"), "upper_spec": float("nan")},
            "cohesion": {"reps": [1500], "lower_spec": float("nan"), "upper_spec": float("nan")},
        })

        params = repo.get_parameters()
        assert sorted(params) == ["adhesion", "cohesion"]
