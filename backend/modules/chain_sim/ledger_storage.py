"""Bounded persistent-storage policy for the local GlyphChain ledger.

The bound covers the SQLite database and its WAL/SHM companions.  It is a
fail-closed write gate, not pruning: once capacity is reached the operator must
increase the approved limit or complete a verified snapshot/pruning workflow.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import sqlite3
from typing import Any


DEFAULT_MAX_BYTES = 512 * 1024 * 1024
MIN_MAX_BYTES = 8 * 1024 * 1024
MAX_MAX_BYTES = 4 * 1024 * 1024 * 1024 * 1024


class LedgerStorageLimitError(RuntimeError):
    pass


def _bounded_int(value: Any, default: int, *, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(maximum, parsed))


def _participation_limit() -> int | None:
    configured = str(os.getenv("GLYPHCHAIN_PARTICIPATION_DIR", "") or "").strip()
    if configured:
        path = Path(configured) / "network-participation.json"
    else:
        state_root = Path(str(os.getenv("GLYPHCHAIN_STATE_DIR", "") or ".glyphchain_state"))
        path = state_root / "participation" / "network-participation.json"
    if not path.exists():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        limit = int(value.get("storage_limit_bytes"))
    except (OSError, ValueError, TypeError, json.JSONDecodeError, AttributeError):
        return None
    return limit if MIN_MAX_BYTES <= limit <= MAX_MAX_BYTES else None


def configured_ledger_limit_bytes() -> int:
    explicit_raw = str(os.getenv("GLYPHCHAIN_LEDGER_MAX_BYTES", "") or "").strip()
    explicit = None
    if explicit_raw:
        try:
            explicit = int(explicit_raw)
        except ValueError as exc:
            raise LedgerStorageLimitError("glyphchain_ledger_storage_limit_invalid") from exc
        if not MIN_MAX_BYTES <= explicit <= MAX_MAX_BYTES:
            raise LedgerStorageLimitError("glyphchain_ledger_storage_limit_invalid")
    participation = _participation_limit()
    candidates = [value for value in (explicit, participation) if value is not None]
    return min(candidates) if candidates else DEFAULT_MAX_BYTES


def storage_files(db_path: Path) -> tuple[Path, Path, Path]:
    path = Path(db_path)
    return path, Path(str(path) + "-wal"), Path(str(path) + "-shm")


def ledger_storage_status(db_path: Path, *, max_bytes: int | None = None) -> dict[str, Any]:
    limit = int(max_bytes if max_bytes is not None else configured_ledger_limit_bytes())
    sizes = []
    for path in storage_files(Path(db_path)):
        try:
            sizes.append(int(path.stat().st_size))
        except FileNotFoundError:
            sizes.append(0)
    used = sum(sizes)
    remaining = max(0, limit - used)
    ratio = (used / limit) if limit > 0 else 1.0
    return {
        "schema_version": "glyphchain.ledger-storage-status.v1",
        "max_bytes": limit,
        "used_bytes": used,
        "remaining_bytes": remaining,
        "database_bytes": sizes[0],
        "wal_bytes": sizes[1],
        "shared_memory_bytes": sizes[2],
        "utilization_percent": round(ratio * 100.0, 3),
        "near_capacity": ratio >= 0.9,
        "at_capacity": used >= limit,
        "policy": "fail_closed_no_automatic_pruning",
    }


def write_reserve_bytes(max_bytes: int) -> int:
    configured = str(os.getenv("GLYPHCHAIN_LEDGER_RESERVE_BYTES", "") or "").strip()
    if configured:
        try:
            reserve = int(configured)
        except ValueError as exc:
            raise LedgerStorageLimitError("glyphchain_ledger_storage_reserve_invalid") from exc
        if reserve < 0 or reserve >= max_bytes:
            raise LedgerStorageLimitError("glyphchain_ledger_storage_reserve_invalid")
        return reserve
    return min(64 * 1024 * 1024, max(1 * 1024 * 1024, int(max_bytes * 0.05)))


def assert_ledger_write_capacity(
    db_path: Path,
    *,
    estimated_growth_bytes: int,
    max_bytes: int | None = None,
) -> dict[str, Any]:
    status = ledger_storage_status(db_path, max_bytes=max_bytes)
    estimate = max(0, int(estimated_growth_bytes))
    reserve = write_reserve_bytes(int(status["max_bytes"]))
    writable_limit = int(status["max_bytes"]) - reserve
    if int(status["used_bytes"]) + estimate > writable_limit:
        raise LedgerStorageLimitError("glyphchain_ledger_storage_capacity_reached")
    return {**status, "write_reserve_bytes": reserve, "estimated_growth_bytes": estimate}


def configure_sqlite_storage_bounds(
    connection: sqlite3.Connection,
    db_path: Path,
    *,
    max_bytes: int | None = None,
) -> dict[str, Any]:
    """Apply a hard main-database page bound and bounded WAL checkpoint policy."""
    limit = int(max_bytes if max_bytes is not None else configured_ledger_limit_bytes())
    reserve = write_reserve_bytes(limit)
    assert_ledger_write_capacity(Path(db_path), estimated_growth_bytes=0, max_bytes=limit)
    cursor = connection.cursor()
    page_size = int(cursor.execute("PRAGMA page_size").fetchone()[0] or 4096)
    current_pages = int(cursor.execute("PRAGMA page_count").fetchone()[0] or 0)
    database_budget = max(page_size, limit - reserve)
    requested_pages = max(1, database_budget // page_size)
    if current_pages > requested_pages:
        raise LedgerStorageLimitError("glyphchain_ledger_storage_already_exceeds_limit")
    applied_pages = int(cursor.execute(f"PRAGMA max_page_count={requested_pages}").fetchone()[0])
    checkpoint_pages = _bounded_int(
        os.getenv("GLYPHCHAIN_LEDGER_WAL_AUTOCHECKPOINT_PAGES", "64"),
        64,
        minimum=16,
        maximum=4096,
    )
    cursor.execute(f"PRAGMA wal_autocheckpoint={checkpoint_pages}")
    cursor.execute(f"PRAGMA journal_size_limit={max(page_size, reserve // 2)}")
    status = ledger_storage_status(Path(db_path), max_bytes=limit)
    return {
        **status,
        "page_size": page_size,
        "database_page_limit": applied_pages,
        "wal_autocheckpoint_pages": checkpoint_pages,
        "write_reserve_bytes": reserve,
    }
