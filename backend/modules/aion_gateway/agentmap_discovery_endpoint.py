"""Read-only AgentMap discovery endpoint preview.

Phase 14C lock:
- declares future /agentmap.json and /.well-known/agentmap.json discovery paths;
- returns deterministic preview response objects;
- exposes only safe read-only capability route metadata;
- does not mount a public route;
- does not create booking, payment, escrow, dispatch, external messages, or live jobs.
"""

from __future__ import annotations

import hashlib
import importlib
import json
from copy import deepcopy
from typing import Any, Dict, Mapping, Optional

AGENTMAP_DISCOVERY_ENDPOINT_VERSION = "aion.agentmap_discovery_endpoint.v0.1"

CANONICAL_AGENTMAP_PATH = "/agentmap.json"
WELL_KNOWN_AGENTMAP_PATH = "/.well-known/agentmap.json"

READ_ONLY_METHODS = ("GET", "HEAD")
FORBIDDEN_WRITE_METHODS = ("POST", "PUT", "PATCH", "DELETE")

SAFE_CAPABILITY_ROUTE_TYPES = (
    "agentmap_manifest_preview",
    "machine_metadata_preview",
    "capabilities_catalog_preview",
    "availability_quote_preview",
    "proof_receipt_lookup_preview",
    "trust_summary_preview",
    "public_intent_preview",
    "human_review_handoff_preview",
)


def _canonical_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def _stable_hash(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _load_agentmap_manifest(request: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    """Load the locked Phase 14 AgentMap manifest without binding to one exact helper name.

    The AgentMap manifest module has already been locked in Phase 14A. This endpoint
    preview consumes it if available and falls back to the same safe default identity
    only if helper names change during development.
    """

    request = dict(request or {})

    module = importlib.import_module("backend.modules.aion_gateway.agentmap_manifest")

    builder_names = (
        "build_home_fixed_agentmap_manifest",
        "build_agentmap_manifest",
        "build_agentmap_machine_metadata_manifest",
        "build_agentmap_manifest_preview",
    )

    for name in builder_names:
        builder = getattr(module, name, None)
        if callable(builder):
            try:
                # Phase 14A builder accepts explicit business identity kwargs.
                result = builder(
                    business_id=request.get("business_id", "home_fixed"),
                    business_name=request.get("business_name", "Home Fixed"),
                    vertical_key=request.get("vertical_key", "home_repair"),
                    human_seo_metadata=request.get("human_seo_metadata"),
                    machine_a2a_metadata=request.get("machine_a2a_metadata"),
                    capabilities=request.get("capabilities"),
                    availability=request.get("availability"),
                    accepted_protocols=request.get("accepted_protocols"),
                    auth_requirements=request.get("auth_requirements"),
                    safety_profile=request.get("safety_profile"),
                    schema_refs=request.get("schema_refs"),
                    adapter=request.get("adapter"),
                )
            except TypeError:
                try:
                    result = builder(request)
                except TypeError:
                    result = builder()
            if isinstance(result, dict):
                return deepcopy(result)

    # Safe fallback. This should normally not be used, but it keeps the discovery
    # endpoint preview universal and non-mutating while helper names evolve.
    base = {
        "agentmap_version": "aion.agentmap.v0.1",
        "business_id": request.get("business_id", "home_fixed"),
        "business_name": request.get("business_name", "Home Fixed"),
        "vertical_key": request.get("vertical_key", "home_repair"),
        "human_seo_metadata": {
            "meta_title": request.get("meta_title", "Home Fixed"),
            "meta_description": request.get(
                "meta_description",
                "Home repair and property maintenance services.",
            ),
        },
        "machine_a2a_metadata": {
            "machine_description": request.get(
                "machine_description",
                "Agent-readable Home Fixed service capability map.",
            ),
            "accepted_protocols": [
                "aion.agentmap.preview.v0",
                "aion.a2a.preview.v0",
                "aion.machine_cart.preview.v0",
                "aion.proof_receipt.preview.v0",
            ],
        },
        "safety_profile": _build_safety_profile(),
    }
    base["agentmap_hash"] = _stable_hash(base)
    return base


def _build_safety_profile() -> Dict[str, Any]:
    return {
        "preview_only": True,
        "read_only": True,
        "human_review_required": True,
        "live_side_effects_enabled": False,
        "public_route_mounted": False,
        "unauthenticated_public_write_route_exposed": False,
        "would_create_booking": False,
        "would_create_live_job": False,
        "would_execute_goal_engine": False,
        "would_move_money": False,
        "would_move_pho": False,
        "would_require_wallet": False,
        "would_create_payment": False,
        "would_create_escrow": False,
        "would_release_funds": False,
        "would_dispatch_work": False,
        "would_send_external_messages": False,
        "would_write_live_chain": False,
    }


def _build_safe_capability_routes(manifest: Mapping[str, Any]) -> Dict[str, Any]:
    business_id = manifest.get("business_id", "home_fixed")
    vertical_key = manifest.get("vertical_key", "home_repair")

    return {
        "agentmap_manifest": {
            "route_type": "agentmap_manifest_preview",
            "method": "GET",
            "path": CANONICAL_AGENTMAP_PATH,
            "read_only": True,
            "safe_to_index": True,
            "requires_human_review_before_execution": True,
            "input_schema_ref": "aion.schema.agentmap.discovery.request.v0",
            "output_schema_ref": "aion.schema.agentmap.manifest.response.v0",
            "business_id": business_id,
            "vertical_key": vertical_key,
            "side_effects_enabled": False,
        },
        "well_known_agentmap": {
            "route_type": "agentmap_manifest_preview",
            "method": "GET",
            "path": WELL_KNOWN_AGENTMAP_PATH,
            "read_only": True,
            "safe_to_index": True,
            "requires_human_review_before_execution": True,
            "input_schema_ref": "aion.schema.agentmap.discovery.request.v0",
            "output_schema_ref": "aion.schema.agentmap.manifest.response.v0",
            "business_id": business_id,
            "vertical_key": vertical_key,
            "side_effects_enabled": False,
        },
        "capabilities_catalog": {
            "route_type": "capabilities_catalog_preview",
            "method": "GET",
            "path": "/aion/a2a/capabilities/preview",
            "read_only": True,
            "safe_to_index": True,
            "requires_human_review_before_execution": True,
            "input_schema_ref": "aion.schema.capabilities.request.v0",
            "output_schema_ref": "aion.schema.capabilities.response.v0",
            "business_id": business_id,
            "vertical_key": vertical_key,
            "side_effects_enabled": False,
        },
        "proof_receipt_lookup": {
            "route_type": "proof_receipt_lookup_preview",
            "method": "GET",
            "path": "/aion/a2a/proof-receipt/preview",
            "read_only": True,
            "safe_to_index": True,
            "requires_human_review_before_execution": True,
            "input_schema_ref": "aion.schema.proof_receipt.lookup.request.v0",
            "output_schema_ref": "aion.schema.proof_receipt.lookup.response.v0",
            "business_id": business_id,
            "vertical_key": vertical_key,
            "side_effects_enabled": False,
        },
        "trust_summary": {
            "route_type": "trust_summary_preview",
            "method": "GET",
            "path": "/aion/a2a/trust-summary/preview",
            "read_only": True,
            "safe_to_index": True,
            "requires_human_review_before_execution": True,
            "input_schema_ref": "aion.schema.trust_summary.request.v0",
            "output_schema_ref": "aion.schema.trust_summary.response.v0",
            "business_id": business_id,
            "vertical_key": vertical_key,
            "side_effects_enabled": False,
        },
    }


def build_agentmap_discovery_endpoint_preview(
    request: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Build the read-only AgentMap discovery endpoint preview bundle."""

    request = dict(request or {})

    manifest = _load_agentmap_manifest(request)
    safety_profile = _build_safety_profile()
    capability_routes = _build_safe_capability_routes(manifest)

    response = {
        "endpoint_version": AGENTMAP_DISCOVERY_ENDPOINT_VERSION,
        "status": "agentmap_discovery_endpoint_preview_only",
        "business_id": manifest.get("business_id", "home_fixed"),
        "business_name": manifest.get("business_name", "Home Fixed"),
        "vertical_key": manifest.get("vertical_key", "home_repair"),
        "paths": {
            "canonical": CANONICAL_AGENTMAP_PATH,
            "well_known": WELL_KNOWN_AGENTMAP_PATH,
        },
        "http_preview": {
            "allowed_methods": list(READ_ONLY_METHODS),
            "forbidden_write_methods": list(FORBIDDEN_WRITE_METHODS),
            "content_type": "application/json",
            "status_code_preview": 200,
            "route_exposed": False,
            "public_route_mounted": False,
        },
        "agentmap_manifest": manifest,
        "agentmap_hash": manifest.get("agentmap_hash") or manifest.get("metadata_hash"),
        "safe_capability_routes": capability_routes,
        "safety_profile": safety_profile,
        "schema_refs": {
            "request_schema_ref": "aion.schema.agentmap.discovery.request.v0",
            "response_schema_ref": "aion.schema.agentmap.discovery.response.v0",
            "agentmap_schema_ref": "aion.schema.agentmap.manifest.v0",
            "capability_route_schema_ref": "aion.schema.agentmap.capability_route.v0",
        },
    }

    hash_payload = deepcopy(response)
    hash_payload.pop("endpoint_hash", None)
    hash_payload.pop("summary_hash", None)
    response["endpoint_hash"] = _stable_hash({
        "request_identity": {
            "business_id": request.get("business_id"),
            "business_name": request.get("business_name"),
            "vertical_key": request.get("vertical_key"),
        },
        "endpoint_payload": hash_payload,
    })

    summary_payload = {
        "endpoint_version": response["endpoint_version"],
        "business_id": response["business_id"],
        "vertical_key": response["vertical_key"],
        "paths": response["paths"],
        "agentmap_hash": response["agentmap_hash"],
        "endpoint_hash": response["endpoint_hash"],
        "safety_profile": response["safety_profile"],
    }
    response["summary_hash"] = _stable_hash(summary_payload)

    return response


def build_agentmap_discovery_endpoint_summary(
    request: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    preview = build_agentmap_discovery_endpoint_preview(request)
    return {
        "endpoint_version": preview["endpoint_version"],
        "status": preview["status"],
        "business_id": preview["business_id"],
        "vertical_key": preview["vertical_key"],
        "canonical_path": preview["paths"]["canonical"],
        "well_known_path": preview["paths"]["well_known"],
        "agentmap_hash": preview["agentmap_hash"],
        "endpoint_hash": preview["endpoint_hash"],
        "summary_hash": preview["summary_hash"],
        "preview_only": preview["safety_profile"]["preview_only"],
        "read_only": preview["safety_profile"]["read_only"],
        "human_review_required": preview["safety_profile"]["human_review_required"],
        "public_route_mounted": preview["safety_profile"]["public_route_mounted"],
        "live_side_effects_enabled": preview["safety_profile"]["live_side_effects_enabled"],
    }


__all__ = [
    "AGENTMAP_DISCOVERY_ENDPOINT_VERSION",
    "CANONICAL_AGENTMAP_PATH",
    "WELL_KNOWN_AGENTMAP_PATH",
    "SAFE_CAPABILITY_ROUTE_TYPES",
    "build_agentmap_discovery_endpoint_preview",
    "build_agentmap_discovery_endpoint_summary",
]
