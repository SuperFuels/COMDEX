"""Shared retention and legal-hold rules for protected Legal records."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import json
from typing import Any, Mapping
from uuid import uuid4


class LegalRecordGovernanceError(ValueError):
    pass


def iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def default_governance() -> dict[str, Any]:
    return {
        "retention_policy": "OWNER_CONTROLLED",
        "retain_until": None,
        "legal_hold": False,
        "legal_hold_reason": None,
        "legal_hold_changed_at": None,
        "legal_hold_changed_by": None,
        "last_exported_at": None,
    }


def governance_for(record: Mapping[str, Any]) -> dict[str, Any]:
    return {**default_governance(), **deepcopy(dict(record.get("records_governance") or {}))}


def update_governance(
    record: dict[str, Any],
    *,
    now: datetime,
    actor_id: str,
    retain_until: str | None = None,
    legal_hold: bool | None = None,
    legal_hold_reason: str = "",
) -> tuple[dict[str, Any], dict[str, Any]]:
    current = governance_for(record)
    changes: dict[str, Any] = {}
    if retain_until is not None:
        parsed = _parse_timestamp(retain_until)
        current["retain_until"] = iso(parsed) if parsed else None
        changes["retain_until"] = current["retain_until"]
    if legal_hold is not None:
        reason = " ".join(str(legal_hold_reason or "").split()).strip()[:1000]
        if legal_hold and not reason:
            raise LegalRecordGovernanceError("legal_hold_reason_required")
        current.update({
            "legal_hold": bool(legal_hold),
            "legal_hold_reason": reason if legal_hold else None,
            "legal_hold_changed_at": iso(now),
            "legal_hold_changed_by": str(actor_id or "unknown")[:160],
        })
        changes.update({"legal_hold": bool(legal_hold), "legal_hold_reason_recorded": bool(reason)})
    if not changes:
        raise LegalRecordGovernanceError("retention_or_legal_hold_change_required")
    record["records_governance"] = current
    return current, changes


def mark_exported(record: dict[str, Any], now: datetime) -> None:
    current = governance_for(record)
    current["last_exported_at"] = iso(now)
    record["records_governance"] = current


def assert_deletable(record: Mapping[str, Any], *, now: datetime, terminal: bool) -> None:
    governance = governance_for(record)
    if governance["legal_hold"]:
        raise LegalRecordGovernanceError("record_is_under_legal_hold")
    if not terminal:
        raise LegalRecordGovernanceError("record_must_be_closed_or_terminal_before_deletion")
    retain_until = _parse_timestamp(governance.get("retain_until"))
    if retain_until is None:
        raise LegalRecordGovernanceError("retention_end_date_required_before_deletion")
    if now.astimezone(timezone.utc) < retain_until:
        raise LegalRecordGovernanceError("retention_period_has_not_elapsed")
    if not governance.get("last_exported_at"):
        raise LegalRecordGovernanceError("record_export_required_before_deletion")


def destruction_receipt(
    record: Mapping[str, Any],
    *,
    record_type: str,
    record_id: str,
    workspace_id: str,
    actor_id: str,
    now: datetime,
) -> dict[str, Any]:
    return {
        "schema_version": "tessaris.legal-record-destruction-receipt.v1",
        "receipt_id": f"destroy-{uuid4().hex}",
        "record_type": record_type,
        "record_id": record_id,
        "workspace_id": workspace_id,
        "destroyed_at": iso(now),
        "destroyed_by": str(actor_id or "unknown")[:160],
        "destroyed_record_sha256": sha256(canonical(record)).hexdigest(),
        "retention": governance_for(record),
        "notice": "This receipt proves which encrypted local record was destroyed; it does not contain the record content.",
    }


def _parse_timestamp(value: Any) -> datetime | None:
    clean = str(value or "").strip()
    if not clean:
        return None
    try:
        parsed = datetime.fromisoformat(clean.replace("Z", "+00:00"))
    except ValueError as exc:
        raise LegalRecordGovernanceError("retain_until_must_be_iso8601") from exc
    if parsed.tzinfo is None:
        raise LegalRecordGovernanceError("retain_until_timezone_required")
    return parsed.astimezone(timezone.utc)
