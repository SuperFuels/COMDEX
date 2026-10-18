from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


EVIDENCE_SOURCE_SCHEMA_VERSION = "aion.goal_engine.evidence_source.v1"

SUPPORTED_EVIDENCE_TYPES = {
    "manual_confirmation",
}

DEFAULT_MIN_EVIDENCE_CONFIDENCE = 0.7


@dataclass(frozen=True)
class EvidenceSourceContract:
    evidence_id: str
    evidence_type: str
    source: str
    source_connector: str | None = None
    source_ref: str | None = None
    confidence: float = 0.0
    freshness: str | None = None
    provenance: dict[str, Any] = field(default_factory=dict)
    verified: bool = False
    created_at: str | None = None
    notes: str = ""

    def validate(self) -> list[str]:
        errors: list[str] = []

        if not str(self.evidence_id or "").strip():
            errors.append("evidence_id is required")

        if not str(self.evidence_type or "").strip():
            errors.append("evidence_type is required")
        elif self.evidence_type not in SUPPORTED_EVIDENCE_TYPES:
            errors.append("unsupported evidence_type")

        if not str(self.source or "").strip() and not str(self.source_connector or "").strip():
            errors.append("evidence source or source_connector is required")

        if not 0 <= float(self.confidence or 0) <= 1:
            errors.append("confidence must be between 0 and 1")

        return errors


def normalize_evidence_source(value: Any) -> EvidenceSourceContract | None:
    if isinstance(value, EvidenceSourceContract):
        return value

    if not isinstance(value, dict):
        return None

    return EvidenceSourceContract(
        evidence_id=str(value.get("evidence_id") or value.get("id") or "").strip(),
        evidence_type=str(value.get("evidence_type") or value.get("type") or "").strip(),
        source=str(value.get("source") or "").strip(),
        source_connector=(
            str(value.get("source_connector")).strip()
            if value.get("source_connector") is not None
            else None
        ),
        source_ref=(
            str(value.get("source_ref")).strip()
            if value.get("source_ref") is not None
            else None
        ),
        confidence=float(value.get("confidence") or 0),
        freshness=(
            str(value.get("freshness")).strip()
            if value.get("freshness") is not None
            else None
        ),
        provenance=dict(value.get("provenance") or {})
        if isinstance(value.get("provenance"), dict)
        else {},
        verified=bool(value.get("verified") is True),
        created_at=(
            str(value.get("created_at")).strip()
            if value.get("created_at") is not None
            else None
        ),
        notes=str(value.get("notes") or ""),
    )


def validate_evidence_source(
    value: Any,
    *,
    min_confidence: float = DEFAULT_MIN_EVIDENCE_CONFIDENCE,
) -> dict[str, Any]:
    evidence = normalize_evidence_source(value)

    if evidence is None:
        return {
            "schema_version": EVIDENCE_SOURCE_SCHEMA_VERSION,
            "valid": False,
            "supports_outcome_success": False,
            "blocked_reasons": ["invalid_evidence_source"],
            "evidence": {},
        }

    errors = evidence.validate()
    blocked_reasons = list(errors)

    confidence = float(evidence.confidence or 0)

    if confidence < min_confidence:
        blocked_reasons.append("evidence_confidence_below_threshold")

    if not evidence.verified:
        blocked_reasons.append("evidence_not_verified")

    supports_outcome_success = (
        not blocked_reasons
        and evidence.evidence_type == "manual_confirmation"
        and evidence.verified is True
        and confidence >= min_confidence
    )

    return {
        "schema_version": EVIDENCE_SOURCE_SCHEMA_VERSION,
        "valid": not bool(errors),
        "supports_outcome_success": supports_outcome_success,
        "blocked_reasons": blocked_reasons,
        "evidence": asdict(evidence),
        "confidence": confidence,
        "min_confidence": min_confidence,
        "evidence_type": evidence.evidence_type,
        "verified": evidence.verified,
        "source": evidence.source,
        "source_connector": evidence.source_connector,
        "source_ref": evidence.source_ref,
    }


def summarize_evidence_sources(
    evidence_items: list[Any],
    *,
    min_confidence: float = DEFAULT_MIN_EVIDENCE_CONFIDENCE,
) -> dict[str, Any]:
    validations = [
        validate_evidence_source(item, min_confidence=min_confidence)
        for item in evidence_items
    ]

    supported = [
        item for item in validations
        if item.get("supports_outcome_success") is True
    ]

    blocked_reasons: list[str] = []
    for validation in validations:
        for reason in validation.get("blocked_reasons") or []:
            reason_text = str(reason or "").strip()
            if reason_text and reason_text not in blocked_reasons:
                blocked_reasons.append(reason_text)

    return {
        "schema_version": EVIDENCE_SOURCE_SCHEMA_VERSION,
        "trace_type": "evidence_source_summary",
        "evidence_count": len(validations),
        "supported_evidence_count": len(supported),
        "blocked_evidence_count": len(validations) - len(supported),
        "supports_outcome_success": len(supported) > 0,
        "blocked_reasons": blocked_reasons,
        "validations": validations,
    }

from hashlib import sha256
import json

EVIDENCE_POINTER_SCHEMA_VERSION = "aion.goal_engine.evidence_pointer.v1"

SUPPORTED_EVIDENCE_POINTER_TYPES = {
    "gmail_reply",
    "crm_lead",
    "utm_click",
    "booking",
    "payment",
    "revenue",
    "screenshot",
    "file",
    "manual",
}


def stable_evidence_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload or {}, sort_keys=True, separators=(",", ":"), default=str)
    return sha256(encoded.encode("utf-8")).hexdigest()


def build_evidence_pointer_preview(
    *,
    evidence_type: str,
    reference_pointer: str,
    source: str = "",
    payload: dict[str, Any] | None = None,
    confidence: float = 0.0,
) -> dict[str, Any]:
    """
    Canonical evidence pointer preview.

    This creates a stable reference/hash shell only. It does not read Gmail,
    CRM, analytics, bookings, payment systems, screenshots, or files.
    """
    payload = dict(payload or {})
    evidence_type = str(evidence_type or "").strip()
    reference_pointer = str(reference_pointer or "").strip()
    source = str(source or "").strip()

    blocked_reasons: list[str] = []

    if evidence_type not in SUPPORTED_EVIDENCE_POINTER_TYPES:
        blocked_reasons.append("unsupported_evidence_pointer_type")

    if not reference_pointer:
        blocked_reasons.append("reference_pointer_required")

    if not source:
        blocked_reasons.append("source_required")

    try:
        confidence_value = float(confidence or 0.0)
    except Exception:
        confidence_value = 0.0

    if confidence_value < 0.0 or confidence_value > 1.0:
        blocked_reasons.append("confidence_out_of_range")

    hash_payload = {
        "evidence_type": evidence_type,
        "reference_pointer": reference_pointer,
        "source": source,
        "payload": payload,
    }

    return {
        "schema_version": EVIDENCE_POINTER_SCHEMA_VERSION,
        "runtime": "aion_goal_engine",
        "trace_type": "evidence_pointer_preview",
        "evidence_type": evidence_type,
        "reference_pointer": reference_pointer,
        "source": source,
        "payload": payload,
        "confidence": confidence_value,
        "evidence_hash": stable_evidence_hash(hash_payload),
        "valid": not blocked_reasons,
        "blocked_reasons": blocked_reasons,
        "resolved": False,
        "would_read_external": False,
        "would_write_external": False,
        "would_grant_permission": False,
        "dry_run_only": True,
    }
