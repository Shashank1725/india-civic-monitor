"""
scripts/package_db_snapshot.py
==============================
Builds the compressed database snapshot used to restore the app's data at boot
on hosts with ephemeral filesystems (e.g. Render free instances).

What it does:
  1. Checkpoints the SQLite WAL so the .db file is self-contained.
  2. Compresses it with zstd (level 10) to snapshots/<name>.db.zst.
  3. Prints the SHA-256 and exact upload instructions.

Usage (run from the repo root, after ingestion):
    python scripts/package_db_snapshot.py

Then upload the file as a GitHub Release asset and set DB_SNAPSHOT_URL /
DB_SNAPSHOT_SHA256 in your Render service (see DEPLOY.md).
"""

from __future__ import annotations

import argparse
import hashlib
import sqlite3
import sys
import time
from pathlib import Path

import zstandard

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class _HashingWriter:
    """Wraps a binary file and hashes every byte written."""

    def __init__(self, fh):
        self._fh = fh
        self.hasher = hashlib.sha256()
        self.written = 0

    def write(self, data: bytes) -> int:
        self.hasher.update(data)
        self.written += len(data)
        return self._fh.write(data)


def main() -> int:
    parser = argparse.ArgumentParser(description="Package the SQLite DB as a .zst snapshot")
    parser.add_argument("--db", default=str(PROJECT_ROOT / "india_civic_monitor.db"))
    parser.add_argument("--out", default=str(PROJECT_ROOT / "snapshots" / "india_civic_monitor.db.zst"))
    parser.add_argument("--level", type=int, default=10, help="zstd level (default 10)")
    args = parser.parse_args()

    db_path = Path(args.db)
    out_path = Path(args.out)
    if not db_path.exists():
        print(f"ERROR: database not found: {db_path}", file=sys.stderr)
        return 1

    # 1. Checkpoint WAL so the main file contains everything
    print(f"Checkpointing WAL: {db_path}")
    con = sqlite3.connect(str(db_path))
    try:
        mode = con.execute("PRAGMA journal_mode").fetchone()[0]
        print(f"  journal_mode={mode}")
        result = con.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
        print(f"  checkpoint result={result}")  # (busy, log_frames, checkpointed_frames)
        rows = con.execute("SELECT COUNT(*) FROM service_requests").fetchone()[0]
        print(f"  service_requests rows={rows:,}")
    finally:
        con.close()

    # 2. Compress
    out_path.parent.mkdir(parents=True, exist_ok=True)
    src_size = db_path.stat().st_size
    print(f"Compressing with zstd level {args.level} ...")
    t0 = time.monotonic()
    with open(db_path, "rb") as fin, open(out_path, "wb") as fout_raw:
        writer = _HashingWriter(fout_raw)
        cctx = zstandard.ZstdCompressor(level=args.level)
        cctx.copy_stream(fin, writer)
        digest = writer.hasher.hexdigest()
        compressed = writer.written
    elapsed = time.monotonic() - t0

    # 3. Report
    ratio = compressed / src_size * 100
    print()
    print("=" * 70)
    print("  SNAPSHOT READY")
    print("=" * 70)
    print(f"  source     : {db_path}  ({src_size / 1e6:.1f} MB)")
    print(f"  snapshot   : {out_path}  ({compressed / 1e6:.1f} MB, {ratio:.1f}% of original)")
    print(f"  sha256     : {digest}")
    print(f"  compressed in {elapsed:.1f}s")
    print()
    print("  NEXT STEPS (see DEPLOY.md):")
    print("  1. Push the repo to GitHub, then create a Release (tag v1) and")
    print(f"     upload this file as an asset: {out_path.name}")
    print("  2. In Render -> your service -> Environment, set:")
    print(f"       DB_SNAPSHOT_URL=https://github.com/<you>/<repo>/releases/download/v1/{out_path.name}")
    print(f"       DB_SNAPSHOT_SHA256={digest}")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
