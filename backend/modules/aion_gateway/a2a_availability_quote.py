# backend/modules/aion_gateway/a2a_availability_quote.py
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Optional

from backend.modules.aion_gateway.a2a_api import A2A_API_VERSION
from backend.modules.aion_gateway.a2a_capabilities import A2A_CAPABILITIES_VERSION


A2A_AVAILABILITY_QUOTE_VERSION = "aion.a2a_availability_quote.v0.1"


def _stable_hash(payload: Dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _base_safety() -> Dict[str, bool]:
    return {
        "guarded": True,
        "preview_only": True,
        "public_route_exposed": False,
        "requires_auth": True,
        "human_review_required": True,
        "would_execute_workflow": False,
        "would_create_booking": False,
        "would_move_money": False,
        "would_move_pho": False,
        "would_create_payment": False,
        "would_create_escrow": False,
        "would_send_external_message": False,
        "quote_negotiation_enabled": False,
        "live_booking_supported": False,
    }


def build_business_availability_preview(
    *,
    business_id: str = "home_fixed",
    business_name: str = "Home Fixed",
    vertical_key: str = "home_repair",
    industry_key: str = "trades",
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "ok": True,
        "status": "preview_ready",
        "contract_version": A2A_AVAILABILITY_QUOTE_VERSION,
        "a2a_namespace_version": A2A_API_VERSION,
        "capabilities_version": A2A_CAPABILITIES_VERSION,
        "endpoint_key": "business_availability",
        "method": "GET",
        "path": f"/api/aion/a2a/{business_id}/business_availability",
        "business_id": business_id,
        "business_name": business_name,
        "vertical_key": vertical_key,
        "industry_key": industry_key,
        "universal_gateway": True,
        "availability_mode": "preview_only",
        "timezone": "Europe/Madrid",
        "availability_windows": [
            {
                "window_id": "weekday_standard_preview",
                "label": "Weekday standard preview",
                "days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
                "start_time": "09:00",
                "end_time": "17:00",
                "booking_allowed": False,
                "human_review_required": True,
            },
            {
                "window_id": "urgent_review_preview",
                "label": "Urgent request review preview",
                "days": ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday"],
                "start_time": "09:00",
                "end_time": "19:00",
                "booking_allowed": False,
                "human_review_required": True,
            },
        ],
        "availability_state": {
            "can_accept_request_preview": True,
            "can_quote_preview": True,
            "can_create_live_booking": False,
            "requires_human_review_before_booking": True,
            "next_step": "submit_preview_request_for_human_review",
        },
        "vertical_mapping_notes": [
            "Home Fixed is the default validation fixture.",
            "Availability envelope is universal.",
            "Legal, accounting, healthcare, hospitality, property, and other verticals should map their own availability rules through a vertical adapter.",
        ],
        "blocked_reasons": [
            "preview_only",
            "guarded_namespace",
            "auth_required",
            "public_route_not_exposed",
            "no_live_booking",
            "human_review_required",
        ],
        "safety": _base_safety(),
    }
    payload["availability_hash"] = _stable_hash(payload)
    return payload


def validate_machine_cart_quote_request_preview(request: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    req = request or {}
    missing: List[str] = []

    for key in ["business_id", "vertical_key", "service_id", "requested_outcome"]:
        if not req.get(key):
            missing.append(key)

    return {
        "ok": not missing,
        "status": "valid" if not missing else "invalid",
        "missing_fields": missing,
        "schema": "machine_cart_quote_request_preview.v0",
        "preview_only": True,
        "human_review_required": True,
    }


def build_machine_cart_quote_request_preview(
    request: Optional[Dict[str, Any]] = None,
    *,
    business_id: str = "home_fixed",
    business_name: str = "Home Fixed",
    vertical_key: str = "home_repair",
    industry_key: str = "trades",
) -> Dict[str, Any]:
    req = request or {
        "business_id": business_id,
        "vertical_key": vertical_key,
        "industry_key": industry_key,
        "service_id": "inspection_and_quote",
        "requested_outcome": "Preview quote for a service request",
        "customer_context": {
            "location_hint": "Almería preview area",
            "urgency": "standard",
        },
    }

    validation = validate_machine_cart_quote_request_preview(req)

    payload: Dict[str, Any] = {
        "ok": validation["ok"],
        "status": "preview_ready" if validation["ok"] else "blocked",
        "contract_version": A2A_AVAILABILITY_QUOTE_VERSION,
        "a2a_namespace_version": A2A_API_VERSION,
        "capabilities_version": A2A_CAPABILITIES_VERSION,
        "endpoint_key": "machine_cart_quote_request_preview",
        "method": "POST",
        "path": f"/api/aion/a2a/{business_id}/machine_cart_quote_request_preview",
        "business_id": business_id,
        "business_name": business_name,
        "vertical_key": vertical_key,
        "industry_key": industry_key,
        "universal_gateway": True,
        "request": req,
        "validation": validation,
        "quote_preview": {
            "quote_preview_id": "quote_preview_home_fixed_001",
            "status": "quote_preview_only",
            "currency": "EUR",
            "estimated_min": 0,
            "estimated_max": 0,
            "pricing_mode": "requires_human_review",
            "final_quote_created": False,
            "quote_negotiation_enabled": False,
            "human_review_required": True,
            "notes": [
                "This is not a final quote.",
                "The business must review the request before any live quote, booking, payment, or external message.",
            ],
        },
        "next_step": {
            "type": "future_guarded_approval_path",
            "label": "Route quote preview to human review",
            "live_action_allowed": False,
        },
        "blocked_reasons": [
            "preview_only",
            "guarded_namespace",
            "auth_required",
            "public_route_not_exposed",
            "no_live_booking",
            "no_quote_negotiation",
            "no_payment_side_effect",
            "human_review_required",
            *validation["missing_fields"],
        ],
        "safety": _base_safety(),
    }
    payload["quote_request_hash"] = _stable_hash(payload)
    return payload


def build_a2a_availability_quote_bundle(
    *,
    business_id: str = "home_fixed",
    business_name: str = "Home Fixed",
    vertical_key: str = "home_repair",
    industry_key: str = "trades",
) -> Dict[str, Any]:
    availability = build_business_availability_preview(
        business_id=business_id,
        business_name=business_name,
        vertical_key=vertical_key,
        industry_key=industry_key,
    )
    quote = build_machine_cart_quote_request_preview(
        business_id=business_id,
        business_name=business_name,
        vertical_key=vertical_key,
        industry_key=industry_key,
    )

    payload: Dict[str, Any] = {
        "ok": True,
        "status": "preview_ready",
        "contract_version": A2A_AVAILABILITY_QUOTE_VERSION,
        "business_id": business_id,
        "business_name": business_name,
        "vertical_key": vertical_key,
        "industry_key": industry_key,
        "universal_gateway": True,
        "availability": availability,
        "quote_request_preview": quote,
        "safety": _base_safety(),
    }
    payload["bundle_hash"] = _stable_hash(payload)
    return payload
