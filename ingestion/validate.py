"""
ingestion/validate.py
=====================
Data validation for BBMP grievance records.

Each function receives a pandas DataFrame (one batch) and returns:
  - A filtered DataFrame of VALID records
  - A filtered DataFrame of REJECTED records
  - A dict with quality-check metrics (for storing in data_quality_results)

Design principle:
  - Records with missing ward/status are RETAINED (tagged is_valid=True)
    because they still contribute to category/date analysis.
  - Records with missing complaint_id or unparseable date are REJECTED
    because they cannot be reliably stored or deduplicated.
  - Future-dated records are REJECTED (likely test/corrupt data).
  - All quality metrics are calculated and returned for storage.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Known valid status values (from Phase 1 inspection)
# ─────────────────────────────────────────────────────────────────────────────
OPEN_STATUSES   = {"Registered", "ReOpen", "In Progress"}
CLOSED_STATUSES = {"Closed", "Resolved"}
ALL_STATUSES    = OPEN_STATUSES | CLOSED_STATUSES | {
    "Rejected", "Non Relevant", "Long Term Solution"
}

# ─────────────────────────────────────────────────────────────────────────────
# Column mapping: CSV header → internal name
# ─────────────────────────────────────────────────────────────────────────────
COLUMN_MAP = {
    "Complaint ID"     : "complaint_id",
    "Category"         : "category",
    "Sub Category"     : "sub_category",
    "Grievance Date"   : "grievance_date",
    "Ward Name"        : "ward_name",
    "Grievance Status" : "status",
    "Staff Remarks"    : "staff_remarks",
    "Staff Name"       : "staff_name",
}


# ─────────────────────────────────────────────────────────────────────────────
# STEP 1: Normalize column names
# ─────────────────────────────────────────────────────────────────────────────
def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Rename CSV headers to internal snake_case names.
    Strips leading/trailing whitespace from all string columns.
    Raises ValueError if any expected column is missing.
    """
    missing = [col for col in COLUMN_MAP if col not in df.columns]
    if missing:
        raise ValueError(
            f"Schema mismatch — expected columns not found: {missing}. "
            f"Got: {list(df.columns)}"
        )

    df = df.rename(columns=COLUMN_MAP)

    # Strip whitespace from all string columns
    str_cols = df.select_dtypes(include="object").columns
    for col in str_cols:
        df[col] = df[col].str.strip()

    return df


# ─────────────────────────────────────────────────────────────────────────────
# STEP 2: Parse dates
# ─────────────────────────────────────────────────────────────────────────────
def parse_dates(df: pd.DataFrame) -> pd.DataFrame:
    """
    Parse grievance_date from its nanosecond-precision string format.
    Records where parsing fails are tagged with NaT (will be rejected later).
    """
    df["grievance_date"] = pd.to_datetime(
        df["grievance_date"],
        errors="coerce",
        infer_datetime_format=True,
    )
    # Drop nanosecond precision (not needed, causes issues with SQLite)
    df["grievance_date"] = df["grievance_date"].dt.floor("s")
    return df


# ─────────────────────────────────────────────────────────────────────────────
# STEP 3: Individual validation checks
# ─────────────────────────────────────────────────────────────────────────────
def _check(
    df: pd.DataFrame,
    mask_bad: pd.Series,
    check_name: str,
    is_blocking: bool,
    details_sample: list | None = None,
) -> dict[str, Any]:
    """
    Internal helper: given a boolean mask of BAD rows, build a quality metric
    dict and optionally tag bad rows with a rejection reason.

    Args:
        df            : the full DataFrame (modified in-place if blocking)
        mask_bad      : True where the row is BAD
        check_name    : name for the quality_results record
        is_blocking   : if True, rows are marked rejected; else just counted
        details_sample: list of sample bad values to store as JSON

    Returns:
        quality metric dict
    """
    total   = len(df)
    n_bad   = int(mask_bad.sum())
    n_good  = total - n_bad
    rate    = round(n_bad / total * 100, 4) if total else 0.0

    if is_blocking and n_bad > 0:
        # Mark bad rows as rejected — don't overwrite existing rejection reason
        no_reason = df.get("_rejection_reason", pd.Series("", index=df.index)) == ""
        df.loc[mask_bad & no_reason, "_rejection_reason"] = check_name
        df.loc[mask_bad, "_is_valid"] = False

    return {
        "check_name"   : check_name,
        "total_checked": total,
        "passed"       : n_good,
        "failed"       : n_bad,
        "failure_rate" : rate,
        "details"      : json.dumps({"sample_bad_values": details_sample or []}, default=str),
    }


def validate_batch(
    df: pd.DataFrame,
    ingestion_cutoff: datetime | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, list[dict[str, Any]]]:
    """
    Run all validation checks on a normalized+date-parsed DataFrame.

    Args:
        df               : normalized DataFrame (from normalize_columns + parse_dates)
        ingestion_cutoff : records with grievance_date > this are rejected as future-dated.
                           Defaults to now().

    Returns:
        valid_df    : rows that passed all BLOCKING checks (is_valid=True)
        rejected_df : rows that failed at least one BLOCKING check
        metrics     : list of quality metric dicts (one per check)
    """
    if ingestion_cutoff is None:
        ingestion_cutoff = datetime.now()

    # Initialise tracking columns
    df = df.copy()
    df["_is_valid"]          = True
    df["_rejection_reason"]  = ""

    quality_metrics: list[dict[str, Any]] = []

    # ── CHECK 1: Missing complaint_id (BLOCKING) ──────────────────────────
    mask = df["complaint_id"].isna()
    quality_metrics.append(_check(df, mask, "missing_complaint_id", is_blocking=True))

    # ── CHECK 2: Missing/unparseable grievance_date (BLOCKING) ───────────
    mask = df["grievance_date"].isna()
    quality_metrics.append(_check(df, mask, "invalid_date", is_blocking=True))

    # ── CHECK 3: Future-dated records (BLOCKING) ──────────────────────────
    valid_dates = df["grievance_date"].notna()  # only test parseable dates
    mask = valid_dates & (df["grievance_date"] > ingestion_cutoff)
    sample = df.loc[mask, "grievance_date"].dt.strftime("%Y-%m-%d").head(5).tolist()
    quality_metrics.append(_check(df, mask, "future_dated", is_blocking=True, details_sample=sample))

    # ── CHECK 4: Missing category (BLOCKING — category is core to analysis)
    mask = df["category"].isna() | (df["category"] == "")
    quality_metrics.append(_check(df, mask, "missing_category", is_blocking=True))

    # ── CHECK 5: Missing ward_name (NON-BLOCKING — still usable for trends)
    mask = df["ward_name"].isna() | (df["ward_name"] == "")
    quality_metrics.append(_check(df, mask, "missing_ward", is_blocking=False))

    # ── CHECK 6: Missing status (NON-BLOCKING) ────────────────────────────
    mask = df["status"].isna() | (df["status"] == "")
    quality_metrics.append(_check(df, mask, "missing_status", is_blocking=False))

    # ── CHECK 7: Unexpected status values (NON-BLOCKING, informational) ───
    has_status = df["status"].notna() & (df["status"] != "")
    mask = has_status & ~df["status"].isin(ALL_STATUSES)
    sample = df.loc[mask, "status"].value_counts().head(5).to_dict()
    quality_metrics.append(_check(
        df, mask, "unexpected_status", is_blocking=False,
        details_sample=[str(sample)]
    ))

    # ── CHECK 8: Duplicate complaint_ids within this batch (BLOCKING) ─────
    dup_mask = df.duplicated(subset=["complaint_id"], keep="first")
    sample = df.loc[dup_mask, "complaint_id"].head(5).tolist()
    quality_metrics.append(_check(
        df, dup_mask, "intra_batch_duplicate_id", is_blocking=True,
        details_sample=[str(x) for x in sample]
    ))

    # ── Split into valid and rejected ────────────────────────────────────
    valid_df    = df[df["_is_valid"]].copy()
    rejected_df = df[~df["_is_valid"]].copy()

    # Remove our internal tracking columns before returning
    valid_df    = valid_df.drop(columns=["_is_valid", "_rejection_reason"])
    rejected_df = rejected_df.drop(columns=["_is_valid"])

    logger.info(
        "Batch validated: %d valid, %d rejected out of %d total",
        len(valid_df), len(rejected_df), len(df)
    )
    return valid_df, rejected_df, quality_metrics
