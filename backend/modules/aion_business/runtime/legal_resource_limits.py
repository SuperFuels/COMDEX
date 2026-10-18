"""Shared, fail-closed storage and enumeration bounds for Legal workspaces."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Iterable, TypeVar


ErrorT = TypeVar("ErrorT", bound=Exception)


def _bounded_env(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(str(os.getenv(name, default)).strip())
    except (TypeError, ValueError):
        value = default
    return max(minimum, min(value, maximum))


def configured_legal_workspace_record_limit() -> int:
    return _bounded_env("TESSARIS_LEGAL_WORKSPACE_MAX_RECORDS", 5_000, 100, 100_000)


def configured_legal_workspace_bytes_limit() -> int:
    return _bounded_env(
        "TESSARIS_LEGAL_WORKSPACE_MAX_BYTES",
        5 * 1024 * 1024 * 1024,
        100 * 1024 * 1024,
        100 * 1024 * 1024 * 1024,
    )


def configured_legal_record_bytes_limit() -> int:
    return _bounded_env(
        "TESSARIS_LEGAL_MAX_ENCRYPTED_RECORD_BYTES",
        256 * 1024 * 1024,
        1 * 1024 * 1024,
        1024 * 1024 * 1024,
    )


def estimated_encrypted_record_bytes(record: Any) -> int:
    # The authenticated encrypted envelope is encoded text.  Twice the canonical
    # JSON size plus fixed headroom is deliberately conservative.
    raw = json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return (len(raw) * 2) + (64 * 1024)


def bounded_record_paths(
    folder: Path,
    patterns: Iterable[str],
    *,
    error_type: type[ErrorT],
) -> list[Path]:
    """Return a complete bounded record set or fail instead of partial results."""

    maximum = configured_legal_workspace_record_limit()
    unique: dict[str, Path] = {}
    if not folder.exists():
        return []
    for pattern in patterns:
        for path in folder.glob(pattern):
            unique.setdefault(path.stem, path)
            if len(unique) > maximum:
                raise error_type("legal_workspace_record_limit_exceeded")
    return list(unique.values())


def ensure_workspace_record_write(
    *,
    workspace_folder: Path,
    record_path: Path,
    record_patterns: Iterable[str],
    estimated_bytes: int,
    error_type: type[ErrorT],
) -> None:
    """Reject writes exceeding a per-component workspace record or byte quota."""

    if estimated_bytes > configured_legal_record_bytes_limit():
        raise error_type("legal_record_size_limit_exceeded")
    workspace_folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        os.chmod(workspace_folder, 0o700)
    except OSError:
        pass
    records = bounded_record_paths(workspace_folder, record_patterns, error_type=error_type)
    known_stems = {path.stem for path in records}
    if not record_path.exists() and record_path.stem not in known_stems:
        if len(known_stems) >= configured_legal_workspace_record_limit():
            raise error_type("legal_workspace_record_limit_exceeded")

    maximum_bytes = configured_legal_workspace_bytes_limit()
    used = 0
    file_count = 0
    maximum_files = configured_legal_workspace_record_limit() * 8
    for path in workspace_folder.rglob("*"):
        if path.is_symlink() or not path.is_file():
            continue
        file_count += 1
        if file_count > maximum_files:
            raise error_type("legal_workspace_file_limit_exceeded")
        try:
            used += path.stat().st_size
        except OSError:
            raise error_type("legal_workspace_storage_measurement_failed") from None
        if used > maximum_bytes:
            raise error_type("legal_workspace_storage_limit_exceeded")
    existing = record_path.stat().st_size if record_path.exists() else 0
    if used - existing + max(0, int(estimated_bytes)) > maximum_bytes:
        raise error_type("legal_workspace_storage_limit_exceeded")
