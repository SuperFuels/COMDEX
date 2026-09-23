"""AION Public Website Widget Request Mapping Preview v0.

Maps public website widget surfaces into safe preview request objects.

This module is intentionally preview-only:
- no public write route is exposed here,
- no live booking is created,
- no live job is created,
- no Goal Engine execution occurs,
- no payment, escrow, PHO movement, fund release, or external send occurs.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict, field
from hashlib import sha256
import json
from typing import Any, Mapping


PUBLIC_WIDGET_REQUEST_MAPPING_VERSION = "aion.public_widget_request_mapping.v0.1"

_ALLOWED_SURFACES = {
    "website_form_widget_preview",
    "website_button_widget_preview",
    "embedded_chat_widget_preview",
}

_SURFACE_ALIASES = {
    "form": "website_form_widget_preview",
    "website_form": "website_form_widget_preview",
    "website_form_widget": "website_form_widget_preview",
    "button": "website_button_widget_preview",
    "website_button": "website_button_widget_preview",
    "website_button_widget": "website_button_widget_preview",
    "chat": "embedded_chat_widget_preview",
    "embedded_chat": "embedded_chat_widget_preview",
    "embedded_chat_widget": "embedded_chat_widget_preview",
}


def _stable_hash(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return sha256(encoded.encode("utf-8")).hexdigest()


def _normalise_surface(surface: str) -> str:
    key = str(surface or "").strip()
    return _SURFACE_ALIASES.get(key, key)


def _safe_payload(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    if not payload:
        return {}
    return dict(payload)


@dataclass(frozen=True)
class PublicWidgetRequestMappingInput:
    business_id: str = "home_fixed"
    business_name: str = "Home Fixed"
    vertical_key: str = "home_repair"
    widget_surface: str = "website_form_widget_preview"
    customer_message: str = ""
    requested_service_key: str = ""
    requested_location: str = ""
    requested_window: str = ""
    max_fiat_price: str = ""
    currency: str = "EUR"
    customer_contact_preview: str = "redacted_preview_only"


@dataclass(frozen=True)
class PublicWidgetRequestMappingPreview:
    ok: bool
    status: str
    contract_version: str
    preview_only: bool
    business_id: str
    business_name: str
    vertical_key: str
    widget_surface: str
    mapping_kind: str
    normalized_intent_preview: dict[str, Any]
    machine_cart_request_preview: dict[str, Any]
    public_intent_gateway_preview: dict[str, Any]
    required_guards: dict[str, bool]
    safety: dict[str, bool]
    blocked_reasons: list[str]
    request_hash: str
    normalized_intent_hash: str
    machine_cart_request_hash: str
    response_hash: str


def build_public_widget_request_mapping_preview(
    *,
    widget_surface: str = "website_form_widget_preview",
    payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a deterministic preview mapping for a public website widget request."""

    raw = _safe_payload(payload)
    surface = _normalise_surface(widget_surface or raw.get("widget_surface", ""))

    business_id = str(raw.get("business_id") or "home_fixed")
    business_name = str(raw.get("business_name") or "Home Fixed")
    vertical_key = str(raw.get("vertical_key") or "home_repair")

    request = PublicWidgetRequestMappingInput(
        business_id=business_id,
        business_name=business_name,
        vertical_key=vertical_key,
        widget_surface=surface,
        customer_message=str(raw.get("customer_message") or raw.get("message") or ""),
        requested_service_key=str(raw.get("requested_service_key") or raw.get("service_key") or ""),
        requested_location=str(raw.get("requested_location") or raw.get("location") or ""),
        requested_window=str(raw.get("requested_window") or ""),
        max_fiat_price=str(raw.get("max_fiat_price") or ""),
        currency=str(raw.get("currency") or "EUR"),
        customer_contact_preview=str(raw.get("customer_contact_preview") or "redacted_preview_only"),
    )

    request_dict = asdict(request)
    request_hash = _stable_hash(request_dict)

    if surface not in _ALLOWED_SURFACES:
        blocked = [
            "unsupported_widget_surface",
            "preview_only",
            "human_review_required",
            "no_live_job_creation",
            "no_booking_side_effect",
            "no_payment_side_effect",
            "no_external_message_side_effect",
        ]
        response = {
            "ok": False,
            "status": "unsupported_widget_surface",
            "contract_version": PUBLIC_WIDGET_REQUEST_MAPPING_VERSION,
            "preview_only": True,
            "business_id": business_id,
            "business_name": business_name,
            "vertical_key": vertical_key,
            "widget_surface": surface,
            "blocked_reasons": blocked,
            "request_hash": request_hash,
            "safety": _safety(),
        }
        response["response_hash"] = _stable_hash(response)
        return response

    mapping_kind = {
        "website_form_widget_preview": "human_form_to_normalized_inbound_intent",
        "website_button_widget_preview": "button_request_to_machine_cart_request",
        "embedded_chat_widget_preview": "chat_request_to_normalized_intent_or_machine_cart_request",
    }[surface]

    normalized_intent_preview = {
        "status": "normalized_intent_preview_only",
        "intent_type": "public_website_widget_request",
        "source_surface": surface,
        "business_id": business_id,
        "vertical_key": vertical_key,
        "customer_message": request.customer_message,
        "requested_service_key": request.requested_service_key,
        "requested_location": request.requested_location,
        "customer_contact_preview": request.customer_contact_preview,
        "human_review_required": True,
        "live_intent_created": False,
    }

    machine_cart_request_preview = {
        "status": "machine_cart_request_preview_only",
        "source_surface": surface,
        "business_id": business_id,
        "vertical_key": vertical_key,
        "service_key": request.requested_service_key,
        "location": request.requested_location,
        "requested_window": request.requested_window,
        "max_fiat_price": request.max_fiat_price,
        "currency": request.currency,
        "human_review_required": True,
        "live_cart_created": False,
        "quote_preview_only": True,
    }

    public_intent_gateway_preview = {
        "status": "public_intent_gateway_preview_only",
        "gateway_contract": "aion.public_intent_gateway.v0.1",
        "tenant_business_key_validation_required": True,
        "signed_request_validation_required": True,
        "rate_limiting_required": True,
        "abuse_protection_required": True,
        "human_review_required": True,
        "unauthenticated_public_write_route_exposed": False,
    }

    normalized_intent_hash = _stable_hash(normalized_intent_preview)
    machine_cart_request_hash = _stable_hash(machine_cart_request_preview)

    result = PublicWidgetRequestMappingPreview(
        ok=True,
        status="widget_request_mapping_preview_ready",
        contract_version=PUBLIC_WIDGET_REQUEST_MAPPING_VERSION,
        preview_only=True,
        business_id=business_id,
        business_name=business_name,
        vertical_key=vertical_key,
        widget_surface=surface,
        mapping_kind=mapping_kind,
        normalized_intent_preview=normalized_intent_preview,
        machine_cart_request_preview=machine_cart_request_preview,
        public_intent_gateway_preview=public_intent_gateway_preview,
        required_guards={
            "tenant_business_key_validation_required": True,
            "signed_request_validation_required": True,
            "rate_limiting_required": True,
            "abuse_protection_required": True,
            "human_review_required": True,
        },
        safety=_safety(),
        blocked_reasons=[
            "preview_only",
            "human_review_required",
            "no_live_job_creation",
            "no_booking_side_effect",
            "no_goal_engine_execution",
            "no_payment_side_effect",
            "no_escrow_side_effect",
            "no_external_message_side_effect",
        ],
        request_hash=request_hash,
        normalized_intent_hash=normalized_intent_hash,
        machine_cart_request_hash=machine_cart_request_hash,
        response_hash="",
    )

    response = asdict(result)
    response["response_hash"] = _stable_hash({k: v for k, v in response.items() if k != "response_hash"})
    return response


def build_public_widget_request_mapping_summary(
    *,
    widget_surface: str = "website_form_widget_preview",
    payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    preview = build_public_widget_request_mapping_preview(
        widget_surface=widget_surface,
        payload=payload,
    )

    summary = {
        "ok": bool(preview.get("ok")),
        "status": preview.get("status"),
        "contract_version": PUBLIC_WIDGET_REQUEST_MAPPING_VERSION,
        "preview_only": True,
        "business_id": preview.get("business_id"),
        "vertical_key": preview.get("vertical_key"),
        "widget_surface": preview.get("widget_surface"),
        "has_normalized_intent_preview": bool(preview.get("normalized_intent_preview")),
        "has_machine_cart_request_preview": bool(preview.get("machine_cart_request_preview")),
        "has_public_intent_gateway_preview": bool(preview.get("public_intent_gateway_preview")),
        "human_review_required": True,
        "would_create_booking": False,
        "would_create_live_job": False,
        "would_execute_goal_engine": False,
        "would_move_money": False,
        "would_create_payment": False,
        "would_create_escrow": False,
        "would_send_external_message": False,
        "response_hash": preview.get("response_hash"),
    }
    summary["summary_hash"] = _stable_hash(summary)
    return summary


def _safety() -> dict[str, bool]:
    return {
        "preview_only": True,
        "human_review_required": True,
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
        "would_expose_unauthenticated_public_write_route": False,
    }
