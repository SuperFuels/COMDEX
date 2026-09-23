
"""

AION Public Embed Widget Guard Envelope v0.

This module builds a deterministic preview-only guard envelope for public

website embed/widget requests before any public write route is mounted.

It does not validate live tenant keys, verify live signatures, rate-limit real

traffic, create bookings, create jobs, execute the Goal Engine, send messages,

or move money.

"""

from __future__ import annotations

import hashlib

import json

from copy import deepcopy

from typing import Any, Mapping

PUBLIC_EMBED_GUARD_ENVELOPE_VERSION = "aion.public_embed_guard_envelope.v0.1"

SUPPORTED_WIDGET_SOURCES = {

    "website_form_widget",

    "website_button_widget",

    "embedded_chat_widget",

}

def _canonical(value: Any) -> str:

    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)

def _stable_hash(value: Any) -> str:

    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()

def _bool(value: Any, default: bool = False) -> bool:

    if isinstance(value, bool):

        return value

    return default

def build_public_embed_guard_envelope_preview(

    request: Mapping[str, Any] | None = None,

) -> dict[str, Any]:

    """

    Build a preview-only guard envelope for a public embed/widget request.

    The preview records whether the request shape would require tenant key

    validation, signed request validation, rate limiting, abuse protection, and

    human review before any live job creation path could exist.

    """

    request = dict(request or {})

    widget_source = str(request.get("widget_source") or "website_form_widget")

    business_id = str(request.get("business_id") or "home_fixed")

    vertical_key = str(request.get("vertical_key") or "home_repair")

    tenant_key_present = bool(request.get("tenant_key"))

    signature_present = bool(request.get("signature"))

    request_id = str(request.get("request_id") or "public_embed_request_preview")

    customer_message = str(request.get("customer_message") or "")

    requested_outcome = str(request.get("requested_outcome") or "request_quote")

    unsupported_widget_source = widget_source not in SUPPORTED_WIDGET_SOURCES

    guards = {

        "tenant_business_key_validation_required": True,

        "tenant_business_key_present": tenant_key_present,

        "tenant_business_key_validated": False,

        "signed_request_validation_required": True,

        "signature_present": signature_present,

        "signed_request_validated": False,

        "rate_limiting_required": True,

        "rate_limiting_enforced": False,

        "abuse_protection_required": True,

        "abuse_protection_enforced": False,

        "human_review_required": True,

        "human_review_completed": False,

        "agent_identity_validation_enabled": False,

        "scoped_permissions_enabled": False,

    }

    blocked_reasons = [

        "preview_only",

        "tenant_business_key_validation_not_live",

        "signed_request_validation_not_live",

        "rate_limiting_not_live",

        "abuse_protection_not_live",

        "human_review_required",

        "public_write_route_not_mounted",

        "no_live_job_creation",

    ]

    if unsupported_widget_source:

        blocked_reasons.append("unsupported_widget_source")

    request_preview = {

        "request_id": request_id,

        "business_id": business_id,

        "vertical_key": vertical_key,

        "widget_source": widget_source,

        "customer_message": customer_message,

        "requested_outcome": requested_outcome,

        "preview_only": True,

    }

    safety = {

        "preview_only": True,

        "human_review_required": True,

        "would_create_booking": False,

        "would_create_live_job": False,

        "would_execute_goal_engine": False,

        "would_move_money": False,

        "would_move_pho": False,

        "would_require_wallet": False,

        "would_create_payment": False,

        "would_create_escrow": False,

        "would_release_funds": False,

        "would_send_external_messages": False,

        "unauthenticated_public_write_route_exposed": False,

        "public_route_mounted": False,

    }

    envelope = {

        "contract_version": PUBLIC_EMBED_GUARD_ENVELOPE_VERSION,

        "status": (

            "blocked_unsupported_widget_source"

            if unsupported_widget_source

            else "guard_envelope_preview_ready"

        ),

        "preview_only": True,

        "business_id": business_id,

        "vertical_key": vertical_key,

        "widget_source": widget_source,

        "request_preview": request_preview,

        "guards": guards,

        "blocked_reasons": blocked_reasons,

        "safety": safety,

        "request_hash": _stable_hash(request_preview),

        "guard_hash": _stable_hash(guards),

        "safety_hash": _stable_hash(safety),

    }

    envelope["response_hash"] = _stable_hash(envelope)

    return envelope

def build_public_embed_guard_envelope_summary(

    request: Mapping[str, Any] | None = None,

) -> dict[str, Any]:

    envelope = build_public_embed_guard_envelope_preview(request)

    summary = {

        "contract_version": PUBLIC_EMBED_GUARD_ENVELOPE_VERSION,

        "status": envelope["status"],

        "preview_only": True,

        "business_id": envelope["business_id"],

        "vertical_key": envelope["vertical_key"],

        "widget_source": envelope["widget_source"],

        "has_request_preview": bool(envelope.get("request_preview")),

        "has_guards": bool(envelope.get("guards")),

        "has_safety": bool(envelope.get("safety")),

        "tenant_business_key_validation_required": True,

        "signed_request_validation_required": True,

        "rate_limiting_required": True,

        "abuse_protection_required": True,

        "human_review_required": True,

        "public_route_mounted": False,

        "unauthenticated_public_write_route_exposed": False,

        "would_create_live_job": False,

        "would_execute_goal_engine": False,

        "would_move_money": False,

        "response_hash": envelope["response_hash"],

    }

    summary["summary_hash"] = _stable_hash(summary)

    return summary

__all__ = [

    "PUBLIC_EMBED_GUARD_ENVELOPE_VERSION",

    "SUPPORTED_WIDGET_SOURCES",

    "build_public_embed_guard_envelope_preview",

    "build_public_embed_guard_envelope_summary",

]

