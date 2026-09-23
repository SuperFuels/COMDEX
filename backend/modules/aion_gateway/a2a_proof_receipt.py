"""AION guarded A2A proof commitment and proof receipt preview contracts.

Phase 11F is preview-only. It exposes deterministic internal objects for the
future A2A proof commitment and proof receipt endpoints without exposing public
routes, moving funds, executing workflows, or treating GlyphChain as a payment
rail.
"""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any


A2A_PROOF_RECEIPT_VERSION = "aion.a2a_proof_receipt.preview.v0.1"


def _stable_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _stable_hash(value: Any) -> str:
    return hashlib.sha256(_stable_json(value).encode("utf-8")).hexdigest()


def _default_business_context() -> dict[str, Any]:
    return {
        "business_id": "home_fixed",
        "business_name": "Home Fixed",
        "vertical_key": "home_repair",
        "industry_key": "trades",
    }


def _default_safety() -> dict[str, Any]:
    return {
        "guarded": True,
        "preview_only": True,
        "visibility_only": True,
        "public_route_exposed": False,
        "human_review_required": True,
        "autonomous_execution_allowed": False,
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
        "glyphchain_is_payment_rail": False,
        "proof_only_not_payment": True,
    }


def build_a2a_proof_commitment_preview(
    *,
    business_id: str = "home_fixed",
    business_name: str = "Home Fixed",
    vertical_key: str = "home_repair",
    industry_key: str = "trades",
    job_id: str = "home_fixed_job_preview",
    evidence_hash: str = "preview_evidence_hash_unavailable",
    settlement_readiness_hash: str = "preview_settlement_readiness_hash_unavailable",
    proof_subject: str = "job_evidence_and_settlement_readiness",
) -> dict[str, Any]:
    """Build a deterministic guarded proof commitment preview."""

    context = {
        **_default_business_context(),
        "business_id": business_id,
        "business_name": business_name,
        "vertical_key": vertical_key,
        "industry_key": industry_key,
    }

    commitment = {
        "ok": True,
        "status": "proof_commitment_preview_only",
        "contract_version": A2A_PROOF_RECEIPT_VERSION,
        "endpoint_key": "proof_commitment",
        "method": "GET",
        "schema_version": A2A_PROOF_RECEIPT_VERSION,
        **context,
        "job_id": job_id,
        "proof_subject": proof_subject,
        "evidence_hash": evidence_hash,
        "settlement_readiness_hash": settlement_readiness_hash,
        "proof_commitment_created": False,
        "proof_commitment_status": "preview_not_committed",
        "glyphchain_commit_enabled": False,
        "glyphchain_commit_executed": False,
        "glyphchain_is_payment_rail": False,
        "proof_only_not_payment": True,
        "human_review_required": True,
        "next_step": "future_guarded_approval_path",
        "blocked_reasons": [
            "preview_only",
            "public_route_not_exposed",
            "human_review_required",
            "glyphchain_commit_not_executed",
            "no_payment_side_effect",
            "no_escrow_side_effect",
            "no_fund_release_side_effect",
        ],
        "safety": _default_safety(),
    }

    commitment["proof_commitment_hash"] = _stable_hash(
        {k: v for k, v in commitment.items() if k != "proof_commitment_hash"}
    )
    return commitment


def build_a2a_proof_receipt_preview(
    *,
    business_id: str = "home_fixed",
    business_name: str = "Home Fixed",
    vertical_key: str = "home_repair",
    industry_key: str = "trades",
    job_id: str = "home_fixed_job_preview",
    proof_commitment_hash: str = "preview_proof_commitment_hash_unavailable",
) -> dict[str, Any]:
    """Build a deterministic guarded proof receipt preview."""

    context = {
        **_default_business_context(),
        "business_id": business_id,
        "business_name": business_name,
        "vertical_key": vertical_key,
        "industry_key": industry_key,
    }

    receipt = {
        "ok": True,
        "status": "proof_receipt_preview_only",
        "contract_version": A2A_PROOF_RECEIPT_VERSION,
        "endpoint_key": "proof_receipt",
        "method": "GET",
        "schema_version": A2A_PROOF_RECEIPT_VERSION,
        **context,
        "job_id": job_id,
        "proof_commitment_hash": proof_commitment_hash,
        "proof_receipt_created": False,
        "proof_receipt_status": "preview_not_issued",
        "proof_verified": False,
        "verification_status": "not_verified_preview_only",
        "glyphchain_receipt_lookup_enabled": False,
        "glyphchain_receipt_lookup_executed": False,
        "glyphchain_is_payment_rail": False,
        "proof_only_not_payment": True,
        "human_review_required": True,
        "next_step": "future_guarded_approval_path",
        "blocked_reasons": [
            "preview_only",
            "public_route_not_exposed",
            "human_review_required",
            "proof_receipt_not_issued",
            "proof_verification_not_executed",
            "no_payment_side_effect",
            "no_escrow_side_effect",
            "no_fund_release_side_effect",
        ],
        "safety": _default_safety(),
    }

    receipt["proof_receipt_hash"] = _stable_hash(
        {k: v for k, v in receipt.items() if k != "proof_receipt_hash"}
    )
    return receipt


def build_a2a_proof_bundle_preview(
    *,
    business_id: str = "home_fixed",
    business_name: str = "Home Fixed",
    vertical_key: str = "home_repair",
    industry_key: str = "trades",
    job_id: str = "home_fixed_job_preview",
    evidence_hash: str = "preview_evidence_hash_unavailable",
    settlement_readiness_hash: str = "preview_settlement_readiness_hash_unavailable",
) -> dict[str, Any]:
    """Build the combined proof commitment and receipt preview bundle."""

    commitment = build_a2a_proof_commitment_preview(
        business_id=business_id,
        business_name=business_name,
        vertical_key=vertical_key,
        industry_key=industry_key,
        job_id=job_id,
        evidence_hash=evidence_hash,
        settlement_readiness_hash=settlement_readiness_hash,
    )

    receipt = build_a2a_proof_receipt_preview(
        business_id=business_id,
        business_name=business_name,
        vertical_key=vertical_key,
        industry_key=industry_key,
        job_id=job_id,
        proof_commitment_hash=commitment["proof_commitment_hash"],
    )

    bundle = {
        "ok": True,
        "status": "proof_bundle_preview_only",
        "contract_version": A2A_PROOF_RECEIPT_VERSION,
        "business_id": business_id,
        "business_name": business_name,
        "vertical_key": vertical_key,
        "industry_key": industry_key,
        "job_id": job_id,
        "guarded": True,
        "preview_only": True,
        "public_route_exposed": False,
        "human_review_required": True,
        "glyphchain_is_payment_rail": False,
        "proof_only_not_payment": True,
        "proof_commitment": commitment,
        "proof_receipt": receipt,
        "safety": _default_safety(),
    }

    bundle["bundle_hash"] = _stable_hash(
        {k: v for k, v in bundle.items() if k != "bundle_hash"}
    )
    return bundle


def build_a2a_proof_bundle_summary(bundle: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build a compact summary for boardroom/API preview checks."""

    source = deepcopy(bundle) if bundle is not None else build_a2a_proof_bundle_preview()
    commitment = source.get("proof_commitment") or {}
    receipt = source.get("proof_receipt") or {}

    summary = {
        "ok": bool(source.get("ok")),
        "status": source.get("status", "proof_bundle_preview_only"),
        "contract_version": source.get("contract_version", A2A_PROOF_RECEIPT_VERSION),
        "business_id": source.get("business_id", "home_fixed"),
        "vertical_key": source.get("vertical_key", "home_repair"),
        "job_id": source.get("job_id", "home_fixed_job_preview"),
        "has_proof_commitment": bool(commitment),
        "has_proof_receipt": bool(receipt),
        "proof_commitment_created": bool(commitment.get("proof_commitment_created")),
        "proof_receipt_created": bool(receipt.get("proof_receipt_created")),
        "proof_verified": bool(receipt.get("proof_verified")),
        "glyphchain_is_payment_rail": False,
        "human_review_required": True,
        "public_route_exposed": False,
        "bundle_hash": source.get("bundle_hash", "preview_unavailable"),
    }
    summary["summary_hash"] = _stable_hash(
        {k: v for k, v in summary.items() if k != "summary_hash"}
    )
    return summary
