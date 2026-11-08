"""
api/routes/metadata.py
======================
Metadata and available filter options for the dataset.
"""

from datetime import datetime, date
from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from database.database import get_db
from api.schemas import MetadataResponse, FilterOptionsResponse

router = APIRouter(prefix="/api", tags=["Metadata"])


@router.get("/metadata", response_model=MetadataResponse)
def get_metadata(db: Session = Depends(get_db)):
    # 1. Total records, wards, categories, min date, max date
    stats_query = text("""
        SELECT
            COUNT(*) AS total_records,
            MIN(DATE(grievance_date)) AS min_date,
            MAX(DATE(grievance_date)) AS max_date
        FROM service_requests
        WHERE is_valid = 1
    """)
    stats_row = db.execute(stats_query).mappings().first()

    wards_count = db.execute(text("SELECT COUNT(DISTINCT ward_name) FROM daily_aggregates")).scalar() or 0
    categories_count = db.execute(text("SELECT COUNT(DISTINCT category) FROM daily_aggregates")).scalar() or 0

    last_run = db.execute(text("""
        SELECT completed_at, started_at
        FROM ingestion_runs
        WHERE status = 'success'
        ORDER BY started_at DESC
        LIMIT 1
    """)).mappings().first()

    last_ingestion_time = last_run["completed_at"] if last_run and last_run["completed_at"] else (last_run["started_at"] if last_run else None)

    min_d_str = stats_row["min_date"] if stats_row else None
    max_d_str = stats_row["max_date"] if stats_row else None

    days_span = 0
    if min_d_str and max_d_str:
        d1 = datetime.strptime(min_d_str, "%Y-%m-%d").date()
        d2 = datetime.strptime(max_d_str, "%Y-%m-%d").date()
        days_span = (d2 - d1).days

    return MetadataResponse(
        total_records=stats_row["total_records"] if stats_row else 0,
        total_wards=wards_count,
        total_categories=categories_count,
        earliest_record=min_d_str,
        latest_record=max_d_str,
        days_span=days_span,
        freshness_status="HISTORICAL SNAPSHOT",
        last_ingestion_time=last_ingestion_time,
    )


@router.get("/filters", response_model=FilterOptionsResponse)
def get_filter_options(db: Session = Depends(get_db)):
    cats = [r[0] for r in db.execute(text("SELECT DISTINCT category FROM daily_aggregates ORDER BY category")).fetchall() if r[0]]
    wards = [r[0] for r in db.execute(text("SELECT DISTINCT ward_name FROM daily_aggregates ORDER BY ward_name")).fetchall() if r[0]]
    statuses = [r[0] for r in db.execute(text("SELECT DISTINCT status FROM service_requests WHERE status IS NOT NULL ORDER BY status")).fetchall()]

    min_max = db.execute(text("SELECT MIN(agg_date), MAX(agg_date) FROM daily_aggregates")).first()

    return FilterOptionsResponse(
        categories=cats,
        wards=wards,
        statuses=statuses,
        min_date=str(min_max[0]) if min_max and min_max[0] else None,
        max_date=str(min_max[1]) if min_max and min_max[1] else None,
    )
