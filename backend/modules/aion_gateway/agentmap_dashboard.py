"""Phase 14G — AgentMap dashboard / Generate button preview v0.

This module exposes a deterministic, preview-only dashboard payload for the
frontend AgentMap generation surface.

It does not publish public routes, write website files, send messages, create
bookings, create payments, create escrow, dispatch jobs, or write live chain data.
"""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any, Dict, Mapping, Optional

from .agentmap_discovery_endpoint import build_agentmap_discovery_endpoint_preview
from .agentmap_live_verification import build_agentmap_live_verification_preview
from .agentmap_synthetic_agent_simulation import (
    build_synthetic_inbound_agent_simulation_preview,
)
from .agentmap_human_review_simulation_bridge import (
    build_agentmap_human_review_simulation_bridge_preview,
)


DASHBOARD_VERSION = "aion.agentmap.dashboard.v0.1"


def _stable_hash(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _default_request(request: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    request = dict(request or {})
    return {
        "business_id": request.get("business_id", "home_fixed"),
        "business_name": request.get("business_name", "Home Fixed"),
        "vertical_key": request.get("vertical_key", "home_repair"),
    }


def _blocked_side_effects() -> Dict[str, bool]:
    return {
        "published_public_route": False,
        "self_hosted_file_written": False,
        "booking_created": False,
        "payment_created": False,
        "escrow_created": False,
        "job_dispatched": False,
        "external_message_sent": False,
        "live_chain_written": False,
    }


def build_agentmap_dashboard_preview(
    request: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Build the preview-only AgentMap dashboard payload for the frontend."""

    request = dict(request or {})
    identity = _default_request(request)

    endpoint = build_agentmap_discovery_endpoint_preview(identity)

    verification = build_agentmap_live_verification_preview(
        {
            **identity,
            "observed_agentmap_payload": endpoint,
            "expected_agentmap_hash": endpoint.get("agentmap_hash"),
            "expected_endpoint_hash": endpoint.get("endpoint_hash"),
            "observed_status_code": request.get("observed_status_code", 200),
            "observed_content_type": request.get(
                "observed_content_type", "application/json"
            ),
        }
    )

    simulation = build_synthetic_inbound_agent_simulation_preview(identity)

    human_review_bridge = build_agentmap_human_review_simulation_bridge_preview(identity)

    install_tag = endpoint.get("http_preview", {}).get(
        "install_tag",
        '<link rel="agentmap" type="application/json" href="/agentmap.json">',
    )

    ui_actions = {
        "generate_agentmap": {
            "label": "Generate AgentMap",
            "enabled": True,
            "preview_only": True,
            "requires_human_review": True,
        },
        "regenerate_agentmap": {
            "label": "Regenerate AgentMap",
            "enabled": True,
            "preview_only": True,
            "requires_human_review": True,
        },
        "copy_agentmap_url": {
            "label": "Copy AgentMap URL",
            "enabled": True,
            "value": endpoint["paths"]["canonical"],
        },
        "download_agentmap_json": {
            "label": "Download agentmap.json",
            "enabled": True,
            "filename": "agentmap.json",
            "payload_ref": "agentmap_manifest",
        },
        "copy_install_tag": {
            "label": "Copy website install tag",
            "enabled": True,
            "value": install_tag,
        },
        "run_live_verification_preview": {
            "label": "Verify AgentMap Live",
            "enabled": True,
            "preview_only": True,
        },
        "run_e2e_simulation_preview": {
            "label": "Run E2E Agent Simulation",
            "enabled": True,
            "preview_only": True,
            "halts_at": "human_review",
        },
    }

    status = {
        "agentmap_generated": bool(endpoint.get("agentmap_hash")),
        "agentmap_verified": verification.get("verified") is True,
        "simulation_passed": simulation.get("passed") is True,
        "human_review_bridge_ready": human_review_bridge.get("ready") is True
        or human_review_bridge.get("status") in {"ready", "waiting_human_review"},
        "preview_only": True,
        "live_execution_enabled": False,
    }

    side_effects = _blocked_side_effects()

    checks = {
        "generate_button_available": ui_actions["generate_agentmap"]["enabled"] is True,
        "settings_panel_available": True,
        "agentmap_preview_available": bool(endpoint.get("agentmap_manifest")),
        "validation_status_available": bool(status),
        "agentmap_hash_visible": bool(endpoint.get("agentmap_hash")),
        "copy_agentmap_url_available": ui_actions["copy_agentmap_url"]["enabled"] is True,
        "download_agentmap_json_available": ui_actions["download_agentmap_json"]["enabled"] is True,
        "copy_install_tag_available": ui_actions["copy_install_tag"]["enabled"] is True,
        "hosted_agentmap_url_available": bool(endpoint["paths"]["canonical"]),
        "self_hosted_well_known_export_available": bool(endpoint["paths"]["well_known"]),
        "regenerate_action_available": ui_actions["regenerate_agentmap"]["enabled"] is True,
        "live_verification_available": verification.get("verified") is True,
        "e2e_simulation_available": simulation.get("passed") is True,
        "human_review_required": True,
        "no_live_side_effects": not any(side_effects.values()),
    }

    passed = all(checks.values())

    response: Dict[str, Any] = {
        "dashboard_version": DASHBOARD_VERSION,
        "status": "ready" if passed else "not_ready",
        "passed": passed,
        "business_id": endpoint["business_id"],
        "business_name": endpoint["business_name"],
        "vertical_key": endpoint["vertical_key"],
        "agentmap_hash": endpoint["agentmap_hash"],
        "endpoint_hash": endpoint["endpoint_hash"],
        "verification_hash": verification["verification_hash"],
        "simulation_hash": simulation["simulation_hash"],
        "human_review_bridge_hash": human_review_bridge.get("bridge_hash")
        or human_review_bridge.get("summary_hash"),
        "paths": endpoint["paths"],
        "install_tag": install_tag,
        "ui_actions": ui_actions,
        "status_panel": status,
        "agentmap_preview": endpoint.get("agentmap_manifest"),
        "validation_preview": verification,
        "simulation_preview": {
            "status": simulation["status"],
            "passed": simulation["passed"],
            "human_review_required": simulation["safety_profile"][
                "human_review_required"
            ],
            "live_execution_enabled": simulation["safety_profile"][
                "live_execution_enabled"
            ],
        },
        "human_review_preview": {
            "status": human_review_bridge.get("status"),
            "human_review_required": True,
            "live_execution_enabled": False,
        },
        "side_effects": side_effects,
        "checks": checks,
        "safety_profile": {
            "preview_only": True,
            "read_only": True,
            "human_review_required": True,
            "live_execution_enabled": False,
        },
    }

    hash_payload = deepcopy(response)
    hash_payload.pop("dashboard_hash", None)
    hash_payload.pop("summary_hash", None)
    response["dashboard_hash"] = _stable_hash(hash_payload)

    summary_payload = {
        "dashboard_version": response["dashboard_version"],
        "status": response["status"],
        "business_id": response["business_id"],
        "vertical_key": response["vertical_key"],
        "agentmap_hash": response["agentmap_hash"],
        "endpoint_hash": response["endpoint_hash"],
        "verification_hash": response["verification_hash"],
        "simulation_hash": response["simulation_hash"],
        "dashboard_hash": response["dashboard_hash"],
        "preview_only": response["safety_profile"]["preview_only"],
        "human_review_required": response["safety_profile"][
            "human_review_required"
        ],
    }
    response["summary_hash"] = _stable_hash(summary_payload)

    return response


def build_agentmap_dashboard_summary(
    request: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Return a minimal deterministic AgentMap dashboard summary."""

    preview = build_agentmap_dashboard_preview(request)

    return {
        "dashboard_version": preview["dashboard_version"],
        "status": preview["status"],
        "passed": preview["passed"],
        "business_id": preview["business_id"],
        "vertical_key": preview["vertical_key"],
        "agentmap_hash": preview["agentmap_hash"],
        "endpoint_hash": preview["endpoint_hash"],
        "verification_hash": preview["verification_hash"],
        "simulation_hash": preview["simulation_hash"],
        "dashboard_hash": preview["dashboard_hash"],
        "summary_hash": preview["summary_hash"],
        "generate_button_available": preview["checks"]["generate_button_available"],
        "validation_status_available": preview["checks"][
            "validation_status_available"
        ],
        "human_review_required": preview["safety_profile"][
            "human_review_required"
        ],
        "live_execution_enabled": preview["safety_profile"][
            "live_execution_enabled"
        ],
    }


__all__ = [
    "DASHBOARD_VERSION",
    "build_agentmap_dashboard_preview",
    "build_agentmap_dashboard_summary",
]
