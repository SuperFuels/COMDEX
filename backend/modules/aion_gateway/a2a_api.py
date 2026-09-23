# backend/modules/aion_gateway/a2a_api.py
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


A2A_API_VERSION = "aion.a2a_api.v0.1"


A2A_ALLOWED_PREVIEW_ENDPOINTS = {
    "business_capabilities",
    "business_machine_catalog",
    "business_availability",
    "machine_cart_quote_request_preview",
    "job_request_preview",
    "job_trace",
    "job_evidence",
    "settlement_readiness",
    "proof_commitment",
    "proof_receipt",
    "trust_summary",
}


A2A_HTTP_METHOD_BY_ENDPOINT = {
    "business_capabilities": "GET",
    "business_machine_catalog": "GET",
    "business_availability": "GET",
    "machine_cart_quote_request_preview": "POST",
    "job_request_preview": "POST",
    "job_trace": "GET",
    "job_evidence": "GET",
    "settlement_readiness": "GET",
    "proof_commitment": "GET",
    "proof_receipt": "GET",
    "trust_summary": "GET",
}


def _stable_hash(payload: Dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class A2AEndpointPreview:
    endpoint_key: str
    method: str
    path: str
    schema_version: str = A2A_API_VERSION
    deterministic_response: bool = True
    guarded: bool = True
    preview_only: bool = True
    public_route_exposed: bool = False
    requires_auth: bool = True
    auth_mode: str = "api_key_or_signed_agent_preview"
    would_execute_workflow: bool = False
    would_create_booking: bool = False
    would_move_money: bool = False
    would_move_pho: bool = False
    would_create_payment: bool = False
    would_create_escrow: bool = False
    would_send_external_message: bool = False
    blocked_reasons: List[str] = field(default_factory=list)

    def to_payload(self) -> Dict[str, Any]:
        return asdict(self)


def build_a2a_endpoint_preview(
    *,
    endpoint_key: str,
    business_id: str = "home_fixed",
    vertical_key: str = "home_repair",
) -> Dict[str, Any]:
    key = str(endpoint_key or "").strip()
    blocked_reasons: List[str] = []

    if key not in A2A_ALLOWED_PREVIEW_ENDPOINTS:
        blocked_reasons.append("unsupported_a2a_endpoint")

    method = A2A_HTTP_METHOD_BY_ENDPOINT.get(key, "GET")
    path = f"/api/aion/a2a/{business_id}/{key}"

    endpoint = A2AEndpointPreview(
        endpoint_key=key,
        method=method,
        path=path,
        blocked_reasons=[
            *blocked_reasons,
            "preview_only",
            "guarded_namespace",
            "auth_required",
            "public_route_not_exposed",
            "no_live_execution",
            "no_booking_side_effect",
            "no_payment_side_effect",
            "no_escrow_side_effect",
            "no_external_message_side_effect",
        ],
    ).to_payload()

    response = {
        "ok": not blocked_reasons,
        "status": "preview_ready" if not blocked_reasons else "blocked",
        "contract_version": A2A_API_VERSION,
        "business_id": str(business_id or "home_fixed"),
        "vertical_key": str(vertical_key or "home_repair"),
        "endpoint": endpoint,
    }
    response["response_hash"] = _stable_hash(response)
    return response


def build_guarded_a2a_namespace_preview(
    *,
    business_id: str = "home_fixed",
    vertical_key: str = "home_repair",
) -> Dict[str, Any]:
    endpoints = [
        build_a2a_endpoint_preview(
            endpoint_key=key,
            business_id=business_id,
            vertical_key=vertical_key,
        )["endpoint"]
        for key in sorted(A2A_ALLOWED_PREVIEW_ENDPOINTS)
    ]

    payload = {
        "ok": True,
        "status": "guarded_a2a_namespace_preview_ready",
        "contract_version": A2A_API_VERSION,
        "namespace": "/api/aion/a2a/*",
        "business_id": str(business_id or "home_fixed"),
        "vertical_key": str(vertical_key or "home_repair"),
        "guarded": True,
        "preview_only": True,
        "public_route_exposed": False,
        "requires_auth": True,
        "auth_mode": "api_key_or_signed_agent_preview",
        "deterministic_responses": True,
        "schema_versioned": True,
        "endpoints": endpoints,
        "safety": {
            "would_execute_workflow": False,
            "would_create_booking": False,
            "would_move_money": False,
            "would_move_pho": False,
            "would_create_payment": False,
            "would_create_escrow": False,
            "would_send_external_message": False,
            "public_route_exposed": False,
        },
        "blocked_reasons": [
            "preview_only",
            "guarded_namespace",
            "auth_required",
            "public_route_not_exposed",
            "no_live_execution",
            "no_booking_side_effect",
            "no_payment_side_effect",
            "no_escrow_side_effect",
            "no_external_message_side_effect",
        ],
    }
    payload["namespace_hash"] = _stable_hash(payload)
    return payload


def build_a2a_namespace_summary() -> Dict[str, Any]:
    preview = build_guarded_a2a_namespace_preview()
    endpoint_keys = [e["endpoint_key"] for e in preview["endpoints"]]

    return {
        "ok": True,
        "status": "a2a_namespace_summary_ready",
        "contract_version": A2A_API_VERSION,
        "namespace": preview["namespace"],
        "business_id": preview["business_id"],
        "vertical_key": preview["vertical_key"],
        "endpoint_count": len(preview["endpoints"]),
        "endpoint_keys": endpoint_keys,
        "guarded": preview["guarded"],
        "preview_only": preview["preview_only"],
        "public_route_exposed": preview["public_route_exposed"],
        "requires_auth": preview["requires_auth"],
        "namespace_hash": preview["namespace_hash"],
    }
