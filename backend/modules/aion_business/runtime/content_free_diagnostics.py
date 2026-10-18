from __future__ import annotations

import hashlib
import json
import os
import platform
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from backend.modules.aion_business.runtime.node_installation_layout import (
    default_node_installation_layout,
)


DIAGNOSTIC_EVENT_SCHEMA = "tessaris.node-diagnostic-event.v1"
BOOTSTRAP_STATUS_SCHEMA = "tessaris.node-bootstrap-status.v1"


def _system_name(value: str | None = None) -> str:
    current = str(value or platform.system()).strip().lower()
    return {"darwin": "darwin", "windows": "windows", "linux": "linux"}.get(
        current, current
    )


def default_node_diagnostics_root(
    *,
    system: str | None = None,
    environment: Mapping[str, str] | None = None,
) -> Path:
    """Return the disposable diagnostics root outside app, updater and Vault roots."""

    env = dict(os.environ if environment is None else environment)
    layout = default_node_installation_layout(
        system=_system_name(system), environment=env
    )
    return Path(layout.node_state_root).expanduser() / "diagnostics"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def fingerprint(value: Any) -> str:
    return hashlib.sha256(str(value).encode("utf-8", errors="replace")).hexdigest()


def atomic_write_json(path: str | Path, payload: Mapping[str, Any]) -> Path:
    destination = Path(path).expanduser()
    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", dir=destination.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(dict(payload), handle, sort_keys=True, separators=(",", ":"))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        try:
            temporary.chmod(0o600)
        except OSError:
            pass
        os.replace(temporary, destination)
        try:
            destination.chmod(0o600)
        except OSError:
            pass
    finally:
        temporary.unlink(missing_ok=True)
    return destination


def append_diagnostic_event(
    path: str | Path,
    *,
    event_type: str,
    code: str,
    source_fingerprint: str,
    detail_fingerprint: str,
    line: int | None = None,
    max_bytes: int = 1_000_000,
) -> dict[str, Any]:
    """Append a content-free event; raw messages and paths are intentionally absent."""

    event = {
        "schema_version": DIAGNOSTIC_EVENT_SCHEMA,
        "recorded_at": utc_now(),
        "event_type": str(event_type),
        "code": str(code),
        "source_fingerprint": str(source_fingerprint),
        "detail_fingerprint": str(detail_fingerprint),
        "line": int(line or 0),
        "content_free": True,
    }
    destination = Path(path).expanduser()
    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    encoded = json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n"
    limit = int(max_bytes)
    if limit < len(encoded.encode("utf-8")):
        raise ValueError("diagnostic_event_size_limit_invalid")
    try:
        current_size = destination.stat().st_size
    except FileNotFoundError:
        current_size = 0
    if current_size + len(encoded.encode("utf-8")) > limit:
        rotated = destination.with_suffix(destination.suffix + ".1")
        rotated.unlink(missing_ok=True)
        destination.replace(rotated)
        try:
            rotated.chmod(0o600)
        except OSError:
            pass
    descriptor = os.open(
        destination,
        os.O_APPEND | os.O_CREAT | os.O_WRONLY,
        0o600,
    )
    try:
        with os.fdopen(descriptor, "a", encoding="utf-8") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
    finally:
        try:
            destination.chmod(0o600)
        except OSError:
            pass
    return event
