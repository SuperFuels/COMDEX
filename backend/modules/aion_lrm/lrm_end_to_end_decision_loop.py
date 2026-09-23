from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any, Dict, Mapping, Optional

from .reasoning_memory_snapshot import build_default_home_fixed_reasoning_memory_snapshot
from .reasoning_replay_trace import build_reasoning_replay_trace
from .reasoning_replay_boardroom import build_reasoning_replay_boardroom_panel
from .reasoning_recommendation_card import build_reasoning_recommendation_card
from .human_review_decision_envelope import build_human_review_decision_envelope
from .evidence_gap_envelope import build_evidence_gap_envelope
from .evidence_satisfaction_envelope import build_evidence_satisfaction_envelope


LRM_END_TO_END_DECISION_LOOP_VERSION = "aion.lrm.end_to_end_decision_loop.v0.1"


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


def _default_reasoning_packet() -> Dict[str, Any]:
    return {
        "business_id": "home_fixed",
        "reasoning_packet_hash": "reasoning_packet_home_fixed_preview_v0",
        "website_intake": {
            "business_id": "home_fixed",
            "source": "Home Fixed website widget",
            "customer_message": "Leaking pergola roof in Arboleas after rain",
        },
        "commercial_ticket": {
            "ticket_type": "A2A Job / Order Ticket",
            "service": "Pergola / roof repair",
            "route": "discovery_session",
            "pricing": "inspection_required_before_final_quote",
        },
        "workflow_context": {
            "workflow_id": "home_fixed_new_enquiry",
            "workflow_mode": "guarded_preview",
        },
        "agentmap_context": {
            "business_id": "home_fixed",
            "vertical_key": "home_repair",
            "safe_capability_route": "roof_repair_quote_preview",
        },
        "boardroom_context": {
            "surface": "Boardroom",
            "state": "waiting_human_review",
        },
        "proof_context": {
            "proof_receipt_available": True,
            "live_chain_write": False,
        },
        "ets_context": {
            "ets_preview": True,
            "customer_outcome_score_separate": True,
            "system_execution_score_separate": True,
        },
        "safety": {
            "preview_only": True,
            "human_review_required": True,
            "would_create_booking": False,
            "would_create_payment": False,
            "would_create_escrow": False,
            "would_send_external_message": False,
            "would_write_live_chain": False,
            "would_execute_workflow": False,
        },
    }


def build_lrm_end_to_end_decision_loop(
    reasoning_packet: Optional[Mapping[str, Any]] = None,
    *,
    decision: str = "request_more_evidence",
    received_evidence: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    packet = _redact(dict(reasoning_packet or _default_reasoning_packet()))

    memory_snapshot = build_default_home_fixed_reasoning_memory_snapshot()

    replay_trace = build_reasoning_replay_trace(
        reasoning_packet=packet,
        memory_snapshot=memory_snapshot,
    )

    boardroom_panel = build_reasoning_replay_boardroom_panel(replay_trace)

    recommendation_card = build_reasoning_recommendation_card(
        reasoning_packet=packet,
        memory_snapshot=memory_snapshot,
        replay_trace=replay_trace,
    )

    human_decision = build_human_review_decision_envelope(
        recommendation_card,
        decision=decision,
        evidence_requested=[
            "site_photo",
            "roof_or_pergola_measurements",
            "access_notes",
            "customer_contact_confirmation",
        ] if decision == "request_more_evidence" else [],
        reviewer_note="LRM end-to-end loop preview decision.",
    )

    evidence_gap = build_evidence_gap_envelope(human_decision)

    evidence_satisfaction = build_evidence_satisfaction_envelope(
        evidence_gap,
        received_evidence=received_evidence,
        reviewer_note="LRM end-to-end loop evidence intake preview.",
    )

    loop_steps = [
        {
            "step": 1,
            "name": "governed_reasoning_packet",
            "hash": packet.get("reasoning_packet_hash"),
            "status": "available",
        },
        {
            "step": 2,
            "name": "reasoning_memory_snapshot",
            "hash": memory_snapshot.get("snapshot_hash"),
            "status": "available",
        },
        {
            "step": 3,
            "name": "reasoning_replay_trace",
            "hash": replay_trace.get("replay_trace_hash"),
            "status": "available",
        },
        {
            "step": 4,
            "name": "boardroom_replay_visibility",
            "hash": boardroom_panel.get("boardroom_hash"),
            "status": "available",
        },
        {
            "step": 5,
            "name": "reasoning_recommendation_card",
            "hash": recommendation_card.get("card_hash"),
            "status": "available",
        },
        {
            "step": 6,
            "name": "human_review_decision_envelope",
            "hash": human_decision.get("envelope_hash"),
            "status": human_decision.get("decision_state", {}).get("decision"),
        },
        {
            "step": 7,
            "name": "evidence_gap_envelope",
            "hash": evidence_gap.get("evidence_gap_hash"),
            "status": "active" if evidence_gap.get("gap_state", {}).get("evidence_gap_active") else "inactive",
        },
        {
            "step": 8,
            "name": "evidence_satisfaction_envelope",
            "hash": evidence_satisfaction.get("satisfaction_hash"),
            "status": evidence_satisfaction.get("satisfaction_state", {}).get("next_review_state"),
        },
    ]

    safety = {
        "preview_only": True,
        "human_review_required": True,
        "end_to_end_loop_grants_live_permission": False,
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

    loop_core = {
        "loop_version": LRM_END_TO_END_DECISION_LOOP_VERSION,
        "loop_type": "aion_lrm_end_to_end_decision_loop",
        "business_id": packet.get("business_id", "home_fixed"),
        "loop_steps": loop_steps,
        "governed_reasoning_packet": packet,
        "reasoning_memory_snapshot": memory_snapshot,
        "reasoning_replay_trace": replay_trace,
        "boardroom_replay_panel": boardroom_panel,
        "reasoning_recommendation_card": recommendation_card,
        "human_review_decision_envelope": human_decision,
        "evidence_gap_envelope": evidence_gap,
        "evidence_satisfaction_envelope": evidence_satisfaction,
        "final_state": evidence_satisfaction.get("satisfaction_state", {}).get("next_review_state"),
        "safety": safety,
    }

    loop_hash = _hash("lrm_end_to_end_decision_loop", loop_core)

    summary = {
        "loop_version": LRM_END_TO_END_DECISION_LOOP_VERSION,
        "business_id": loop_core["business_id"],
        "final_state": loop_core["final_state"],
        "preview_only": True,
        "human_review_required": True,
        "steps": [step["name"] for step in loop_steps],
        "loop_hash": loop_hash,
    }

    return {
        **loop_core,
        "loop_hash": loop_hash,
        "summary": summary,
        "summary_hash": _hash("lrm_end_to_end_decision_loop_summary", summary),
    }


def build_default_home_fixed_lrm_end_to_end_decision_loop() -> Dict[str, Any]:
    return build_lrm_end_to_end_decision_loop()
