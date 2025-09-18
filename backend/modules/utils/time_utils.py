# backend/modules/utils/time_utils.py
from datetime import datetime, timezone

def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def now_utc_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)

def now_utc_iso_z() -> str:
    # ISO8601 without tzinfo + 'Z' (e.g., 2025-01-01T12:34:56.789Z)
    return datetime.now(timezone.utc).replace(tzinfo=None).isoformat() + "Z"