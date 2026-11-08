"""
scripts/setup_db.py
===================
Creates the SQLite database and all tables.

Run this ONCE before running the ingestion pipeline.

Usage (Windows):
    cd C:\\Users\\Asus\\Downloads\\DATASci\\india-civic-monitor
    python scripts/setup_db.py
"""

import sys
import os
from pathlib import Path

# Make sure the project root is on the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from database.database import init_db, health_check, DATABASE_URL, engine
from database.models import Base

def main():
    print("\n" + "=" * 60)
    print("  India Civic Monitor — Database Setup")
    print("=" * 60)

    print(f"\n  Database URL : {DATABASE_URL}")

    print("\n  Creating tables...")
    init_db()

    # Show what tables were created
    from sqlalchemy import inspect as sa_inspect
    inspector = sa_inspect(engine)
    tables = inspector.get_table_names()
    print(f"\n  Tables created ({len(tables)}):")
    for t in sorted(tables):
        cols = inspector.get_columns(t)
        print(f"    {t:<30s}  ({len(cols)} columns)")

    # Health check
    health = health_check()
    print(f"\n  Health check : {health['status'].upper()}")
    print(f"  Connected to : {health.get('database_url', 'N/A')}")

    if DATABASE_URL.startswith("sqlite"):
        db_file = DATABASE_URL.replace("sqlite:///", "").replace("./", "")
        db_path = Path(db_file).resolve()
        if db_path.exists():
            size_kb = db_path.stat().st_size / 1024
            print(f"\n  SQLite file  : {db_path}")
            print(f"  File size    : {size_kb:.1f} KB")

    print("\n  ✓ Database ready. You can now run the ingestion pipeline.")
    print("    Next step:  python ingestion/ingest.py\n")


if __name__ == "__main__":
    main()
