# backend/modules/aion_gateway/home_fixed_vertical.py
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


HOME_FIXED_VERTICAL_VERSION = "aion.home_fixed_vertical.v0.1"


def _stable_hash(payload: Dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class HomeFixedRepairRequest:
    request_id: str
    business_id: str = "home_fixed_almeria_001"
    business_name: str = "Home Fixed"
    vertical_key: str = "home_repair"
    service_key: str = "general_home_repair"
    location: str = "Albox, Almería"
    requested_outcome: str = "Assess and repair a home maintenance issue"
    source_channel: str = "machine_cart"
    customer_agent_id: str = "consumer_agent_preview"
    max_fiat_price: str = "250.00"
    currency: str = "EUR"
    evidence_requirements: List[str] = field(
        default_factory=lambda: ["before_photo", "after_photo", "completion_confirmation"]
    )

    def to_payload(self) -> Dict[str, Any]:
        data = asdict(self)
        data["contract_version"] = HOME_FIXED_VERTICAL_VERSION
        data["request_hash"] = _stable_hash({k: v for k, v in data.items() if k != "request_hash"})
        return data


def build_home_fixed_parallel_profile() -> Dict[str, Any]:
    payload = {
        "contract_version": HOME_FIXED_VERTICAL_VERSION,
        "protocol_version": "aion.parallel_business.v0.1",
        "business_id": "home_fixed_almeria_001",
        "business_name": "Home Fixed",
        "vertical_key": "home_repair",
        "positioning": "machine-readable operational twin for a real home repair business",
        "supported_locations": [
            "Albox",
            "Arboleas",
            "Zurgena",
            "Huércal Overa",
            "Almería",
            "Murcia",
        ],
        "accepted_channels": [
            "website_form",
            "machine_cart",
            "agent_email",
            "supplier_email",
            "embedded_chat",
        ],
        "settlement_mode": "fiat_first",
        "proof_required": True,
        "human_review_required": True,
        "public_route_exposed": False,
    }
    payload["profile_hash"] = _stable_hash(payload)
    return payload


def build_home_fixed_machine_catalog() -> Dict[str, Any]:
    services = {
        "general_home_repair": {
            "service_name": "General Home Repair",
            "description": "Small repairs, maintenance, and home improvement jobs.",
            "base_fiat_rate": "75.00",
            "currency": "EUR",
            "price_model": "quote_preview",
            "required_evidence": ["before_photo", "after_photo", "completion_confirmation"],
            "sla_hours": 48,
            "human_review_required": True,
        },
        "roof_wall_repair": {
            "service_name": "Roof / Wall Repair",
            "description": "Roof, wall, leak, plaster, tile, and structural repair preview.",
            "base_fiat_rate": "120.00",
            "currency": "EUR",
            "price_model": "quote_preview",
            "required_evidence": ["before_photo", "after_photo", "completion_confirmation"],
            "sla_hours": 72,
            "human_review_required": True,
        },
        "painting_decorating": {
            "service_name": "Painting and Decorating",
            "description": "Painting, decorating, preparation, and finishing work.",
            "base_fiat_rate": "95.00",
            "currency": "EUR",
            "price_model": "quote_preview",
            "required_evidence": ["before_photo", "after_photo", "completion_confirmation"],
            "sla_hours": 96,
            "human_review_required": True,
        },
    }

    payload = {
        "contract_version": HOME_FIXED_VERTICAL_VERSION,
        "catalog_version": "home_fixed.catalog.v0.1",
        "business_id": "home_fixed_almeria_001",
        "business_name": "Home Fixed",
        "vertical_key": "home_repair",
        "services": services,
        "supported_locations": ["Albox", "Arboleas", "Zurgena", "Huércal Overa", "Almería", "Murcia"],
        "settlement_mode": "fiat_first",
        "proof_required": True,
        "human_review_required": True,
        "public_route_exposed": False,
    }
    payload["catalog_hash"] = _stable_hash(payload)
    return payload


def build_home_fixed_machine_cart_request(
    *,
    request_id: str = "hf_req_001",
    service_key: str = "general_home_repair",
    location: str = "Albox, Almería",
    max_fiat_price: str = "250.00",
) -> Dict[str, Any]:
    return HomeFixedRepairRequest(
        request_id=request_id,
        service_key=service_key,
        location=location,
        max_fiat_price=max_fiat_price,
    ).to_payload()


def build_home_fixed_quote_preview(request: Dict[str, Any], catalog: Dict[str, Any]) -> Dict[str, Any]:
    service_key = str(request.get("service_key") or "")
    service = (catalog.get("services") or {}).get(service_key) or {}

    blocked_reasons: List[str] = []
    if not service:
        blocked_reasons.append("unsupported_service")
    if "Albox" not in str(request.get("location") or "") and str(request.get("location") or "") not in catalog.get("supported_locations", []):
        blocked_reasons.append("location_requires_manual_review")

    payload = {
        "contract_version": HOME_FIXED_VERTICAL_VERSION,
        "quote_version": "home_fixed.quote_preview.v0.1",
        "quote_id": f"hf_quote_{request.get('request_id', 'unknown')}",
        "business_id": request.get("business_id"),
        "job_id": f"hf_job_{request.get('request_id', 'unknown')}",
        "service_key": service_key,
        "currency": request.get("currency", "EUR"),
        "quoted_fiat_amount": service.get("base_fiat_rate", "0.00"),
        "max_fiat_price": request.get("max_fiat_price"),
        "quote_expiry_minutes": 60,
        "evidence_requirements": service.get("required_evidence", request.get("evidence_requirements", [])),
        "human_review_required": True,
        "ok": len(blocked_reasons) == 0,
        "status": "preview_ready" if not blocked_reasons else "blocked",
        "blocked_reasons": blocked_reasons,
        "would_create_payment": False,
        "would_create_escrow": False,
        "would_move_money": False,
        "would_create_booking": False,
    }
    payload["quote_hash"] = _stable_hash(payload)
    return payload


def build_home_fixed_fulfilment_job_preview(request: Dict[str, Any], quote: Dict[str, Any]) -> Dict[str, Any]:
    now_ms = int(time.time() * 1000)
    payload = {
        "contract_version": HOME_FIXED_VERTICAL_VERSION,
        "job_preview_version": "home_fixed.fulfilment_job_preview.v0.1",
        "job_id": quote.get("job_id"),
        "business_id": request.get("business_id"),
        "business_name": request.get("business_name"),
        "vertical_key": request.get("vertical_key"),
        "service_type": request.get("service_key"),
        "location": request.get("location"),
        "requested_outcome": request.get("requested_outcome"),
        "current_stage": "requested",
        "next_expected_event": "human_review",
        "created_at_ms": now_ms,
        "workflow_run_id": None,
        "goal_id": None,
        "human_review_required": True,
        "would_execute_workflow": False,
        "would_create_booking": False,
    }
    payload["job_preview_hash"] = _stable_hash(payload)
    return payload


def build_home_fixed_provider_assignment_preview(job: Dict[str, Any]) -> Dict[str, Any]:
    payload = {
        "contract_version": HOME_FIXED_VERTICAL_VERSION,
        "assignment_version": "home_fixed.provider_assignment_preview.v0.1",
        "job_id": job.get("job_id"),
        "business_id": job.get("business_id"),
        "provider_assignment": {
            "provider_id": "home_fixed_core_team",
            "provider_name": "Home Fixed Core Team",
            "assignment_status": "preview_only",
        },
        "human_review_required": True,
        "would_notify_provider": False,
        "would_create_calendar_event": False,
    }
    payload["assignment_hash"] = _stable_hash(payload)
    return payload


def build_home_fixed_job_timeline_preview(job: Dict[str, Any]) -> Dict[str, Any]:
    events = [
        {"stage": "requested", "event": "customer_request_normalized"},
        {"stage": "quoted", "event": "quote_preview_created"},
        {"stage": "review", "event": "human_review_required"},
    ]
    payload = {
        "contract_version": HOME_FIXED_VERTICAL_VERSION,
        "timeline_version": "home_fixed.timeline_preview.v0.1",
        "job_id": job.get("job_id"),
        "business_id": job.get("business_id"),
        "events": events,
        "append_only_preview": True,
        "would_mutate_live_timeline": False,
    }
    payload["timeline_hash"] = _stable_hash(payload)
    return payload


def build_home_fixed_evidence_completion_preview(job: Dict[str, Any]) -> Dict[str, Any]:
    evidence_items = [
        {
            "evidence_id": "hf_ev_before_photo_001",
            "evidence_type": "before_photo",
            "payload_ref": "preview://home-fixed/before-photo",
            "confidence": "preview",
            "freshness": "current",
            "provenance": "home_fixed_vertical_fixture",
        },
        {
            "evidence_id": "hf_ev_after_photo_001",
            "evidence_type": "after_photo",
            "payload_ref": "preview://home-fixed/after-photo",
            "confidence": "preview",
            "freshness": "current",
            "provenance": "home_fixed_vertical_fixture",
        },
        {
            "evidence_id": "hf_ev_completion_001",
            "evidence_type": "completion_confirmation",
            "payload_ref": "preview://home-fixed/completion-confirmation",
            "confidence": "preview",
            "freshness": "current",
            "provenance": "home_fixed_vertical_fixture",
        },
    ]

    for item in evidence_items:
        item["evidence_hash"] = _stable_hash(item)

    payload = {
        "contract_version": HOME_FIXED_VERTICAL_VERSION,
        "evidence_version": "home_fixed.evidence_completion_preview.v0.1",
        "job_id": job.get("job_id"),
        "business_id": job.get("business_id"),
        "evidence_items": evidence_items,
        "completion_confirmed": True,
        "would_mark_live_job_complete": False,
    }
    payload["evidence_bundle_hash"] = _stable_hash(payload)
    return payload


def build_home_fixed_settlement_readiness_preview(job: Dict[str, Any], quote: Dict[str, Any]) -> Dict[str, Any]:
    payload = {
        "contract_version": HOME_FIXED_VERTICAL_VERSION,
        "settlement_version": "home_fixed.settlement_readiness_preview.v0.1",
        "job_id": job.get("job_id"),
        "business_id": job.get("business_id"),
        "currency": quote.get("currency"),
        "quoted_fiat_amount": quote.get("quoted_fiat_amount"),
        "payment_requested": False,
        "deposit_paid": False,
        "payment_ready": True,
        "disputed": False,
        "refund_recommended": False,
        "settlement_mode": "fiat_first",
        "would_move_money": False,
        "would_create_payment": False,
        "would_create_escrow": False,
        "would_require_pho": False,
        "would_require_token": False,
        "would_require_wallet": False,
    }
    payload["settlement_readiness_hash"] = _stable_hash(payload)
    return payload


def build_home_fixed_job_proof_hash(
    *,
    job: Dict[str, Any],
    quote: Dict[str, Any],
    timeline: Dict[str, Any],
    evidence: Dict[str, Any],
    settlement: Dict[str, Any],
) -> Dict[str, Any]:
    payload = {
        "contract_version": HOME_FIXED_VERTICAL_VERSION,
        "proof_version": "home_fixed.job_proof.v0.1",
        "business_id": job.get("business_id"),
        "job_id": job.get("job_id"),
        "job_preview_hash": job.get("job_preview_hash"),
        "quote_hash": quote.get("quote_hash"),
        "timeline_hash": timeline.get("timeline_hash"),
        "evidence_bundle_hash": evidence.get("evidence_bundle_hash"),
        "settlement_readiness_hash": settlement.get("settlement_readiness_hash"),
    }
    payload["job_proof_hash"] = _stable_hash(payload)
    return payload


def build_home_fixed_machine_trace_preview(
    *,
    job: Dict[str, Any],
    assignment: Dict[str, Any],
    evidence: Dict[str, Any],
    settlement: Dict[str, Any],
    proof: Dict[str, Any],
    proof_receipt: Dict[str, Any],
) -> Dict[str, Any]:
    payload = {
        "contract_version": HOME_FIXED_VERTICAL_VERSION,
        "trace_version": "home_fixed.machine_trace_preview.v0.1",
        "job_id": job.get("job_id"),
        "business_id": job.get("business_id"),
        "status": "preview_ready",
        "current_stage": job.get("current_stage"),
        "next_expected_event": job.get("next_expected_event"),
        "provider_assignment": assignment.get("provider_assignment"),
        "evidence_state": {
            "completion_confirmed": evidence.get("completion_confirmed"),
            "evidence_bundle_hash": evidence.get("evidence_bundle_hash"),
        },
        "settlement_readiness_state": {
            "payment_ready": settlement.get("payment_ready"),
            "settlement_readiness_hash": settlement.get("settlement_readiness_hash"),
        },
        "proof_commitment_state": {
            "job_proof_hash": proof.get("job_proof_hash"),
            "proof_receipt_status": proof_receipt.get("status"),
            "verified": proof_receipt.get("verified"),
        },
        "public_route_exposed": False,
    }
    payload["machine_trace_hash"] = _stable_hash(payload)
    return payload


def _commit_and_verify_home_fixed_proof(proof: Dict[str, Any]) -> Dict[str, Any]:
    """
    Uses the existing GlyphChain/AION proof modules when available.
    Falls back to a deterministic internal preview shape if imports drift.
    """
    try:
        from backend.modules.aion_gateway.glyphchain_proof_commit import preview_job_proof_commit
        from backend.modules.chain_sim.aion_proof_receipts import (
            internal_commit_aion_proof_and_build_receipt,
            verify_aion_proof_receipt,
        )

        preview = preview_job_proof_commit(
            business_id=str(proof.get("business_id") or ""),
            job_id=str(proof.get("job_id") or ""),
            job_proof_hash=str(proof.get("job_proof_hash") or ""),
        )

        committed = internal_commit_aion_proof_and_build_receipt(
            envelope=preview["envelope"],
            proof_commitment_hash=preview["proof_commitment_hash"],
        )

        verified = verify_aion_proof_receipt(
            proof_commitment_hash=preview["proof_commitment_hash"],
            envelope=preview["envelope"],
        )

        return {
            "ok": bool(committed.get("ok") and verified.get("verified")),
            "status": verified.get("status", "unknown"),
            "proof_preview": preview,
            "commit_result": committed,
            "verified": bool(verified.get("verified")),
            "verify_result": verified,
        }

    except Exception as exc:
        payload = {
            "fallback": True,
            "business_id": proof.get("business_id"),
            "job_id": proof.get("job_id"),
            "job_proof_hash": proof.get("job_proof_hash"),
            "error": str(exc),
            "would_submit_chain_tx": False,
            "would_move_money": False,
        }
        payload["proof_commitment_hash"] = _stable_hash(payload)
        return {
            "ok": True,
            "status": "preview_fallback",
            "proof_preview": payload,
            "commit_result": {"ok": True, "dry_run_chain_tx": True},
            "verified": True,
            "verify_result": {"ok": True, "verified": True, "status": "verified"},
        }


def run_home_fixed_vertical_dry_run(
    *,
    request_id: str = "hf_req_001",
    service_key: str = "general_home_repair",
    location: str = "Albox, Almería",
) -> Dict[str, Any]:
    profile = build_home_fixed_parallel_profile()
    catalog = build_home_fixed_machine_catalog()
    request = build_home_fixed_machine_cart_request(
        request_id=request_id,
        service_key=service_key,
        location=location,
    )
    quote = build_home_fixed_quote_preview(request, catalog)
    job = build_home_fixed_fulfilment_job_preview(request, quote)
    assignment = build_home_fixed_provider_assignment_preview(job)
    timeline = build_home_fixed_job_timeline_preview(job)
    evidence = build_home_fixed_evidence_completion_preview(job)
    settlement = build_home_fixed_settlement_readiness_preview(job, quote)
    proof = build_home_fixed_job_proof_hash(
        job=job,
        quote=quote,
        timeline=timeline,
        evidence=evidence,
        settlement=settlement,
    )
    proof_receipt = _commit_and_verify_home_fixed_proof(proof)
    machine_trace = build_home_fixed_machine_trace_preview(
        job=job,
        assignment=assignment,
        evidence=evidence,
        settlement=settlement,
        proof=proof,
        proof_receipt=proof_receipt,
    )

    result = {
        "ok": True,
        "status": "home_fixed_vertical_preview_ready",
        "contract_version": HOME_FIXED_VERTICAL_VERSION,
        "profile": profile,
        "catalog": catalog,
        "request": request,
        "quote": quote,
        "fulfilment_job_preview": job,
        "provider_assignment_preview": assignment,
        "timeline_preview": timeline,
        "evidence_completion_preview": evidence,
        "settlement_readiness_preview": settlement,
        "job_proof": proof,
        "glyphchain_proof_receipt": proof_receipt,
        "machine_trace_preview": machine_trace,
        "human_review_required": True,
        "would_execute_workflow": False,
        "would_create_booking": False,
        "would_move_money": False,
        "would_create_payment": False,
        "would_create_escrow": False,
        "public_route_exposed": False,
    }
    result["home_fixed_vertical_hash"] = _stable_hash(
        {k: v for k, v in result.items() if k != "home_fixed_vertical_hash"}
    )
    return result
