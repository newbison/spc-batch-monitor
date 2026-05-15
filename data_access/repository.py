import pandas as pd
import re
from pathlib import Path

from .base import DataRepository
from .file_reader import read_csv, write_csv

BASE_COLUMNS = ["date", "batch_id", "formula", "parameter", "lower_spec", "upper_spec"]


def _rep_columns_from_df(df: pd.DataFrame) -> list[str]:
    return sorted(
        [c for c in df.columns if re.match(r"^rep\d+$", c)],
        key=lambda x: int(x[3:]),
    )


class CsvRepository(DataRepository):
    def __init__(self, filepath: Path):
        self.filepath = filepath

    @property
    def columns(self) -> list[str]:
        if self.filepath.exists():
            df = read_csv(self.filepath)
            return list(df.columns)
        return BASE_COLUMNS

    def load_all(self) -> pd.DataFrame:
        if not self.filepath.exists():
            return pd.DataFrame(columns=BASE_COLUMNS)
        return read_csv(self.filepath)

    def get_for_parameter(self, parameter: str) -> pd.DataFrame:
        df = self.load_all()
        if df.empty:
            return df
        return df[df["parameter"] == parameter].copy().reset_index(drop=True)

    def get_formulas(self) -> list[str]:
        df = self.load_all()
        if df.empty:
            return []
        return df["formula"].unique().tolist()

    def get_parameters(self) -> list[str]:
        df = self.load_all()
        if df.empty:
            return []
        return df["parameter"].unique().tolist()

    def get_specs_for_formula(self, formula: str, parameter: str) -> dict | None:
        df = self.load_all()
        if df.empty:
            return None
        match = df[(df["formula"] == formula) & (df["parameter"] == parameter)]
        if match.empty:
            return None
        row = match.iloc[-1]
        return {"lower_spec": row["lower_spec"], "upper_spec": row["upper_spec"]}

    def subgroup_size(self) -> int:
        df = self.load_all()
        if df.empty:
            return 0
        rep_cols = _rep_columns_from_df(df)
        return len(rep_cols)

    def append_batch(self, batch_id: str, date: str, formula: str,
                     measurements: dict[str, dict]) -> None:
        rows = []
        for param, entry in measurements.items():
            row = {
                "date": date,
                "batch_id": batch_id,
                "formula": formula,
                "parameter": param,
                "lower_spec": entry["lower_spec"],
                "upper_spec": entry["upper_spec"],
            }
            for i, val in enumerate(entry["reps"], start=1):
                row[f"rep{i}"] = val
            rows.append(row)

        new_rows = pd.DataFrame(rows)
        df = self.load_all()
        if df.empty:
            df = new_rows
        else:
            df = pd.concat([df, new_rows], ignore_index=True)
        write_csv(df, self.filepath)
