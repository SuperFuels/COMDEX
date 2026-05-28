from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any, Dict, List


A2A_WELL_KNOWN_DISCOVERY_VERSION = "aion.a2a_well_known_discovery.v0.1"

A2A_WELL_KNOWN_PATHS = [
    "/.well-known/aion-agent",
    "/.well-known/ai-agent",
]

ACCEPTED_PROTOCOLS = [
    "aion.a2a.preview.v0",
    "aion.machine_cart.preview.v0",
    "aion.proof_receipt.preview.v0",
    "aion.trust_summary.preview.v0",
]


def _stable_hash(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class A2AWellKnownDiscoveryPreview:
    contract_version: str
    business_id: str
    business_name: str
    vertical_key: str
    industry_key: str
    preview_only: bool
    public_route_mounted: bool
    requires_auth: bool
    auth_mode: str
    well_known_paths: List[str]
    capability_discovery_preview: Dict[str, Any]
    availability_preview: Dict[str, Any]
    accepted_protocols: List[str]
    authentication_requirements: Dict[str, Any]
    safety: Dict[str, Any]
    blocked_reasons: List[str]
    discovery_hash: str


def build_well_known_discovery_preview(
    *,
    business_id: str = "home_fixed",
    business_name: str = "Home Fixed",
    vertical_key: str = "home_repair",
    industry_key: str = "trades",
) -> Dict[str, Any]:
    capability_discovery_preview = {
        "business_capabilities_available": True,
        "machine_catalog_available": True,
        "availability_preview_available": True,
        "quote_request_preview_available": True,
        "job_request_preview_available": True,
        "job_trace_preview_available": True,
        "job_evidence_preview_available": True,
        "settlement_readiness_preview_available": True,
        "proof_receipt_preview_available": True,
        "trust_summary_preview_available": True,
        "capability_discovery_route": f"/api/aion/a2a/{business_id}/business_capabilities",
    }

    availability_preview = {
        "status": "preview_available",
        "business_id": business_id,
        "vertical_key": vertical_key,
        "availability_mode": "preview_only",
        "live_booking_enabled": False,
        "live_status_polling_enabled": False,
        "human_review_required": True,
    }

    authentication_requirements = {
        "requires_auth": True,
        "auth_mode": "api_key_or_signed_agent_preview",
        "api_key_supported_preview": True,
        "signed_agent_supported_preview": True,
        "agent_identity_validation_enabled": False,
        "scoped_permissions_enabled": False,
    }

    safety = {
        "preview_only": True,
        "public_route_mounted": False,
        "would_expose_public_route": False,
        "would_create_booking": False,
        "would_create_live_job": False,
        "would_execute_goal_engine": False,
        "would_bypass_human_review": False,
        "would_move_money": False,
        "would_move_pho": False,
        "would_require_wallet": False,
        "would_create_payment": False,
        "would_create_escrow": False,
        "would_release_funds": False,
        "would_send_external_messages": False,
        "live_status_polling_enabled": False,
    }

    blocked_reasons = [
        "preview_only",
        "public_route_not_mounted",
        "auth_required",
        "no_live_booking",
        "no_live_job_creation",
        "no_goal_engine_execution",
        "no_payment_side_effect",
        "no_escrow_side_effect",
        "no_external_message_side_effect",
    ]

    payload_without_hash = {
        "contract_version": A2A_WELL_KNOWN_DISCOVERY_VERSION,
        "business_id": business_id,
        "business_name": business_name,
        "vertical_key": vertical_key,
        "industry_key": industry_key,
        "preview_only": True,
        "public_route_mounted": False,
        "requires_auth": True,
        "auth_mode": "api_key_or_signed_agent_preview",
        "well_known_paths": list(A2A_WELL_KNOWN_PATHS),
        "capability_discovery_preview": capability_discovery_preview,
        "availability_preview": availability_preview,
        "accepted_protocols": list(ACCEPTED_PROTOCOLS),
        "authentication_requirements": authentication_requirements,
        "safety": safety,
        "blocked_reasons": blocked_reasons,
    }

    preview = A2AWellKnownDiscoveryPreview(
        **payload_without_hash,
        discovery_hash=_stable_hash(payload_without_hash),
    )

    payload = asdict(preview)
    return {
        "ok": True,
        "status": "well_known_discovery_preview_ready",
        "preview_only": True,
        "public_route_mounted": False,
        "payload": payload,
        "discovery_hash": payload["discovery_hash"],
        "response_hash": _stable_hash(payload),
    }


def build_well_known_discovery_summary(
    *,
    business_id: str = "home_fixed",
    business_name: str = "Home Fixed",
    vertical_key: str = "home_repair",
    industry_key: str = "trades",
) -> Dict[str, Any]:
    wrapped = build_well_known_discovery_preview(
        business_id=business_id,
        business_name=business_name,
        vertical_key=vertical_key,
        industry_key=industry_key,
    )
    payload = wrapped["payload"]

    summary = {
        "contract_version": payload["contract_version"],
        "business_id": payload["business_id"],
        "vertical_key": payload["vertical_key"],
        "well_known_paths": payload["well_known_paths"],
        "accepted_protocol_count": len(payload["accepted_protocols"]),
        "requires_auth": payload["requires_auth"],
        "auth_mode": payload["auth_mode"],
        "public_route_mounted": payload["public_route_mounted"],
        "preview_only": payload["preview_only"],
        "discovery_hash": payload["discovery_hash"],
    }
    summary["summary_hash"] = _stable_hash(summary)
    return summary
