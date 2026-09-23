from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from typing import Any, Mapping


A2A_HANDSHAKE_PREVIEW_VERSION = "aion.a2a_handshake_preview.v0.1"

DEFAULT_BUSINESS_ID = "home_fixed"
DEFAULT_BUSINESS_NAME = "Home Fixed"
DEFAULT_VERTICAL_KEY = "home_repair"
DEFAULT_INDUSTRY_KEY = "trades"

ACCEPTED_PROTOCOLS = [
    "aion.a2a.preview.v0",
    "aion.machine_cart.preview.v0",
    "aion.quote_negotiation.preview.v0",
    "aion.live_status_polling.preview.v0",
    "aion.proof_receipt.preview.v0",
]

HANDSHAKE_REQUIRED_FIELDS = [
    "requesting_agent_id",
    "requesting_agent_name",
    "requested_protocol",
    "business_id",
    "intent_type",
]

QUOTE_NEGOTIATION_REQUIRED_FIELDS = [
    "business_id",
    "service_id",
    "requested_outcome",
    "target_price",
    "currency",
]

STATUS_POLLING_REQUIRED_FIELDS = [
    "business_id",
    "job_id",
    "requesting_agent_id",
]


def _stable_hash(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return sha256(encoded.encode("utf-8")).hexdigest()


def _safe_str(value: Any, fallback: str = "preview_unavailable") -> str:
    if value is None:
        return fallback
    text = str(value).strip()
    return text or fallback


def _missing_fields(source: Mapping[str, Any], required: list[str]) -> list[str]:
    return [key for key in required if not _safe_str(source.get(key), "")]


def _safety() -> dict[str, Any]:
    return {
        "preview_only": True,
        "guarded": True,
        "human_review_required": True,
        "autonomous_execution_allowed": False,
        "public_route_exposed": False,
        "would_execute_workflow": False,
        "would_create_booking": False,
        "would_create_live_job": False,
        "would_move_money": False,
        "would_move_pho": False,
        "would_require_wallet": False,
        "would_create_payment": False,
        "would_create_escrow": False,
        "would_release_funds": False,
        "would_send_external_message": False,
        "live_status_polling_enabled": False,
        "quote_negotiation_enabled": False,
        "real_a2a_handshake_enabled": False,
    }


@dataclass(frozen=True)
class A2AHandshakePreview:
    contract_version: str
    status: str
    business_id: str
    business_name: str
    vertical_key: str
    industry_key: str
    requesting_agent_id: str
    requesting_agent_name: str
    requested_protocol: str
    intent_type: str
    accepted_protocols: list[str]
    auth_mode: str
    requires_auth: bool
    agent_identity_validation_enabled: bool
    scoped_permissions_enabled: bool
    handshake_accepted: bool
    handshake_preview_only: bool
    route_hint: str
    missing_fields: list[str]
    blocked_reasons: list[str]
    safety: dict[str, Any]
    handshake_hash: str


def build_a2a_handshake_preview(request: Mapping[str, Any] | None = None) -> dict[str, Any]:
    source = dict(request or {})
    business_id = _safe_str(source.get("business_id"), DEFAULT_BUSINESS_ID)
    requested_protocol = _safe_str(source.get("requested_protocol"), "aion.a2a.preview.v0")
    missing = _missing_fields(source, HANDSHAKE_REQUIRED_FIELDS)

    payload = {
        "contract_version": A2A_HANDSHAKE_PREVIEW_VERSION,
        "status": "handshake_preview_only",
        "business_id": business_id,
        "business_name": _safe_str(source.get("business_name"), DEFAULT_BUSINESS_NAME),
        "vertical_key": _safe_str(source.get("vertical_key"), DEFAULT_VERTICAL_KEY),
        "industry_key": _safe_str(source.get("industry_key"), DEFAULT_INDUSTRY_KEY),
        "requesting_agent_id": _safe_str(source.get("requesting_agent_id")),
        "requesting_agent_name": _safe_str(source.get("requesting_agent_name")),
        "requested_protocol": requested_protocol,
        "intent_type": _safe_str(source.get("intent_type"), "service_request_preview"),
        "accepted_protocols": list(ACCEPTED_PROTOCOLS),
        "auth_mode": "api_key_or_signed_agent_preview",
        "requires_auth": True,
        "agent_identity_validation_enabled": False,
        "scoped_permissions_enabled": False,
        "handshake_accepted": False,
        "handshake_preview_only": True,
        "route_hint": "future_guarded_approval_path",
        "missing_fields": missing,
        "blocked_reasons": [
            "preview_only",
            "auth_required",
            "agent_identity_validation_not_enabled",
            "scoped_permissions_not_enabled",
            "public_route_not_exposed",
            "no_live_execution",
        ],
        "safety": _safety(),
    }
    payload["handshake_hash"] = _stable_hash(payload)
    return asdict(A2AHandshakePreview(**payload))


def build_a2a_quote_negotiation_preview(request: Mapping[str, Any] | None = None) -> dict[str, Any]:
    source = dict(request or {})
    missing = _missing_fields(source, QUOTE_NEGOTIATION_REQUIRED_FIELDS)

    payload = {
        "contract_version": A2A_HANDSHAKE_PREVIEW_VERSION,
        "status": "quote_negotiation_preview_only",
        "business_id": _safe_str(source.get("business_id"), DEFAULT_BUSINESS_ID),
        "business_name": _safe_str(source.get("business_name"), DEFAULT_BUSINESS_NAME),
        "vertical_key": _safe_str(source.get("vertical_key"), DEFAULT_VERTICAL_KEY),
        "industry_key": _safe_str(source.get("industry_key"), DEFAULT_INDUSTRY_KEY),
        "service_id": _safe_str(source.get("service_id"), "service_preview_unavailable"),
        "requested_outcome": _safe_str(source.get("requested_outcome")),
        "target_price": source.get("target_price"),
        "currency": _safe_str(source.get("currency"), "EUR"),
        "counter_offer_enabled": False,
        "quote_negotiation_enabled": False,
        "final_quote_created": False,
        "pricing_mode": "requires_human_review",
        "human_review_required": True,
        "route_hint": "future_guarded_approval_path",
        "missing_fields": missing,
        "blocked_reasons": [
            "preview_only",
            "quote_negotiation_not_enabled",
            "human_review_required",
            "no_final_quote_created",
            "no_booking_side_effect",
            "no_payment_side_effect",
        ],
        "safety": _safety(),
    }
    payload["quote_negotiation_hash"] = _stable_hash(payload)
    return payload


def build_a2a_live_status_polling_preview(request: Mapping[str, Any] | None = None) -> dict[str, Any]:
    source = dict(request or {})
    missing = _missing_fields(source, STATUS_POLLING_REQUIRED_FIELDS)

    payload = {
        "contract_version": A2A_HANDSHAKE_PREVIEW_VERSION,
        "status": "live_status_polling_preview_only",
        "business_id": _safe_str(source.get("business_id"), DEFAULT_BUSINESS_ID),
        "business_name": _safe_str(source.get("business_name"), DEFAULT_BUSINESS_NAME),
        "vertical_key": _safe_str(source.get("vertical_key"), DEFAULT_VERTICAL_KEY),
        "industry_key": _safe_str(source.get("industry_key"), DEFAULT_INDUSTRY_KEY),
        "job_id": _safe_str(source.get("job_id"), "job_preview_unavailable"),
        "requesting_agent_id": _safe_str(source.get("requesting_agent_id")),
        "current_stage": "waiting_human_review",
        "live_status_polling_enabled": False,
        "polling_interval_seconds": None,
        "public_status_stream_enabled": False,
        "human_review_required": True,
        "route_hint": "future_guarded_approval_path",
        "missing_fields": missing,
        "blocked_reasons": [
            "preview_only",
            "live_status_polling_not_enabled",
            "public_status_stream_not_enabled",
            "human_review_required",
            "no_live_job_created",
        ],
        "safety": _safety(),
    }
    payload["status_polling_hash"] = _stable_hash(payload)
    return payload


def build_a2a_handshake_preview_bundle(request: Mapping[str, Any] | None = None) -> dict[str, Any]:
    source = dict(request or {})
    handshake = build_a2a_handshake_preview(source)
    quote_negotiation = build_a2a_quote_negotiation_preview(source)
    live_status_polling = build_a2a_live_status_polling_preview(source)

    bundle = {
        "ok": True,
        "status": "a2a_handshake_preview_bundle_ready",
        "contract_version": A2A_HANDSHAKE_PREVIEW_VERSION,
        "business_id": handshake["business_id"],
        "business_name": handshake["business_name"],
        "vertical_key": handshake["vertical_key"],
        "industry_key": handshake["industry_key"],
        "preview_only": True,
        "guarded": True,
        "human_review_required": True,
        "real_a2a_handshake_enabled": False,
        "quote_negotiation_enabled": False,
        "live_status_polling_enabled": False,
        "handshake": handshake,
        "quote_negotiation": quote_negotiation,
        "live_status_polling": live_status_polling,
        "safety": _safety(),
        "blocked_reasons": [
            "preview_only",
            "auth_required",
            "public_route_not_exposed",
            "real_a2a_handshake_not_enabled",
            "quote_negotiation_not_enabled",
            "live_status_polling_not_enabled",
            "no_live_execution",
            "no_job_side_effect",
            "no_payment_side_effect",
        ],
    }
    bundle["bundle_hash"] = _stable_hash(bundle)
    return bundle


def build_a2a_handshake_preview_summary(request: Mapping[str, Any] | None = None) -> dict[str, Any]:
    bundle = build_a2a_handshake_preview_bundle(request)
    summary = {
        "ok": True,
        "status": "a2a_handshake_preview_summary_ready",
        "contract_version": A2A_HANDSHAKE_PREVIEW_VERSION,
        "business_id": bundle["business_id"],
        "vertical_key": bundle["vertical_key"],
        "has_handshake_preview": bool(bundle.get("handshake")),
        "has_quote_negotiation_preview": bool(bundle.get("quote_negotiation")),
        "has_live_status_polling_preview": bool(bundle.get("live_status_polling")),
        "real_a2a_handshake_enabled": False,
        "quote_negotiation_enabled": False,
        "live_status_polling_enabled": False,
        "human_review_required": True,
        "preview_only": True,
        "guarded": True,
        "bundle_hash": bundle["bundle_hash"],
    }
    summary["summary_hash"] = _stable_hash(summary)
    return summary
