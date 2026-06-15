"""SQLite-backed repository for measurement data."""
import sqlite3
import pandas as pd
import math
from contextlib import contextmanager
from pathlib import Path

from data_access.base import DataRepository
from data_access.validation import validate_rows
from data_access.file_reader import read_csv

REP_COLUMNS = [f"rep{i}" for i in range(1, 51)]
BASE_COLUMNS = ["date", "batch_id", "formula", "parameter", "lower_spec", "upper_spec"]
ALL_COLUMNS = BASE_COLUMNS + REP_COLUMNS

SCHEMA_SQL = f"""
CREATE TABLE IF NOT EXISTS measurements (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    date        TEXT    NOT NULL,
    batch_id    TEXT    NOT NULL,
    formula     TEXT    NOT NULL,
    parameter   TEXT    NOT NULL,
    {",\n    ".join(f"{c} REAL" for c in REP_COLUMNS)},
    lower_spec  REAL,
    upper_spec  REAL,
    created_at  TEXT    DEFAULT (datetime('now')),
    UNIQUE(batch_id, formula, parameter)
);
"""


def _nan_to_none(v):
    """Convert NaN float to None for SQLite compatibility."""
    return None if isinstance(v, float) and math.isnan(v) else v


def _row_to_dict(row: dict) -> dict:
    """Convert measurement dict to flat dict for SQL insertion."""
    d = {
        "date": row.get("date"),
        "batch_id": row.get("batch_id"),
        "formula": row.get("formula"),
        "parameter": row.get("parameter"),
        "lower_spec": row.get("lower_spec"),
        "upper_spec": row.get("upper_spec"),
    }
    # Clear all rep columns first
    for c in REP_COLUMNS:
        d[c] = None
    # Fill in the ones we have
    for i, val in enumerate(row.get("reps", []), start=1):
        col = f"rep{i}"
        if col in d:
            d[col] = float(val) if val is not None else None
    return d


class SqliteRepository(DataRepository):
    def __init__(self, db_path: Path, auto_migrate: bool = True):
        self.db_path = db_path
        self._init_db()
        if auto_migrate:
            self._auto_migrate_from_csv()

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

    @staticmethod
    def _drop_empty_rep_cols(df: pd.DataFrame) -> pd.DataFrame:
        """Drop rep columns where all values are null (unused in this schema)."""
        rep_cols = [c for c in df.columns if c.startswith("rep") and c[3:].isdigit()]
        empty = [c for c in rep_cols if df[c].isna().all()]
        if empty:
            df = df.drop(columns=empty)
        return df

    def load_all(self) -> pd.DataFrame:
        with self._conn() as conn:
            df = pd.read_sql(f"SELECT {', '.join(ALL_COLUMNS)} FROM measurements ORDER BY date", conn)
            return self._drop_empty_rep_cols(df)

    def get_for_parameter(self, parameter: str) -> pd.DataFrame:
        with self._conn() as conn:
            df = pd.read_sql(
                f"SELECT {', '.join(ALL_COLUMNS)} FROM measurements WHERE parameter=? ORDER BY date",
                conn, params=(parameter,)
            )
            return self._drop_empty_rep_cols(df)

    def get_formulas(self) -> list[str]:
        with self._conn() as conn:
            rows = conn.execute("SELECT DISTINCT formula FROM measurements ORDER BY formula").fetchall()
            return [r["formula"] for r in rows]

    def get_parameters(self) -> list[str]:
        with self._conn() as conn:
            rows = conn.execute("SELECT DISTINCT parameter FROM measurements ORDER BY parameter").fetchall()
            return [r["parameter"] for r in rows]

    def get_specs_for_formula(self, formula: str, parameter: str) -> dict | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT lower_spec, upper_spec FROM measurements WHERE formula=? AND parameter=? ORDER BY date DESC LIMIT 1",
                (formula, parameter)
            ).fetchone()
            if row is None:
                return None
            lsl = row["lower_spec"] if row["lower_spec"] is not None else float("nan")
            usl = row["upper_spec"] if row["upper_spec"] is not None else float("nan")
            return {"lower_spec": lsl, "upper_spec": usl}

    def subgroup_size(self) -> int:
        """Detect max subgroup size from existing rep columns."""
        df = self.load_all()
        if df.empty:
            return 0
        rep_cols = [c for c in df.columns if c.startswith("rep") and c[3:].isdigit()]
        # Count max non-null reps across all rows
        max_n = 0
        for _, row in df.iterrows():
            n = sum(1 for c in rep_cols if pd.notna(row[c]))
            if n > max_n:
                max_n = n
        return max_n

    def append_batch(self, batch_id: str, date: str, formula: str, measurements: dict) -> None:
        rows = []
        for param, entry in measurements.items():
            row = {
                "date": date,
                "batch_id": batch_id,
                "formula": formula,
                "parameter": param,
                "lower_spec": entry["lower_spec"],
                "upper_spec": entry["upper_spec"],
                "reps": entry["reps"],
            }
            rows.append(row)

        # Expand reps into individual columns before validation
        flat_rows = []
        for row in rows:
            d = _row_to_dict(row)
            flat_rows.append(d)

        # Validate using rep1..repN columns
        df = pd.DataFrame(flat_rows)
        errors = validate_rows(df)
        if errors:
            raise ValueError(f"Validation failed:\n" + "\n".join(errors))

        # Insert
        placeholders = ", ".join(["?" for _ in ALL_COLUMNS])
        cols = ", ".join(ALL_COLUMNS)
        insert_sql = f"INSERT OR IGNORE INTO measurements ({cols}) VALUES ({placeholders})"

        with self._conn() as conn:
            for d in flat_rows:
                values = [_nan_to_none(d.get(c)) for c in ALL_COLUMNS]
                conn.execute(insert_sql, values)

    def upload_csv(self, df: pd.DataFrame) -> dict:
        """Upload rows from a CSV DataFrame. Returns {inserted, skipped, errors}.

        - Inserts rows that don't exist (matched by batch_id+formula+parameter)
        - Skips existing rows (silently)
        - Returns list of errors for invalid rows
        """
        result = {"inserted": 0, "skipped": 0, "errors": []}

        # Validate first
        errors = validate_rows(df)
        if errors:
            result["errors"] = errors
            return result

        placeholders = ", ".join(["?" for _ in ALL_COLUMNS])
        cols = ", ".join(ALL_COLUMNS)
        insert_sql = f"INSERT OR IGNORE INTO measurements ({cols}) VALUES ({placeholders})"

        with self._conn() as conn:
            for _, row in df.iterrows():
                rep_vals = []
                rep_cols = sorted(
                    [c for c in df.columns if c.startswith("rep") and c[3:].isdigit()],
                    key=lambda x: int(x[3:]),
                )
                for c in rep_cols:
                    v = row.get(c)
                    if v is not None and not pd.isna(v):
                        try:
                            rep_vals.append(float(v))
                        except (ValueError, TypeError):
                            pass
                d = {
                    "date": row.get("date"),
                    "batch_id": row.get("batch_id"),
                    "formula": row.get("formula"),
                    "parameter": row.get("parameter"),
                    "lower_spec": row.get("lower_spec", None),
                    "upper_spec": row.get("upper_spec", None),
                    "reps": rep_vals,
                }
                sql_row = _row_to_dict(d)
                values = [_nan_to_none(sql_row.get(c)) for c in ALL_COLUMNS]

                try:
                    before = conn.total_changes
                    conn.execute(insert_sql, values)
                    if conn.total_changes > before:
                        result["inserted"] += 1
                    else:
                        result["skipped"] += 1
                except Exception as e:
                    result["errors"].append(f"Row (batch {d['batch_id']}, param {d['parameter']}): {e}")

            conn.commit()

        return result

    def get_batch(self, batch_id: str) -> pd.DataFrame:
        """Return all parameter rows for a given batch_id."""
        with self._conn() as conn:
            df = pd.read_sql(
                f"SELECT {', '.join(ALL_COLUMNS)} FROM measurements WHERE batch_id=? ORDER BY parameter",
                conn, params=(batch_id,)
            )
            return self._drop_empty_rep_cols(df)

    def update_batch(self, batch_id: str, formula: str, parameter: str,
                     new_values: dict) -> bool:
        """Update rep values and specs for an existing batch/parameter row.

        Returns True if the row was found and updated, False if not found.
        Raises ValueError if new_values fails validation.
        """
        # Validate new values
        row = {
            "date": "2025-01-01",  # placeholder for validation
            "batch_id": batch_id,
            "formula": formula,
            "parameter": parameter,
            "lower_spec": new_values["lower_spec"],
            "upper_spec": new_values["upper_spec"],
            "reps": new_values["reps"],
        }
        flat = _row_to_dict(row)
        errors = validate_rows(pd.DataFrame([flat]))
        if errors:
            raise ValueError(f"Validation failed:\n" + "\n".join(errors))

        # Build SET clause from rep columns that have values
        set_parts = []
        params = []
        for i, val in enumerate(new_values["reps"], start=1):
            set_parts.append(f"rep{i} = ?")
            params.append(val)
        set_parts.append("lower_spec = ?")
        params.append(new_values["lower_spec"] if not (
            isinstance(new_values["lower_spec"], float)
            and math.isnan(new_values["lower_spec"])
        ) else None)
        set_parts.append("upper_spec = ?")
        params.append(new_values["upper_spec"] if not (
            isinstance(new_values["upper_spec"], float)
            and math.isnan(new_values["upper_spec"])
        ) else None)

        params.extend([batch_id, formula, parameter])

        sql = f"UPDATE measurements SET {', '.join(set_parts)} WHERE batch_id=? AND formula=? AND parameter=?"

        with self._conn() as conn:
            cursor = conn.execute(sql, params)
            return cursor.rowcount > 0

    def delete_batch(self, batch_id: str, formula: str, parameter: str) -> bool:
        """Delete a single batch/parameter row. Returns True if deleted."""
        with self._conn() as conn:
            cursor = conn.execute(
                "DELETE FROM measurements WHERE batch_id=? AND formula=? AND parameter=?",
                (batch_id, formula, parameter)
            )
            return cursor.rowcount > 0

    def delete_all_for_batch(self, batch_id: str) -> int:
        """Delete all parameter rows for a batch. Returns count of deleted rows."""
        with self._conn() as conn:
            cursor = conn.execute(
                "DELETE FROM measurements WHERE batch_id=?",
                (batch_id,)
            )
            return cursor.rowcount

    def _auto_migrate_from_csv(self):
        """Import existing CSV data into SQLite if DB is empty."""
        with self._conn() as conn:
            count = conn.execute("SELECT COUNT(*) FROM measurements").fetchone()[0]
            if count > 0:
                return  # already has data

        from config import DATA_FILE
        if not DATA_FILE.exists():
            return

        df = read_csv(DATA_FILE)
        if df.empty:
            return

        result = self.upload_csv(df)
        if result["errors"]:
            raise RuntimeError(f"Auto-migration errors:\n" + "\n".join(result["errors"]))
