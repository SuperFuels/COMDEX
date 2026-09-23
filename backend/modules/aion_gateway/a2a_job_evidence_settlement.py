from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any, Mapping

A2A_JOB_EVIDENCE_SETTLEMENT_VERSION = "aion.a2a_job_evidence_settlement.v0.1"

DEFAULT_BUSINESS_ID = "home_fixed"
DEFAULT_BUSINESS_NAME = "Home Fixed"
DEFAULT_VERTICAL_KEY = "home_repair"
DEFAULT_INDUSTRY_KEY = "trades"
DEFAULT_JOB_ID = "home_fixed_job_request_preview"


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
        "would_release_funds": False,
        "would_send_external_message": False,
        "live_status_polling_enabled": False,
    }


def build_a2a_job_evidence_preview(
    job: Mapping[str, Any] | None = None,
    *,
    business_id: str = DEFAULT_BUSINESS_ID,
    business_name: str = DEFAULT_BUSINESS_NAME,
    vertical_key: str = DEFAULT_VERTICAL_KEY,
    industry_key: str = DEFAULT_INDUSTRY_KEY,
    job_id: str = DEFAULT_JOB_ID,
) -> dict[str, Any]:
    source = dict(job or {})
    resolved_business_id = _safe_text(source.get("business_id"), business_id)
    resolved_job_id = _safe_text(source.get("job_id"), job_id)

    required_evidence = list(
        source.get("required_evidence")
        or source.get("evidence_requirements")
        or ["before_photo", "after_photo", "completion_note"]
    )

    submitted_evidence = list(source.get("submitted_evidence") or [])
    missing_evidence = [
        item for item in required_evidence
        if item not in submitted_evidence
    ]

    preview = {
        "ok": True,
        "status": "job_evidence_preview_ready",
        "contract_version": A2A_JOB_EVIDENCE_SETTLEMENT_VERSION,
        "endpoint_key": "job_evidence",
        "method": "GET",
        "path": f"/api/aion/a2a/{resolved_business_id}/job_evidence",
        "business_id": resolved_business_id,
        "business_name": _safe_text(source.get("business_name"), business_name),
        "vertical_key": _safe_text(source.get("vertical_key"), vertical_key),
        "industry_key": _safe_text(source.get("industry_key"), industry_key),
        "job_id": resolved_job_id,
        "evidence_status": "evidence_pending" if missing_evidence else "evidence_preview_complete",
        "required_evidence": required_evidence,
        "submitted_evidence": submitted_evidence,
        "missing_evidence": missing_evidence,
        "evidence_backed_completion": len(missing_evidence) == 0,
        "human_review_required": True,
        "evidence_review_status": "requires_human_review",
        "final_completion_confirmed": False,
        "proof_commit_ready": len(missing_evidence) == 0,
        "blocked_reasons": [
            "preview_only",
            "guarded_evidence",
            "auth_required",
            "public_route_not_exposed",
            "human_review_required",
            "no_live_completion_confirmation",
            "no_workflow_execution",
            "no_payment_side_effect",
            "no_external_message_side_effect",
        ],
        "safety": _safety(),
    }

    preview["evidence_hash"] = _stable_hash(preview)
    return preview


def build_a2a_settlement_readiness_preview(
    job: Mapping[str, Any] | None = None,
    evidence_preview: Mapping[str, Any] | None = None,
    *,
    business_id: str = DEFAULT_BUSINESS_ID,
    business_name: str = DEFAULT_BUSINESS_NAME,
    vertical_key: str = DEFAULT_VERTICAL_KEY,
    industry_key: str = DEFAULT_INDUSTRY_KEY,
    job_id: str = DEFAULT_JOB_ID,
) -> dict[str, Any]:
    source = dict(job or {})
    evidence = dict(evidence_preview or build_a2a_job_evidence_preview(
        source,
        business_id=business_id,
        business_name=business_name,
        vertical_key=vertical_key,
        industry_key=industry_key,
        job_id=job_id,
    ))

    resolved_business_id = _safe_text(source.get("business_id"), evidence.get("business_id", business_id))
    resolved_job_id = _safe_text(source.get("job_id"), evidence.get("job_id", job_id))
    evidence_complete = bool(evidence.get("evidence_backed_completion"))

    preview = {
        "ok": True,
        "status": "settlement_readiness_preview_ready",
        "contract_version": A2A_JOB_EVIDENCE_SETTLEMENT_VERSION,
        "endpoint_key": "settlement_readiness",
        "method": "GET",
        "path": f"/api/aion/a2a/{resolved_business_id}/settlement_readiness",
        "business_id": resolved_business_id,
        "business_name": _safe_text(source.get("business_name"), evidence.get("business_name", business_name)),
        "vertical_key": _safe_text(source.get("vertical_key"), evidence.get("vertical_key", vertical_key)),
        "industry_key": _safe_text(source.get("industry_key"), evidence.get("industry_key", industry_key)),
        "job_id": resolved_job_id,
        "currency": _safe_text(source.get("currency"), "EUR"),
        "quote_amount": source.get("quote_amount"),
        "evidence_status": evidence.get("evidence_status"),
        "evidence_hash": evidence.get("evidence_hash"),
        "evidence_backed_completion": evidence_complete,
        "settlement_status": "not_ready_human_review_required",
        "settlement_ready": False,
        "payment_ready": False,
        "escrow_ready": False,
        "fiat_first": True,
        "glyphchain_is_payment_rail": False,
        "proof_required_before_settlement": True,
        "human_review_required": True,
        "would_move_money": False,
        "would_create_payment": False,
        "would_create_escrow": False,
        "would_release_funds": False,
        "next_step": "future_guarded_approval_path",
        "blocked_reasons": [
            "preview_only",
            "guarded_settlement_readiness",
            "auth_required",
            "public_route_not_exposed",
            "human_review_required",
            "no_payment_movement",
            "no_payment_creation",
            "no_escrow_creation",
            "no_fund_release",
            "no_external_message_side_effect",
        ],
        "safety": _safety(),
    }

    preview["settlement_readiness_hash"] = _stable_hash(preview)
    return preview


def build_a2a_job_evidence_settlement_bundle(
    job: Mapping[str, Any] | None = None,
    *,
    business_id: str = DEFAULT_BUSINESS_ID,
    business_name: str = DEFAULT_BUSINESS_NAME,
    vertical_key: str = DEFAULT_VERTICAL_KEY,
    industry_key: str = DEFAULT_INDUSTRY_KEY,
    job_id: str = DEFAULT_JOB_ID,
) -> dict[str, Any]:
    source = dict(job or {})
    evidence = build_a2a_job_evidence_preview(
        source,
        business_id=business_id,
        business_name=business_name,
        vertical_key=vertical_key,
        industry_key=industry_key,
        job_id=job_id,
    )
    settlement = build_a2a_settlement_readiness_preview(
        source,
        evidence,
        business_id=business_id,
        business_name=business_name,
        vertical_key=vertical_key,
        industry_key=industry_key,
        job_id=job_id,
    )

    bundle = {
        "ok": evidence["ok"] and settlement["ok"],
        "status": "a2a_job_evidence_settlement_preview_ready",
        "contract_version": A2A_JOB_EVIDENCE_SETTLEMENT_VERSION,
        "business_id": evidence["business_id"],
        "business_name": evidence["business_name"],
        "vertical_key": evidence["vertical_key"],
        "industry_key": evidence["industry_key"],
        "job_id": evidence["job_id"],
        "job_evidence_preview": evidence,
        "settlement_readiness_preview": settlement,
        "safety": _safety(),
    }
    bundle["bundle_hash"] = _stable_hash(bundle)
    return bundle
