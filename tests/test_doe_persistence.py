import tempfile
from pathlib import Path

import pytest

from doe.persistence import DoeRepository


SAMPLE_FACTORS = [
    {"name": "line_speed", "type": "continuous", "low": 50, "high": 80},
    {"name": "cure_temp", "type": "continuous", "low": 120, "high": 160},
]

SAMPLE_RESPONSES = [
    {"name": "peel_strength", "goal": "maximize", "target": None, "low": 5.0, "high": 8.0},
]

SAMPLE_DESIGN = [
    {"run": 1, "line_speed": -1, "cure_temp": -1},
    {"run": 2, "line_speed": 1, "cure_temp": -1},
    {"run": 3, "line_speed": -1, "cure_temp": 1},
    {"run": 4, "line_speed": 1, "cure_temp": 1},
    {"run": 5, "line_speed": 0, "cure_temp": 0},
    {"run": 6, "line_speed": 0, "cure_temp": 0},
    {"run": 7, "line_speed": 0, "cure_temp": 0},
]

SAMPLE_RESULTS = [
    {"run": 1, "peel_strength": 6.2},
    {"run": 2, "peel_strength": 7.1},
    {"run": 3, "peel_strength": 6.8},
    {"run": 4, "peel_strength": 7.5},
    {"run": 5, "peel_strength": 7.0},
    {"run": 6, "peel_strength": 6.9},
    {"run": 7, "peel_strength": 7.1},
]


def test_create_and_load_session():
    """Create a DOE session and load it back."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "doe_test.db"
        repo = DoeRepository(db_path)

        session_id = repo.create(
            name="Screening Run 1",
            entry_type="screening",
            factors=SAMPLE_FACTORS,
            responses=SAMPLE_RESPONSES,
        )

        session = repo.load(session_id)
        assert session["name"] == "Screening Run 1"
        assert session["entry_type"] == "screening"
        assert session["status"] == "defined"
        assert session["factors"] == SAMPLE_FACTORS
        assert session["responses"] == SAMPLE_RESPONSES


def test_update_session():
    """Update design and results fields."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "doe_test.db"
        repo = DoeRepository(db_path)

        session_id = repo.create(
            name="Full Factorial", entry_type="full_factorial",
            factors=SAMPLE_FACTORS, responses=SAMPLE_RESPONSES,
        )

        repo.update(session_id, {
            "design": SAMPLE_DESIGN,
            "status": "designed",
        })

        session = repo.load(session_id)
        assert session["status"] == "designed"
        assert session["design"] == SAMPLE_DESIGN

        repo.update(session_id, {
            "results": SAMPLE_RESULTS,
            "status": "running",
        })

        session = repo.load(session_id)
        assert session["status"] == "running"
        assert session["results"] == SAMPLE_RESULTS


def test_list_sessions():
    """List all sessions, optionally filtered by entry_type."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "doe_test.db"
        repo = DoeRepository(db_path)

        repo.create("Screening A", "screening", SAMPLE_FACTORS, SAMPLE_RESPONSES)
        repo.create("Full Fact B", "full_factorial", SAMPLE_FACTORS, SAMPLE_RESPONSES)
        repo.create("Screening C", "screening", SAMPLE_FACTORS, SAMPLE_RESPONSES)

        all_sessions = repo.list_sessions()
        assert len(all_sessions) == 3

        screening = repo.list_sessions(entry_type="screening")
        assert len(screening) == 2
        assert all(s["entry_type"] == "screening" for s in screening)


def test_delete_session():
    """Delete a session."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "doe_test.db"
        repo = DoeRepository(db_path)

        sid = repo.create("To Delete", "screening", SAMPLE_FACTORS, SAMPLE_RESPONSES)
        assert len(repo.list_sessions()) == 1

        repo.delete(sid)
        assert len(repo.list_sessions()) == 0


def test_full_lifecycle():
    """End-to-end: create -> design -> run -> analyze -> optimize."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "doe_test.db"
        repo = DoeRepository(db_path)

        sid = repo.create("Lifecycle Test", "full_factorial",
                          SAMPLE_FACTORS, SAMPLE_RESPONSES)

        repo.update(sid, {"design": SAMPLE_DESIGN, "status": "designed"})
        repo.update(sid, {"results": SAMPLE_RESULTS, "status": "running"})

        sample_model = {
            "coefficients": [
                {"term": "Intercept", "estimate": 7.0, "p_value": 0.001, "significant": True},
                {"term": "line_speed", "estimate": 0.4, "p_value": 0.05, "significant": True},
            ],
            "r_squared": 0.85,
        }
        repo.update(sid, {"model": sample_model, "status": "analyzed"})

        sample_optimum = {
            "optimal_settings": {"line_speed": 75, "cure_temp": 145},
            "desirability": 0.82,
        }
        repo.update(sid, {"optimum": sample_optimum, "status": "optimized"})

        session = repo.load(sid)
        assert session["status"] == "optimized"
        assert session["optimum"]["desirability"] == 0.82


def test_update_rejects_unknown_column():
    """update() raises ValueError for non-whitelisted column names."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "doe_test.db"
        repo = DoeRepository(db_path)
        sid = repo.create("Test", "screening", SAMPLE_FACTORS, SAMPLE_RESPONSES)
        with pytest.raises(ValueError, match="Unknown column"):
            repo.update(sid, {"malicious_column; DROP TABLE doe_sessions; --": "oops"})


def test_update_whitelisted_columns_work():
    """update() accepts all standard whitelisted columns."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "doe_test.db"
        repo = DoeRepository(db_path)
        sid = repo.create("Test", "screening", SAMPLE_FACTORS, SAMPLE_RESPONSES)

        # All these should succeed without error
        repo.update(sid, {"design": SAMPLE_DESIGN, "status": "designed"})
        repo.update(sid, {"results": SAMPLE_RESULTS})
        repo.update(sid, {"model": {"r_squared": 0.9}})
        repo.update(sid, {"optimum": {"desirability": 0.8}})
        repo.update(sid, {"name": "Renamed"})

        session = repo.load(sid)
        assert session["name"] == "Renamed"
        # JSON columns auto-parsed in updated load()
        assert isinstance(session["design"], list)
        assert isinstance(session["model"], dict)


def test_analysis_column_crud():
    """analysis column should store and retrieve JSON data."""
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        repo = DoeRepository(db_path)

        sid = repo.create(
            "Analysis Test",
            "full_factorial",
            [{"name": "A", "type": "continuous", "low": 0, "high": 10}],
            [{"name": "y", "goal": "maximize", "low": 0, "high": 100}],
        )

        analysis_data = {
            "y": {
                "model_type": "linear",
                "anova": {
                    "source": ["Model", "A", "Residual", "Total"],
                    "ss": [0.5, 0.3, 0.1, 0.6],
                    "df": [1, 1, 2, 3],
                    "ms": [0.5, 0.3, 0.05, None],
                    "f": [10.0, 6.0, None, None],
                    "p": [0.05, 0.13, None, None],
                },
                "r_squared": 0.833,
            }
        }

        repo.update(sid, {"analysis": analysis_data, "status": "analyzed"})

        loaded = repo.load(sid)
        assert loaded["analysis"] == analysis_data
        assert loaded["status"] == "analyzed"
