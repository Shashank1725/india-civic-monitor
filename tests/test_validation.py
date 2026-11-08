"""
tests/test_validation.py
========================
Automated unit tests for validation rules in ingestion/validate.py.
"""

from datetime import datetime, timedelta
import pandas as pd
import pytest

from ingestion.validate import (
    normalize_columns,
    parse_dates,
    validate_batch,
    COLUMN_MAP,
)


def create_sample_raw_df():
    return pd.DataFrame({
        "Complaint ID": [101, 102, 103, 104, 105],
        "Category": ["Electrical", "Solid Waste (Garbage) Related", "Road Maintenance(Engg)", "Forest", "Health Dept"],
        "Sub Category": ["Street Light Not Working", "Garbage dump", "Potholes", "Tree fallen", "Mosquito"],
        "Grievance Date": [
            "2023-01-01 10:00:00.000000000",
            "2023-01-02 11:30:00.000000000",
            "2023-01-03 14:15:00.000000000",
            "2023-01-04 09:00:00.000000000",
            "2023-01-05 18:45:00.000000000",
        ],
        "Ward Name": ["Horamavu", "Bellandur", "Begur", "Jakkur", "HSR Layout"],
        "Grievance Status": ["Closed", "Closed", "Registered", "Closed", "Resolved"],
        "Staff Remarks": ["Fixed", "Cleared", "Assigned", "Attended", "Done"],
        "Staff Name": ["Officer A", "Officer B", "Officer C", "Officer D", "Officer E"],
    })


def test_normalize_columns_success():
    df = create_sample_raw_df()
    norm = normalize_columns(df)
    assert "complaint_id" in norm.columns
    assert "ward_name" in norm.columns
    assert "category" in norm.columns
    assert "grievance_date" in norm.columns
    assert len(norm) == 5


def test_normalize_columns_missing_expected():
    df = pd.DataFrame({"Complaint ID": [101], "Category": ["Electrical"]})
    with pytest.raises(ValueError, match="Schema mismatch"):
        normalize_columns(df)


def test_parse_dates():
    df = create_sample_raw_df()
    norm = normalize_columns(df)
    parsed = parse_dates(norm)
    assert pd.api.types.is_datetime64_any_dtype(parsed["grievance_date"])
    assert parsed["grievance_date"].iloc[0] == pd.Timestamp("2023-01-01 10:00:00")


def test_validation_detects_future_dates():
    df = create_sample_raw_df()
    norm = normalize_columns(df)
    parsed = parse_dates(norm)
    
    # Introduce a future date beyond cutoff
    cutoff = datetime(2023, 1, 3, 0, 0, 0)
    valid_df, rejected_df, metrics = validate_batch(parsed, ingestion_cutoff=cutoff)
    
    # Records from Jan 3, 4, 5 are after cutoff
    assert len(rejected_df) == 3
    assert len(valid_df) == 2


def test_validation_retains_missing_ward():
    # Ward missing should NOT reject the row (it is non-blocking)
    df = create_sample_raw_df()
    df.loc[0, "Ward Name"] = None
    norm = normalize_columns(df)
    parsed = parse_dates(norm)
    
    valid_df, rejected_df, metrics = validate_batch(parsed)
    assert 101 in valid_df["complaint_id"].values
    
    # Check that missing_ward was recorded in metrics
    ward_metric = next(m for m in metrics if m["check_name"] == "missing_ward")
    assert ward_metric["failed"] == 1


def test_validation_rejects_missing_complaint_id():
    df = create_sample_raw_df()
    df.loc[0, "Complaint ID"] = None
    norm = normalize_columns(df)
    parsed = parse_dates(norm)
    
    valid_df, rejected_df, metrics = validate_batch(parsed)
    assert len(rejected_df) == 1
    assert len(valid_df) == 4
