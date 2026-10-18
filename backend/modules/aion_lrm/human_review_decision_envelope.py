from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any, Dict, Mapping, Optional

from .reasoning_recommendation_card import (
    build_default_home_fixed_reasoning_recommendation_card,
    build_reasoning_recommendation_card,
)


HUMAN_REVIEW_DECISION_ENVELOPE_VERSION = "aion.lrm.human_review_decision_envelope.v0.1"

ALLOWED_DECISIONS = {
    "approve_preview",
    "reject",
    "request_more_evidence",
}


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


def build_human_review_decision_envelope(
    recommendation_card: Optional[Mapping[str, Any]] = None,
    *,
    decision: str = "request_more_evidence",
    reviewer_id: str = "human_operator_preview",
    reviewer_note: str = "Review required before any live action.",
    evidence_requested: Optional[list[str]] = None,
) -> Dict[str, Any]:
    if decision not in ALLOWED_DECISIONS:
        raise ValueError(f"Unsupported human review decision: {decision}")

    card = _redact(dict(recommendation_card or build_default_home_fixed_reasoning_recommendation_card()))

    decision_state = {
        "decision": decision,
        "reviewer_id": reviewer_id,
        "reviewer_note": reviewer_note,
        "evidence_requested": evidence_requested or [],
        "approval_scope": "preview_only",
        "approval_result": (
            "preview_may_continue_to_next_review_stage"
            if decision == "approve_preview"
            else "blocked_pending_operator_action"
        ),
    }

    safety = {
        "preview_only": True,
        "human_review_required": True,
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

    blocked_live_actions = [
        "booking",
        "payment",
        "escrow",
        "external_message",
        "live_chain_write",
        "workflow_execution",
    ]

    envelope_core = {
        "envelope_version": HUMAN_REVIEW_DECISION_ENVELOPE_VERSION,
        "envelope_type": "aion_lrm_human_review_decision",
        "business_id": card.get("business_id", "home_fixed"),
        "recommendation_card_hash": card.get("card_hash"),
        "recommendation_summary_hash": card.get("summary_hash"),
        "decision_state": decision_state,
        "blocked_live_actions": blocked_live_actions,
        "recommendation_card": card,
        "safety": safety,
    }

    envelope_hash = _hash("human_review_decision_envelope", envelope_core)

    summary = {
        "envelope_version": HUMAN_REVIEW_DECISION_ENVELOPE_VERSION,
        "business_id": envelope_core["business_id"],
        "decision": decision,
        "approval_scope": decision_state["approval_scope"],
        "decision_grants_live_permission": False,
        "preview_only": True,
        "human_review_required": True,
        "recommendation_card_hash": card.get("card_hash"),
        "envelope_hash": envelope_hash,
    }

    return {
        **envelope_core,
        "envelope_hash": envelope_hash,
        "summary": summary,
        "summary_hash": _hash("human_review_decision_summary", summary),
    }


def build_default_home_fixed_human_review_decision_envelope() -> Dict[str, Any]:
    return build_human_review_decision_envelope()
