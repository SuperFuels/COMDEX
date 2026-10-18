from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Type


def connect_private_sqlite(
    path: str | Path,
    *,
    timeout: float = 5.0,
    factory: Type[sqlite3.Connection] = sqlite3.Connection,
) -> sqlite3.Connection:
    """Open a Node database with owner-only directory and file permissions."""

    db_path = Path(path)
    if db_path.is_symlink():
        raise ValueError(f"private_sqlite_symlink_target_forbidden:{db_path}")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        db_path.parent.chmod(0o700)
    except OSError:
        pass
    connection = sqlite3.connect(db_path, timeout=timeout, factory=factory)
    try:
        db_path.chmod(0o600)
    except OSError:
        connection.close()
        raise
    connection.row_factory = sqlite3.Row
    return connection
