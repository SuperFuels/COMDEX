from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any, Mapping

PUBLIC_INTENT_GATEWAY_VERSION = "aion.public_intent_gateway.v0.1"


def _stable_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class PublicIntentGatewayRequest:
    business_id: str = "home_fixed"
    tenant_key: str = "home_fixed_preview"
    source: str = "website_form"
    customer_name: str = "Preview Customer"
    customer_contact: str = "preview@example.com"
    message: str = "Need help with a home repair."
    location: str = "Albox"
    requested_service: str = "home_repair"
    preferred_window: str = "human_review_required"
    max_fiat_price: str | None = None
    currency: str = "EUR"


@dataclass(frozen=True)
class PublicIntentGatewayPreview:
    ok: bool
    status: str
    contract_version: str
    business_id: str
    tenant_key: str
    source: str
    normalized_intent_preview: dict[str, Any]
    machine_cart_request_preview: dict[str, Any]
    human_friendly_quote_preview: dict[str, Any]
    safety: dict[str, Any]
    blocked_reasons: list[str]
    request_hash: str
    response_hash: str


def build_public_intent_gateway_preview(
    request: PublicIntentGatewayRequest | Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if request is None:
        req = PublicIntentGatewayRequest()
    elif isinstance(request, PublicIntentGatewayRequest):
        req = request
    else:
        req = PublicIntentGatewayRequest(**dict(request))

    request_payload = asdict(req)
    request_hash = _stable_hash(request_payload)

    normalized_intent_preview = {
        "intent_type": "public_website_service_enquiry",
        "business_id": req.business_id,
        "tenant_key": req.tenant_key,
        "source": req.source,
        "customer_name": req.customer_name,
        "customer_contact": req.customer_contact,
        "raw_message": req.message,
        "location": req.location,
        "requested_service": req.requested_service,
        "preferred_window": req.preferred_window,
        "normalization_status": "preview_only",
        "human_review_required": True,
        "normalized_intent_hash": _stable_hash(
            {
                "business_id": req.business_id,
                "source": req.source,
                "message": req.message,
                "location": req.location,
                "requested_service": req.requested_service,
            }
        ),
    }

    machine_cart_request_preview = {
        "status": "machine_cart_request_preview_only",
        "business_id": req.business_id,
        "service_key": req.requested_service,
        "location": req.location,
        "requested_window": req.preferred_window,
        "max_fiat_price": req.max_fiat_price,
        "currency": req.currency,
        "human_review_required": True,
        "would_create_quote": False,
        "would_create_booking": False,
        "would_create_live_job": False,
        "machine_cart_request_hash": _stable_hash(
            {
                "business_id": req.business_id,
                "service_key": req.requested_service,
                "location": req.location,
                "requested_window": req.preferred_window,
                "max_fiat_price": req.max_fiat_price,
                "currency": req.currency,
            }
        ),
    }

    human_friendly_quote_preview = {
        "status": "quote_preview_requires_human_review",
        "display_message": "Thanks — we have received your request. A human operator must review it before a live quote, booking, payment, or job is created.",
        "human_review_required": True,
        "final_quote_created": False,
        "live_job_created": False,
        "payment_created": False,
        "escrow_created": False,
    }

    safety = {
        "preview_only": True,
        "public_gateway_preview": True,
        "tenant_validation_required": True,
        "signed_request_validation_required": True,
        "rate_limiting_required": True,
        "abuse_protection_required": True,
        "human_review_required": True,
        "would_create_booking": False,
        "would_create_live_job": False,
        "would_execute_goal_engine": False,
        "would_move_money": False,
        "would_move_pho": False,
        "would_require_wallet": False,
        "would_create_payment": False,
        "would_create_escrow": False,
        "would_send_external_message": False,
    }

    blocked_reasons = [
        "preview_only",
        "tenant_validation_required",
        "signed_request_validation_required",
        "rate_limiting_required",
        "abuse_protection_required",
        "human_review_required",
        "no_live_job_creation",
        "no_booking_side_effect",
        "no_payment_side_effect",
        "no_escrow_side_effect",
        "no_external_message_side_effect",
    ]

    response_without_hash = {
        "ok": True,
        "status": "public_intent_gateway_preview_ready",
        "contract_version": PUBLIC_INTENT_GATEWAY_VERSION,
        "business_id": req.business_id,
        "tenant_key": req.tenant_key,
        "source": req.source,
        "normalized_intent_preview": normalized_intent_preview,
        "machine_cart_request_preview": machine_cart_request_preview,
        "human_friendly_quote_preview": human_friendly_quote_preview,
        "safety": safety,
        "blocked_reasons": blocked_reasons,
        "request_hash": request_hash,
    }

    response_hash = _stable_hash(response_without_hash)

    return {
        **response_without_hash,
        "response_hash": response_hash,
    }


def build_public_intent_gateway_summary(
    request: PublicIntentGatewayRequest | Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    preview = build_public_intent_gateway_preview(request)
    summary = {
        "ok": preview["ok"],
        "status": preview["status"],
        "contract_version": preview["contract_version"],
        "business_id": preview["business_id"],
        "tenant_key": preview["tenant_key"],
        "source": preview["source"],
        "has_normalized_intent_preview": bool(preview.get("normalized_intent_preview")),
        "has_machine_cart_request_preview": bool(preview.get("machine_cart_request_preview")),
        "has_human_friendly_quote_preview": bool(preview.get("human_friendly_quote_preview")),
        "human_review_required": preview["safety"]["human_review_required"],
        "preview_only": preview["safety"]["preview_only"],
        "would_create_booking": preview["safety"]["would_create_booking"],
        "would_create_live_job": preview["safety"]["would_create_live_job"],
        "would_create_payment": preview["safety"]["would_create_payment"],
        "would_create_escrow": preview["safety"]["would_create_escrow"],
        "would_send_external_message": preview["safety"]["would_send_external_message"],
        "response_hash": preview["response_hash"],
    }
    return {**summary, "summary_hash": _stable_hash(summary)}
