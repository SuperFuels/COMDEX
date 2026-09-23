from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any, Mapping

A2A_JOB_TRACE_VERSION = "aion.a2a_job_trace.v0.1"

DEFAULT_BUSINESS_ID = "home_fixed"
DEFAULT_BUSINESS_NAME = "Home Fixed"
DEFAULT_VERTICAL_KEY = "home_repair"
DEFAULT_INDUSTRY_KEY = "trades"

_REQUIRED_JOB_REQUEST_FIELDS = (
    "business_id",
    "vertical_key",
    "requested_outcome",
)


def _stable_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _stable_hash(value: Any) -> str:
    return hashlib.sha256(_stable_json(value).encode("utf-8")).hexdigest()


def _safe_text(value: Any, fallback: str = "") -> str:
    if value is None:
        return fallback
    return str(value)


def _safety() -> dict[str, Any]:
    return {
        "guarded": True,
        "preview_only": True,
        "public_route_exposed": False,
        "requires_auth": True,
        "auth_mode": "api_key_or_signed_agent_preview",
        "schema_versioned": True,
        "deterministic_response": True,
        "human_review_required": True,
        "would_execute_workflow": False,
        "would_create_booking": False,
        "would_create_live_job": False,
        "would_move_money": False,
        "would_move_pho": False,
        "would_require_wallet": False,
        "would_create_payment": False,
        "would_create_escrow": False,
        "would_send_external_message": False,
        "live_status_polling_enabled": False,
    }


def validate_a2a_job_request_preview(request: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = dict(request or {})
    missing = [field for field in _REQUIRED_JOB_REQUEST_FIELDS if not payload.get(field)]

    result = {
        "ok": not missing,
        "status": "valid" if not missing else "blocked_missing_required_fields",
        "contract_version": A2A_JOB_TRACE_VERSION,
        "required_fields": list(_REQUIRED_JOB_REQUEST_FIELDS),
        "missing_fields": missing,
        "request_preview": deepcopy(payload),
        "safety": _safety(),
    }
    result["validation_hash"] = _stable_hash(result)
    return result


def build_a2a_job_request_preview(
    request: Mapping[str, Any] | None = None,
    *,
    business_id: str = DEFAULT_BUSINESS_ID,
    business_name: str = DEFAULT_BUSINESS_NAME,
    vertical_key: str = DEFAULT_VERTICAL_KEY,
    industry_key: str = DEFAULT_INDUSTRY_KEY,
) -> dict[str, Any]:
    incoming = dict(request or {})
    request_payload = {
        "business_id": _safe_text(incoming.get("business_id"), business_id),
        "business_name": _safe_text(incoming.get("business_name"), business_name),
        "vertical_key": _safe_text(incoming.get("vertical_key"), vertical_key),
        "industry_key": _safe_text(incoming.get("industry_key"), industry_key),
        "requested_outcome": _safe_text(incoming.get("requested_outcome"), "repair request preview"),
        "source_channel": _safe_text(incoming.get("source_channel"), "a2a_preview"),
        "customer_location": _safe_text(incoming.get("customer_location"), "preview_location"),
        "preferred_time_window": _safe_text(incoming.get("preferred_time_window"), "requires_human_review"),
        "budget_hint": incoming.get("budget_hint"),
        "evidence_requirements": list(incoming.get("evidence_requirements") or []),
        "risk_flags": list(incoming.get("risk_flags") or []),
    }

    validation = validate_a2a_job_request_preview(request_payload)
    blocked_reasons = [
        "preview_only",
        "guarded_job_request",
        "auth_required",
        "public_route_not_exposed",
        "human_review_required",
        "no_live_job_creation",
        "no_workflow_execution",
        "no_booking_side_effect",
        "no_payment_side_effect",
        "no_escrow_side_effect",
        "no_external_message_side_effect",
    ]

    preview = {
        "ok": validation["ok"],
        "status": "job_request_preview_ready" if validation["ok"] else "job_request_preview_blocked",
        "contract_version": A2A_JOB_TRACE_VERSION,
        "endpoint_key": "job_request_preview",
        "method": "POST",
        "path": f"/api/aion/a2a/{request_payload['business_id']}/job_request_preview",
        "business_id": request_payload["business_id"],
        "business_name": request_payload["business_name"],
        "vertical_key": request_payload["vertical_key"],
        "industry_key": request_payload["industry_key"],
        "job_id": f"{request_payload['business_id']}_job_request_preview",
        "requested_outcome": request_payload["requested_outcome"],
        "source_channel": request_payload["source_channel"],
        "customer_location": request_payload["customer_location"],
        "preferred_time_window": request_payload["preferred_time_window"],
        "budget_hint": request_payload["budget_hint"],
        "evidence_requirements": request_payload["evidence_requirements"],
        "risk_flags": request_payload["risk_flags"],
        "validation": validation,
        "final_job_created": False,
        "workflow_run_created": False,
        "booking_created": False,
        "human_review_required": True,
        "next_step": "future_guarded_approval_path",
        "safety": _safety(),
        "blocked_reasons": blocked_reasons,
    }
    preview["job_request_hash"] = _stable_hash(preview)
    return preview


def build_a2a_job_trace_preview(
    job_request_preview: Mapping[str, Any] | None = None,
    *,
    business_id: str = DEFAULT_BUSINESS_ID,
    business_name: str = DEFAULT_BUSINESS_NAME,
    vertical_key: str = DEFAULT_VERTICAL_KEY,
    industry_key: str = DEFAULT_INDUSTRY_KEY,
) -> dict[str, Any]:
    request_preview = dict(job_request_preview or build_a2a_job_request_preview(
        {
            "business_id": business_id,
            "business_name": business_name,
            "vertical_key": vertical_key,
            "industry_key": industry_key,
            "requested_outcome": "repair request preview",
        }
    ))

    job_id = _safe_text(request_preview.get("job_id"), f"{business_id}_job_request_preview")
    trace_events = [
        {
            "event_key": "a2a_job_request_received",
            "stage": "request_received",
            "status": "preview_only",
            "human_review_required": True,
            "would_execute_workflow": False,
        },
        {
            "event_key": "a2a_job_request_normalized",
            "stage": "normalized",
            "status": "preview_only",
            "human_review_required": True,
            "would_create_live_job": False,
        },
        {
            "event_key": "a2a_job_request_waiting_human_review",
            "stage": "waiting_human_review",
            "status": "blocked_until_guarded_approval",
            "human_review_required": True,
            "would_create_booking": False,
        },
    ]

    trace = {
        "ok": True,
        "status": "job_trace_preview_ready",
        "contract_version": A2A_JOB_TRACE_VERSION,
        "endpoint_key": "job_trace",
        "method": "GET",
        "path": f"/api/aion/a2a/{request_preview.get('business_id', business_id)}/job_trace",
        "business_id": request_preview.get("business_id", business_id),
        "business_name": request_preview.get("business_name", business_name),
        "vertical_key": request_preview.get("vertical_key", vertical_key),
        "industry_key": request_preview.get("industry_key", industry_key),
        "job_id": job_id,
        "current_stage": "waiting_human_review",
        "live_status_polling_enabled": False,
        "human_review_required": True,
        "trace_events": trace_events,
        "blocked_reasons": [
            "preview_only",
            "guarded_trace",
            "auth_required",
            "public_route_not_exposed",
            "no_live_status_polling",
            "no_workflow_execution",
            "no_booking_side_effect",
            "no_payment_side_effect",
        ],
        "safety": _safety(),
    }
    trace["trace_hash"] = _stable_hash(trace)
    return trace


def build_a2a_job_request_trace_bundle(
    request: Mapping[str, Any] | None = None,
    *,
    business_id: str = DEFAULT_BUSINESS_ID,
    business_name: str = DEFAULT_BUSINESS_NAME,
    vertical_key: str = DEFAULT_VERTICAL_KEY,
    industry_key: str = DEFAULT_INDUSTRY_KEY,
) -> dict[str, Any]:
    job_request = build_a2a_job_request_preview(
        request,
        business_id=business_id,
        business_name=business_name,
        vertical_key=vertical_key,
        industry_key=industry_key,
    )
    job_trace = build_a2a_job_trace_preview(
        job_request,
        business_id=business_id,
        business_name=business_name,
        vertical_key=vertical_key,
        industry_key=industry_key,
    )

    bundle = {
        "ok": job_request["ok"] and job_trace["ok"],
        "status": "a2a_job_request_trace_preview_ready",
        "contract_version": A2A_JOB_TRACE_VERSION,
        "business_id": job_request["business_id"],
        "business_name": job_request["business_name"],
        "vertical_key": job_request["vertical_key"],
        "industry_key": job_request["industry_key"],
        "job_request_preview": job_request,
        "job_trace_preview": job_trace,
        "safety": _safety(),
    }
    bundle["bundle_hash"] = _stable_hash(bundle)
    return bundle
