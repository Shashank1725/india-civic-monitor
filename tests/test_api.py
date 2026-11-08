"""
tests/test_api.py
=================
Automated tests for FastAPI endpoints against the active database.
"""

import pytest
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    content_type = response.headers.get("content-type", "")
    if "application/json" in content_type:
        # Frontend not built yet — API info payload
        data = response.json()
        assert data["project"] == "India Civic Disruption Monitoring System"
    else:
        # Frontend built — the React dashboard is served
        assert "text/html" in content_type
        assert "<div id=\"root\"" in response.text or "<!doctype html" in response.text.lower()


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["ok", "degraded"]


def test_metadata():
    response = client.get("/api/metadata")
    assert response.status_code == 200
    data = response.json()
    assert data["total_records"] >= 766000
    assert data["total_wards"] >= 190
    assert data["freshness_status"] == "HISTORICAL SNAPSHOT"


def test_filters():
    response = client.get("/api/filters")
    assert response.status_code == 200
    data = response.json()
    assert len(data["categories"]) >= 30
    assert len(data["wards"]) >= 190
    assert "Electrical" in data["categories"]


def test_requests_pagination_and_privacy():
    response = client.get("/api/requests?page=1&limit=10")
    assert response.status_code == 200
    data = response.json()
    assert data["page"] == 1
    assert data["limit"] == 10
    assert len(data["items"]) == 10

    # Privacy verification: neither staff_remarks nor staff_name must be present!
    first_item = data["items"][0]
    assert "staff_remarks" not in first_item
    assert "staff_name" not in first_item
    assert "complaint_id" in first_item
    assert "category" in first_item
    assert "ward_name" in first_item


def test_areas_endpoint():
    response = client.get("/api/areas")
    assert response.status_code == 200
    areas = response.json()
    assert len(areas) >= 190
    top_area = areas[0]
    assert "ward_name" in top_area
    assert top_area["total_complaints"] > 0


def test_area_drilldown():
    # Use one of the known high volume wards: Horamavu
    response = client.get("/api/areas/Horamavu")
    assert response.status_code == 200
    data = response.json()
    assert data["ward_name"] == "Horamavu"
    assert data["total_complaints"] > 10000
    assert len(data["category_breakdown"]) > 0
    assert len(data["recent_trend"]) > 0


def test_aggregates_daily():
    response = client.get("/api/aggregates/daily?start_date=2025-06-01&end_date=2025-06-15")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert "date" in data[0]
    assert "complaint_count" in data[0]


def test_aggregates_categories():
    response = client.get("/api/aggregates/categories")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 30
    assert data[0]["category"] == "Electrical"


def test_anomalies_endpoint():
    response = client.get("/api/anomalies?target_date=2025-06-16&anomaly_only=true")
    assert response.status_code == 200
    anomalies = response.json()
    assert isinstance(anomalies, list)
    if len(anomalies) > 0:
        a = anomalies[0]
        assert a["is_anomaly"] is True
        assert "z_score" in a
        assert "explanation" in a


def test_data_quality_endpoint():
    response = client.get("/api/data-quality")
    assert response.status_code == 200
    checks = response.json()
    assert len(checks) >= 5
    check_names = [c["check_name"] for c in checks]
    assert "missing_complaint_id" in check_names
    assert "missing_ward" in check_names


def test_ingestion_runs_endpoint():
    response = client.get("/api/ingestion-runs")
    assert response.status_code == 200
    runs = response.json()
    assert len(runs) >= 1
    assert runs[0]["status"] == "success"
