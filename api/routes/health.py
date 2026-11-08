"""
api/routes/health.py
====================
Health check endpoint.
"""

from datetime import datetime
from fastapi import APIRouter
from database.database import health_check
from database.bootstrap import bootstrap_status, data_ready
from api.schemas import HealthResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
def get_health():
    db_status = health_check()
    status = bootstrap_status()
    return HealthResponse(
        status="ok" if db_status.get("status") == "ok" else "degraded",
        database=db_status.get("status", "unknown"),
        timestamp=datetime.now(),
        data_ready=data_ready(),
        bootstrap_state=status.get("state", "unknown"),
    )
