"""Phase 14E — Synthetic inbound agent simulation preview v0.

This module simulates an external AI agent discovering the business through
AgentMap, parsing safe capability routes, submitting a synthetic intent, and
halting at the human-review boundary.

It is preview-only. It MUST NOT perform live HTTP requests, create bookings,
move money, create escrow, dispatch work, send external messages, or write
live chain data.
"""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any, Dict, Mapping, Optional

from backend.modules.aion_gateway.agentmap_discovery_endpoint import (
    build_agentmap_discovery_endpoint_preview,
)
from backend.modules.aion_gateway.agentmap_live_verification import (
    build_agentmap_live_verification_preview,
)


SIMULATION_VERSION = "aion.agentmap.synthetic_agent_simulation.v0.1"


def _stable_hash(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _default_synthetic_intent() -> Dict[str, Any]:
    return {
        "intent_id": "synthetic_home_fixed_roof_repair_v0",
        "intent_type": "service_quote_request",
        "request_text": "Synthetic agent requests preview quote for leaking roof repair in Albox.",
        "vertical_key": "home_repair",
        "service_category": "roofing",
        "service_area": "Albox",
        "urgency": "normal",
        "customer_visible": False,
        "synthetic": True,
    }


def _safe_handoff_state() -> Dict[str, Any]:
    return {
        "state": "waiting_human_review",
        "human_review_required": True,
        "preview_only": True,
        "live_execution_authorized": False,
        "approval_required_before": [
            "booking",
            "payment",
            "escrow",
            "dispatch",
            "external_message",
            "live_chain_write",
        ],
    }


def _blocked_side_effects() -> Dict[str, bool]:
    return {
        "booking_created": False,
        "payment_created": False,
        "escrow_created": False,
        "job_dispatched": False,
        "external_message_sent": False,
        "live_chain_written": False,
        "public_route_mutated": False,
    }



def _normalise_capability_routes(value):
    """Return capability routes as a list regardless of endpoint container shape."""
    if value is None:
        return []

    if isinstance(value, list):
        return [route for route in value if isinstance(route, dict)]

    if isinstance(value, dict):
        routes = []
        for key, item in value.items():
            if isinstance(item, dict):
                route = dict(item)
                route.setdefault("route_key", key)
                routes.append(route)
            elif isinstance(item, list):
                for nested in item:
                    if isinstance(nested, dict):
                        route = dict(nested)
                        route.setdefault("route_group", key)
                        routes.append(route)
        return routes

    return []

def build_synthetic_inbound_agent_simulation_preview(
    request: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Build a deterministic synthetic inbound-agent simulation preview.

    The flow is:
    1. Build read-only AgentMap discovery endpoint preview.
    2. Verify the discovered endpoint payload.
    3. Parse safe capability routes.
    4. Submit synthetic intent preview.
    5. Halt at human-review boundary.
    """

    request = dict(request or {})

    endpoint_request = {
        "business_id": request.get("business_id", "home_fixed"),
        "business_name": request.get("business_name", "Home Fixed"),
        "vertical_key": request.get("vertical_key", "home_repair"),
    }

    endpoint = build_agentmap_discovery_endpoint_preview(endpoint_request)

    verification = build_agentmap_live_verification_preview(
        {
            **endpoint_request,
            "observed_agentmap_payload": endpoint,
            "expected_agentmap_hash": endpoint.get("agentmap_hash"),
            "expected_endpoint_hash": endpoint.get("endpoint_hash"),
            "observed_status_code": request.get("observed_status_code", 200),
            "observed_content_type": request.get(
                "observed_content_type", "application/json"
            ),
        }
    )

    synthetic_intent = deepcopy(
        request.get("synthetic_intent") or _default_synthetic_intent()
    )
    synthetic_intent["synthetic"] = True

    capability_routes = _normalise_capability_routes(
        endpoint.get("capability_routes")
        or endpoint.get("safe_capability_routes")
        or endpoint.get("routes")
        or endpoint.get("capabilities")
    )

    safe_routes = [
        route
        for route in capability_routes
        if route.get("safe_for_agent_discovery", True) is True
        and route.get("preview_only", True) is True
        and route.get("human_review_required", True) is True
    ]

    selected_route = safe_routes[0] if safe_routes else None

    gateway_preview = {
        "accepted": bool(verification.get("verified") and selected_route),
        "normalized_intent": synthetic_intent,
        "selected_capability_route": selected_route,
        "route_count": len(safe_routes),
        "gateway_stage": "synthetic_preview_only",
        "would_create_fulfilment_job_preview": bool(
            verification.get("verified") and selected_route
        ),
        "handoff": _safe_handoff_state(),
    }

    side_effects = _blocked_side_effects()

    checks = {
        "agentmap_discovery_available": bool(endpoint.get("endpoint_hash")),
        "agentmap_live_verification_passed": verification.get("verified") is True,
        "safe_capability_route_selected": selected_route is not None,
        "synthetic_intent_marked_synthetic": synthetic_intent.get("synthetic") is True,
        "halted_at_human_review": gateway_preview["handoff"]["state"]
        == "waiting_human_review",
        "human_review_required": gateway_preview["handoff"][
            "human_review_required"
        ]
        is True,
        "no_live_side_effects": not any(side_effects.values()),
    }

    response: Dict[str, Any] = {
        "simulation_version": SIMULATION_VERSION,
        "status": "passed" if all(checks.values()) else "failed",
        "passed": all(checks.values()),
        "business_id": endpoint["business_id"],
        "business_name": endpoint["business_name"],
        "vertical_key": endpoint["vertical_key"],
        "agentmap_hash": endpoint["agentmap_hash"],
        "endpoint_hash": endpoint["endpoint_hash"],
        "verification_hash": verification["verification_hash"],
        "synthetic_intent": synthetic_intent,
        "gateway_preview": gateway_preview,
        "side_effects": side_effects,
        "checks": checks,
        "safety_profile": {
            "preview_only": True,
            "read_only": True,
            "synthetic_only": True,
            "human_review_required": True,
            "live_execution_enabled": False,
        },
    }

    hash_payload = deepcopy(response)
    hash_payload.pop("simulation_hash", None)
    hash_payload.pop("summary_hash", None)
    response["simulation_hash"] = _stable_hash(hash_payload)

    summary_payload = {
        "simulation_version": response["simulation_version"],
        "status": response["status"],
        "business_id": response["business_id"],
        "vertical_key": response["vertical_key"],
        "agentmap_hash": response["agentmap_hash"],
        "endpoint_hash": response["endpoint_hash"],
        "verification_hash": response["verification_hash"],
        "simulation_hash": response["simulation_hash"],
        "human_review_required": response["safety_profile"][
            "human_review_required"
        ],
        "live_execution_enabled": response["safety_profile"][
            "live_execution_enabled"
        ],
    }
    response["summary_hash"] = _stable_hash(summary_payload)

    return response


def build_synthetic_inbound_agent_simulation_summary(
    request: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Return a minimal deterministic simulation summary."""

    preview = build_synthetic_inbound_agent_simulation_preview(request)

    return {
        "simulation_version": preview["simulation_version"],
        "status": preview["status"],
        "passed": preview["passed"],
        "business_id": preview["business_id"],
        "vertical_key": preview["vertical_key"],
        "agentmap_hash": preview["agentmap_hash"],
        "endpoint_hash": preview["endpoint_hash"],
        "verification_hash": preview["verification_hash"],
        "simulation_hash": preview["simulation_hash"],
        "summary_hash": preview["summary_hash"],
        "human_review_required": preview["safety_profile"]["human_review_required"],
        "live_execution_enabled": preview["safety_profile"][
            "live_execution_enabled"
        ],
    }


__all__ = [
    "SIMULATION_VERSION",
    "build_synthetic_inbound_agent_simulation_preview",
    "build_synthetic_inbound_agent_simulation_summary",
]
