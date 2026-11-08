"""
api/routes/data_quality.py
==========================
Data Quality monitoring and ingestion run audit endpoints.
"""

from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from database.database import get_db
from api.schemas import QualityCheckItem, IngestionRunItem

router = APIRouter(prefix="/api", tags=["Data Quality"])


@router.get("/data-quality", response_model=List[QualityCheckItem])
def get_data_quality_metrics(db: Session = Depends(get_db)):
    # Get the latest run's quality results
    latest_run_id = db.execute(text("SELECT id FROM ingestion_runs ORDER BY started_at DESC LIMIT 1")).scalar()
    if not latest_run_id:
        return []

    query = text("""
        SELECT check_name, total_checked, passed, failed, failure_rate, details
        FROM data_quality_results
        WHERE ingestion_run_id = :run_id
        ORDER BY check_name ASC
    """)
    rows = db.execute(query, {"run_id": latest_run_id}).mappings().fetchall()

    return [
        QualityCheckItem(
            check_name=r["check_name"],
            total_checked=r["total_checked"],
            passed=r["passed"],
            failed=r["failed"],
            failure_rate=r["failure_rate"],
            details=r.get("details"),
        )
        for r in rows
    ]


@router.get("/ingestion-runs", response_model=List[IngestionRunItem])
def get_ingestion_runs(db: Session = Depends(get_db)):
    query = text("""
        SELECT id, run_uuid, started_at, completed_at, status, total_read, total_inserted, total_skipped, total_rejected
        FROM ingestion_runs
        ORDER BY started_at DESC
        LIMIT 20
    """)
    rows = db.execute(query).mappings().fetchall()
    return [
        IngestionRunItem(
            id=r["id"],
            run_uuid=r["run_uuid"],
            started_at=r["started_at"],
            completed_at=r["completed_at"],
            status=r["status"],
            total_read=r["total_read"],
            total_inserted=r["total_inserted"],
            total_skipped=r["total_skipped"],
            total_rejected=r["total_rejected"],
        )
        for r in rows
    ]
