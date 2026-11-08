"""
api/routes/requests.py
======================
Paginated service requests query endpoint.
Privacy preserved: excludes staff names and staff remarks.
"""

import math
from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from database.database import get_db
from api.schemas import PaginatedRequestsResponse, ServiceRequestItem

router = APIRouter(prefix="/api", tags=["Requests"])


@router.get("/requests", response_model=PaginatedRequestsResponse)
def get_service_requests(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=200, description="Items per page"),
    ward_name: Optional[str] = Query(None, description="Filter by ward name"),
    category: Optional[str] = Query(None, description="Filter by complaint category"),
    status: Optional[str] = Query(None, description="Filter by grievance status"),
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
):
    offset = (page - 1) * limit
    where_clauses = ["is_valid = 1"]
    params = {"limit": limit, "offset": offset}

    if ward_name:
        where_clauses.append("ward_name = :ward_name")
        params["ward_name"] = ward_name
    if category:
        where_clauses.append("category = :category")
        params["category"] = category
    if status:
        where_clauses.append("status = :status")
        params["status"] = status
    if start_date:
        where_clauses.append("DATE(grievance_date) >= :start_date")
        params["start_date"] = start_date.isoformat()
    if end_date:
        where_clauses.append("DATE(grievance_date) <= :end_date")
        params["end_date"] = end_date.isoformat()

    where_sql = " AND ".join(where_clauses)

    count_sql = f"SELECT COUNT(*) FROM service_requests WHERE {where_sql}"
    total = db.execute(text(count_sql), params).scalar() or 0

    items_sql = f"""
        SELECT id, complaint_id, category, sub_category, grievance_date, ward_name, status
        FROM service_requests
        WHERE {where_sql}
        ORDER BY grievance_date DESC
        LIMIT :limit OFFSET :offset
    """
    rows = db.execute(text(items_sql), params).mappings().fetchall()

    items = [ServiceRequestItem.model_validate(r) for r in rows]
    total_pages = math.ceil(total / limit) if total > 0 else 0

    return PaginatedRequestsResponse(
        total=total,
        page=page,
        limit=limit,
        total_pages=total_pages,
        items=items,
    )
