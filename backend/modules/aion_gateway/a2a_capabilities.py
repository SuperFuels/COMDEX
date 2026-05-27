# backend/modules/aion_gateway/a2a_capabilities.py
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List

from backend.modules.aion_gateway.a2a_api import A2A_API_VERSION


A2A_CAPABILITIES_VERSION = "aion.a2a_capabilities.v0.1"


def _stable_hash(payload: Dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _base_safety() -> Dict[str, bool]:
    return {
        "guarded": True,
        "preview_only": True,
        "public_route_exposed": False,
        "requires_auth": True,
        "would_execute_workflow": False,
        "would_create_booking": False,
        "would_move_money": False,
        "would_move_pho": False,
        "would_create_payment": False,
        "would_create_escrow": False,
        "would_send_external_message": False,
    }


def build_business_capabilities_preview(
    *,
    business_id: str = "home_fixed",
    business_name: str = "Home Fixed",
    vertical_key: str = "home_repair",
    industry_key: str = "trades",
) -> Dict[str, Any]:
    """
    Build a universal business capabilities preview.

    Home Fixed is only the default fixture. The contract is universal and can
    later map legal, accounting, medical, hospitality, property, and other
    verticals through vertical adapters.
    """
    payload: Dict[str, Any] = {
        "ok": True,
        "status": "preview_ready",
        "contract_version": A2A_CAPABILITIES_VERSION,
        "a2a_namespace_version": A2A_API_VERSION,
        "endpoint_key": "business_capabilities",
        "method": "GET",
        "path": f"/api/aion/a2a/{business_id}/business_capabilities",
        "business_id": business_id,
        "business_name": business_name,
        "vertical_key": vertical_key,
        "industry_key": industry_key,
        "universal_gateway": True,
        "vertical_adapter_required": True,
        "capability_profile": {
            "accepts_customer_requests": True,
            "supports_machine_catalog": True,
            "supports_availability_preview": True,
            "supports_quote_preview": True,
            "supports_job_request_preview": True,
            "supports_job_trace_preview": True,
            "supports_evidence_preview": True,
            "supports_settlement_readiness_preview": True,
            "supports_proof_receipt_preview": True,
            "supports_trust_summary_preview": True,
            "supports_public_ranking": False,
            "supports_live_booking": False,
            "supports_live_payment": False,
            "supports_live_escrow": False,
        },
        "service_categories": [
            {
                "category_id": "general_service_request",
                "label": "General service request",
                "description": "Universal request category used by the Gateway before vertical-specific mapping.",
            },
            {
                "category_id": "quote_request",
                "label": "Quote request",
                "description": "Preview-only quote request capability.",
            },
            {
                "category_id": "evidence_backed_completion",
                "label": "Evidence-backed completion",
                "description": "Capability to attach completion evidence to a job trace.",
            },
        ],
        "accepted_protocols": [
            "aion.a2a.preview.v0",
            "aion.machine_cart.preview.v0",
            "aion.proof_receipt.preview.v0",
        ],
        "authentication": {
            "required": True,
            "mode": "api_key_or_signed_agent_preview",
            "production_auth_enforced": False,
        },
        "schemas": {
            "request_schema": "universal_service_request_preview.v0",
            "quote_schema": "machine_cart_quote_preview.v0",
            "evidence_schema": "evidence_bundle_preview.v0",
            "settlement_schema": "settlement_readiness_preview.v0",
            "trust_schema": "business_trust_summary.v0",
        },
        "blocked_reasons": [
            "preview_only",
            "guarded_namespace",
            "auth_required",
            "public_route_not_exposed",
            "no_live_booking",
            "no_live_payment",
            "no_live_escrow",
            "no_external_message_side_effect",
        ],
        "safety": _base_safety(),
    }
    payload["capabilities_hash"] = _stable_hash(payload)
    return payload


def build_business_machine_catalog_preview(
    *,
    business_id: str = "home_fixed",
    business_name: str = "Home Fixed",
    vertical_key: str = "home_repair",
    industry_key: str = "trades",
) -> Dict[str, Any]:
    """
    Build a universal machine catalog preview.

    The catalog contains generic capability slots plus Home Fixed fixture
    examples. Future vertical adapters should replace the item set while
    preserving the universal response envelope.
    """
    payload: Dict[str, Any] = {
        "ok": True,
        "status": "preview_ready",
        "contract_version": A2A_CAPABILITIES_VERSION,
        "a2a_namespace_version": A2A_API_VERSION,
        "endpoint_key": "business_machine_catalog",
        "method": "GET",
        "path": f"/api/aion/a2a/{business_id}/business_machine_catalog",
        "business_id": business_id,
        "business_name": business_name,
        "vertical_key": vertical_key,
        "industry_key": industry_key,
        "universal_gateway": True,
        "vertical_adapter_required": True,
        "catalog_profile": {
            "catalog_type": "machine_readable_service_catalog",
            "quote_preview_supported": True,
            "availability_preview_supported": True,
            "evidence_requirements_supported": True,
            "settlement_readiness_supported": True,
            "proof_receipt_supported": True,
        },
        "items": [
            {
                "service_id": "home_repair_general",
                "label": "General home repair",
                "category": "home_repair",
                "request_schema": "universal_service_request_preview.v0",
                "quote_schema": "machine_cart_quote_preview.v0",
                "evidence_schema": "photo_and_completion_note_evidence.v0",
                "requires_human_review": True,
                "live_booking_supported": False,
            },
            {
                "service_id": "inspection_and_quote",
                "label": "Inspection and quote",
                "category": "quote_request",
                "request_schema": "universal_service_request_preview.v0",
                "quote_schema": "machine_cart_quote_preview.v0",
                "evidence_schema": "inspection_notes_preview.v0",
                "requires_human_review": True,
                "live_booking_supported": False,
            },
            {
                "service_id": "completion_evidence",
                "label": "Completion evidence",
                "category": "evidence_backed_completion",
                "request_schema": "job_evidence_preview.v0",
                "quote_schema": "not_applicable",
                "evidence_schema": "evidence_bundle_preview.v0",
                "requires_human_review": True,
                "live_booking_supported": False,
            },
        ],
        "vertical_mapping_notes": [
            "Home Fixed is the default validation fixture.",
            "The catalog envelope is universal.",
            "Legal, accounting, healthcare, hospitality, and other verticals should replace catalog items through a vertical adapter.",
        ],
        "blocked_reasons": [
            "preview_only",
            "guarded_namespace",
            "auth_required",
            "public_route_not_exposed",
            "no_live_booking",
            "no_live_payment",
            "no_live_escrow",
            "no_external_message_side_effect",
        ],
        "safety": _base_safety(),
    }
    payload["catalog_hash"] = _stable_hash(payload)
    return payload


def build_a2a_capabilities_catalog_bundle(
    *,
    business_id: str = "home_fixed",
    business_name: str = "Home Fixed",
    vertical_key: str = "home_repair",
    industry_key: str = "trades",
) -> Dict[str, Any]:
    capabilities = build_business_capabilities_preview(
        business_id=business_id,
        business_name=business_name,
        vertical_key=vertical_key,
        industry_key=industry_key,
    )
    catalog = build_business_machine_catalog_preview(
        business_id=business_id,
        business_name=business_name,
        vertical_key=vertical_key,
        industry_key=industry_key,
    )

    payload: Dict[str, Any] = {
        "ok": True,
        "status": "preview_ready",
        "contract_version": A2A_CAPABILITIES_VERSION,
        "business_id": business_id,
        "business_name": business_name,
        "vertical_key": vertical_key,
        "industry_key": industry_key,
        "universal_gateway": True,
        "capabilities": capabilities,
        "machine_catalog": catalog,
        "safety": _base_safety(),
    }
    payload["bundle_hash"] = _stable_hash(payload)
    return payload
