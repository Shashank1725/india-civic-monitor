"""
database/bootstrap.py
=====================
Background data bootstrap for production (Render) and fresh local clones.

Render free instances have an *ephemeral filesystem*: the SQLite database is
wiped every time the service sleeps (15 min idle), restarts, or redeploys.
Re-running the full CSV ingestion takes ~15 minutes on a normal machine — far
too slow to do inline during startup (Render fails deploys that don't open a
port quickly). Instead, at boot we:

  1. do nothing if ``service_requests`` already has rows (normal local case);
  2. otherwise stream a pre-built compressed snapshot from ``DB_SNAPSHOT_URL``
     (a GitHub Release asset), verify it, and atomically swap it into place;
  3. otherwise fall back to the CSV ingestion pipeline (slow but correct).

The bootstrap runs in a daemon thread so uvicorn can bind its port immediately.

Environment variables:
    DB_SNAPSHOT_URL     https://github.com/<user>/<repo>/releases/download/...
    DB_SNAPSHOT_SHA256  optional hex digest of the compressed snapshot
"""

from __future__ import annotations

import hashlib
import logging
import os
import shutil
import sqlite3
import threading
import time
import zlib
from pathlib import Path

import httpx

from database.database import DATABASE_URL, engine, init_db

logger = logging.getLogger("bootstrap")

# Minimum rows we expect in a valid snapshot of this dataset (766,648 rows).
MIN_SNAPSHOT_ROWS = 100_000
_CHUNK = 1024 * 1024
_MAX_ATTEMPTS = 3

_status: dict = {"state": "idle", "detail": "", "data_ready": None}
_lock = threading.Lock()
_started = False


# ── Status helpers (read by /health) ─────────────────────────────────────────
def data_ready() -> bool:
    """True once the database contains data (re-checked until ready)."""
    with _lock:
        if _status["data_ready"] is not True:
            try:
                _status["data_ready"] = _count_rows() > 0
            except Exception:
                _status["data_ready"] = False
        return bool(_status["data_ready"])


def bootstrap_status() -> dict:
    with _lock:
        return dict(_status)


def _set(state: str, detail: str = "", ready: bool | None = None) -> None:
    with _lock:
        _status["state"] = state
        _status["detail"] = detail
        if ready is not None:
            _status["data_ready"] = ready
    logger.info("bootstrap: state=%s %s", state, detail)


# ── DB helpers ───────────────────────────────────────────────────────────────
def _db_path() -> Path | None:
    """Filesystem path of the SQLite database, or None if not file-backed."""
    if not DATABASE_URL.startswith("sqlite"):
        return None
    db = engine.url.database
    if not db or db == ":memory:":
        return None
    return Path(db).expanduser().resolve()


def _count_rows(path: Path | None = None) -> int:
    target = path or _db_path()
    if target is None or not target.exists():
        return 0
    try:
        con = sqlite3.connect(f"file:{target}?mode=ro", uri=True, timeout=10)
        try:
            return int(con.execute("SELECT COUNT(*) FROM service_requests").fetchone()[0])
        finally:
            con.close()
    except sqlite3.Error:
        return 0


# ── Streaming decompressors (zstd preferred, gzip fallback) ─────────────────
class _StreamDecompressor:
    """Feeds compressed chunks in, writes decompressed bytes out."""

    def __init__(self, url: str, out):
        self._out = out
        path = url.split("?")[0].lower()
        if path.endswith(".gz") or path.endswith(".gzip"):
            self._mode = "gzip"
            self._obj = zlib.decompressobj(16 + zlib.MAX_WBITS)
        elif path.endswith(".zst") or path.endswith(".zstd"):
            self._mode = "zstd"
            import zstandard
            self._obj = zstandard.ZstdDecompressor().decompressobj()
        else:
            # Raw uncompressed stream (e.g. .db)
            self._mode = "raw"
            self._obj = None

    def feed(self, chunk: bytes) -> None:
        if self._mode == "raw":
            self._out.write(chunk)
            return
        data = self._obj.decompress(chunk)
        if data:
            self._out.write(data)

    def finish(self) -> None:
        if self._mode == "raw":
            return
        data = self._obj.flush()
        if data:
            self._out.write(data)


def _stream_snapshot(url: str, sha256: str | None, dest: Path) -> None:
    """Download → hash → decompress → verify → atomically swap into place."""
    tmp = dest.with_name(dest.name + ".tmp")
    tmp.unlink(missing_ok=True)

    hasher = hashlib.sha256()
    compressed = 0
    last_log = time.monotonic()

    logger.info("downloading snapshot: %s", url)
    with httpx.stream(
        "GET", url, follow_redirects=True, timeout=httpx.Timeout(30.0, read=60.0)
    ) as resp:
        resp.raise_for_status()
        with open(tmp, "wb") as out:
            dec = _StreamDecompressor(url, out)
            for chunk in resp.iter_bytes(_CHUNK):
                hasher.update(chunk)
                dec.feed(chunk)
                compressed += len(chunk)
                now = time.monotonic()
                if now - last_log > 10:
                    logger.info("  received %.0f MB compressed ...", compressed / 1e6)
                    last_log = now
            dec.finish()

    # 1. Optional integrity hash of the *compressed* stream
    actual = hasher.hexdigest()
    if sha256:
        if actual.lower() != sha256.lower():
            tmp.unlink(missing_ok=True)
            raise RuntimeError(
                f"SHA-256 mismatch: expected {sha256.lower()}, got {actual.lower()}"
            )
        logger.info("snapshot sha256 verified (%s)", actual[:16])
    else:
        logger.warning("DB_SNAPSHOT_SHA256 not set — skipping hash verification")

    # 2. SQLite sanity check + row-count sanity check
    # Avoid memory-heavy PRAGMA quick_check to protect 512 MB free tier limits
    t0 = time.monotonic()
    con = sqlite3.connect(str(tmp))
    try:
        # Lightweight check: verify table can be queried
        con.execute("SELECT 1 FROM service_requests LIMIT 1")
        rows = int(con.execute("SELECT COUNT(*) FROM service_requests").fetchone()[0])
    finally:
        con.close()
    if rows < MIN_SNAPSHOT_ROWS:
        tmp.unlink(missing_ok=True)
        raise RuntimeError(f"snapshot has too few rows ({rows} < {MIN_SNAPSHOT_ROWS})")
    logger.info(
        "snapshot verified: %s rows ready (%.1fs)",
        f"{rows:,}",
        time.monotonic() - t0,
    )

    # 3. Atomic swap: close pooled connections, drop stale WAL files, rename
    engine.dispose()
    for suffix in ("-wal", "-shm"):
        sidecar = dest.with_name(dest.name + suffix)
        if sidecar.exists():
            sidecar.unlink()
    os.replace(tmp, dest)
    logger.info("database installed at %s (%.1f MB)", dest, dest.stat().st_size / 1e6)


# ── Orchestrator ─────────────────────────────────────────────────────────────
def run_bootstrap() -> None:
    _set(state="starting")
    try:
        disk = shutil.disk_usage(Path.cwd())
        logger.info(
            "ephemeral disk: total=%.1f GB, free=%.1f GB",
            disk.total / 1e9,
            disk.free / 1e9,
        )

        # Ensure schema exists (also creates an empty DB file if missing).
        init_db()

        rows = _count_rows()
        if rows > 0:
            _set(state="ready", detail=f"{rows:,} rows already present", ready=True)
            logger.info("database already populated (%s rows) — bootstrap skipped",
                        f"{rows:,}")
            return

        # Try the pre-built snapshot first (fast path on Render).
        url = os.getenv("DB_SNAPSHOT_URL", "").strip()
        dest = _db_path()
        if url and dest is not None:
            sha = os.getenv("DB_SNAPSHOT_SHA256", "").strip() or None
            last_err: Exception | None = None
            for attempt in range(1, _MAX_ATTEMPTS + 1):
                _set(state="downloading", detail=f"attempt {attempt}/{_MAX_ATTEMPTS}")
                try:
                    _stream_snapshot(url, sha, dest)
                    _set(state="ready", detail="snapshot restored", ready=True)
                    return
                except Exception as exc:  # noqa: BLE001 — retry any failure
                    last_err = exc
                    logger.warning("snapshot attempt %d failed: %s", attempt, exc)
                    time.sleep(5 * attempt)
            logger.error(
                "all %d snapshot attempts failed (%s) — falling back to CSV ingestion",
                _MAX_ATTEMPTS,
                last_err,
            )
        elif not url:
            logger.info("DB_SNAPSHOT_URL not set — using CSV ingestion fallback")

        # Slow but correct fallback: full CSV ingestion (~15 min).
        _set(state="ingesting", detail="CSV ingestion fallback (slow path)")
        from ingestion.ingest import main as ingest_main

        ingest_main()
        _set(state="ready", detail="ingested from CSV", ready=True)

    except Exception as exc:  # noqa: BLE001 — never kill the web process
        logger.exception("bootstrap failed: %s", exc)
        ready = False
        try:
            ready = _count_rows() > 0
        except Exception:
            pass
        _set(state="failed", detail=str(exc), ready=ready)


def start_bootstrap() -> None:
    """Spawn the bootstrap thread once (idempotent, non-blocking)."""
    global _started
    with _lock:
        if _started:
            return
        _started = True
    # Make sure bootstrap progress is visible in server logs (Render log stream).
    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        )
    threading.Thread(target=run_bootstrap, name="db-bootstrap", daemon=True).start()
