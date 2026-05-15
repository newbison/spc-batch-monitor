import pandas as pd
from pathlib import Path


def read_csv(filepath: Path) -> pd.DataFrame:
    return pd.read_csv(filepath)


def read_excel(filepath: Path) -> pd.DataFrame:
    return pd.read_excel(filepath)


def write_csv(df: pd.DataFrame, filepath: Path) -> None:
    filepath.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(filepath, index=False)
