# backend/modules/lean/lean_audit.py
# -*- coding: utf-8 -*-

"""
Lean Audit Log (JSONL)
─────────────────────────────────────────────
Single audit stream for Lean-related actions:
  - inject (container <- Lean)
  - export (container -> Lean)
  - verify (optional: container verification)
  - viz (optional: proof graph generation)

Design:
  * append-only JSONL
  * safe rotation by size
  * stable event builders used by CLI + API
  * small query helpers (tail/search/list)

Fixes included:
  ✅ remove buggy/duplicate get_last_audit_events (AUDIT_LOG_PATH / Path misuse)
  ✅ keep one canonical get_last_audit_events as alias to tail
  ✅ normalize validation_errors consistently
"""

from __future__ import annotations

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

def _utc_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


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
    Ensure validation_errors are structured dicts with {code,message}.
    Backward compatible:
      - list[str] -> wrap each
      - str -> wrap
      - dict -> wrap
      - list[dict] -> pass through (best-effort)
    """
    if not errors:
        return []

    out: List[Dict[str, str]] = []

    def wrap_one(e: Any) -> Dict[str, str]:
        if isinstance(e, dict):
            code = str(e.get("code", "E000"))
            msg = str(e.get("message", e))
            return {"code": code, "message": msg}
        return {"code": "E000", "message": str(e)}

    if isinstance(errors, list):
        for e in errors:
            out.append(wrap_one(e))
        return out

    # scalar/dict
    out.append(wrap_one(errors))
    return out


# ──────────────────────────────
# Audit writing
# ──────────────────────────────

def audit_event(event: Dict[str, Any], path: str = DEFAULT_PATH) -> None:
    """
    Append an audit event into the JSONL audit log.
    Each event is one line of JSON.
    Rotates the log file if it exceeds MAX_SIZE_MB.
    """
    root = os.path.dirname(path) or "."
    os.makedirs(root, exist_ok=True)
    _rotate_if_needed(path)
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"[lean_audit] audit_event write failed: {e}")


# ──────────────────────────────
# Event builders (used by CLI/API)
# ──────────────────────────────

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
    """Build an audit record for a container <- Lean injection."""
    v_errors = _normalize_validation_errors(validation_errors or [])
    evt: Dict[str, Any] = {
        "ts": _utc_iso(),
        "kind": "lean.inject",
        "container_path": container_path,
        "container_id": container_id,
        "lean_path": lean_path,
        "count": int(num_items),
        "previews": previews or [],
        "origin": origin,
        "validation_errors": v_errors,
        "validation_errors_version": "v1",
        "hash": _sha1(f"{container_path}|{lean_path}|{num_items}|{previews or []}"),
    }
    if extra:
        evt.update(extra)
    return evt


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
    """Build an audit record for a Lean -> container export."""
    v_errors = _normalize_validation_errors(validation_errors or [])
    evt: Dict[str, Any] = {
        "ts": _utc_iso(),
        "kind": "lean.export",
        "out_path": out_path,
        "container_id": container_id,
        "container_type": container_type,
        "lean_path": lean_path,
        "count": int(num_items),
        "previews": previews or [],
        "origin": origin,
        "validation_errors": v_errors,
        "validation_errors_version": "v1",
        "hash": _sha1(f"{out_path}|{lean_path}|{num_items}|{previews or []}"),
    }
    if extra:
        evt.update(extra)
    return evt


def build_verify_event(
    *,
    container_path: str,
    container_id: Optional[str] = None,
    status: str = "ok",
    extra: Optional[Dict[str, Any]] = None,
    validation_errors: Optional[List[Any]] = None,
    origin: str = "CLI",
) -> Dict[str, Any]:
    """
    Optional audit record for verification steps.
    (Only used if/when verifier emits it.)
    """
    v_errors = _normalize_validation_errors(validation_errors or [])
    evt: Dict[str, Any] = {
        "ts": _utc_iso(),
        "kind": "lean.verify",
        "container_path": container_path,
        "container_id": container_id,
        "status": status,
        "origin": origin,
        "validation_errors": v_errors,
        "validation_errors_version": "v1",
        "hash": _sha1(f"{container_path}|{container_id}|{status}|{len(v_errors)}"),
    }
    if extra:
        evt.update(extra)
    return evt


def build_viz_event(
    *,
    container_path: str,
    container_id: Optional[str] = None,
    png_out: Optional[str] = None,
    status: str = "ok",
    extra: Optional[Dict[str, Any]] = None,
    origin: str = "CLI",
) -> Dict[str, Any]:
    """
    Optional audit record for visualization generation steps.
    """
    evt: Dict[str, Any] = {
        "ts": _utc_iso(),
        "kind": "lean.viz",
        "container_path": container_path,
        "container_id": container_id,
        "png_out": png_out,
        "status": status,
        "origin": origin,
        "hash": _sha1(f"{container_path}|{container_id}|{png_out}|{status}"),
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
    if n <= 0:
        return []
    if not os.path.exists(path):
        return []

    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()[-n:]
        out: List[Dict[str, Any]] = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return out
    except Exception as e:
        print(f"[lean_audit] tail_audit_events failed: {e}")
        return []


def get_last_audit_events(n: int = 20, path: str = DEFAULT_PATH) -> List[Dict[str, Any]]:
    """
    Compatibility helper for older API routes.
    Canonical alias for tail_audit_events.
    """
    return tail_audit_events(n=n, path=path)


def search_audit_events(keyword: str, path: str = DEFAULT_PATH) -> List[Dict[str, Any]]:
    """
    Search audit log for events containing a keyword (in JSON string form).
    """
    if not keyword:
        return []
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
    root = os.path.dirname(base) or "."
    prefix = os.path.basename(base)
    if not os.path.exists(root):
        return []
    try:
        return sorted(
            [os.path.join(root, f) for f in os.listdir(root) if f.startswith(prefix)]
        )
    except Exception:
        return []