"""
database/database.py
====================
Database engine, session management, and table initialisation.

Usage:
    from database.database import get_session, init_db

    # In a script:
    init_db()                    # create tables if they don't exist

    with get_session() as session:
        # use session here
        pass

    # In FastAPI (as a dependency):
    def my_endpoint(session: Session = Depends(get_db)):
        ...

Design notes:
- DATABASE_URL is read from the .env file.
- SQLite: uses check_same_thread=False (required for multithreaded use).
- PostgreSQL: simply set DATABASE_URL=postgresql://... — no other code changes needed.
- Sessions use autocommit=False and expire_on_commit=False for safety.
"""

import os
import logging
from contextlib import contextmanager
from typing import Generator

# Pre-load the sqlite dialect directly to avoid prisma-client-py's broken
# entry-point registration ("sqlalchemy.dialects:prisma.postgres") from
# crashing SQLAlchemy's plugin scanner.
import sqlalchemy.dialects.sqlite  # noqa: F401
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning, module="sqlalchemy")

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, Session

# Load .env if present (won't fail if file is missing)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from database.models import Base

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Read config from environment
# ─────────────────────────────────────────────────────────────────────────────
DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "sqlite:///./india_civic_monitor.db"   # safe default for development
)

# ─────────────────────────────────────────────────────────────────────────────
# Engine creation
# ─────────────────────────────────────────────────────────────────────────────
def _build_engine():
    """
    Create the SQLAlchemy engine with database-appropriate settings.

    SQLite quirks handled here:
      - check_same_thread=False   — needed when the engine is shared across threads
      - PRAGMA journal_mode=WAL   — allows concurrent reads while writing
      - PRAGMA foreign_keys=ON    — SQLite doesn't enforce FK by default!
    """
    connect_args = {}
    if DATABASE_URL.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    engine = create_engine(
        DATABASE_URL,
        connect_args=connect_args,
        echo=os.getenv("DEBUG", "false").lower() == "true",  # log SQL when DEBUG=true
        # Pool settings (SQLite uses StaticPool automatically; PostgreSQL uses QueuePool)
        pool_pre_ping=True,   # test connection health before using from pool
    )

    # SQLite-specific pragmas — these only fire for SQLite connections
    if DATABASE_URL.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def set_sqlite_pragmas(dbapi_conn, _connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")      # faster concurrent reads
            cursor.execute("PRAGMA foreign_keys=ON")       # enforce FK constraints
            cursor.execute("PRAGMA synchronous=NORMAL")    # faster writes, still safe
            cursor.execute("PRAGMA cache_size=-64000")     # 64MB page cache
            cursor.close()

    return engine


engine = _build_engine()

# ─────────────────────────────────────────────────────────────────────────────
# Session factory
# ─────────────────────────────────────────────────────────────────────────────
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,       # we manage transactions explicitly
    autoflush=False,        # we flush manually when ready
    expire_on_commit=False, # keep objects usable after commit
)


# ─────────────────────────────────────────────────────────────────────────────
# Public helpers
# ─────────────────────────────────────────────────────────────────────────────
def init_db() -> None:
    """
    Create all tables defined in models.py if they don't already exist.
    Safe to call multiple times — won't drop or alter existing tables.
    """
    logger.info("Initialising database at: %s", DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables ready.")


def drop_all_tables() -> None:
    """
    ⚠ WARNING: Drops ALL tables. Only used in tests with a test database.
    Never call this on the production database.
    """
    Base.metadata.drop_all(bind=engine)
    logger.warning("All tables dropped.")


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """
    Context manager for use in scripts and the ingestion pipeline.

    Example:
        with get_session() as session:
            session.add(some_object)
            session.commit()
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency injection — yields a session per HTTP request.

    Usage in a FastAPI route:
        @app.get("/something")
        def my_endpoint(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def health_check() -> dict:
    """
    Returns a dict describing database connectivity status.
    Used by the /health API endpoint.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok", "database_url": _safe_url(DATABASE_URL)}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


def _safe_url(url: str) -> str:
    """Return the DB URL with any password masked, safe for logging/display."""
    try:
        from sqlalchemy.engine import make_url
        u = make_url(url)
        return u.render_as_string(hide_password=True)
    except Exception:
        return url.split("@")[-1] if "@" in url else url
