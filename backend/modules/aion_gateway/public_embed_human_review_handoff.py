"""
AION Public Embed Human Review Handoff Preview v0.

This module builds a deterministic preview-only human review handoff for public
website embed/widget requests after the guard envelope has blocked live execution.

It does not create bookings, create live jobs, execute the Goal Engine, send
external messages, create payments, create escrow, release funds, or expose a
public write route.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping


PUBLIC_EMBED_HUMAN_REVIEW_HANDOFF_VERSION = "aion.public_embed_human_review_handoff.v0.1"

SUPPORTED_REVIEW_DECISIONS = {
    "approve_preview_only",
    "reject_preview_only",
    "request_more_info_preview_only",
    "escalate_preview_only",
}


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _stable_hash(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def build_public_embed_human_review_handoff_preview(
    request: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Build a preview-only human review handoff for a public embed/widget request.

    The handoff converts a guarded public request into an internal review package.
    It is not an approval action and cannot create a live job.
    """

    request = dict(request or {})

    business_id = str(request.get("business_id") or "home_fixed")
    business_name = str(request.get("business_name") or "Home Fixed")
    vertical_key = str(request.get("vertical_key") or "home_repair")
    widget_source = str(request.get("widget_source") or "website_form_widget")
    request_id = str(request.get("request_id") or "public_embed_request_preview")
    customer_message = str(request.get("customer_message") or "")
    requested_outcome = str(request.get("requested_outcome") or "request_quote")
    service_key = str(request.get("service_key") or "unknown_service")
    location = str(request.get("location") or "unknown_location")
    currency = str(request.get("currency") or "EUR")

    guard_status = str(request.get("guard_status") or "guard_envelope_preview_ready")
    normalized_intent_hash = str(request.get("normalized_intent_hash") or "")
    machine_cart_request_hash = str(request.get("machine_cart_request_hash") or "")
    guard_hash = str(request.get("guard_hash") or "")

    review_package = {
        "review_id": f"review_{request_id}",
        "business_id": business_id,
        "business_name": business_name,
        "vertical_key": vertical_key,
        "widget_source": widget_source,
        "request_id": request_id,
        "customer_message": customer_message,
        "requested_outcome": requested_outcome,
        "service_key": service_key,
        "location": location,
        "currency": currency,
        "guard_status": guard_status,
        "normalized_intent_hash": normalized_intent_hash,
        "machine_cart_request_hash": machine_cart_request_hash,
        "guard_hash": guard_hash,
        "review_reason": "public_embed_request_requires_human_review",
        "review_queue": "aion_public_embed_human_review",
        "review_priority": "normal",
    }

    approval_boundary = {
        "human_review_required": True,
        "human_review_completed": False,
        "approval_decision_recorded": False,
        "supported_review_decisions": sorted(SUPPORTED_REVIEW_DECISIONS),
        "approval_can_create_live_job": False,
        "approval_can_execute_goal_engine": False,
        "approval_can_move_money": False,
        "approval_can_send_external_messages": False,
        "next_step": "future_guarded_approval_path",
    }

    safety = {
        "preview_only": True,
        "public_route_mounted": False,
        "unauthenticated_public_write_route_exposed": False,
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
    }

    blocked_reasons = [
        "preview_only",
        "human_review_not_completed",
        "approval_decision_not_recorded",
        "future_guarded_approval_path_required",
        "no_live_job_creation",
        "no_goal_engine_execution",
        "no_payment_or_escrow",
        "no_external_messages",
        "public_write_route_not_mounted",
    ]

    handoff = {
        "contract_version": PUBLIC_EMBED_HUMAN_REVIEW_HANDOFF_VERSION,
        "status": "waiting_human_review_preview_only",
        "preview_only": True,
        "business_id": business_id,
        "vertical_key": vertical_key,
        "request_id": request_id,
        "review_package": review_package,
        "approval_boundary": approval_boundary,
        "safety": safety,
        "blocked_reasons": blocked_reasons,
        "review_package_hash": _stable_hash(review_package),
        "approval_boundary_hash": _stable_hash(approval_boundary),
        "safety_hash": _stable_hash(safety),
    }

    handoff["response_hash"] = _stable_hash(handoff)
    return handoff


def build_public_embed_human_review_handoff_summary(
    request: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    handoff = build_public_embed_human_review_handoff_preview(request)

    summary = {
        "contract_version": PUBLIC_EMBED_HUMAN_REVIEW_HANDOFF_VERSION,
        "status": handoff["status"],
        "preview_only": True,
        "business_id": handoff["business_id"],
        "vertical_key": handoff["vertical_key"],
        "request_id": handoff["request_id"],
        "has_review_package": bool(handoff.get("review_package")),
        "has_approval_boundary": bool(handoff.get("approval_boundary")),
        "has_safety": bool(handoff.get("safety")),
        "human_review_required": True,
        "human_review_completed": False,
        "approval_decision_recorded": False,
        "public_route_mounted": False,
        "would_create_live_job": False,
        "would_execute_goal_engine": False,
        "would_move_money": False,
        "would_send_external_messages": False,
        "next_step": "future_guarded_approval_path",
        "response_hash": handoff["response_hash"],
    }

    summary["summary_hash"] = _stable_hash(summary)
    return summary


__all__ = [
    "PUBLIC_EMBED_HUMAN_REVIEW_HANDOFF_VERSION",
    "SUPPORTED_REVIEW_DECISIONS",
    "build_public_embed_human_review_handoff_preview",
    "build_public_embed_human_review_handoff_summary",
]
