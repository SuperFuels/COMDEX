"""Phase 14D: AgentMap live verification preview.

This module does not perform live HTTP calls. It verifies a supplied AgentMap
discovery payload as a deterministic preview model, similar to a Google
Analytics-style install verification flow, without mounting public routes or
triggering side effects.
"""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any, Dict, Mapping, Optional

from backend.modules.aion_gateway.agentmap_discovery_endpoint import (
    build_agentmap_discovery_endpoint_preview,
)


VERIFICATION_VERSION = "aion.agentmap.verification.v0.1"


def _canonical_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def _stable_hash(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _default_install_targets() -> Dict[str, Any]:
    return {
        "canonical_path": "/agentmap.json",
        "well_known_path": "/.well-known/agentmap.json",
        "install_tag": '<link rel="agentmap" type="application/json" href="/agentmap.json">',
    }


def _safe_status_flags() -> Dict[str, bool]:
    return {
        "preview_only": True,
        "read_only": True,
        "human_review_required": True,
        "public_route_mounted": False,
        "live_side_effects_enabled": False,
        "would_create_booking": False,
        "would_create_payment": False,
        "would_create_escrow": False,
        "would_dispatch_job": False,
        "would_send_external_message": False,
        "would_write_live_chain": False,
    }


def build_agentmap_live_verification_preview(
    request: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Build a deterministic AgentMap live-install verification preview.

    The caller may provide a request with:
    - business_id
    - business_name
    - vertical_key
    - observed_agentmap_payload
    - observed_status_code
    - observed_content_type

    No network request is performed here.
    """

    request = dict(request or {})
    endpoint_preview = build_agentmap_discovery_endpoint_preview(request)
    expected_targets = _default_install_targets()

    observed_payload = deepcopy(
        request.get("observed_agentmap_payload") or endpoint_preview.get("agentmap") or {}
    )
    observed_status_code = int(request.get("observed_status_code", 200))
    observed_content_type = request.get("observed_content_type", "application/json")

    expected_agentmap_hash = endpoint_preview.get("agentmap_hash")
    observed_agentmap_hash = observed_payload.get("agentmap_hash")

    # Phase 14D can verify either:
    # 1. a raw AgentMap manifest payload, or
    # 2. the read-only discovery endpoint preview payload from Phase 14C.
    manifest_shape_valid = all(
        [
            bool(observed_payload.get("agentmap_version")),
            bool(observed_payload.get("business_id")),
            bool(observed_payload.get("vertical_key")),
            bool(observed_agentmap_hash),
            bool(
                observed_payload.get("machine_metadata")
                or observed_payload.get("machine_a2a_metadata")
            ),
        ]
    )

    endpoint_shape_valid = all(
        [
            bool(observed_payload.get("endpoint_version")),
            bool(observed_payload.get("business_id")),
            bool(observed_payload.get("vertical_key")),
            bool(observed_payload.get("agentmap_hash")),
            bool(observed_payload.get("endpoint_hash")),
            bool(observed_payload.get("summary_hash")),
            bool(observed_payload.get("paths", {}).get("canonical")),
            bool(observed_payload.get("paths", {}).get("well_known")),
            bool(observed_payload.get("safety_profile")),
        ]
    )

    schema_checks = {
        "manifest_shape_valid": manifest_shape_valid,
        "endpoint_shape_valid": endpoint_shape_valid,
        "has_business_id": bool(observed_payload.get("business_id")),
        "has_vertical_key": bool(observed_payload.get("vertical_key")),
        "has_agentmap_hash": bool(observed_agentmap_hash),
    }

    safety = _safe_status_flags()
    payload_safety = observed_payload.get("safety_profile", {})
    if isinstance(payload_safety, Mapping):
        safety["preview_only"] = bool(payload_safety.get("preview_only", True))
        safety["human_review_required"] = bool(
            payload_safety.get("human_review_required", True)
        )
        safety["live_side_effects_enabled"] = bool(
            payload_safety.get("live_side_effects_enabled", False)
        )

    checks = {
        "canonical_path_declared": endpoint_preview["paths"]["canonical"]
        == expected_targets["canonical_path"],
        "well_known_path_declared": endpoint_preview["paths"]["well_known"]
        == expected_targets["well_known_path"],
        "status_code_ok": observed_status_code == 200,
        "content_type_json": "json" in str(observed_content_type).lower(),
        "schema_valid": bool(manifest_shape_valid or endpoint_shape_valid),
        "agentmap_hash_present": bool(observed_agentmap_hash),
        "agentmap_hash_matches_expected": observed_agentmap_hash == expected_agentmap_hash,
        "endpoint_hash_present": bool(endpoint_preview.get("endpoint_hash")),
        "summary_hash_present": bool(endpoint_preview.get("summary_hash")),
        "preview_only": safety["preview_only"] is True,
        "human_review_required": safety["human_review_required"] is True,
        "live_side_effects_disabled": safety["live_side_effects_enabled"] is False,
    }

    verified = all(checks.values())

    response: Dict[str, Any] = {
        "verification_version": VERIFICATION_VERSION,
        "status": "verified" if verified else "not_verified",
        "business_id": endpoint_preview["business_id"],
        "business_name": endpoint_preview["business_name"],
        "vertical_key": endpoint_preview["vertical_key"],
        "install_targets": expected_targets,
        "observed": {
            "status_code": observed_status_code,
            "content_type": observed_content_type,
            "agentmap_hash": observed_agentmap_hash,
        },
        "expected": {
            "agentmap_hash": expected_agentmap_hash,
            "endpoint_hash": endpoint_preview["endpoint_hash"],
            "summary_hash": endpoint_preview["summary_hash"],
        },
        "schema_checks": schema_checks,
        "checks": checks,
        "safety_profile": safety,
        "verified": verified,
    }

    hash_payload = deepcopy(response)
    hash_payload.pop("verification_hash", None)
    response["verification_hash"] = _stable_hash(hash_payload)

    summary_payload = {
        "verification_version": response["verification_version"],
        "status": response["status"],
        "business_id": response["business_id"],
        "vertical_key": response["vertical_key"],
        "verified": response["verified"],
        "agentmap_hash": response["expected"]["agentmap_hash"],
        "verification_hash": response["verification_hash"],
        "safety_profile": response["safety_profile"],
    }
    response["summary_hash"] = _stable_hash(summary_payload)

    return response


def build_agentmap_live_verification_summary(
    request: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    preview = build_agentmap_live_verification_preview(request)
    return {
        "verification_version": preview["verification_version"],
        "status": preview["status"],
        "business_id": preview["business_id"],
        "vertical_key": preview["vertical_key"],
        "verified": preview["verified"],
        "agentmap_hash": preview["expected"]["agentmap_hash"],
        "verification_hash": preview["verification_hash"],
        "summary_hash": preview["summary_hash"],
        "preview_only": preview["safety_profile"]["preview_only"],
        "read_only": preview["safety_profile"]["read_only"],
        "human_review_required": preview["safety_profile"]["human_review_required"],
        "live_side_effects_enabled": preview["safety_profile"]["live_side_effects_enabled"],
    }


__all__ = [
    "VERIFICATION_VERSION",
    "build_agentmap_live_verification_preview",
    "build_agentmap_live_verification_summary",
]
