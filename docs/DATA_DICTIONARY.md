# Data Dictionary & Schema Specification

## India Civic Disruption Monitoring System
*Bruhat Bengaluru Mahanagara Palike (BBMP) Grievances*

---

## 1. Raw Source Dataset (BBMP Grievance CSVs)

The source data consists of municipal citizen grievances recorded through Bengaluru's grievance redressal portal across 6 bulk CSV files (766,648 total records).

| Column in CSV | Inferred Data Type | Nullable | Example Value | Description |
|---|---|---|---|---|
| `Complaint ID` | Integer / String | No | `20096307` | Unique identifier assigned by BBMP portal |
| `Grievance Date` | Date String (ISO) | No | `2025-06-19 14:22:00` | Timestamp when grievance was registered |
| `Department` | String | Yes | `Solid Waste Management` | Responsible municipal department |
| `Category` | String | No | `Solid Waste (Garbage) Related` | Primary classification of the civic issue |
| `Sub Category` | String | Yes | `Garbage Dumping on Vacant Site` | Fine-grained nature of the complaint |
| `Ward No` | String / Integer | Yes | `85` | BBMP ward numerical identifier |
| `Ward Name` | String | No | `Dodda Bidarkallu` | Official name of the municipal ward |
| `Grievance Status` | String | Yes | `Closed`, `Resolved`, `Pending` | Resolution workflow status |
| `Staff Name` | String | Yes | `[Redacted]` | Name of assigned BBMP field officer *(Withheld)* |
| `Staff Remarks` | String | Yes | `Work completed` | Internal officer notes *(Withheld from API)* |

---

## 2. Relational Database Schema (`india_civic_monitor.db`)

### 2.1 Table: `service_requests`
Primary storage for all normalized, validated grievance records.

| Column | SQL Type | Constraints | Description |
|---|---|---|---|
| `id` | `INTEGER` / `BIGINT` | `AUTOINCREMENT` | Internal synthetic sequence key |
| `complaint_id` | `BIGINT` | `UNIQUE`, `NOT NULL`, `INDEXED` | BBMP grievance tracking identifier (Primary natural key) |
| `grievance_date` | `TIMESTAMP` | `NOT NULL`, `INDEXED` | Normalized grievance submission timestamp |
| `department` | `VARCHAR(128)` | `NULLABLE` | Municipal department |
| `category` | `VARCHAR(128)` | `NOT NULL`, `INDEXED` | High-level grievance category |
| `sub_category` | `VARCHAR(256)` | `NULLABLE` | Granular issue classification |
| `ward_no` | `VARCHAR(32)` | `NULLABLE` | Municipal ward numerical index |
| `ward_name` | `VARCHAR(128)` | `NOT NULL`, `INDEXED` | Ward name (Used for choropleth joining) |
| `status` | `VARCHAR(64)` | `NOT NULL`, `INDEXED` | Standardized status (`Closed`, `Resolved`, `Pending`, `Under Process`) |
| `staff_name` | `VARCHAR(128)` | `NULLABLE` | Field staff name *(Restricted; excluded from REST API)* |
| `staff_remarks` | `TEXT` | `NULLABLE` | Internal remarks *(Restricted; excluded from REST API)* |
| `source_file` | `VARCHAR(256)` | `NULLABLE` | Originating CSV filename for lineage tracing |
| `ingested_at` | `TIMESTAMP` | `DEFAULT CURRENT_TIMESTAMP` | Pipeline ingestion timestamp |

**Indexes**:
- `ix_service_requests_complaint_id` (`complaint_id` UNIQUE)
- `ix_service_requests_ward_name` (`ward_name`)
- `ix_service_requests_category` (`category`)
- `ix_service_requests_grievance_date` (`grievance_date`)
- `ix_service_requests_status` (`status`)

---

### 2.2 Table: `daily_aggregates`
Precomputed daily rollups for high-throughput temporal and spatial analytical queries.

| Column | SQL Type | Constraints | Description |
|---|---|---|---|
| `id` | `INTEGER` | `PRIMARY KEY AUTOINCREMENT` | Internal identifier |
| `agg_date` | `DATE` | `NOT NULL`, `INDEXED` | Calendar date of aggregation |
| `ward_name` | `VARCHAR(128)` | `NOT NULL`, `INDEXED` | Ward name |
| `category` | `VARCHAR(128)` | `NOT NULL`, `INDEXED` | Grievance category |
| `complaint_count` | `INTEGER` | `NOT NULL` | Total complaints logged on this day |
| `open_count` | `INTEGER` | `NOT NULL` | Number of complaints pending or under process |
| `closed_count` | `INTEGER` | `NOT NULL` | Number of complaints resolved or closed |

**Composite Unique Index**: `(agg_date, ward_name, category)` ensures rollup idempotence.

---

### 2.3 Table: `ingestion_runs`
Audit ledger tracking execution history of the ingestion pipeline.

| Column | SQL Type | Constraints | Description |
|---|---|---|---|
| `id` | `INTEGER` | `PRIMARY KEY AUTOINCREMENT` | Internal run ID |
| `run_uuid` | `VARCHAR(64)` | `UNIQUE`, `NOT NULL` | Unique execution identifier (UUID v4) |
| `started_at` | `TIMESTAMP` | `NOT NULL` | Pipeline start timestamp |
| `completed_at` | `TIMESTAMP` | `NULLABLE` | Pipeline termination timestamp |
| `status` | `VARCHAR(32)` | `NOT NULL` | Run outcome (`RUNNING`, `SUCCESS`, `FAILED`) |
| `total_read` | `INTEGER` | `DEFAULT 0` | Total records read from disk |
| `total_inserted` | `INTEGER` | `DEFAULT 0` | New records inserted |
| `total_skipped` | `INTEGER` | `DEFAULT 0` | Existing duplicate records skipped |
| `total_rejected` | `INTEGER` | `DEFAULT 0` | Malformed records rejected by validation |

---

### 2.4 Table: `data_quality_results`
Stores automated validation rule outcomes evaluated across each ingestion batch.

| Column | SQL Type | Constraints | Description |
|---|---|---|---|
| `id` | `INTEGER` | `PRIMARY KEY AUTOINCREMENT` | Internal test ID |
| `run_id` | `INTEGER` | `FOREIGN KEY(ingestion_runs.id)` | Associated ingestion run |
| `check_name` | `VARCHAR(128)` | `NOT NULL` | Unique rule identifier |
| `total_checked` | `INTEGER` | `NOT NULL` | Total rows evaluated |
| `passed` | `INTEGER` | `NOT NULL` | Rows conforming to rule |
| `failed` | `INTEGER` | `NOT NULL` | Rows violating rule |
| `failure_rate` | `FLOAT` | `NOT NULL` | Failure percentage ($(\text{failed} / \text{total}) \times 100$) |
| `details` | `TEXT` | `NULLABLE` | JSON or text explanation of anomalies |
