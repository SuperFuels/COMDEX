from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


REQUIRED_FOUNDATION_FIELDS = (
    "business_name",
    "industry",
    "business_type",
    "service_area",
    "primary_goal",
)

APPROVED_FOUNDATION_FILENAME = "approved_foundation.json"
FOUNDATION_RECEIPT_FILENAME = "foundation_receipt.json"


def _clean_string(value: Any) -> str:
    return str(value or "").strip()


def _safe_business_id(value: str) -> str:
    raw = _clean_string(value).lower()
    raw = re.sub(r"[^a-z0-9_-]+", "-", raw)
    raw = raw.strip("-")
    return raw or "business"


def canonicalise_foundation(foundation: Mapping[str, Any] | None) -> dict[str, Any]:
    source = dict(foundation or {})
    canonical: dict[str, Any] = {}

    for key in sorted(source):
        value = source[key]
        if isinstance(value, str):
            canonical[key] = value.strip()
        elif value is None:
            canonical[key] = ""
        else:
            canonical[key] = value

    return canonical


def get_missing_required_foundation_fields(
    foundation: Mapping[str, Any] | None,
) -> list[str]:
    canonical = canonicalise_foundation(foundation)
    return [
        field
        for field in REQUIRED_FOUNDATION_FIELDS
        if not _clean_string(canonical.get(field))
    ]


def foundation_is_approvable(foundation: Mapping[str, Any] | None) -> bool:
    return not get_missing_required_foundation_fields(foundation)


def compute_foundation_hash(foundation: Mapping[str, Any] | None) -> str:
    canonical = canonicalise_foundation(foundation)
    payload = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_foundation_receipt(
    *,
    business_id: str,
    foundation: Mapping[str, Any],
    approved_by: str = "founder",
    source: str = "small_business_foundation_review",
) -> dict[str, Any]:
    canonical = canonicalise_foundation(foundation)
    foundation_hash = compute_foundation_hash(canonical)

    return {
        "receipt_type": "small_business_foundation_approval",
        "business_id": _safe_business_id(business_id),
        "approved": True,
        "approved_by": _clean_string(approved_by) or "founder",
        "approved_at": datetime.now(timezone.utc).isoformat(),
        "source": _clean_string(source) or "small_business_foundation_review",
        "foundation_hash": foundation_hash,
        "required_fields": list(REQUIRED_FOUNDATION_FIELDS),
        "missing_required_fields": get_missing_required_foundation_fields(canonical),
        "live_side_effects": {
            "external_message_sent": False,
            "payment_created": False,
            "booking_created": False,
            "publishing_performed": False,
            "chain_write_performed": False,
        },
    }


def business_foundation_container(root: str | Path, business_id: str) -> Path:
    return Path(root) / "aion_businesses" / _safe_business_id(business_id) / "foundation"


def approve_and_persist_foundation(
    *,
    root: str | Path,
    business_id: str,
    foundation: Mapping[str, Any],
    approved_by: str = "founder",
    source: str = "small_business_foundation_review",
) -> dict[str, Any]:
    canonical = canonicalise_foundation(foundation)
    missing = get_missing_required_foundation_fields(canonical)

    if missing:
        return {
            "ok": False,
            "approved": False,
            "business_id": _safe_business_id(business_id),
            "missing_required_fields": missing,
            "error": "foundation_missing_required_fields",
        }

    container = business_foundation_container(root, business_id)
    container.mkdir(parents=True, exist_ok=True)

    receipt = build_foundation_receipt(
        business_id=business_id,
        foundation=canonical,
        approved_by=approved_by,
        source=source,
    )

    approved_payload = {
        "foundation": canonical,
        "receipt": receipt,
    }

    foundation_path = container / APPROVED_FOUNDATION_FILENAME
    receipt_path = container / FOUNDATION_RECEIPT_FILENAME

    foundation_path.write_text(
        json.dumps(approved_payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    receipt_path.write_text(
        json.dumps(receipt, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {
        "ok": True,
        "approved": True,
        "business_id": _safe_business_id(business_id),
        "foundation_hash": receipt["foundation_hash"],
        "foundation_path": str(foundation_path),
        "receipt_path": str(receipt_path),
        "receipt": receipt,
    }


def departments_can_start_from_foundation(foundation_record: Mapping[str, Any] | None) -> bool:
    record = dict(foundation_record or {})
    receipt = dict(record.get("receipt") or {})
    foundation = dict(record.get("foundation") or {})

    if receipt.get("approved") is not True:
        return False

    expected_hash = compute_foundation_hash(foundation)
    return receipt.get("foundation_hash") == expected_hash
