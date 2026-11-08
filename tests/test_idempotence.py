"""
tests/test_idempotence.py
=========================
Verifies that database constraints prevent duplicates and that running
ingestion repeatedly is completely idempotent.
"""

from datetime import datetime
import pytest
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import sessionmaker

from database.models import Base, ServiceRequest, IngestionRun, RunStatus
from ingestion.ingest import bulk_insert_ignore


@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_bulk_insert_deduplication(test_db):
    now = datetime.now()
    records = [
        {
            "complaint_id": 999001,
            "category": "Electrical",
            "sub_category": "Street Light Not Working",
            "grievance_date": now,
            "ward_name": "Horamavu",
            "status": "Closed",
            "staff_remarks": "Fixed",
            "staff_name": "Officer X",
            "ingestion_run_id": None,
            "is_valid": True,
            "rejection_reason": None,
            "created_at": now,
            "updated_at": now,
        },
        {
            "complaint_id": 999002,
            "category": "Road Maintenance",
            "sub_category": "Potholes",
            "grievance_date": now,
            "ward_name": "Bellandur",
            "status": "Registered",
            "staff_remarks": "Assigned",
            "staff_name": "Officer Y",
            "ingestion_run_id": None,
            "is_valid": True,
            "rejection_reason": None,
            "created_at": now,
            "updated_at": now,
        },
    ]

    # First insert: 2 inserted, 0 skipped
    ins1, skip1 = bulk_insert_ignore(test_db, records)
    test_db.commit()
    assert ins1 == 2
    assert skip1 == 0

    # Verify count in DB
    total = test_db.scalar(select(func.count(ServiceRequest.id)))
    assert total == 2

    # Second insert with same records (simulating rerun)
    ins2, skip2 = bulk_insert_ignore(test_db, records)
    test_db.commit()
    assert ins2 == 0
    assert skip2 == 2

    # Total in DB must remain exactly 2
    total_after = test_db.scalar(select(func.count(ServiceRequest.id)))
    assert total_after == 2
