from __future__ import annotations

import re


BLOCKED_BUSINESS_IDS = {
    "",
    "global",
    "root",
    "session-vfs",
    "session_vfs",
    "tmp",
    "temp",
    "business-not-registered",
    "business_not_registered",
}


def canonical_business_id(value: str) -> str:
    """Return the one business/workspace/container identifier used by AION Business."""
    raw = str(value or "").strip().lower().replace("_", "-")
    normalized = re.sub(r"[^a-z0-9-]+", "-", raw)
    normalized = re.sub(r"-+", "-", normalized).strip("-")
    if normalized in BLOCKED_BUSINESS_IDS:
        raise ValueError("valid_registered_business_id_required")
    return normalized


def canonical_business_aliases(value: str) -> list[str]:
    canonical = canonical_business_id(value)
    aliases = {canonical, canonical.replace("-", "_")}
    raw = str(value or "").strip().lower()
    if raw:
        aliases.add(raw)
    return sorted(aliases)
