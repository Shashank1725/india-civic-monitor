"""
database/models.py
==================
SQLAlchemy ORM models for the India Civic Disruption Monitoring System.

Design decisions:
- Uses SQLAlchemy 2.x declarative style with type annotations.
- Works with SQLite (dev) and PostgreSQL (production) — only the
  DATABASE_URL in .env needs to change.
- Every field is annotated with its SOURCE (original CSV column name)
  or GENERATED (computed by the pipeline), so traceability is clear.
- Staff Remarks and Staff Name are stored but intentionally excluded
  from all public-facing API responses to limit PII exposure.
"""

from __future__ import annotations

import enum
from datetime import datetime, date
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func


# ─────────────────────────────────────────────────────────────────────────────
# Base class — all models inherit from this
# ─────────────────────────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    pass


# ─────────────────────────────────────────────────────────────────────────────
# Enum: ingestion run status
# ─────────────────────────────────────────────────────────────────────────────
class RunStatus(str, enum.Enum):
    RUNNING = "running"
    SUCCESS = "success"
    FAILED  = "failed"


# ─────────────────────────────────────────────────────────────────────────────
# TABLE 1: ingestion_runs
# Tracks every time we run the data pipeline.
# ─────────────────────────────────────────────────────────────────────────────
class IngestionRun(Base):
    """
    One row per pipeline execution.
    Lets us answer: when was data last loaded, how many records, any errors?
    """
    __tablename__ = "ingestion_runs"

    # GENERATED fields
    id           : Mapped[int]           = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_uuid     : Mapped[str]           = mapped_column(String(36), unique=True, nullable=False, comment="UUID assigned at pipeline start")
    started_at   : Mapped[datetime]      = mapped_column(DateTime, nullable=False, default=func.now())
    completed_at : Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    status       : Mapped[str]           = mapped_column(String(20), nullable=False, default=RunStatus.RUNNING)
    source_files : Mapped[Optional[str]] = mapped_column(Text, nullable=True,  comment="JSON list of CSV filenames processed")
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Counts — populated at end of run
    total_read      : Mapped[int] = mapped_column(Integer, default=0)
    total_inserted  : Mapped[int] = mapped_column(Integer, default=0)
    total_updated   : Mapped[int] = mapped_column(Integer, default=0)
    total_skipped   : Mapped[int] = mapped_column(Integer, default=0)
    total_rejected  : Mapped[int] = mapped_column(Integer, default=0)
    total_duplicates: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    service_requests  : Mapped[list["ServiceRequest"]]   = relationship(back_populates="ingestion_run", lazy="noload")
    quality_results   : Mapped[list["DataQualityResult"]]= relationship(back_populates="ingestion_run", lazy="noload")

    def __repr__(self) -> str:
        return f"<IngestionRun id={self.id} status={self.status} inserted={self.total_inserted}>"


# ─────────────────────────────────────────────────────────────────────────────
# TABLE 2: service_requests
# Core table — one row per BBMP citizen grievance.
# ─────────────────────────────────────────────────────────────────────────────
class ServiceRequest(Base):
    """
    Stores a single BBMP citizen grievance/complaint.

    SOURCE columns (mapped directly from CSV):
      complaint_id    ← "Complaint ID"      (integer, unique identifier)
      category        ← "Category"
      sub_category    ← "Sub Category"
      grievance_date  ← "Grievance Date"
      ward_name       ← "Ward Name"
      status          ← "Grievance Status"
      staff_remarks   ← "Staff Remarks"     (excluded from API)
      staff_name      ← "Staff Name"        (excluded from API — semi-PII)

    GENERATED columns (added by the pipeline):
      id              — auto-increment surrogate PK
      ingestion_run_id— FK to the run that inserted this record
      is_valid        — False if the record failed validation
      rejection_reason— why it was rejected, if is_valid=False
      created_at      — when the row was first inserted
      updated_at      — when the row was last updated
    """
    __tablename__ = "service_requests"

    # GENERATED
    id               : Mapped[int]  = mapped_column(Integer, primary_key=True, autoincrement=True)
    ingestion_run_id : Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("ingestion_runs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    is_valid         : Mapped[bool]           = mapped_column(Boolean, default=True, nullable=False)
    rejection_reason : Mapped[Optional[str]]  = mapped_column(Text,    nullable=True)
    created_at       : Mapped[datetime]       = mapped_column(DateTime, default=func.now(), nullable=False)
    updated_at       : Mapped[datetime]       = mapped_column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # SOURCE — from CSV
    complaint_id   : Mapped[int]            = mapped_column(BigInteger, unique=True, nullable=False,
                                               comment="SOURCE: Complaint ID — primary deduplication key")
    category       : Mapped[str]            = mapped_column(String(120), nullable=False, index=True,
                                               comment="SOURCE: Category")
    sub_category   : Mapped[Optional[str]]  = mapped_column(String(180), nullable=True,
                                               comment="SOURCE: Sub Category")
    grievance_date : Mapped[datetime]       = mapped_column(DateTime, nullable=False, index=True,
                                               comment="SOURCE: Grievance Date")
    ward_name      : Mapped[Optional[str]]  = mapped_column(String(120), nullable=True, index=True,
                                               comment="SOURCE: Ward Name")
    status         : Mapped[Optional[str]]  = mapped_column(String(40),  nullable=True, index=True,
                                               comment="SOURCE: Grievance Status")

    # Stored but NOT returned by any public API endpoint
    staff_remarks  : Mapped[Optional[str]]  = mapped_column(Text,       nullable=True,
                                               comment="SOURCE: Staff Remarks — internal, not exposed via API")
    staff_name     : Mapped[Optional[str]]  = mapped_column(String(120), nullable=True,
                                               comment="SOURCE: Staff Name — semi-PII, not exposed via API")

    # Relationships
    ingestion_run : Mapped[Optional["IngestionRun"]] = relationship(back_populates="service_requests")

    # Composite indexes for the most common query patterns
    __table_args__ = (
        Index("ix_sr_ward_date",     "ward_name",  "grievance_date"),
        Index("ix_sr_cat_date",      "category",   "grievance_date"),
        Index("ix_sr_ward_cat",      "ward_name",  "category"),
        Index("ix_sr_ward_cat_date", "ward_name",  "category", "grievance_date"),
        Index("ix_sr_status",        "status"),
        Index("ix_sr_is_valid",      "is_valid"),
    )

    def __repr__(self) -> str:
        return f"<ServiceRequest complaint_id={self.complaint_id} ward={self.ward_name} cat={self.category}>"


# ─────────────────────────────────────────────────────────────────────────────
# TABLE 3: data_quality_results
# One row per validation check per ingestion run.
# ─────────────────────────────────────────────────────────────────────────────
class DataQualityResult(Base):
    """
    Stores the outcome of each validation check performed during ingestion.
    Allows the dashboard to show "X% of records missed ward information" etc.

    Check examples:
      - "missing_ward"          → records with null/empty ward_name
      - "missing_status"        → records with null status
      - "duplicate_ids"         → complaint_ids seen more than once
      - "future_dated"          → grievance_date > ingestion time
      - "invalid_date_format"   → dates that could not be parsed
    """
    __tablename__ = "data_quality_results"

    # GENERATED
    id               : Mapped[int]      = mapped_column(Integer, primary_key=True, autoincrement=True)
    ingestion_run_id : Mapped[int]      = mapped_column(
        Integer, ForeignKey("ingestion_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at       : Mapped[datetime] = mapped_column(DateTime, default=func.now())

    # Check details
    check_name     : Mapped[str]            = mapped_column(String(80),  nullable=False)
    total_checked  : Mapped[int]            = mapped_column(Integer,     default=0)
    passed         : Mapped[int]            = mapped_column(Integer,     default=0)
    failed         : Mapped[int]            = mapped_column(Integer,     default=0)
    failure_rate   : Mapped[float]          = mapped_column(Float,       default=0.0, comment="failed / total_checked * 100")
    details        : Mapped[Optional[str]]  = mapped_column(Text,        nullable=True, comment="JSON — extra context or sample bad values")

    # Relationship
    ingestion_run : Mapped["IngestionRun"] = relationship(back_populates="quality_results")

    def __repr__(self) -> str:
        return f"<DataQualityResult check={self.check_name} failed={self.failed}/{self.total_checked}>"


# ─────────────────────────────────────────────────────────────────────────────
# TABLE 4: daily_aggregates
# Pre-computed complaint counts per (date, ward, category).
# Rebuilt after each ingestion. Powers fast API queries and charts.
# ─────────────────────────────────────────────────────────────────────────────
class DailyAggregate(Base):
    """
    Stores pre-aggregated complaint counts by (date, ward_name, category).
    This avoids expensive GROUP BY queries on the full 766K-row table at
    every API request.

    Rebuilt from scratch (DELETE + INSERT) after each successful ingestion.
    Also stores open/closed sub-counts for the status distribution chart.

    All fields are GENERATED by the analytics pipeline.
    """
    __tablename__ = "daily_aggregates"

    id             : Mapped[int]  = mapped_column(Integer, primary_key=True, autoincrement=True)
    agg_date       : Mapped[date] = mapped_column(Date,    nullable=False, index=True)
    ward_name      : Mapped[str]  = mapped_column(String(120), nullable=False, index=True)
    category       : Mapped[str]  = mapped_column(String(120), nullable=False, index=True)
    complaint_count: Mapped[int]  = mapped_column(Integer, nullable=False, default=0)
    open_count     : Mapped[int]  = mapped_column(Integer, nullable=False, default=0,
                                     comment="Registered + ReOpen + In Progress")
    closed_count   : Mapped[int]  = mapped_column(Integer, nullable=False, default=0,
                                     comment="Closed + Resolved")
    last_updated   : Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("agg_date", "ward_name", "category", name="uq_daily_agg"),
        Index("ix_da_date_ward",     "agg_date", "ward_name"),
        Index("ix_da_date_cat",      "agg_date", "category"),
        Index("ix_da_ward_cat",      "ward_name", "category"),
    )

    def __repr__(self) -> str:
        return (
            f"<DailyAggregate date={self.agg_date} ward={self.ward_name} "
            f"cat={self.category} count={self.complaint_count}>"
        )
