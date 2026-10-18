from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any, Dict, Mapping, Optional

A2A_TRUST_SUMMARY_CONTRACT_VERSION = "aion.a2a_trust_summary_endpoint.v0.1"

DEFAULT_BUSINESS_ID = "home_fixed"
DEFAULT_BUSINESS_NAME = "Home Fixed"
DEFAULT_VERTICAL_KEY = "home_repair"
DEFAULT_INDUSTRY_KEY = "trades"

SAFETY_FLAGS: Dict[str, Any] = {
    "preview_only": True,
    "guarded": True,
    "requires_auth": True,
    "auth_mode": "api_key_or_signed_agent_preview",
    "public_route_exposed": False,
    "public_ranking_exposed": False,
    "no_public_ranking": True,
    "human_review_required": True,
    "would_execute_workflow": False,
    "would_create_booking": False,
    "would_create_live_job": False,
    "would_confirm_final_completion": False,
    "would_move_money": False,
    "would_move_pho": False,
    "would_require_wallet": False,
    "would_create_payment": False,
    "would_create_escrow": False,
    "would_release_funds": False,
    "would_send_external_message": False,
    "live_status_polling_enabled": False,
}

DEFAULT_TRUST_SUMMARY: Dict[str, Any] = {
    "business_id": DEFAULT_BUSINESS_ID,
    "business_name": DEFAULT_BUSINESS_NAME,
    "vertical_key": DEFAULT_VERTICAL_KEY,
    "industry_key": DEFAULT_INDUSTRY_KEY,
    "verified_completed_jobs": 0,
    "disputed_jobs": 0,
    "cancelled_jobs": 0,
    "failed_jobs": 0,
    "average_response_time_minutes": 0,
    "average_completion_time_minutes": 0,
    "evidence_backed_completion_rate": 0.0,
    "proof_commitment_rate": 0.0,
    "proof_verification_success_rate": 0.0,
    "quote_reliability_rate": 0.0,
    "recovery_success_rate": 0.0,
    "trust_score_preview": 0.0,
    "trust_tier_preview": "unrated_preview",
    "explainability_notes": [
        "Trust summary is preview-only.",
        "No public ranking is exposed.",
        "Human review remains required.",
    ],
    "human_review_required": True,
    "no_public_ranking": True,
}


def _stable_hash(value: Mapping[str, Any]) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _clamp_rate(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, number))


def _normalise_summary(summary: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    merged = deepcopy(DEFAULT_TRUST_SUMMARY)
    if summary:
        merged.update(dict(summary))

    merged["business_id"] = str(merged.get("business_id") or DEFAULT_BUSINESS_ID)
    merged["business_name"] = str(merged.get("business_name") or DEFAULT_BUSINESS_NAME)
    merged["vertical_key"] = str(merged.get("vertical_key") or DEFAULT_VERTICAL_KEY)
    merged["industry_key"] = str(merged.get("industry_key") or DEFAULT_INDUSTRY_KEY)

    for key in [
        "verified_completed_jobs",
        "disputed_jobs",
        "cancelled_jobs",
        "failed_jobs",
        "average_response_time_minutes",
        "average_completion_time_minutes",
    ]:
        try:
            merged[key] = max(0, int(merged.get(key) or 0))
        except (TypeError, ValueError):
            merged[key] = 0

    for key in [
        "evidence_backed_completion_rate",
        "proof_commitment_rate",
        "proof_verification_success_rate",
        "quote_reliability_rate",
        "recovery_success_rate",
        "trust_score_preview",
    ]:
        merged[key] = _clamp_rate(merged.get(key))

    notes = merged.get("explainability_notes")
    if not isinstance(notes, list):
        notes = [str(notes)] if notes else []
    merged["explainability_notes"] = [str(item) for item in notes]
    if "No public ranking is exposed." not in merged["explainability_notes"]:
        merged["explainability_notes"].append("No public ranking is exposed.")
    if "Human review remains required." not in merged["explainability_notes"]:
        merged["explainability_notes"].append("Human review remains required.")

    merged["human_review_required"] = True
    merged["no_public_ranking"] = True
    merged["public_ranking_exposed"] = False

    hash_source = {k: v for k, v in merged.items() if k != "trust_summary_hash"}
    merged["trust_summary_hash"] = _stable_hash(hash_source)
    return merged


def build_a2a_trust_summary_endpoint_preview(
    trust_summary: Optional[Mapping[str, Any]] = None,
    *,
    business_id: str = DEFAULT_BUSINESS_ID,
    business_name: str = DEFAULT_BUSINESS_NAME,
    vertical_key: str = DEFAULT_VERTICAL_KEY,
    industry_key: str = DEFAULT_INDUSTRY_KEY,
) -> Dict[str, Any]:
    """Build a guarded, deterministic A2A trust summary endpoint preview.

    This is not a public endpoint and does not expose public ranking.
    """
    seed = {
        "business_id": business_id,
        "business_name": business_name,
        "vertical_key": vertical_key,
        "industry_key": industry_key,
    }

    if trust_summary:
        seed.update(dict(trust_summary))

    summary = _normalise_summary(seed)

    payload: Dict[str, Any] = {
        "ok": True,
        "status": "trust_summary_preview_ready",
        "contract_version": A2A_TRUST_SUMMARY_CONTRACT_VERSION,
        "endpoint_key": "trust_summary",
        "method": "GET",
        "path": f"/api/aion/a2a/{summary['business_id']}/trust_summary",
        "schema_versioned": True,
        "deterministic_response": True,
        "preview_only": True,
        "guarded": True,
        "requires_auth": True,
        "auth_mode": "api_key_or_signed_agent_preview",
        "public_route_exposed": False,
        "public_ranking_exposed": False,
        "no_public_ranking": True,
        "business_id": summary["business_id"],
        "business_name": summary["business_name"],
        "vertical_key": summary["vertical_key"],
        "industry_key": summary["industry_key"],
        "trust_summary": summary,
        "safety": deepcopy(SAFETY_FLAGS),
        "blocked_reasons": [
            "preview_only",
            "guarded_endpoint",
            "auth_required",
            "public_route_not_exposed",
            "public_ranking_not_exposed",
            "no_live_execution",
            "no_booking_side_effect",
            "no_payment_side_effect",
            "no_escrow_side_effect",
            "no_external_message_side_effect",
        ],
    }

    payload["response_hash"] = _stable_hash(payload)
    payload["bundle_hash"] = _stable_hash(
        {
            "contract_version": payload["contract_version"],
            "endpoint_key": payload["endpoint_key"],
            "business_id": payload["business_id"],
            "vertical_key": payload["vertical_key"],
            "trust_summary_hash": summary["trust_summary_hash"],
            "response_hash": payload["response_hash"],
        }
    )
    return payload


def build_a2a_trust_summary_endpoint_summary(
    trust_summary: Optional[Mapping[str, Any]] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    preview = build_a2a_trust_summary_endpoint_preview(trust_summary, **kwargs)
    summary = preview["trust_summary"]

    result = {
        "ok": True,
        "status": preview["status"],
        "contract_version": preview["contract_version"],
        "endpoint_key": preview["endpoint_key"],
        "business_id": preview["business_id"],
        "vertical_key": preview["vertical_key"],
        "verified_completed_jobs": summary["verified_completed_jobs"],
        "trust_score_preview": summary["trust_score_preview"],
        "trust_tier_preview": summary["trust_tier_preview"],
        "trust_summary_hash": summary["trust_summary_hash"],
        "response_hash": preview["response_hash"],
        "bundle_hash": preview["bundle_hash"],
        "preview_only": True,
        "requires_auth": True,
        "public_route_exposed": False,
        "public_ranking_exposed": False,
        "no_public_ranking": True,
        "human_review_required": True,
    }

    result["summary_hash"] = _stable_hash(result)
    return result
