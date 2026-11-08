"""
api/routes/areas.py
===================
Ward / Area aggregated analytics and drill-down endpoints.
"""

from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from database.database import get_db
from api.schemas import AreaSummary, AreaDetailResponse

router = APIRouter(prefix="/api/areas", tags=["Areas"])


@router.get("", response_model=List[AreaSummary])
def get_areas_summary(
    start_date: Optional[date] = Query(None, description="Start date filter"),
    end_date: Optional[date] = Query(None, description="End date filter"),
    category: Optional[str] = Query(None, description="Category filter"),
    db: Session = Depends(get_db),
):
    where_clauses = ["1=1"]
    params = {}

    if start_date:
        where_clauses.append("agg_date >= :start_date")
        params["start_date"] = start_date.isoformat()
    if end_date:
        where_clauses.append("agg_date <= :end_date")
        params["end_date"] = end_date.isoformat()
    if category:
        where_clauses.append("category = :category")
        params["category"] = category

    where_sql = " AND ".join(where_clauses)

    query = f"""
        SELECT
            ward_name,
            SUM(complaint_count) AS total_complaints,
            SUM(open_count) AS open_complaints,
            SUM(closed_count) AS closed_complaints,
            MAX(agg_date) AS latest_activity_date
        FROM daily_aggregates
        WHERE {where_sql}
        GROUP BY ward_name
        ORDER BY total_complaints DESC
    """
    rows = db.execute(text(query), params).mappings().fetchall()

    result = []
    for r in rows:
        result.append(AreaSummary(
            ward_name=r["ward_name"],
            total_complaints=r["total_complaints"],
            open_complaints=r["open_complaints"],
            closed_complaints=r["closed_complaints"],
            top_category=None,
            latest_activity_date=str(r["latest_activity_date"]) if r["latest_activity_date"] else None,
        ))

    return result


@router.get("/{ward_name}", response_model=AreaDetailResponse)
def get_area_detail(
    ward_name: str,
    db: Session = Depends(get_db),
):
    # Total counts for this ward
    totals_query = text("""
        SELECT
            SUM(complaint_count) AS total_complaints,
            SUM(open_count) AS open_complaints,
            SUM(closed_count) AS closed_complaints
        FROM daily_aggregates
        WHERE ward_name = :ward_name
    """)
    totals = db.execute(totals_query, {"ward_name": ward_name}).mappings().first()

    if not totals or not totals["total_complaints"]:
        raise HTTPException(status_code=404, detail=f"Ward '{ward_name}' not found.")

    # Category breakdown
    cat_query = text("""
        SELECT
            category,
            SUM(complaint_count) AS count
        FROM daily_aggregates
        WHERE ward_name = :ward_name
        GROUP BY category
        ORDER BY count DESC
    """)
    cat_rows = db.execute(cat_query, {"ward_name": ward_name}).mappings().fetchall()
    category_breakdown = [{"category": r["category"], "count": r["count"]} for r in cat_rows]

    # Recent daily trend (last 60 recorded days)
    trend_query = text("""
        SELECT
            agg_date,
            SUM(complaint_count) AS count,
            SUM(open_count) AS open_count,
            SUM(closed_count) AS closed_count
        FROM daily_aggregates
        WHERE ward_name = :ward_name
        GROUP BY agg_date
        ORDER BY agg_date DESC
        LIMIT 60
    """)
    trend_rows = db.execute(trend_query, {"ward_name": ward_name}).mappings().fetchall()
    recent_trend = [
        {
            "date": str(r["agg_date"]),
            "count": r["count"],
            "open_count": r["open_count"],
            "closed_count": r["closed_count"],
        }
        for r in reversed(trend_rows)
    ]

    return AreaDetailResponse(
        ward_name=ward_name,
        total_complaints=totals["total_complaints"],
        open_complaints=totals["open_complaints"],
        closed_complaints=totals["closed_complaints"],
        category_breakdown=category_breakdown,
        recent_trend=recent_trend,
    )
