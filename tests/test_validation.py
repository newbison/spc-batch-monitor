import pandas as pd
from data_access.validation import validate_rows


def test_valid_rows_pass():
    df = pd.DataFrame({
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
    errors = validate_rows(df)
    assert len(errors) == 0


def test_negative_rep_values_fail():
    df = pd.DataFrame({
        "date": ["2025-06-01"],
        "batch_id": ["B-001"],
        "formula": ["Grade A"],
        "parameter": ["viscosity"],
        "rep1": [1.05],
        "rep2": [-0.5],  # negative — reject
        "rep3": [1.02],
        "lower_spec": [0.6],
        "upper_spec": [1.5],
    })
    errors = validate_rows(df)
    assert len(errors) >= 1
    assert any("negative" in e.lower() for e in errors)


def test_all_nan_reps_fail():
    df = pd.DataFrame({
        "date": ["2025-06-01"],
        "batch_id": ["B-001"],
        "formula": ["Grade A"],
        "parameter": ["viscosity"],
        "rep1": [float("nan")],
        "rep2": [float("nan")],
        "rep3": [float("nan")],
        "lower_spec": [0.6],
        "upper_spec": [1.5],
    })
    errors = validate_rows(df)
    assert len(errors) >= 1
    assert any("no valid" in e.lower() for e in errors)


def test_bad_date_format_fails():
    df = pd.DataFrame({
        "date": ["not-a-date"],
        "batch_id": ["B-001"],
        "formula": ["Grade A"],
        "parameter": ["viscosity"],
        "rep1": [1.05],
        "rep2": [1.10],
        "rep3": [1.02],
        "lower_spec": [0.6],
        "upper_spec": [1.5],
    })
    errors = validate_rows(df)
    assert any("date" in e.lower() for e in errors)


def test_negative_spec_fails():
    df = pd.DataFrame({
        "date": ["2025-06-01"],
        "batch_id": ["B-001"],
        "formula": ["Grade A"],
        "parameter": ["viscosity"],
        "rep1": [1.05],
        "rep2": [1.10],
        "rep3": [1.02],
        "lower_spec": [-0.5],  # negative spec — reject
        "upper_spec": [1.5],
    })
    errors = validate_rows(df)
    assert len(errors) >= 1
    assert any("spec" in e.lower() for e in errors)


def test_non_numeric_rep_is_flagged():
    """Non-numeric values should be flagged as invalid reps."""
    df = pd.DataFrame({
        "date": ["2025-06-01"],
        "batch_id": ["B-001"],
        "formula": ["Grade A"],
        "parameter": ["viscosity"],
        "rep1": [1.05],
        "rep2": ["abc"],  # non-numeric
        "rep3": [1.02],
        "lower_spec": [0.6],
        "upper_spec": [1.5],
    })
    errors = validate_rows(df)
    assert any("non-numeric" in e.lower() for e in errors)


def test_non_numeric_spec_is_flagged():
    """Non-numeric spec values should be flagged."""
    df = pd.DataFrame({
        "date": ["2025-06-01"],
        "batch_id": ["B-001"],
        "formula": ["Grade A"],
        "parameter": ["viscosity"],
        "rep1": [1.05],
        "rep2": [1.10],
        "rep3": [1.02],
        "lower_spec": ["not-a-number"],
        "upper_spec": [1.5],
    })
    errors = validate_rows(df)
    assert any("non-numeric" in e.lower() for e in errors)
