from __future__ import annotations

from datetime import datetime
import hashlib
import re
from typing import Any, Dict, Iterable, Optional


_CODE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
_SAFE_STATUSES = {
    "created",
    "starting",
    "running",
    "paused",
    "stopping",
    "stopped",
    "degraded",
    "error",
    "unknown",
}
_SAFE_COMMANDS = {"none", "running", "pause", "resume", "stop"}
_SAFE_ACTOR_CLASSES = {
    "system",
    "founder",
    "guardian",
    "cloud_control",
    "updater",
    "operator",
}
_SAFE_REASON_CODES = {
    "initialized",
    "user_request",
    "remote_command",
    "update_required",
    "maintenance",
    "policy_blocked",
    "resource_limit",
    "shutdown",
    "unspecified",
}
_SAFE_ERROR_CODES = {
    "authentication_error",
    "authorization_error",
    "connection_error",
    "dependency_unavailable",
    "network_error",
    "policy_blocked",
    "rate_limited",
    "runtime_error",
    "sync_error",
    "timeout",
    "unclassified_error",
}
_SAFE_METADATA_COUNTERS = {
    "approved_count",
    "cancelled_count",
    "completed_count",
    "failed_count",
    "pending_download_count",
    "pending_upload_count",
    "queued_count",
    "rejected_count",
    "running_count",
    "waiting_approval_count",
}
_SAFE_METADATA_FLAGS = {"connected", "healthy", "offline", "ready"}


def diagnostic_fingerprint(value: Any) -> Optional[str]:
    """Return a one-way correlation value without retaining diagnostic text."""
    if value is None:
        return None
    raw = str(value)
    if not raw:
        return None
    return hashlib.sha256(raw.encode("utf-8", errors="replace")).hexdigest()


def safe_fingerprint(value: Any, *, fallback_value: Any = None) -> Optional[str]:
    candidate = str(value or "").strip().lower()
    if re.fullmatch(r"[0-9a-f]{64}", candidate):
        return candidate
    return diagnostic_fingerprint(fallback_value)


def safe_status(value: Any) -> str:
    candidate = str(value or "unknown").strip().lower()
    return candidate if candidate in _SAFE_STATUSES else "unknown"


def safe_command(value: Any) -> str:
    candidate = str(value or "none").strip().lower()
    return candidate if candidate in _SAFE_COMMANDS else "none"


def safe_actor_class(value: Any) -> str:
    candidate = str(value or "system").strip().lower()
    return candidate if candidate in _SAFE_ACTOR_CLASSES else "operator"


def safe_reason_code(value: Any) -> Optional[str]:
    if value is None or str(value).strip() == "":
        return None
    candidate = str(value).strip().lower()
    return candidate if candidate in _SAFE_REASON_CODES else "unspecified"


def safe_error_code(value: Any) -> Optional[str]:
    if value is None or str(value).strip() == "":
        return None
    candidate = str(value).strip().lower()
    if candidate in _SAFE_ERROR_CODES:
        return candidate

    lowered = candidate
    if "timeout" in lowered or "timed out" in lowered:
        return "timeout"
    if "rate limit" in lowered or "too many requests" in lowered:
        return "rate_limited"
    if "auth" in lowered or "oauth" in lowered or "sign in" in lowered:
        return "authentication_error"
    if "permission" in lowered or "forbidden" in lowered:
        return "authorization_error"
    if "network" in lowered or "connection" in lowered:
        return "network_error"
    if "policy" in lowered or "blocked" in lowered:
        return "policy_blocked"
    if "sync" in lowered:
        return "sync_error"
    return "unclassified_error"


def safe_timestamp(value: Any) -> Optional[str]:
    if not isinstance(value, str) or not value or len(value) > 64:
        return None
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return value


def safe_identifier(value: Any, *, fallback: Optional[str] = None) -> Optional[str]:
    """Allow only bounded machine identifiers, never arbitrary prose."""
    if value is None:
        return fallback
    candidate = str(value).strip()
    if _CODE_RE.fullmatch(candidate):
        return candidate
    return fallback


def content_free_metadata(value: Any) -> Dict[str, Any]:
    """Retain only explicitly approved primitive health counters and flags."""
    if not isinstance(value, dict):
        return {}
    clean: Dict[str, Any] = {}
    for key in _SAFE_METADATA_COUNTERS:
        raw = value.get(key)
        if isinstance(raw, bool):
            continue
        if isinstance(raw, int):
            clean[key] = max(0, raw)
    for key in _SAFE_METADATA_FLAGS:
        raw = value.get(key)
        if isinstance(raw, bool):
            clean[key] = raw
    return clean


def safe_counter(value: Any) -> int:
    if isinstance(value, bool):
        return 0
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def first_safe_timestamp(values: Iterable[Any]) -> Optional[str]:
    for value in values:
        clean = safe_timestamp(value)
        if clean:
            return clean
    return None
