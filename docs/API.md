# REST API Specification

## India Civic Disruption Monitoring System
*Base URL:* `http://127.0.0.1:8000`

---

## 1. System Health & Metadata

### `GET /health`
Returns the operational health of the FastAPI service and database connection.

**Response (200 OK):**
```json
{
  "status": "ok",
  "database": "ok",
  "timestamp": "2026-10-10T16:55:44.611672"
}
```

---

### `GET /api/metadata`
Returns high-level statistics, date spans, and dataset freshness classification.

**Response (200 OK):**
```json
{
  "total_records": 766648,
  "total_wards": 199,
  "total_categories": 19,
  "earliest_record": "2020-01-01",
  "latest_record": "2025-06-19",
  "days_span": 1958,
  "freshness_status": "HISTORICAL SNAPSHOT",
  "last_ingestion_time": "2026-10-10T11:18:58"
}
```

---

### `GET /api/filters`
Returns available filter options for dropdown selectors.

**Response (200 OK):**
```json
{
  "categories": [
    "Solid Waste (Garbage) Related",
    "Electrical",
    "Road Maintenance(Engg)",
    "Forest",
    "Storm Water Drain(SWD)",
    "Health Dept"
  ],
  "wards": ["A Narayanapura", "Adugodi", "Agaram", "Anjanapur", "BTM Layout"],
  "statuses": ["Closed", "Resolved", "Pending", "Under Process"],
  "min_date": "2020-01-01",
  "max_date": "2025-06-19"
}
```

---

## 2. Grievance Records (PII-Sanitized)

### `GET /api/requests`
Returns paginated grievance records with optional filtering. Citizen details and BBMP staff names are withheld.

**Query Parameters:**
- `page` (int, default: 1): Page number
- `limit` (int, default: 50, max: 200): Records per page
- `ward_name` (string, optional): Filter by ward
- `category` (string, optional): Filter by category
- `status` (string, optional): Filter by status
- `start_date` (date string `YYYY-MM-DD`, optional)
- `end_date` (date string `YYYY-MM-DD`, optional)

**Example Request:**
```bash
curl -X GET "http://127.0.0.1:8000/api/requests?ward_name=BTM%20Layout&limit=2"
```

**Response (200 OK):**
```json
{
  "total": 12840,
  "page": 1,
  "limit": 2,
  "pages": 6420,
  "items": [
    {
      "complaint_id": 20096300,
      "grievance_date": "2025-06-19T10:15:00",
      "department": "Solid Waste Management",
      "category": "Solid Waste (Garbage) Related",
      "sub_category": "Garbage Dumping on Vacant Site",
      "ward_no": "176",
      "ward_name": "BTM Layout",
      "status": "Closed"
    }
  ]
}
```

---

## 3. Geospatial & Area Analytics

### `GET /api/areas`
Returns aggregated complaint volume, resolution metrics, and top category for each ward.

**Query Parameters:**
- `start_date` (date string `YYYY-MM-DD`, optional)
- `end_date` (date string `YYYY-MM-DD`, optional)
- `category` (string, optional)

**Response (200 OK):**
```json
[
  {
    "ward_name": "Horamavu",
    "total_complaints": 14210,
    "open_complaints": 215,
    "closed_complaints": 13995,
    "top_category": "Solid Waste (Garbage) Related",
    "latest_activity_date": "2025-06-19"
  }
]
```

---

### `GET /api/areas/{ward_name}`
Returns in-depth analytical drill-down for a specific ward.

**Response (200 OK):**
```json
{
  "ward_name": "BTM Layout",
  "total_complaints": 12840,
  "open_complaints": 184,
  "closed_complaints": 12656,
  "category_breakdown": [
    { "category": "Solid Waste (Garbage) Related", "count": 5420 },
    { "category": "Electrical", "count": 3910 }
  ],
  "recent_trend": [
    { "date": "2025-06-18", "count": 22, "open_count": 2, "closed_count": 20 },
    { "date": "2025-06-19", "count": 28, "open_count": 3, "closed_count": 25 }
  ]
}
```

---

## 4. Time-Series & Aggregations

### `GET /api/aggregates/daily`
Returns daily aggregated complaint volumes.

**Query Parameters:**
- `start_date` (string `YYYY-MM-DD`, optional)
- `end_date` (string `YYYY-MM-DD`, optional)
- `ward_name` (string, optional)
- `category` (string, optional)

**Response (200 OK):**
```json
[
  {
    "date": "2025-06-19",
    "complaint_count": 1240,
    "open_count": 85,
    "closed_count": 1155
  }
]
```

---

### `GET /api/aggregates/categories`
Returns volume distribution across all grievance categories.

**Response (200 OK):**
```json
[
  {
    "category": "Solid Waste (Garbage) Related",
    "complaint_count": 284520,
    "percentage": 37.1
  },
  {
    "category": "Electrical",
    "complaint_count": 210840,
    "percentage": 27.5
  }
]
```

---

## 5. Statistical Anomaly Surveillance

### `GET /api/anomalies`
Evaluates complaint counts against historical same-weekday rolling baselines and flags unusual activity spikes.

**Query Parameters:**
- `target_date` (string `YYYY-MM-DD`, optional; defaults to latest available date)
- `category` (string, optional)
- `ward_name` (string, optional)
- `anomaly_only` (boolean, default: false)

**Response (200 OK):**
```json
[
  {
    "date": "2025-06-16",
    "ward_name": "Bapuji Nagar",
    "category": "Electrical",
    "current_count": 24,
    "baseline_mean": 0.8,
    "baseline_std": 0.7,
    "sample_size": 8,
    "z_score": 32.88,
    "severity": "CRITICAL",
    "is_anomaly": true,
    "explanation": "Unusual spike on Monday (2025-06-16): 24 Electrical complaints reported in Bapuji Nagar, compared to a historical Monday baseline of 0.8 (std: 0.7, N=8). Anomaly score: +32.88σ."
  }
]
```

---

## 6. Data Quality & Pipeline Auditing

### `GET /api/data-quality`
Returns the status of all automated schema validation rules.

**Response (200 OK):**
```json
[
  {
    "check_name": "missing_complaint_id",
    "total_checked": 766648,
    "passed": 766648,
    "failed": 0,
    "failure_rate": 0.0,
    "details": "Unique primary key check"
  },
  {
    "check_name": "missing_ward",
    "total_checked": 766648,
    "passed": 766648,
    "failed": 0,
    "failure_rate": 0.0,
    "details": "Ward name completeness check"
  }
]
```

---

### `GET /api/ingestion-runs`
Returns the execution history of pipeline ingestion runs.

**Response (200 OK):**
```json
[
  {
    "id": 1,
    "run_uuid": "2e4053f9-32e8-476f-b197-0792d9541506",
    "started_at": "2026-10-10T16:48:58",
    "completed_at": "2026-10-10T16:54:20",
    "status": "SUCCESS",
    "total_read": 766648,
    "total_inserted": 766648,
    "total_skipped": 0,
    "total_rejected": 0
  }
]
```
