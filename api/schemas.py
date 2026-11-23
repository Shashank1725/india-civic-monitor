"""
api/schemas.py
==============
Pydantic schemas for the India Civic Disruption Monitoring System API.
Strict validation and clean serialized responses without PII.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ── Health & Metadata ────────────────────────────────────────────────────────
class HealthResponse(BaseModel):
    status: str
    database: str
    timestamp: datetime
    # True once the database contains data (snapshot restored or ingested).
    data_ready: bool = True
    # Background bootstrap lifecycle: starting/downloading/ingesting/ready/failed
    bootstrap_state: str = "ready"
    bootstrap_detail: str = ""


class MetadataResponse(BaseModel):
    total_records: int
    total_wards: int
    total_categories: int
    earliest_record: Optional[str]
    latest_record: Optional[str]
    days_span: int
    freshness_status: str  # "HISTORICAL SNAPSHOT", "STALE", "FRESH"
    last_ingestion_time: Optional[datetime]


class FilterOptionsResponse(BaseModel):
    categories: List[str]
    wards: List[str]
    statuses: List[str]
    min_date: Optional[str]
    max_date: Optional[str]


# ── Service Requests (Sanitized — No PII) ──────────────────────────────────
class ServiceRequestItem(BaseModel):
    id: int
    complaint_id: int
    category: str
    sub_category: Optional[str]
    grievance_date: datetime
    ward_name: Optional[str]
    status: Optional[str]

    class Config:
        from_attributes = True


class PaginatedRequestsResponse(BaseModel):
    total: int
    page: int
    limit: int
    total_pages: int
    items: List[ServiceRequestItem]


# ── Areas / Wards ────────────────────────────────────────────────────────────
class AreaSummary(BaseModel):
    ward_name: str
    total_complaints: int
    open_complaints: int
    closed_complaints: int
    top_category: Optional[str] = None
    latest_activity_date: Optional[str] = None


class AreaDetailResponse(BaseModel):
    ward_name: str
    total_complaints: int
    open_complaints: int
    closed_complaints: int
    category_breakdown: List[Dict[str, Any]]
    recent_trend: List[Dict[str, Any]]


# ── Aggregates / Time Series ─────────────────────────────────────────────────
class DailyAggregateItem(BaseModel):
    date: str
    complaint_count: int
    open_count: int
    closed_count: int


class CategoryAggregateItem(BaseModel):
    category: str
    complaint_count: int
    percentage: float


# ── Anomalies ────────────────────────────────────────────────────────────────
class AnomalyItem(BaseModel):
    date: str
    ward_name: str
    category: str
    current_count: int
    baseline_mean: float
    baseline_std: float
    sample_size: int
    z_score: float
    severity: str
    is_anomaly: bool
    explanation: str


# ── Data Quality & Ingestion Runs ────────────────────────────────────────────
class QualityCheckItem(BaseModel):
    check_name: str
    total_checked: int
    passed: int
    failed: int
    failure_rate: float
    details: Optional[str]


class IngestionRunItem(BaseModel):
    id: int
    run_uuid: str
    started_at: datetime
    completed_at: Optional[datetime]
    status: str
    total_read: int
    total_inserted: int
    total_skipped: int
    total_rejected: int
