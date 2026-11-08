"""
api/routes/anomalies.py
=======================
Endpoints for historical weekday anomaly detection.
"""

from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from database.database import get_db, engine
from analytics.anomalies import AnomalyDetector
from api.schemas import AnomalyItem

router = APIRouter(prefix="/api/anomalies", tags=["Anomalies"])
detector = AnomalyDetector(db_engine=engine)


@router.get("", response_model=List[AnomalyItem])
def get_anomalies(
    target_date: Optional[date] = Query(None, description="Date to evaluate (defaults to latest recorded date)"),
    lookback_weeks: int = Query(8, ge=2, le=24, description="Lookback window in weeks"),
    z_threshold: float = Query(2.5, ge=1.0, le=10.0, description="Statistical Z-score threshold"),
    min_diff: int = Query(3, ge=1, le=50, description="Minimum absolute complaint increase"),
    category: Optional[str] = Query(None, description="Filter by category"),
    ward_name: Optional[str] = Query(None, description="Filter by ward name"),
    anomaly_only: bool = Query(True, description="Return only flagged anomalies"),
    db: Session = Depends(get_db),
):
    if not target_date:
        latest = db.execute(text("SELECT MAX(agg_date) FROM daily_aggregates")).scalar()
        if not latest:
            return []
        if isinstance(latest, str):
            target_date = date.fromisoformat(latest)
        else:
            target_date = latest

    results = detector.get_anomalies_for_date(
        target_date=target_date,
        lookback_weeks=lookback_weeks,
        z_threshold=z_threshold,
        min_abs_increase=min_diff,
        category_filter=category,
        ward_filter=ward_name,
    )

    if anomaly_only:
        results = [r for r in results if r.is_anomaly]

    # Sort descending by z_score
    results.sort(key=lambda x: x.z_score, reverse=True)

    return [AnomalyItem(**r.to_dict()) for r in results]
