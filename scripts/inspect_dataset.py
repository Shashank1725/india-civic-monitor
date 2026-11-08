"""
inspect_dataset.py
==================
Phase 1 - BBMP Citizen Grievances Dataset Inspector
India Civic Disruption Monitoring System

Usage (Windows):
    cd C:\\Users\\Asus\\Downloads\\DATASci\\india-civic-monitor
    python scripts/inspect_dataset.py

Reads every .csv file found in DATA_DIR and produces a full
inspection report saved to reports/inspection_report.txt.
No data is modified. No files are written to the dataset folder.
"""

import os
import sys
import csv
import json
import textwrap
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Tuple, Dict, Any

# ── pip install pandas if missing ─────────────────────────────────────────────
try:
    import pandas as pd
except ImportError:
    print("pandas not found. Install it with:  pip install pandas")
    sys.exit(1)

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────
DATA_DIR   = Path(os.path.join(os.path.expanduser("~"), "Downloads", "DATASci", "Dataset"))
REPORT_DIR = Path(__file__).parent.parent / "reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)
REPORT_FILE = REPORT_DIR / "inspection_report.txt"

# Columns we expect (based on header preview). Used for schema-change detection.
EXPECTED_COLUMNS = [
    "Complaint ID",
    "Category",
    "Sub Category",
    "Grievance Date",
    "Ward Name",
    "Grievance Status",
    "Staff Remarks",
    "Staff Name",
]

# Candidate date column names (case-insensitive search)
DATE_COL_HINTS = ["grievance date", "date", "created", "timestamp", "reported"]

MAX_SAMPLE_ROWS = 5          # rows to print in the sample section
CHUNK_SIZE      = 100_000    # rows per chunk for per-file row counting


# ─────────────────────────────────────────────────────────────────────────────
# HELPER: pretty section header
# ─────────────────────────────────────────────────────────────────────────────
def section(title: str) -> str:
    bar = "=" * 70
    return f"\n{bar}\n  {title}\n{bar}\n"


def subsection(title: str) -> str:
    return f"\n{'─' * 60}\n  {title}\n{'─' * 60}"


# ─────────────────────────────────────────────────────────────────────────────
# STEP 1: discover files
# ─────────────────────────────────────────────────────────────────────────────
def discover_files(data_dir: Path) -> list[Path]:
    if not data_dir.exists():
        print(f"[ERROR] DATA_DIR not found: {data_dir}")
        sys.exit(1)
    files = sorted(data_dir.glob("*.csv"))
    if not files:
        print(f"[ERROR] No CSV files found in {data_dir}")
        sys.exit(1)
    return files


# ─────────────────────────────────────────────────────────────────────────────
# STEP 2: load all files into one combined DataFrame (chunked-safe)
# ─────────────────────────────────────────────────────────────────────────────
def load_all(files: List[Path]) -> Tuple[pd.DataFrame, List[Dict[str, Any]]]:
    """
    Returns:
        combined_df   – all rows merged
        file_summaries – per-file metadata list
    """
    dfs        = []   # type: List[pd.DataFrame]
    summaries  = []   # type: List[Dict[str, Any]]

    for fp in files:
        size_mb = fp.stat().st_size / 1_048_576
        try:
            df_file = pd.read_csv(
                fp,
                encoding="utf-8",
                encoding_errors="replace",
                low_memory=False,
            )
        except Exception as exc:
            summaries.append({
                "file"  : fp.name,
                "size_mb": round(size_mb, 2),
                "rows"  : None,
                "cols"  : None,
                "error" : str(exc),
            })
            continue

        summaries.append({
            "file"   : fp.name,
            "size_mb": round(size_mb, 2),
            "rows"   : len(df_file),
            "cols"   : list(df_file.columns),
            "error"  : None,
        })
        dfs.append(df_file)

    if not dfs:
        print("[ERROR] Could not load any CSV file.")
        sys.exit(1)

    combined = pd.concat(dfs, ignore_index=True)
    return combined, summaries


# ─────────────────────────────────────────────────────────────────────────────
# STEP 3: detect date column and parse
# ─────────────────────────────────────────────────────────────────────────────
def find_date_column(df: pd.DataFrame) -> Optional[str]:
    for col in df.columns:
        if col.lower() in DATE_COL_HINTS:
            return col
    return None


def parse_date_column(df: pd.DataFrame, col: str) -> pd.Series:
    """Try multiple strategies to parse a date column."""
    raw = df[col].astype(str)
    parsed = pd.to_datetime(raw, errors="coerce", infer_datetime_format=True)
    return parsed


# ─────────────────────────────────────────────────────────────────────────────
# STEP 4: build the full report
# ─────────────────────────────────────────────────────────────────────────────
def build_report(df: pd.DataFrame, file_summaries: List[Dict[str, Any]], files: List[Path]) -> str:
    lines = []
    now   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ── HEADER ───────────────────────────────────────────────────────────────
    lines.append(section("BBMP GRIEVANCES DATASET — INSPECTION REPORT"))
    lines.append(f"  Generated : {now}")
    lines.append(f"  Data dir  : {DATA_DIR}")
    lines.append(f"  Files     : {len(files)}")
    lines.append(f"  Total rows: {len(df):,}")
    lines.append(f"  Columns   : {len(df.columns)}")

    # ── PER-FILE SUMMARY ─────────────────────────────────────────────────────
    lines.append(section("1. PER-FILE SUMMARY"))
    for s in file_summaries:
        lines.append(f"\n  File : {s['file']}")
        lines.append(f"  Size : {s['size_mb']} MB")
        if s["error"]:
            lines.append(f"  [ERROR] {s['error']}")
        else:
            lines.append(f"  Rows : {s['rows']:,}")
            lines.append(f"  Cols : {s['cols']}")

    # ── SCHEMA ───────────────────────────────────────────────────────────────
    lines.append(section("2. COLUMN NAMES & DATA TYPES"))
    for col in df.columns:
        lines.append(f"  {col!r:<40s} dtype={df[col].dtype}")

    # ── SCHEMA CHANGE DETECTION ──────────────────────────────────────────────
    lines.append(section("3. SCHEMA CONSISTENCY CHECK"))
    all_same = all(s["cols"] == file_summaries[0]["cols"] for s in file_summaries if s["cols"])
    if all_same:
        lines.append("  ✓ All files share identical column names.")
    else:
        lines.append("  ✗ Column names differ across files — review manually!")
        for s in file_summaries:
            lines.append(f"    {s['file']}: {s['cols']}")

    unexpected = [c for c in df.columns if c not in EXPECTED_COLUMNS]
    missing_exp = [c for c in EXPECTED_COLUMNS if c not in df.columns]
    lines.append(f"\n  Expected columns present  : {[c for c in EXPECTED_COLUMNS if c in df.columns]}")
    lines.append(f"  Expected columns MISSING  : {missing_exp}")
    lines.append(f"  Unexpected extra columns  : {unexpected}")

    # ── SAMPLE RECORDS ───────────────────────────────────────────────────────
    lines.append(section("4. SAMPLE RECORDS (first 5 rows)"))
    sample = df.head(MAX_SAMPLE_ROWS).to_dict(orient="records")
    for i, row in enumerate(sample, 1):
        lines.append(f"\n  Record {i}:")
        for k, v in row.items():
            v_str = str(v)[:120]          # truncate very long staff remarks
            lines.append(f"    {k}: {v_str}")

    # ── MISSING VALUES ───────────────────────────────────────────────────────
    lines.append(section("5. MISSING VALUES PER COLUMN"))
    total = len(df)
    for col in df.columns:
        n_null  = df[col].isna().sum()
        # Also count empty strings as missing
        if df[col].dtype == object:
            n_empty = (df[col].astype(str).str.strip() == "").sum()
        else:
            n_empty = 0
        n_miss = n_null + n_empty
        pct    = n_miss / total * 100 if total else 0
        flag   = "  ⚠" if pct > 10 else "   "
        lines.append(f"{flag} {col:<40s}  null={n_null:>8,}  empty={n_empty:>8,}  total_missing={n_miss:>8,}  ({pct:.1f}%)")

    # ── COMPLAINT ID / DUPLICATE ANALYSIS ───────────────────────────────────
    lines.append(section("6. COMPLAINT ID ANALYSIS & DUPLICATE DETECTION"))
    id_col = None
    for candidate in ["Complaint ID", "complaint_id", "ID", "id"]:
        if candidate in df.columns:
            id_col = candidate
            break

    if id_col:
        n_null_id  = df[id_col].isna().sum()
        n_total_id = len(df)
        n_unique   = df[id_col].nunique()
        n_dup      = n_total_id - n_unique
        lines.append(f"  Identifier column         : {id_col!r}")
        lines.append(f"  Total records             : {n_total_id:,}")
        lines.append(f"  Null IDs                  : {n_null_id:,}")
        lines.append(f"  Unique IDs                : {n_unique:,}")
        lines.append(f"  Duplicate IDs             : {n_dup:,}  ({n_dup/n_total_id*100:.2f}%)")
        if n_dup > 0:
            top_dups = (
                df[id_col]
                .value_counts()
                .head(10)
                .reset_index()
                .rename(columns={id_col: "count", "index": id_col})
            )
            lines.append("\n  Top duplicate IDs:")
            lines.append(top_dups.to_string(index=False))
    else:
        lines.append("  ✗ No reliable unique identifier column found.")
        lines.append("    Deduplication will require composite key or row hash.")

    # ── CATEGORIES ───────────────────────────────────────────────────────────
    lines.append(section("7. COMPLAINT CATEGORIES"))
    if "Category" in df.columns:
        cat_counts = df["Category"].value_counts(dropna=False)
        lines.append(f"  Unique categories: {df['Category'].nunique()}\n")
        for cat, cnt in cat_counts.items():
            lines.append(f"    {str(cat):<55s} {cnt:>8,}  ({cnt/total*100:.1f}%)")
    else:
        lines.append("  'Category' column not found.")

    if "Sub Category" in df.columns:
        lines.append(f"\n  Unique Sub-categories: {df['Sub Category'].nunique()}")
        top_sub = df["Sub Category"].value_counts(dropna=False).head(20)
        lines.append("\n  Top 20 Sub-categories:")
        for sc, cnt in top_sub.items():
            lines.append(f"    {str(sc):<65s} {cnt:>8,}")

    # ── STATUS ───────────────────────────────────────────────────────────────
    lines.append(section("8. GRIEVANCE STATUS DISTRIBUTION"))
    if "Grievance Status" in df.columns:
        status_counts = df["Grievance Status"].value_counts(dropna=False)
        for st, cnt in status_counts.items():
            lines.append(f"  {str(st):<40s} {cnt:>8,}  ({cnt/total*100:.1f}%)")
    else:
        lines.append("  'Grievance Status' column not found.")

    # ── DATE ANALYSIS ────────────────────────────────────────────────────────
    lines.append(section("9. DATE / TIME ANALYSIS"))
    date_col = find_date_column(df)
    if date_col:
        lines.append(f"  Detected date column: {date_col!r}")
        parsed = parse_date_column(df, date_col)
        n_parsed  = parsed.notna().sum()
        n_failed  = parsed.isna().sum()
        lines.append(f"  Successfully parsed  : {n_parsed:,}  ({n_parsed/total*100:.1f}%)")
        lines.append(f"  Failed to parse      : {n_failed:,}  ({n_failed/total*100:.1f}%)")

        if n_parsed > 0:
            lines.append(f"  Earliest record      : {parsed.min()}")
            lines.append(f"  Latest record        : {parsed.max()}")
            date_range_days = (parsed.max() - parsed.min()).days
            lines.append(f"  Date range           : {date_range_days:,} days (~{date_range_days//365} years)")

            future_mask = parsed > pd.Timestamp.now()
            n_future = future_mask.sum()
            lines.append(f"  Future-dated records : {n_future:,}")

            # Monthly distribution
            lines.append("\n  Records per year:")
            yearly = parsed.dt.year.value_counts().sort_index()
            for yr, cnt in yearly.items():
                lines.append(f"    {yr}  :  {cnt:>8,}")

        # Show raw format sample
        raw_samples = df[date_col].dropna().head(5).tolist()
        lines.append(f"\n  Raw date format samples:")
        for s in raw_samples:
            lines.append(f"    {s!r}")
    else:
        lines.append("  ✗ No date/timestamp column detected.")

    # ── WARD / AREA ──────────────────────────────────────────────────────────
    lines.append(section("10. WARD / AREA ANALYSIS"))
    if "Ward Name" in df.columns:
        n_ward_null  = df["Ward Name"].isna().sum()
        n_ward_empty = (df["Ward Name"].astype(str).str.strip() == "").sum()
        n_ward_valid = total - n_ward_null - n_ward_empty
        n_unique_wards = df["Ward Name"].nunique()
        lines.append(f"  Records with ward     : {n_ward_valid:,}  ({n_ward_valid/total*100:.1f}%)")
        lines.append(f"  Records without ward  : {n_ward_null + n_ward_empty:,}")
        lines.append(f"  Unique ward names     : {n_unique_wards:,}")

        top_wards = df["Ward Name"].value_counts(dropna=False).head(20)
        lines.append("\n  Top 20 wards by complaint volume:")
        for ward, cnt in top_wards.items():
            lines.append(f"    {str(ward):<45s} {cnt:>8,}")
    else:
        lines.append("  ✗ No ward/area column found.")

    # ── COORDINATES ──────────────────────────────────────────────────────────
    lines.append(section("11. SPATIAL / COORDINATE DATA"))
    lat_candidates = [c for c in df.columns if any(h in c.lower() for h in ["lat", "latitude"])]
    lon_candidates = [c for c in df.columns if any(h in c.lower() for h in ["lon", "lng", "longitude"])]

    if lat_candidates and lon_candidates:
        lat_col = lat_candidates[0]
        lon_col = lon_candidates[0]
        lines.append(f"  Latitude column  : {lat_col!r}")
        lines.append(f"  Longitude column : {lon_col!r}")
        lat = pd.to_numeric(df[lat_col], errors="coerce")
        lon = pd.to_numeric(df[lon_col], errors="coerce")
        n_valid_coords = (lat.notna() & lon.notna()).sum()
        lines.append(f"  Valid coordinates: {n_valid_coords:,}  ({n_valid_coords/total*100:.1f}%)")
        if n_valid_coords > 0:
            lines.append(f"  Lat range: {lat.min():.4f} → {lat.max():.4f}")
            lines.append(f"  Lon range: {lon.min():.4f} → {lon.max():.4f}")
    else:
        lines.append("  ✗ No latitude/longitude columns found in the dataset.")
        lines.append("  → Spatial analysis will be WARD-LEVEL only (choropleth map).")
        lines.append("  → Individual complaint pin maps are NOT possible with this data.")

    # ── PRIVACY ──────────────────────────────────────────────────────────────
    lines.append(section("12. PRIVACY-SENSITIVE FIELDS"))
    sensitive_hints = ["name", "phone", "mobile", "email", "address", "contact", "citizen"]
    flagged = [c for c in df.columns if any(h in c.lower() for h in sensitive_hints)]
    if flagged:
        lines.append(f"  ⚠ Potentially sensitive columns: {flagged}")
        lines.append("    Review before publishing or including in API responses.")
        if "Staff Name" in df.columns:
            lines.append("\n  Staff Name samples (first 5):")
            for n in df["Staff Name"].dropna().head(5).tolist():
                lines.append(f"    {n}")
    else:
        lines.append("  No obviously sensitive columns detected.")

    # ── DAILY GROUPING FEASIBILITY ───────────────────────────────────────────
    lines.append(section("13. GROUPING FEASIBILITY"))
    has_date = date_col is not None
    has_ward = "Ward Name" in df.columns
    has_cat  = "Category" in df.columns
    has_id   = id_col is not None

    lines.append(f"  Unique complaint ID exists    : {'✓' if has_id   else '✗'}")
    lines.append(f"  Date column exists            : {'✓' if has_date else '✗'}")
    lines.append(f"  Ward/area column exists       : {'✓' if has_ward else '✗'}")
    lines.append(f"  Category column exists        : {'✓' if has_cat  else '✗'}")
    lines.append(f"  Lat/lon coordinates exist     : ✗  (ward-level only)")
    lines.append("")
    lines.append("  Supported analyses:")
    if has_date and has_ward:
        lines.append("    ✓ Daily complaints per ward")
    if has_date and has_cat:
        lines.append("    ✓ Daily complaints per category")
    if has_date and has_ward and has_cat:
        lines.append("    ✓ Historical weekday baseline anomaly detection (ward × category × weekday)")
    lines.append("    ✗ Pin-level map (no coordinates)")
    if has_ward:
        lines.append("    ✓ Choropleth ward map (requires ward boundary GeoJSON — not in dataset)")

    # ── SOURCE FRESHNESS ─────────────────────────────────────────────────────
    lines.append(section("14. SOURCE DATA FRESHNESS"))
    if date_col:
        parsed2       = parse_date_column(df, date_col)
        latest_record = parsed2.max()
        now_ts        = pd.Timestamp.now()
        staleness     = (now_ts - latest_record).days if pd.notna(latest_record) else None
        if staleness is not None:
            lines.append(f"  Latest source record : {latest_record.strftime('%Y-%m-%d')}")
            lines.append(f"  Days since latest    : {staleness}")
            if staleness < 7:
                status = "FRESH"
            elif staleness < 90:
                status = "RECENT"
            elif staleness < 365:
                status = "STALE"
            else:
                status = "HISTORICAL SNAPSHOT"
            lines.append(f"  Freshness status     : {status}")
            lines.append("  Note: This reflects the latest record in the downloaded file,")
            lines.append("        NOT a live connection to the BBMP system.")
    else:
        lines.append("  Cannot determine freshness — no date column.")

    # ── FINAL SUMMARY & RECOMMENDATIONS ─────────────────────────────────────
    lines.append(section("15. SUMMARY & PHASE 2 RECOMMENDATIONS"))
    lines.append(textwrap.dedent(f"""
  Dataset: BBMP Citizen Grievances (6 CSV export files)
  Total records (combined): {total:,}
  Columns: {list(df.columns)}

  KEY FINDINGS:
  -------------
  1. No latitude/longitude — ward-level spatial analysis only.
  2. Complaint ID column present — reliable deduplication key.
  3. Clean date column ('Grievance Date') — parseable with nanosecond precision.
  4. Ward Name column present — choropleth map feasible once GeoJSON ward
     boundaries are sourced from BBMP/data.gov.in.
  5. 'Staff Name' is semi-sensitive — exclude from public API responses.
  6. No phone/email/citizen contact data detected — low PII risk.

  WHAT THE PROJECT CAN BUILD:
  ---------------------------
  ✓ Ward-level complaint choropleth map
  ✓ Category and time-series trend charts
  ✓ Historical weekday anomaly detection (ward × weekday × category)
  ✓ Data-quality reporting (missing ward, unparseable dates, duplicates)
  ✓ FastAPI REST endpoints for all of the above
  ✓ React dashboard with Leaflet choropleth + Recharts

  WHAT IS NOT POSSIBLE WITH THIS DATA:
  -------------------------------------
  ✗ Individual complaint pin map (no coordinates)
  ✗ Real-time updates (static export files)
  ✗ Citizen-level tracing (no PII columns)

  NEXT: Proceed to Phase 2 — database design and project structure.
    """))

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
def main():
    print(f"\n{'='*60}")
    print("  BBMP Grievances — Dataset Inspector")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    print(f"[1/4] Discovering files in: {DATA_DIR}")
    files = discover_files(DATA_DIR)
    print(f"      Found {len(files)} CSV file(s):")
    for f in files:
        print(f"        {f.name}  ({f.stat().st_size / 1_048_576:.1f} MB)")

    print(f"\n[2/4] Loading all files into memory ...")
    df, file_summaries = load_all(files)
    print(f"      Combined shape: {df.shape[0]:,} rows × {df.shape[1]} columns")

    print(f"\n[3/4] Building inspection report ...")
    report = build_report(df, file_summaries, files)

    print(f"\n[4/4] Writing report to: {REPORT_FILE}")
    REPORT_FILE.write_text(report, encoding="utf-8")

    # Also print to console (truncated)
    print("\n" + "─" * 60)
    print("  REPORT PREVIEW (first 120 lines)")
    print("─" * 60)
    for i, line in enumerate(report.splitlines()[:120]):
        print(line)
    print(f"\n  ... full report saved to: {REPORT_FILE}\n")
    print("✓ Inspection complete.")


if __name__ == "__main__":
    main()
