"""Phase 14F — AgentMap Human Review E2E Simulation Bridge Preview v0.

This module connects the Phase 14E synthetic inbound-agent simulation preview
to a deterministic human-review handoff preview.

It is preview-only. It MUST NOT create bookings, payments, escrow, dispatch jobs,
send external messages, write live chain data, or mutate public routes.
"""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any, Dict, Mapping, Optional

from .agentmap_synthetic_agent_simulation import (
    build_synthetic_inbound_agent_simulation_preview,
)


BRIDGE_VERSION = "aion.agentmap.human_review_bridge.v0.1"


def _stable_hash(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _blocked_side_effects() -> Dict[str, bool]:
    return {
        "booking_created": False,
        "payment_created": False,
        "escrow_created": False,
        "job_dispatched": False,
        "external_message_sent": False,
        "live_chain_written": False,
        "public_route_mutated": False,
        "approval_auto_executed": False,
    }


def _build_review_request(simulation: Mapping[str, Any]) -> Dict[str, Any]:
    synthetic_intent = simulation.get("synthetic_intent", {})
    gateway_preview = simulation.get("gateway_preview", {})
    selected_route = gateway_preview.get("selected_capability_route") or {}

    return {
        "review_request_id": "human_review_preview_" + simulation["simulation_hash"][:16],
        "review_type": "synthetic_agentmap_e2e_preview",
        "status": "waiting_human_review",
        "preview_only": True,
        "synthetic_only": True,
        "human_review_required": True,
        "live_execution_authorized": False,
        "business_id": simulation["business_id"],
        "business_name": simulation["business_name"],
        "vertical_key": simulation["vertical_key"],
        "intent_id": synthetic_intent.get("intent_id"),
        "intent_type": synthetic_intent.get("intent_type"),
        "service_category": synthetic_intent.get("service_category"),
        "service_area": synthetic_intent.get("service_area"),
        "selected_route_key": selected_route.get("route_key")
        or selected_route.get("capability_key")
        or selected_route.get("id")
        or "safe_preview_route",
        "operator_action_required": "review_preview",
        "allowed_preview_actions": [
            "approve_preview_only",
            "reject_preview_only",
            "request_more_information_preview_only",
        ],
        "blocked_live_actions": [
            "booking",
            "payment",
            "escrow",
            "dispatch",
            "external_message",
            "live_chain_write",
        ],
    }


def build_agentmap_human_review_simulation_bridge_preview(
    request: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Build deterministic human-review bridge preview for synthetic AgentMap E2E."""

    request = dict(request or {})
    simulation = build_synthetic_inbound_agent_simulation_preview(request)
    review_request = _build_review_request(simulation)
    side_effects = _blocked_side_effects()

    checks = {
        "synthetic_simulation_passed": simulation.get("passed") is True,
        "review_request_created_as_preview": review_request["preview_only"] is True,
        "review_request_waiting_human": review_request["status"] == "waiting_human_review",
        "human_review_required": review_request["human_review_required"] is True,
        "live_execution_not_authorized": review_request["live_execution_authorized"] is False,
        "no_live_side_effects": not any(side_effects.values()),
        "simulation_hash_present": bool(simulation.get("simulation_hash")),
        "verification_hash_present": bool(simulation.get("verification_hash")),
    }

    passed = all(checks.values())

    response: Dict[str, Any] = {
        "bridge_version": BRIDGE_VERSION,
        "status": "passed" if passed else "failed",
        "passed": passed,
        "business_id": simulation["business_id"],
        "business_name": simulation["business_name"],
        "vertical_key": simulation["vertical_key"],
        "agentmap_hash": simulation["agentmap_hash"],
        "endpoint_hash": simulation["endpoint_hash"],
        "verification_hash": simulation["verification_hash"],
        "simulation_hash": simulation["simulation_hash"],
        "review_request": review_request,
        "side_effects": side_effects,
        "checks": checks,
        "safety_profile": {
            "preview_only": True,
            "read_only": True,
            "synthetic_only": True,
            "human_review_required": True,
            "live_execution_enabled": False,
            "approval_required_before_live_execution": True,
        },
    }

    hash_payload = deepcopy(response)
    hash_payload.pop("bridge_hash", None)
    hash_payload.pop("summary_hash", None)
    response["bridge_hash"] = _stable_hash(hash_payload)

    summary_payload = {
        "bridge_version": response["bridge_version"],
        "status": response["status"],
        "business_id": response["business_id"],
        "vertical_key": response["vertical_key"],
        "agentmap_hash": response["agentmap_hash"],
        "endpoint_hash": response["endpoint_hash"],
        "verification_hash": response["verification_hash"],
        "simulation_hash": response["simulation_hash"],
        "bridge_hash": response["bridge_hash"],
        "review_request_id": response["review_request"]["review_request_id"],
        "human_review_required": response["safety_profile"]["human_review_required"],
        "live_execution_enabled": response["safety_profile"]["live_execution_enabled"],
    }
    response["summary_hash"] = _stable_hash(summary_payload)

    return response


def build_agentmap_human_review_simulation_bridge_summary(
    request: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Return minimal deterministic human-review bridge summary."""

    preview = build_agentmap_human_review_simulation_bridge_preview(request)

    return {
        "bridge_version": preview["bridge_version"],
        "status": preview["status"],
        "passed": preview["passed"],
        "business_id": preview["business_id"],
        "vertical_key": preview["vertical_key"],
        "agentmap_hash": preview["agentmap_hash"],
        "endpoint_hash": preview["endpoint_hash"],
        "verification_hash": preview["verification_hash"],
        "simulation_hash": preview["simulation_hash"],
        "bridge_hash": preview["bridge_hash"],
        "summary_hash": preview["summary_hash"],
        "review_request_id": preview["review_request"]["review_request_id"],
        "review_status": preview["review_request"]["status"],
        "human_review_required": preview["safety_profile"]["human_review_required"],
        "live_execution_enabled": preview["safety_profile"]["live_execution_enabled"],
    }


__all__ = [
    "BRIDGE_VERSION",
    "build_agentmap_human_review_simulation_bridge_preview",
    "build_agentmap_human_review_simulation_bridge_summary",
]
