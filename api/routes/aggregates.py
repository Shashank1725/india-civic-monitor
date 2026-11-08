"""
api/routes/aggregates.py
========================
Aggregated time series and category distribution endpoints.
"""

from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from database.database import get_db
from api.schemas import DailyAggregateItem, CategoryAggregateItem

router = APIRouter(prefix="/api/aggregates", tags=["Aggregates"])


@router.get("/daily", response_model=List[DailyAggregateItem])
def get_daily_aggregates(
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    ward_name: Optional[str] = Query(None, description="Filter by ward name"),
    category: Optional[str] = Query(None, description="Filter by category"),
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
    if ward_name:
        where_clauses.append("ward_name = :ward_name")
        params["ward_name"] = ward_name
    if category:
        where_clauses.append("category = :category")
        params["category"] = category

    where_sql = " AND ".join(where_clauses)

    query = f"""
        SELECT
            agg_date,
            SUM(complaint_count) AS complaint_count,
            SUM(open_count) AS open_count,
            SUM(closed_count) AS closed_count
        FROM daily_aggregates
        WHERE {where_sql}
        GROUP BY agg_date
        ORDER BY agg_date ASC
    """
    rows = db.execute(text(query), params).mappings().fetchall()

    return [
        DailyAggregateItem(
            date=str(r["agg_date"]),
            complaint_count=r["complaint_count"],
            open_count=r["open_count"],
            closed_count=r["closed_count"],
        )
        for r in rows
    ]


@router.get("/categories", response_model=List[CategoryAggregateItem])
def get_category_aggregates(
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    ward_name: Optional[str] = Query(None, description="Filter by ward name"),
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
    if ward_name:
        where_clauses.append("ward_name = :ward_name")
        params["ward_name"] = ward_name

    where_sql = " AND ".join(where_clauses)

    query = f"""
        SELECT
            category,
            SUM(complaint_count) AS complaint_count
        FROM daily_aggregates
        WHERE {where_sql}
        GROUP BY category
        ORDER BY complaint_count DESC
    """
    rows = db.execute(text(query), params).mappings().fetchall()
    total_complaints = sum(r["complaint_count"] for r in rows) if rows else 0

    return [
        CategoryAggregateItem(
            category=r["category"],
            complaint_count=r["complaint_count"],
            percentage=round((r["complaint_count"] / total_complaints * 100), 2) if total_complaints else 0.0,
        )
        for r in rows
    ]
