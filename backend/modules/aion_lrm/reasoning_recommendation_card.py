from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any, Dict, Mapping, Optional

try:
    from .reasoning_packet import build_default_home_fixed_reasoning_packet
except ImportError:
    build_default_home_fixed_reasoning_packet = None

from .reasoning_memory_snapshot import build_default_home_fixed_reasoning_memory_snapshot
from .reasoning_replay_trace import (
    build_default_home_fixed_reasoning_replay_trace,
    build_reasoning_replay_trace,
)
from .reasoning_replay_boardroom import build_reasoning_replay_boardroom_panel


REASONING_RECOMMENDATION_CARD_VERSION = "aion.lrm.reasoning_recommendation_card.v0.1"

def _default_reasoning_packet() -> Dict[str, Any]:
    if build_default_home_fixed_reasoning_packet is not None:
        return dict(build_default_home_fixed_reasoning_packet())

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


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _hash(prefix: str, value: Any) -> str:
    return f"{prefix}_{hashlib.sha256(_canonical(value).encode('utf-8')).hexdigest()[:32]}"


def _redact(value: Any) -> Any:
    forbidden = {
        "private_chain_of_thought",
        "chain_of_thought",
        "hidden_reasoning",
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

    return value


def build_reasoning_recommendation_card(
    *,
    reasoning_packet: Optional[Mapping[str, Any]] = None,
    memory_snapshot: Optional[Mapping[str, Any]] = None,
    replay_trace: Optional[Mapping[str, Any]] = None,
    requested_recommendation: Optional[str] = None,
    recommendation_label: Optional[str] = None,
    confidence: str = "medium",
) -> Dict[str, Any]:
    packet = _redact(deepcopy(dict(reasoning_packet or _default_reasoning_packet())))
    memory = _redact(deepcopy(dict(memory_snapshot or build_default_home_fixed_reasoning_memory_snapshot())))
    replay = _redact(deepcopy(dict(replay_trace or build_default_home_fixed_reasoning_replay_trace())))

    # Phase 20D boardroom projection accepts a replay trace only.
    # If a custom packet/memory pair is supplied, rebuild the replay trace first.
    if replay_trace is None:
        replay = build_reasoning_replay_trace(
            reasoning_packet=packet,
            memory_snapshot=memory,
        )

    boardroom_panel = build_reasoning_replay_boardroom_panel(replay)

    recommendation = {
        "recommendation_id": "lrm_recommendation_home_fixed_preview_v0",
        "recommendation_label": recommendation_label or "Proceed to human review with guarded workflow preview",
        "requested_recommendation": requested_recommendation
        or "Prepare a human-reviewed Home Fixed workflow preview from the governed intake, ticket, AgentMap, proof, and ETS context.",
        "confidence": confidence,
        "recommended_next_step": "human_review_required_before_live_action",
        "operator_action": "review_before_approval",
        "execution_status": "not_executed_preview_only",
    }

    replay_evidence_context = replay.get("evidence_context", {})
    replay_governed_inputs = replay.get("governed_inputs", {})

    evidence_support = {
        "reasoning_packet_hash": (
            packet.get("reasoning_packet_hash")
            or replay_evidence_context.get("source_reasoning_packet_hash")
        ),
        "memory_snapshot_hash": (
            memory.get("snapshot_hash")
            or replay_evidence_context.get("reasoning_memory_snapshot_hash")
        ),
        "replay_trace_hash": replay.get("replay_trace_hash"),
        "boardroom_hash": boardroom_panel.get("boardroom_hash"),
        "evidence_hashes": replay_governed_inputs.get("evidence_hashes", []),
        "proof_hashes": (
            replay_governed_inputs.get("proof_hashes")
            or [replay_evidence_context.get("proof_hash")]
            if replay_evidence_context.get("proof_hash")
            else []
        ),
        "context_hashes": (
            replay_governed_inputs.get("context_hashes")
            or [replay_evidence_context.get("agentmap_hash")]
            if replay_evidence_context.get("agentmap_hash")
            else []
        ),
    }

    blockers = [
        "human_review_required",
        "live_booking_blocked",
        "payment_blocked",
        "escrow_blocked",
        "external_message_blocked",
        "live_chain_write_blocked",
    ]

    safety = {
        "preview_only": True,
        "human_review_required": True,
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
        "recommendation_grants_permission": False,
    }

    card_core = {
        "card_version": REASONING_RECOMMENDATION_CARD_VERSION,
        "card_type": "boardroom_reasoning_recommendation",
        "title": "AION Recommendation",
        "business_id": packet.get("business_id") or memory.get("business_id") or "home_fixed",
        "recommendation": recommendation,
        "evidence_support": evidence_support,
        "blockers": blockers,
        "safety": safety,
    }

    card_hash = _hash("reasoning_recommendation_card", card_core)

    summary = {
        "card_version": REASONING_RECOMMENDATION_CARD_VERSION,
        "business_id": card_core["business_id"],
        "recommendation_label": recommendation["recommendation_label"],
        "recommended_next_step": recommendation["recommended_next_step"],
        "confidence": confidence,
        "preview_only": True,
        "human_review_required": True,
        "card_hash": card_hash,
    }

    return {
        **card_core,
        "boardroom_panel": boardroom_panel,
        "card_hash": card_hash,
        "summary": summary,
        "summary_hash": _hash("reasoning_recommendation_summary", summary),
    }


def build_default_home_fixed_reasoning_recommendation_card() -> Dict[str, Any]:
    return build_reasoning_recommendation_card()
