# backend/modules/lean/lean_audit.py
import json
import os
import hashlib
import time
from typing import Any, Dict, List, Optional

DEFAULT_PATH = "data/lean_audit.jsonl"
MAX_SIZE_MB = 50  # rotate after 50 MB (tunable)


# ──────────────────────────────
# Internals
# ──────────────────────────────

def _sha1(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()


def _rotate_if_needed(path: str) -> None:
    """
    Rotate the audit file if it exceeds MAX_SIZE_MB.
    Keeps old files with a timestamp suffix.
    """
    try:
        if os.path.exists(path) and os.path.getsize(path) > MAX_SIZE_MB * 1024 * 1024:
            ts = time.strftime("%Y%m%d-%H%M%S", time.gmtime())
            rotated = f"{path}.{ts}.bak"
            os.rename(path, rotated)
    except Exception as e:
        # Fail gracefully; don't block audit logging
        print(f"[lean_audit] rotation check failed: {e}")


def _normalize_validation_errors(errors: Any) -> List[Dict[str, str]]:
    """
    Ensure validation_errors are structured dicts with codes/messages.
    Backward compatible: if list of strings, wrap them.
    """
    normalized: List[Dict[str, str]] = []
    if isinstance(errors, list):
        for e in errors:
            if isinstance(e, dict):
                normalized.append(e)
            else:
                normalized.append({"code": "E000", "message": str(e)})
    return normalized


# ──────────────────────────────
# Audit writing
# ──────────────────────────────

def audit_event(event: Dict[str, Any], path: str = DEFAULT_PATH) -> None:
    """
    Append an audit event into the JSONL audit log.
    Each event is one line of JSON.
    Rotates the log file if it exceeds MAX_SIZE_MB.
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    _rotate_if_needed(path)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


def build_inject_event(
    *,
    container_path: str,
    container_id: Optional[str],
    lean_path: str,
    num_items: int,
    previews: Optional[List[str]] = None,
    extra: Optional[Dict[str, Any]] = None,
    validation_errors: Optional[List[Any]] = None,
    origin: str = "CLI",
) -> Dict[str, Any]:
    """Build an audit record for a container → Lean injection."""
    v_errors = _normalize_validation_errors(validation_errors or [])
    evt: Dict[str, Any] = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "kind": "lean.inject",
        "container_path": container_path,
        "container_id": container_id,
        "lean_path": lean_path,
        "count": num_items,
        "previews": previews or [],
        "origin": origin,
        "validation_errors": v_errors,
        "validation_errors_version": "v1",
        "hash": _sha1(f"{container_path}|{lean_path}|{num_items}|{previews}"),
    }
    if extra:
        evt.update(extra)
    return evt

# ──────────────────────────────
# Audit query helpers
# ──────────────────────────────

def get_last_audit_events(n: int = 10) -> list[dict]:
    """
    Return the last N audit events from the audit log file.
    If the log file doesn't exist, return [].
    """
    path = AUDIT_LOG_PATH
    events = []
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        evt = json.loads(line)
                        events.append(evt)
                    except Exception:
                        continue
        return events[-n:]
    except Exception:
        return []

def build_export_event(
    *,
    out_path: Optional[str],
    container_id: Optional[str],
    container_type: Optional[str],
    lean_path: str,
    num_items: int,
    previews: Optional[List[str]] = None,
    extra: Optional[Dict[str, Any]] = None,
    validation_errors: Optional[List[Any]] = None,
    origin: str = "CLI",
) -> Dict[str, Any]:
    """Build an audit record for a Lean → container export."""
    v_errors = _normalize_validation_errors(validation_errors or [])
    evt: Dict[str, Any] = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "kind": "lean.export",
        "out_path": out_path,
        "container_id": container_id,
        "container_type": container_type,
        "lean_path": lean_path,
        "count": num_items,
        "previews": previews or [],
        "origin": origin,
        "validation_errors": v_errors,
        "validation_errors_version": "v1",
        "hash": _sha1(f"{out_path}|{lean_path}|{num_items}|{previews}"),
    }
    if extra:
        evt.update(extra)
    return evt


# ──────────────────────────────
# Audit reading (API/CLI helpers)
# ──────────────────────────────

def tail_audit_events(n: int = 50, path: str = DEFAULT_PATH) -> List[Dict[str, Any]]:
    """
    Return the last N audit events from the log file.
    Safe for use in CLI/API (e.g. /audit route).
    """
    if not os.path.exists(path):
        return []
    events: List[Dict[str, Any]] = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()[-n:]
        for line in lines:
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    except Exception as e:
        print(f"[lean_audit] tail_audit_events failed: {e}")
    return events


def search_audit_events(keyword: str, path: str = DEFAULT_PATH) -> List[Dict[str, Any]]:
    """
    Search audit log for events containing a keyword (in JSON string form).
    """
    if not os.path.exists(path):
        return []
    results: List[Dict[str, Any]] = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if keyword in line:
                    try:
                        results.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    except Exception as e:
        print(f"[lean_audit] search_audit_events failed: {e}")
    return results


def list_audit_files(base: str = DEFAULT_PATH) -> List[str]:
    """
    List current + rotated audit files.
    """
    root = os.path.dirname(base)
    prefix = os.path.basename(base)
    if not os.path.exists(root):
        return []
    return sorted(
        [os.path.join(root, f) for f in os.listdir(root) if f.startswith(prefix)]
    )

def get_last_audit_events(n: int = 20, path: str = DEFAULT_PATH) -> list[dict]:
    """
    Compatibility helper for API routes.
    Returns the last N audit events (alias for tail_audit_events).
    """
    return tail_audit_events(n, path)