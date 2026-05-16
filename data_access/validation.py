"""Row-level data validation for batch measurements."""
import pandas as pd
from datetime import datetime

__all__ = ["validate_rows"]


def validate_rows(df: pd.DataFrame) -> list[str]:
    """Validate all measurement rows. Returns list of error messages (empty = valid)."""
    errors: list[str] = []

    for idx, row in df.iterrows():
        row_num = idx + 2  # 1-indexed + header row
        prefix = f"Row {row_num}"
        batch_id = row.get("batch_id", "?")

        # Check date format
        date_val = row.get("date")
        if pd.isna(date_val) or not _is_valid_date(str(date_val)):
            errors.append(f"{prefix} (batch {batch_id}): Invalid or missing date '{date_val}'")

        # Check that at least one rep is valid
        rep_values = []
        for col in df.columns:
            if col.startswith("rep") and col[3:].isdigit():
                val = row.get(col)
                if val is not None and not pd.isna(val):
                    try:
                        v = float(val)
                        if v < 0:
                            errors.append(
                                f"{prefix} (batch {batch_id}, {col}): Negative value {v}"
                            )
                        else:
                            rep_values.append(v)
                    except (ValueError, TypeError):
                        errors.append(
                            f"{prefix} (batch {batch_id}, {col}): Non-numeric value '{val}'"
                        )

        if len(rep_values) == 0:
            errors.append(f"{prefix} (batch {batch_id}): No valid replicate values")

        # Check specs
        for spec_col in ["lower_spec", "upper_spec"]:
            val = row.get(spec_col)
            if val is not None and not pd.isna(val):
                try:
                    v = float(val)
                    if v < 0:
                        errors.append(
                            f"{prefix} (batch {batch_id}, {spec_col}): Negative value {v}"
                        )
                except (ValueError, TypeError):
                    errors.append(
                        f"{prefix} (batch {batch_id}, {spec_col}): Non-numeric value '{val}'"
                    )

    return errors


def _is_valid_date(s: str) -> bool:
    """Check if string is a valid YYYY-MM-DD date."""
    try:
        datetime.strptime(s.strip(), "%Y-%m-%d")
        return True
    except (ValueError, AttributeError):
        return False
