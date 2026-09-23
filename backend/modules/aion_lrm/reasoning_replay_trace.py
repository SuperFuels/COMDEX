from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any, Dict, Mapping, Optional

try:
    from .reasoning_memory_snapshot import build_default_home_fixed_reasoning_memory_snapshot
except Exception:  # pragma: no cover
    build_default_home_fixed_reasoning_memory_snapshot = None


REASONING_REPLAY_TRACE_VERSION = "aion.lrm.reasoning_replay_trace.v0.1"

_PRIVATE_KEYS = {
    "chain_of_thought",
    "private_chain_of_thought",
    "hidden_reasoning",
    "scratchpad",
    "private_scratchpad",
    "access_token",
    "refresh_token",
    "api_key",
    "secret",
    "password",
    "credential",
    "credentials",
}


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _hash(prefix: str, value: Any) -> str:
    return f"{prefix}_{hashlib.sha256(_canonical(value).encode('utf-8')).hexdigest()[:32]}"


def _safe_copy(value: Any) -> Any:
    if isinstance(value, Mapping):
        cleaned: Dict[str, Any] = {}
        for key, item in value.items():
            key_s = str(key)
            if key_s in _PRIVATE_KEYS:
                continue
            cleaned[key_s] = _safe_copy(item)
        return cleaned
    if isinstance(value, list):
        return [_safe_copy(item) for item in value]
    return deepcopy(value)


def _default_snapshot() -> Dict[str, Any]:
    if build_default_home_fixed_reasoning_memory_snapshot is not None:
        return build_default_home_fixed_reasoning_memory_snapshot()

    return {
        "snapshot_version": "aion.lrm.reasoning_memory_snapshot.v0.1",
        "memory_scope": "business_operation_preview",
        "source_reasoning_packet_hash": "reasoning_packet_preview",
        "business_context": {"business_id": "home_fixed", "vertical_key": "home_repair"},
        "website_intake": {"detected_service": "pergola_roof_repair", "location": "Arboleas"},
        "commercial_ticket": {"route_type": "discovery_session", "pricing_model": "quote_required"},
        "workflow_context": {"workflow_id": "home_fixed_new_enquiry"},
        "agentmap_context": {"agentmap_hash": "agentmap_preview_hash"},
        "proof_context": {"proof_receipt_id": "proof_receipt_preview", "proof_hash": "proof_preview_hash"},
        "ets_context": {"preview_only": True, "customer_outcome_score": None, "system_execution_score": None},
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
        "snapshot_hash": "reasoning_memory_snapshot_preview",
    }


def build_reasoning_replay_trace(
    reasoning_packet: Optional[Mapping[str, Any]] = None,
    memory_snapshot: Optional[Mapping[str, Any]] = None,
    recommendation: Optional[str] = None,
) -> Dict[str, Any]:
    safe_packet = _safe_copy(reasoning_packet or {})
    safe_snapshot = _safe_copy(memory_snapshot or _default_snapshot())

    safety = {
        "preview_only": True,
        "human_review_required": True,
        "private_reasoning_exposed": False,
        "credentials_retained": False,
        "would_create_booking": False,
        "would_create_payment": False,
        "would_create_escrow": False,
        "would_send_external_message": False,
        "would_write_live_chain": False,
        "would_execute_workflow": False,
        "live_side_effects_enabled": False,
    }

    evidence_context = {
        "source_reasoning_packet_hash": safe_snapshot.get("source_reasoning_packet_hash")
        or safe_packet.get("reasoning_packet_hash"),
        "reasoning_memory_snapshot_hash": safe_snapshot.get("snapshot_hash"),
        "agentmap_hash": (safe_snapshot.get("agentmap_context") or {}).get("agentmap_hash"),
        "proof_hash": (safe_snapshot.get("proof_context") or {}).get("proof_hash"),
        "proof_receipt_id": (safe_snapshot.get("proof_context") or {}).get("proof_receipt_id"),
        "ets_preview_only": (safe_snapshot.get("ets_context") or {}).get("preview_only", True),
    }

    operational_explanation = recommendation or (
        "AION selected a guarded human-review recommendation because the website intake "
        "describes a Home Fixed repair request, the commercial ticket requires inspection "
        "before final quote, the AgentMap context supports safe preview routing, proof and "
        "ETS context remain preview-only, and live execution is blocked until human review."
    )

    replay_steps = [
        {
            "step": 1,
            "name": "Read governed reasoning packet",
            "result": "safe_packet_context_available",
            "uses_private_reasoning": False,
        },
        {
            "step": 2,
            "name": "Read reasoning memory snapshot",
            "result": "safe_memory_context_available",
            "uses_private_reasoning": False,
        },
        {
            "step": 3,
            "name": "Check evidence and proof anchors",
            "result": "hash_context_available",
            "uses_private_reasoning": False,
        },
        {
            "step": 4,
            "name": "Check safety boundary",
            "result": "live_side_effects_blocked",
            "uses_private_reasoning": False,
        },
        {
            "step": 5,
            "name": "Produce governed replay explanation",
            "result": "human_review_required",
            "uses_private_reasoning": False,
        },
    ]

    trace_base = {
        "trace_version": REASONING_REPLAY_TRACE_VERSION,
        "trace_type": "aion_lrm_reasoning_replay_trace",
        "runtime": "aion_lrm",
        "preview_only": True,
        "reasoning_packet_context": safe_packet,
        "memory_snapshot_context": safe_snapshot,
        "evidence_context": evidence_context,
        "replay_steps": replay_steps,
        "operational_explanation": operational_explanation,
        "safety": safety,
    }

    replay_trace_hash = _hash("reasoning_replay_trace", trace_base)

    summary = {
        "trace_version": REASONING_REPLAY_TRACE_VERSION,
        "trace_type": "aion_lrm_reasoning_replay_trace_summary",
        "preview_only": True,
        "human_review_required": True,
        "private_reasoning_exposed": False,
        "reasoning_memory_snapshot_hash": evidence_context.get("reasoning_memory_snapshot_hash"),
        "proof_hash": evidence_context.get("proof_hash"),
        "recommendation_state": "human_review_required",
        "replay_trace_hash": replay_trace_hash,
    }

    result = {
        **trace_base,
        "replay_trace_hash": replay_trace_hash,
        "summary": summary,
        "summary_hash": _hash("reasoning_replay_summary", summary),
    }

    return result


def build_default_home_fixed_reasoning_replay_trace() -> Dict[str, Any]:
    return build_reasoning_replay_trace()
