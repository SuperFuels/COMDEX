from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any, Dict, Mapping, Optional

from .human_review_decision_envelope import (
    build_default_home_fixed_human_review_decision_envelope,
    build_human_review_decision_envelope,
)


EVIDENCE_GAP_ENVELOPE_VERSION = "aion.lrm.evidence_gap_envelope.v0.1"

DEFAULT_REQUIRED_EVIDENCE = [
    "site_photo",
    "roof_or_pergola_measurements",
    "access_notes",
    "customer_contact_confirmation",
]


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _hash(prefix: str, value: Any) -> str:
    return f"{prefix}_{hashlib.sha256(_canonical(value).encode('utf-8')).hexdigest()[:32]}"


def _redact(value: Any) -> Any:
    forbidden = {
        "private_chain_of_thought",
        "chain_of_thought",
        "hidden_reasoning",
        "private_reasoning",
        "secret",
        "secrets",
        "password",
        "api_key",
        "access_token",
        "refresh_token",
        "credential",
        "credentials",
    }

    if isinstance(value, Mapping):
        cleaned: Dict[str, Any] = {}
        for k, v in value.items():
            key = str(k)
            if key.lower() in forbidden:
                continue
            cleaned[key] = _redact(v)
        return cleaned

    if isinstance(value, list):
        return [_redact(v) for v in value]

    return deepcopy(value)


def _extract_existing_evidence(decision_envelope: Mapping[str, Any]) -> list[str]:
    card = decision_envelope.get("recommendation_card", {})
    support = card.get("evidence_support", {}) if isinstance(card, Mapping) else {}
    evidence_hashes = support.get("evidence_hashes", []) if isinstance(support, Mapping) else []
    return [str(item) for item in evidence_hashes if item]


def build_evidence_gap_envelope(
    decision_envelope: Optional[Mapping[str, Any]] = None,
    *,
    required_evidence: Optional[list[str]] = None,
    reason: str = "Human review requested more evidence before approval.",
) -> Dict[str, Any]:
    envelope = _redact(dict(decision_envelope or build_default_home_fixed_human_review_decision_envelope()))

    decision_state = envelope.get("decision_state", {})
    decision = decision_state.get("decision", "request_more_evidence")

    required = required_evidence or decision_state.get("evidence_requested") or DEFAULT_REQUIRED_EVIDENCE
    existing_evidence = _extract_existing_evidence(envelope)

    missing_evidence = [
        item for item in required
        if item not in existing_evidence
    ]

    recommendation_card = envelope.get("recommendation_card", {})
    card_hash = envelope.get("recommendation_card_hash") or recommendation_card.get("card_hash")
    card_summary_hash = envelope.get("recommendation_summary_hash") or recommendation_card.get("summary_hash")

    evidence_support = recommendation_card.get("evidence_support", {}) if isinstance(recommendation_card, Mapping) else {}

    gap_state = {
        "decision": decision,
        "evidence_gap_active": decision == "request_more_evidence",
        "reason": reason,
        "required_evidence": required,
        "existing_evidence": existing_evidence,
        "missing_evidence": missing_evidence,
        "blocks_recommendation_card_hash": card_hash,
        "blocks_recommendation_summary_hash": card_summary_hash,
        "proof_hashes": evidence_support.get("proof_hashes", []) if isinstance(evidence_support, Mapping) else [],
        "context_hashes": evidence_support.get("context_hashes", []) if isinstance(evidence_support, Mapping) else [],
        "replay_trace_hash": evidence_support.get("replay_trace_hash") if isinstance(evidence_support, Mapping) else None,
    }

    safety = {
        "preview_only": True,
        "human_review_required": True,
        "evidence_request_sends_message": False,
        "decision_grants_live_permission": False,
        "private_chain_of_thought_exposed": False,
        "hidden_reasoning_exposed": False,
        "credentials_exposed": False,
        "would_create_booking": False,
        "would_create_payment": False,
        "would_create_escrow": False,
        "would_send_external_message": False,
        "would_write_live_chain": False,
        "would_execute_workflow": False,
        "live_side_effects_enabled": False,
    }

    envelope_core = {
        "envelope_version": EVIDENCE_GAP_ENVELOPE_VERSION,
        "envelope_type": "aion_lrm_evidence_gap",
        "business_id": envelope.get("business_id", "home_fixed"),
        "source_decision_envelope_hash": envelope.get("envelope_hash"),
        "source_decision_summary_hash": envelope.get("summary_hash"),
        "gap_state": gap_state,
        "source_decision_envelope": envelope,
        "safety": safety,
    }

    evidence_gap_hash = _hash("evidence_gap_envelope", envelope_core)

    summary = {
        "envelope_version": EVIDENCE_GAP_ENVELOPE_VERSION,
        "business_id": envelope_core["business_id"],
        "decision": decision,
        "evidence_gap_active": gap_state["evidence_gap_active"],
        "missing_evidence_count": len(missing_evidence),
        "preview_only": True,
        "human_review_required": True,
        "source_decision_envelope_hash": envelope.get("envelope_hash"),
        "evidence_gap_hash": evidence_gap_hash,
    }

    return {
        **envelope_core,
        "evidence_gap_hash": evidence_gap_hash,
        "summary": summary,
        "summary_hash": _hash("evidence_gap_summary", summary),
    }


def build_default_home_fixed_evidence_gap_envelope() -> Dict[str, Any]:
    decision = build_human_review_decision_envelope(
        decision="request_more_evidence",
        evidence_requested=DEFAULT_REQUIRED_EVIDENCE,
        reviewer_note="Request site evidence before approving the Home Fixed workflow preview.",
    )
    return build_evidence_gap_envelope(decision)
