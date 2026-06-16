"""DOE session persistence to SQLite.

Stores DOE sessions in a `doe_sessions` table with JSON columns for
variable-shape data. Pure Python — no Streamlit imports.
"""

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS doe_sessions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    entry_type  TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'defined',
    factors     TEXT NOT NULL,
    responses   TEXT NOT NULL,
    design      TEXT,
    results     TEXT,
    model       TEXT,
    optimum     TEXT,
    created_at  TEXT DEFAULT (datetime('now')),
    updated_at  TEXT DEFAULT (datetime('now'))
);
"""


class DoeRepository:
    """SQLite repository for DOE sessions."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()

    # Whitelist of allowed column names (prevents SQL injection via dict keys)
    ALLOWED_COLUMNS = {
        "name", "status", "entry_type",
        "factors", "responses", "design", "results", "model", "optimum",
    }
    JSON_COLUMNS = {"factors", "responses", "design", "results", "model", "optimum"}

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self):
        with self._conn() as conn:
            conn.execute(SCHEMA_SQL)

    def create(self, name: str, entry_type: str, factors: list[dict],
               responses: list[dict]) -> int:
        """Create a new DOE session.

        Parameters
        ----------
        name : str
            Human-readable session name.
        entry_type : str
            One of 'screening', 'full_factorial', 'analyze_only'.
        factors : list of dict
            Factor definitions.
        responses : list of dict
            Response definitions.

        Returns
        -------
        int
            The session ID.
        """
        sql = """
        INSERT INTO doe_sessions (name, entry_type, status, factors, responses)
        VALUES (?, ?, 'defined', ?, ?)
        """
        with self._conn() as conn:
            cursor = conn.execute(
                sql,
                (name, entry_type, json.dumps(factors), json.dumps(responses)),
            )
            return cursor.lastrowid

    def load(self, session_id: int) -> dict:
        """Load a DOE session by ID.

        Returns a dict with all columns. JSON columns (factors, responses,
        design, results, model, optimum) are auto-parsed into Python objects.
        """
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM doe_sessions WHERE id = ?", (session_id,)
            ).fetchone()
            if row is None:
                raise KeyError(f"DOE session {session_id} not found")
            result = dict(row)
            # Auto-parse JSON columns
            for col in self.JSON_COLUMNS:
                if col in result and result[col] is not None:
                    try:
                        result[col] = json.loads(result[col])
                    except (json.JSONDecodeError, TypeError):
                        pass  # Leave as-is if not valid JSON
            return result

    def update(self, session_id: int, updates: dict) -> None:
        """Update specific fields of a DOE session.

        Parameters
        ----------
        session_id : int
        updates : dict
            Keys are column names. JSON-serializable values are auto-serialized
            for JSON columns (design, results, model, optimum).
            'status' and 'updated_at' are handled automatically.
        """
        set_parts = []
        params = []

        for key, value in updates.items():
            if key not in self.ALLOWED_COLUMNS:
                raise ValueError(
                    f"Unknown column '{key}'. Allowed: {sorted(self.ALLOWED_COLUMNS)}"
                )
            if key in self.JSON_COLUMNS:
                set_parts.append(f"{key} = ?")
                params.append(json.dumps(value))
            else:
                set_parts.append(f"{key} = ?")
                params.append(value)

        # Always update timestamp
        set_parts.append("updated_at = ?")
        params.append(datetime.now().isoformat())

        params.append(session_id)

        sql = f"UPDATE doe_sessions SET {', '.join(set_parts)} WHERE id = ?"
        with self._conn() as conn:
            conn.execute(sql, params)

    def list_sessions(self, entry_type: str | None = None) -> list[dict]:
        """List all DOE sessions, optionally filtered by entry_type.

        Returns list of dicts with columns: id, name, entry_type, status,
        created_at, updated_at.
        """
        with self._conn() as conn:
            if entry_type:
                rows = conn.execute(
                    "SELECT id, name, entry_type, status, created_at, updated_at "
                    "FROM doe_sessions WHERE entry_type = ? ORDER BY updated_at DESC",
                    (entry_type,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT id, name, entry_type, status, created_at, updated_at "
                    "FROM doe_sessions ORDER BY updated_at DESC"
                ).fetchall()
            return [dict(r) for r in rows]

    def delete(self, session_id: int) -> None:
        """Delete a DOE session."""
        with self._conn() as conn:
            conn.execute("DELETE FROM doe_sessions WHERE id = ?", (session_id,))
