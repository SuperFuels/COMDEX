from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any, Dict, Mapping, Optional

from .evidence_gap_envelope import (
    DEFAULT_REQUIRED_EVIDENCE,
    build_default_home_fixed_evidence_gap_envelope,
)


EVIDENCE_SATISFACTION_ENVELOPE_VERSION = "aion.lrm.evidence_satisfaction_envelope.v0.1"


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
        for key, item in value.items():
            key_text = str(key)
            if key_text.lower() in forbidden:
                continue
            cleaned[key_text] = _redact(item)
        return cleaned

    if isinstance(value, list):
        return [_redact(item) for item in value]

    return deepcopy(value)


def _normalise_received_evidence(received_evidence: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    evidence = _redact(dict(received_evidence or {}))

    if not evidence:
        evidence = {
            "site_photo": {
                "received": True,
                "evidence_hash": "evidence_site_photo_preview",
            },
            "roof_or_pergola_measurements": {
                "received": True,
                "evidence_hash": "evidence_measurements_preview",
            },
            "access_notes": {
                "received": True,
                "evidence_hash": "evidence_access_notes_preview",
            },
            "customer_contact_confirmation": {
                "received": True,
                "evidence_hash": "evidence_contact_confirmation_preview",
            },
        }

    return evidence


def _received_keys(received_evidence: Mapping[str, Any]) -> list[str]:
    keys: list[str] = []

    for key, value in received_evidence.items():
        if isinstance(value, Mapping):
            if value.get("received", True) is True:
                keys.append(str(key))
        else:
            keys.append(str(key))

    return sorted(keys)


def _evidence_hashes(received_evidence: Mapping[str, Any]) -> list[str]:
    hashes: list[str] = []

    for key, value in received_evidence.items():
        if isinstance(value, Mapping) and value.get("evidence_hash"):
            hashes.append(str(value["evidence_hash"]))
        else:
            hashes.append(_hash("evidence_item", {str(key): value}))

    return sorted(hashes)


def build_evidence_satisfaction_envelope(
    evidence_gap_envelope: Optional[Mapping[str, Any]] = None,
    *,
    received_evidence: Optional[Mapping[str, Any]] = None,
    reviewer_note: str = "Evidence received for human review.",
) -> Dict[str, Any]:
    gap = _redact(dict(evidence_gap_envelope or build_default_home_fixed_evidence_gap_envelope()))
    evidence = _normalise_received_evidence(received_evidence)

    gap_state = gap.get("gap_state", {}) if isinstance(gap.get("gap_state", {}), Mapping) else {}
    required_evidence = list(gap_state.get("required_evidence") or DEFAULT_REQUIRED_EVIDENCE)
    received = _received_keys(evidence)
    remaining_missing = [item for item in required_evidence if item not in received]
    satisfied = len(remaining_missing) == 0

    satisfaction_state = {
        "evidence_received": received,
        "evidence_hashes": _evidence_hashes(evidence),
        "required_evidence": required_evidence,
        "remaining_missing_evidence": remaining_missing,
        "evidence_gap_satisfied": satisfied,
        "unblocks_recommendation_card_hash": gap_state.get("blocks_recommendation_card_hash"),
        "unblocks_recommendation_summary_hash": gap_state.get("blocks_recommendation_summary_hash"),
        "source_evidence_gap_hash": gap.get("evidence_gap_hash"),
        "source_evidence_gap_summary_hash": gap.get("summary_hash"),
        "proof_hashes": gap_state.get("proof_hashes", []),
        "context_hashes": gap_state.get("context_hashes", []),
        "replay_trace_hash": gap_state.get("replay_trace_hash"),
        "next_review_state": "return_to_human_review" if satisfied else "request_more_evidence",
        "reviewer_note": reviewer_note,
    }

    safety = {
        "preview_only": True,
        "human_review_required": True,
        "evidence_satisfaction_grants_live_permission": False,
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
        "envelope_version": EVIDENCE_SATISFACTION_ENVELOPE_VERSION,
        "envelope_type": "aion_lrm_evidence_satisfaction",
        "business_id": gap.get("business_id", "home_fixed"),
        "source_evidence_gap_hash": gap.get("evidence_gap_hash"),
        "source_evidence_gap_summary_hash": gap.get("summary_hash"),
        "received_evidence": evidence,
        "satisfaction_state": satisfaction_state,
        "source_evidence_gap_envelope": gap,
        "safety": safety,
    }

    satisfaction_hash = _hash("evidence_satisfaction_envelope", envelope_core)

    summary = {
        "envelope_version": EVIDENCE_SATISFACTION_ENVELOPE_VERSION,
        "business_id": envelope_core["business_id"],
        "source_evidence_gap_hash": gap.get("evidence_gap_hash"),
        "evidence_gap_satisfied": satisfied,
        "remaining_missing_evidence_count": len(remaining_missing),
        "next_review_state": satisfaction_state["next_review_state"],
        "preview_only": True,
        "human_review_required": True,
        "satisfaction_hash": satisfaction_hash,
    }

    return {
        **envelope_core,
        "satisfaction_hash": satisfaction_hash,
        "summary": summary,
        "summary_hash": _hash("evidence_satisfaction_summary", summary),
    }


def build_default_home_fixed_evidence_satisfaction_envelope() -> Dict[str, Any]:
    return build_evidence_satisfaction_envelope()
