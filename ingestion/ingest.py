"""
ingestion/ingest.py
===================
Main data ingestion pipeline for the BBMP Citizen Grievances dataset.

What this script does (in order):
  1. Creates an IngestionRun record (status=running) in the database.
  2. Discovers all CSV files in DATASET_DIR.
  3. For each file: reads → normalizes → validates → bulk-inserts.
  4. Uses INSERT OR IGNORE to safely skip already-existing complaint_ids.
  5. Stores data-quality metrics per check.
  6. Rebuilds the daily_aggregates table from scratch.
  7. Updates the IngestionRun record (status=success/failed + counts).

Safe to rerun:
  - On first run   : inserts all 766,648 records.
  - On second run  : all records skipped (complaint_ids already exist).
  - No duplicates are ever created regardless of how many times you run it.

Usage (Windows):
    cd C:\\Users\\Asus\\Downloads\\DATASci\\india-civic-monitor
    python ingestion/ingest.py
"""

from __future__ import annotations

import json
import logging
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

# ── project path setup ────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
except ImportError:
    pass

import pandas as pd
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy import text

from database.database import SessionLocal, init_db, engine
from database.models import (
    IngestionRun,
    ServiceRequest,
    DataQualityResult,
    DailyAggregate,
    RunStatus,
)
from ingestion.validate import normalize_columns, parse_dates, validate_batch

# ─────────────────────────────────────────────────────────────────────────────
# Logging setup
# ─────────────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Config from environment
# ─────────────────────────────────────────────────────────────────────────────
_raw_dataset_dir = os.getenv("DATASET_DIR", "./Dataset")
DATASET_DIR = (PROJECT_ROOT / _raw_dataset_dir).resolve() if not Path(_raw_dataset_dir).is_absolute() else Path(_raw_dataset_dir)
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "500"))  # validation chunk size (not DB insert size)

# Status values we treat as "open" vs "closed" for aggregate counts
OPEN_STATUSES   = {"Registered", "ReOpen", "In Progress"}
CLOSED_STATUSES = {"Closed", "Resolved"}


# ─────────────────────────────────────────────────────────────────────────────
# STEP 1: Discover CSV files
# ─────────────────────────────────────────────────────────────────────────────
def discover_files(dataset_dir: Path) -> list[Path]:
    if not dataset_dir.exists():
        raise FileNotFoundError(f"DATASET_DIR not found: {dataset_dir}")
    files = sorted(dataset_dir.glob("*.csv"))
    if not files:
        raise FileNotFoundError(f"No CSV files found in {dataset_dir}")
    logger.info("Found %d CSV file(s) in %s", len(files), dataset_dir)
    return files


# ─────────────────────────────────────────────────────────────────────────────
# STEP 2: Convert a validated DataFrame to a list of dicts for bulk insert
# ─────────────────────────────────────────────────────────────────────────────
def df_to_records(
    df: pd.DataFrame,
    run_id: int,
) -> list[dict[str, Any]]:
    """Map validated DataFrame rows to ServiceRequest column dicts."""
    records = []
    now = datetime.now()

    for row in df.itertuples(index=False):
        records.append({
            "complaint_id"   : int(row.complaint_id),
            "category"       : str(row.category) if pd.notna(row.category) else None,
            "sub_category"   : str(row.sub_category) if pd.notna(row.sub_category) else None,
            "grievance_date" : row.grievance_date.to_pydatetime() if hasattr(row.grievance_date, "to_pydatetime") else row.grievance_date,
            "ward_name"      : str(row.ward_name) if pd.notna(row.ward_name) else None,
            "status"         : str(row.status) if pd.notna(row.status) else None,
            "staff_remarks"  : str(row.staff_remarks) if pd.notna(row.staff_remarks) else None,
            "staff_name"     : str(row.staff_name) if pd.notna(row.staff_name) else None,
            "ingestion_run_id": run_id,
            "is_valid"       : True,
            "rejection_reason": None,
            "created_at"     : now,
            "updated_at"     : now,
        })
    return records


# ─────────────────────────────────────────────────────────────────────────────
# STEP 3: Bulk insert with ON CONFLICT DO NOTHING (safe re-run)
# ─────────────────────────────────────────────────────────────────────────────
# SQLite limits: max 999 bind variables per statement, and each row has 14
# columns, so we insert rows one at a time using executemany-style looping
# via SQLAlchemy Core. This is still much faster than ORM session.add().
_DB_CHUNK = 60  # rows per INSERT statement (60 × 14 = 840 bind vars — safely under 999)

def bulk_insert_ignore(session, records: list[dict]) -> tuple[int, int]:
    """
    Insert records into service_requests, skipping any complaint_id that
    already exists. Safe for repeated ingestion runs.

    Returns:
        (inserted_count, skipped_count)
    """
    if not records:
        return 0, 0

    total_inserted = 0
    total_skipped  = 0

    # Insert in small chunks to stay within SQLite's bind-variable limit
    for chunk_start in range(0, len(records), _DB_CHUNK):
        chunk = records[chunk_start : chunk_start + _DB_CHUNK]
        stmt  = sqlite_insert(ServiceRequest).values(chunk)
        stmt  = stmt.on_conflict_do_nothing(index_elements=["complaint_id"])
        result = session.execute(stmt)
        inserted = result.rowcount if result.rowcount >= 0 else len(chunk)
        total_inserted += inserted
        total_skipped  += len(chunk) - inserted

    session.flush()
    return total_inserted, total_skipped


# ─────────────────────────────────────────────────────────────────────────────
# STEP 4: Process one CSV file
# ─────────────────────────────────────────────────────────────────────────────
def process_file(
    filepath: Path,
    run_id: int,
    session,
    cutoff: datetime,
    counters: dict,
    all_quality_metrics: list,
) -> None:
    """
    Reads, validates, and inserts one CSV file in batches.
    Updates `counters` dict in-place with cumulative stats.
    """
    logger.info("  Processing: %s  (%.1f MB)", filepath.name, filepath.stat().st_size / 1_048_576)

    try:
        df_raw = pd.read_csv(
            filepath,
            encoding="utf-8",
            encoding_errors="replace",
            low_memory=False,
        )
    except Exception as exc:
        logger.error("  Failed to read %s: %s", filepath.name, exc)
        counters["rejected"] += 0  # can't even count rows
        return

    n_rows = len(df_raw)
    counters["read"] += n_rows
    logger.info("  Read %d rows", n_rows)

    # Normalize + parse dates for whole file at once
    try:
        df_norm = normalize_columns(df_raw)
        df_norm = parse_dates(df_norm)
    except ValueError as exc:
        logger.error("  Schema error in %s: %s", filepath.name, exc)
        counters["rejected"] += n_rows
        return

    # Process in batches
    for start in range(0, n_rows, BATCH_SIZE):
        batch = df_norm.iloc[start : start + BATCH_SIZE].copy()

        valid_df, rejected_df, metrics = validate_batch(batch, ingestion_cutoff=cutoff)

        # Accumulate quality metrics (merge with existing checks)
        for m in metrics:
            existing = next(
                (q for q in all_quality_metrics if q["check_name"] == m["check_name"]),
                None,
            )
            if existing:
                existing["total_checked"] += m["total_checked"]
                existing["passed"]        += m["passed"]
                existing["failed"]        += m["failed"]
                # Recompute rate
                if existing["total_checked"] > 0:
                    existing["failure_rate"] = round(
                        existing["failed"] / existing["total_checked"] * 100, 4
                    )
            else:
                all_quality_metrics.append(dict(m))

        # Insert valid records
        records = df_to_records(valid_df, run_id)
        inserted, skipped = bulk_insert_ignore(session, records)
        counters["inserted"]   += inserted
        counters["skipped"]    += skipped
        counters["duplicates"] += skipped   # skipped = already-in-DB = duplicates on rerun
        counters["rejected"]   += len(rejected_df)

        logger.debug(
            "    Batch %d–%d → inserted=%d  skipped=%d  rejected=%d",
            start, start + len(batch), inserted, skipped, len(rejected_df),
        )

    session.commit()
    logger.info(
        "  File done: inserted=%d  skipped=%d  rejected=%d",
        counters["inserted"], counters["skipped"], counters["rejected"],
    )


# ─────────────────────────────────────────────────────────────────────────────
# STEP 5: Rebuild daily_aggregates
# ─────────────────────────────────────────────────────────────────────────────
def rebuild_daily_aggregates(session) -> int:
    """
    Deletes and rebuilds the daily_aggregates table from service_requests.
    Uses a single SQL query for efficiency — avoids loading all rows into Python.

    Returns the number of aggregate rows created.
    """
    logger.info("Rebuilding daily_aggregates ...")

    # Delete existing aggregates
    session.execute(text("DELETE FROM daily_aggregates"))
    session.flush()

    # Rebuild using SQL GROUP BY — much faster than Python-side aggregation
    session.execute(text("""
        INSERT INTO daily_aggregates
            (agg_date, ward_name, category, complaint_count, open_count, closed_count, last_updated)
        SELECT
            DATE(grievance_date)            AS agg_date,
            COALESCE(ward_name, 'Unknown')  AS ward_name,
            category,
            COUNT(*)                        AS complaint_count,
            SUM(CASE WHEN status IN ('Registered','ReOpen','In Progress') THEN 1 ELSE 0 END) AS open_count,
            SUM(CASE WHEN status IN ('Closed','Resolved') THEN 1 ELSE 0 END)                 AS closed_count,
            CURRENT_TIMESTAMP
        FROM service_requests
        WHERE is_valid = 1
          AND grievance_date IS NOT NULL
          AND category IS NOT NULL
        GROUP BY DATE(grievance_date), COALESCE(ward_name,'Unknown'), category
    """))
    session.commit()

    agg_count = session.execute(text("SELECT COUNT(*) FROM daily_aggregates")).scalar()
    logger.info("Daily aggregates rebuilt: %d rows", agg_count)
    return agg_count


# ─────────────────────────────────────────────────────────────────────────────
# STEP 6: Save quality results to DB
# ─────────────────────────────────────────────────────────────────────────────
def save_quality_results(session, run_id: int, metrics: list[dict]) -> None:
    for m in metrics:
        qr = DataQualityResult(
            ingestion_run_id=run_id,
            check_name=m["check_name"],
            total_checked=m["total_checked"],
            passed=m["passed"],
            failed=m["failed"],
            failure_rate=m["failure_rate"],
            details=m.get("details"),
        )
        session.add(qr)
    session.commit()
    logger.info("Saved %d quality check results", len(metrics))


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
def main():
    # ── Pretty header ─────────────────────────────────────────────────────
    sep = "=" * 64
    print(f"\n{sep}")
    print("  India Civic Monitor — BBMP Data Ingestion Pipeline")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(sep)

    # ─ Ensure tables exist ───────────────────────────────────────────────
    logger.info("Initialising database ...")
    init_db()

    # ── Discover source files ─────────────────────────────────────────────
    files = discover_files(DATASET_DIR)
    file_names = [f.name for f in files]

    # ── Create an IngestionRun record ─────────────────────────────────────
    run_uuid  = str(uuid.uuid4())
    cutoff    = datetime.now()
    counters  = {"read": 0, "inserted": 0, "skipped": 0, "rejected": 0, "duplicates": 0}
    all_quality_metrics: list[dict] = []

    session = SessionLocal()

    run = IngestionRun(
        run_uuid    = run_uuid,
        started_at  = cutoff,
        status      = RunStatus.RUNNING,
        source_files= json.dumps(file_names),
    )
    session.add(run)
    session.commit()
    run_id = run.id
    logger.info("Ingestion run started: id=%d  uuid=%s", run_id, run_uuid)

    try:
        # ── Process each file ─────────────────────────────────────────────
        for i, fp in enumerate(files, 1):
            print(f"\n[{i}/{len(files)}] {fp.name}")
            process_file(fp, run_id, session, cutoff, counters, all_quality_metrics)

        # ── Rebuild aggregates ────────────────────────────────────────────
        print("\n[Aggregates] Rebuilding daily_aggregates ...")
        agg_count = rebuild_daily_aggregates(session)

        # ── Save quality results ──────────────────────────────────────────
        print("[Quality]    Saving data-quality metrics ...")
        save_quality_results(session, run_id, all_quality_metrics)

        # ── Update run record to SUCCESS ──────────────────────────────────
        run.status          = RunStatus.SUCCESS
        run.completed_at    = datetime.now()
        run.total_read      = counters["read"]
        run.total_inserted  = counters["inserted"]
        run.total_skipped   = counters["skipped"]
        run.total_rejected  = counters["rejected"]
        run.total_duplicates= counters["duplicates"]
        session.commit()

        # ── Final report ──────────────────────────────────────────────────
        elapsed = (run.completed_at - cutoff).total_seconds()
        print(f"\n{sep}")
        print("  INGESTION COMPLETE")
        print(sep)
        print(f"  Status          : {run.status}")
        print(f"  Duration        : {elapsed:.1f} seconds")
        print(f"  Files processed : {len(files)}")
        print(f"  Records read    : {counters['read']:>10,}")
        print(f"  Records inserted: {counters['inserted']:>10,}")
        print(f"  Records skipped : {counters['skipped']:>10,}  (already in DB — safe re-run)")
        print(f"  Records rejected: {counters['rejected']:>10,}  (failed validation)")
        print(f"  Daily agg rows  : {agg_count:>10,}")
        print()

        if counters["read"] > 0:
            pct_inserted = counters["inserted"] / counters["read"] * 100
            pct_skipped  = counters["skipped"]  / counters["read"] * 100
            pct_rejected = counters["rejected"] / counters["read"] * 100
            print(f"  Insert rate     : {pct_inserted:.1f}%")
            print(f"  Skip rate       : {pct_skipped:.1f}%")
            print(f"  Rejection rate  : {pct_rejected:.1f}%")

        print()
        print("  Data Quality Checks:")
        for m in sorted(all_quality_metrics, key=lambda x: x["check_name"]):
            flag = "  ⚠" if m["failure_rate"] > 5 else "   "
            print(
                f"{flag}  {m['check_name']:<35s}"
                f"  failed={m['failed']:>8,}  ({m['failure_rate']:.2f}%)"
            )

        print(f"\n{sep}")
        print("  ✓ Run database/verify_db.py to query the loaded data.")
        print(f"{sep}\n")

    except Exception as exc:
        logger.exception("Ingestion failed: %s", exc)
        run.status        = RunStatus.FAILED
        run.completed_at  = datetime.now()
        run.error_message = str(exc)
        run.total_read    = counters["read"]
        run.total_inserted= counters["inserted"]
        run.total_rejected= counters["rejected"]
        session.commit()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
