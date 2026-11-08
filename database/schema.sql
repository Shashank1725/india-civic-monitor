-- =============================================================================
-- schema.sql — India Civic Disruption Monitoring System
-- =============================================================================
-- This file is the human-readable reference for the database schema.
-- The actual tables are created by SQLAlchemy (database/models.py).
-- You can also use this file to recreate the schema manually in a DB client.
--
-- Column annotations:
--   [SOURCE]    = value comes directly from the BBMP CSV
--   [GENERATED] = value computed or assigned by the pipeline
-- =============================================================================


-- ---------------------------------------------------------------------------
-- TABLE: ingestion_runs
-- One row per execution of the data ingestion pipeline.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ingestion_runs (
    id              INTEGER     PRIMARY KEY AUTOINCREMENT,               -- [GENERATED]
    run_uuid        TEXT        UNIQUE NOT NULL,                         -- [GENERATED] UUID
    started_at      DATETIME    NOT NULL,                                -- [GENERATED] pipeline start time
    completed_at    DATETIME,                                            -- [GENERATED] pipeline end time
    status          TEXT        NOT NULL DEFAULT 'running',              -- [GENERATED] running|success|failed
    source_files    TEXT,                                                -- [GENERATED] JSON list of filenames
    error_message   TEXT,                                                -- [GENERATED] if status=failed
    total_read      INTEGER     DEFAULT 0,                               -- [GENERATED] rows read from CSV
    total_inserted  INTEGER     DEFAULT 0,                               -- [GENERATED]
    total_updated   INTEGER     DEFAULT 0,                               -- [GENERATED]
    total_skipped   INTEGER     DEFAULT 0,                               -- [GENERATED] already in DB, unchanged
    total_rejected  INTEGER     DEFAULT 0,                               -- [GENERATED] failed validation
    total_duplicates INTEGER    DEFAULT 0                                -- [GENERATED] duplicate IDs found
);


-- ---------------------------------------------------------------------------
-- TABLE: service_requests
-- One row per BBMP citizen grievance (complaint).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS service_requests (
    id                  INTEGER     PRIMARY KEY AUTOINCREMENT,           -- [GENERATED]
    ingestion_run_id    INTEGER     REFERENCES ingestion_runs(id) ON DELETE SET NULL,  -- [GENERATED]
    is_valid            INTEGER     NOT NULL DEFAULT 1,                  -- [GENERATED] 0=rejected
    rejection_reason    TEXT,                                            -- [GENERATED] why rejected

    -- SOURCE columns (mapped from CSV)
    complaint_id        INTEGER     UNIQUE NOT NULL,                     -- [SOURCE] "Complaint ID"
    category            TEXT        NOT NULL,                            -- [SOURCE] "Category"
    sub_category        TEXT,                                            -- [SOURCE] "Sub Category"
    grievance_date      DATETIME    NOT NULL,                            -- [SOURCE] "Grievance Date"
    ward_name           TEXT,                                            -- [SOURCE] "Ward Name"
    status              TEXT,                                            -- [SOURCE] "Grievance Status"
    staff_remarks       TEXT,                                            -- [SOURCE] "Staff Remarks" — NOT in API
    staff_name          TEXT,                                            -- [SOURCE] "Staff Name"    — NOT in API

    -- Pipeline timestamps
    created_at          DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,  -- [GENERATED]
    updated_at          DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP   -- [GENERATED]
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS ix_sr_ward_date     ON service_requests(ward_name, grievance_date);
CREATE INDEX IF NOT EXISTS ix_sr_cat_date      ON service_requests(category, grievance_date);
CREATE INDEX IF NOT EXISTS ix_sr_ward_cat      ON service_requests(ward_name, category);
CREATE INDEX IF NOT EXISTS ix_sr_ward_cat_date ON service_requests(ward_name, category, grievance_date);
CREATE INDEX IF NOT EXISTS ix_sr_status        ON service_requests(status);
CREATE INDEX IF NOT EXISTS ix_sr_is_valid      ON service_requests(is_valid);
CREATE INDEX IF NOT EXISTS ix_sr_run_id        ON service_requests(ingestion_run_id);


-- ---------------------------------------------------------------------------
-- TABLE: data_quality_results
-- One row per validation check per ingestion run.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS data_quality_results (
    id                  INTEGER     PRIMARY KEY AUTOINCREMENT,           -- [GENERATED]
    ingestion_run_id    INTEGER     NOT NULL REFERENCES ingestion_runs(id) ON DELETE CASCADE,
    created_at          DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,

    check_name          TEXT        NOT NULL,   -- e.g. "missing_ward", "duplicate_ids"
    total_checked       INTEGER     DEFAULT 0,
    passed              INTEGER     DEFAULT 0,
    failed              INTEGER     DEFAULT 0,
    failure_rate        REAL        DEFAULT 0.0, -- failed / total_checked * 100
    details             TEXT                    -- JSON: sample bad values, extra context
);

CREATE INDEX IF NOT EXISTS ix_dqr_run_id ON data_quality_results(ingestion_run_id);


-- ---------------------------------------------------------------------------
-- TABLE: daily_aggregates
-- Pre-computed complaint counts per (date, ward, category).
-- Rebuilt after every successful ingestion.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS daily_aggregates (
    id              INTEGER     PRIMARY KEY AUTOINCREMENT,               -- [GENERATED]
    agg_date        DATE        NOT NULL,                                -- [GENERATED] date portion of grievance_date
    ward_name       TEXT        NOT NULL,                                -- [GENERATED] from service_requests
    category        TEXT        NOT NULL,                                -- [GENERATED]
    complaint_count INTEGER     NOT NULL DEFAULT 0,                      -- [GENERATED] total complaints that day
    open_count      INTEGER     NOT NULL DEFAULT 0,                      -- [GENERATED] Registered + ReOpen + In Progress
    closed_count    INTEGER     NOT NULL DEFAULT 0,                      -- [GENERATED] Closed + Resolved
    last_updated    DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(agg_date, ward_name, category)
);

CREATE INDEX IF NOT EXISTS ix_da_date_ward ON daily_aggregates(agg_date, ward_name);
CREATE INDEX IF NOT EXISTS ix_da_date_cat  ON daily_aggregates(agg_date, category);
CREATE INDEX IF NOT EXISTS ix_da_ward_cat  ON daily_aggregates(ward_name, category);


-- =============================================================================
-- USEFUL REFERENCE QUERIES
-- (These are not part of the schema — just examples for exploration)
-- =============================================================================

-- Total complaints per ward (all time):
-- SELECT ward_name, SUM(complaint_count) AS total
-- FROM daily_aggregates
-- GROUP BY ward_name ORDER BY total DESC LIMIT 20;

-- Daily total complaints:
-- SELECT agg_date, SUM(complaint_count) AS total
-- FROM daily_aggregates
-- GROUP BY agg_date ORDER BY agg_date;

-- Last ingestion run:
-- SELECT * FROM ingestion_runs ORDER BY started_at DESC LIMIT 1;
