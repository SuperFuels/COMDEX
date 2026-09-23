"""AION-LRM Reasoning Memory Snapshot v0.

This module creates a deterministic, preview-only memory snapshot from an
AION governed reasoning packet.

It stores structured operational context only. It must not store private
chain-of-thought, hidden reasoning, credentials, secrets, or live execution
authority.
"""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any, Mapping


REASONING_MEMORY_SNAPSHOT_VERSION = "aion.lrm.reasoning_memory_snapshot.v0.1"

_CONTEXT_KEYS = (
    "website_intake",
    "commercial_ticket",
    "workflow_context",
    "agentmap_context",
    "boardroom_context",
    "proof_context",
    "ets_context",
)

_FORBIDDEN_KEYS = {
    "chain_of_thought",
    "private_chain_of_thought",
    "hidden_reasoning",
    "scratchpad",
    "secret",
    "secrets",
    "access_token",
    "refresh_token",
    "api_key",
    "password",
    "authorization",
}


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _hash(prefix: str, value: Any) -> str:
    digest = hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()
    return f"{prefix}_{digest[:32]}"


def _redact(value: Any) -> Any:
    if isinstance(value, Mapping):
        cleaned: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            if key_text in _FORBIDDEN_KEYS or key_text.lower() in _FORBIDDEN_KEYS:
                continue
            cleaned[key_text] = _redact(item)
        return cleaned

    if isinstance(value, list):
        return [_redact(item) for item in value]

    return deepcopy(value)


def _extract_context(reasoning_packet: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: _redact(reasoning_packet.get(key, {}))
        for key in _CONTEXT_KEYS
    }


def build_reasoning_memory_snapshot(
    reasoning_packet: Mapping[str, Any] | None = None,
    *,
    workspace_id: str = "home_fixed",
    memory_scope: str = "business_runtime_preview",
) -> dict[str, Any]:
    """Build a deterministic preview-only reasoning memory snapshot."""

    packet = _redact(reasoning_packet or {})
    context = _extract_context(packet)

    source_packet_hash = str(
        packet.get("reasoning_packet_hash")
        or packet.get("packet_hash")
        or _hash("reasoning_packet", packet)
    )

    memory_slots = {
        "website_intake": context["website_intake"],
        "commercial_ticket": context["commercial_ticket"],
        "workflow_context": context["workflow_context"],
        "agentmap_context": context["agentmap_context"],
        "boardroom_context": context["boardroom_context"],
        "proof_context": context["proof_context"],
        "ets_context": context["ets_context"],
    }

    retention_policy = {
        "preview_only": True,
        "store_private_chain_of_thought": False,
        "store_hidden_reasoning": False,
        "store_credentials": False,
        "store_live_execution_authority": False,
        "human_review_required": True,
    }

    safety = {
        "preview_only": True,
        "human_review_required": True,
        "would_create_booking": False,
        "would_create_payment": False,
        "would_create_escrow": False,
        "would_send_external_message": False,
        "would_write_live_chain": False,
        "would_execute_workflow": False,
        "live_side_effects_enabled": False,
    }

    snapshot_core = {
        "snapshot_version": REASONING_MEMORY_SNAPSHOT_VERSION,
        "workspace_id": workspace_id,
        "memory_scope": memory_scope,
        "source_packet_hash": source_packet_hash,
        "memory_slots": memory_slots,
        "retention_policy": retention_policy,
        "safety": safety,
    }

    snapshot_hash = _hash("reasoning_memory_snapshot", snapshot_core)

    summary = {
        "snapshot_version": REASONING_MEMORY_SNAPSHOT_VERSION,
        "workspace_id": workspace_id,
        "memory_scope": memory_scope,
        "source_packet_hash": source_packet_hash,
        "snapshot_hash": snapshot_hash,
        "preview_only": True,
        "human_review_required": True,
    }

    return {
        **snapshot_core,
        "snapshot_hash": snapshot_hash,
        "summary": summary,
        "summary_hash": _hash("reasoning_memory_summary", summary),
    }


def build_default_home_fixed_reasoning_memory_snapshot() -> dict[str, Any]:
    """Build the default Home Fixed reasoning memory snapshot preview."""

    packet = {
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
    }

    return build_reasoning_memory_snapshot(packet, workspace_id="home_fixed")
