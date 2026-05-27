# backend/modules/aion_gateway/boardroom_parallel_twin_payload.py
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict

from backend.modules.aion_gateway import home_fixed_vertical as home_fixed


BOARDROOM_PARALLEL_TWIN_PAYLOAD_VERSION = "aion.boardroom_parallel_twin_payload.v0.1"


def _stable_hash(payload: Dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _pick(source: Dict[str, Any], *names: str) -> Dict[str, Any]:
    for name in names:
        value = source.get(name)
        if isinstance(value, dict):
            return value
    return {}


def _build_home_fixed_vertical_dry_run(*, business_id: str, job_id: str) -> Dict[str, Any]:
    """
    Resolve the locked Home Fixed Phase 8 dry-run builder.

    Phase 8 locked this function as run_home_fixed_vertical_dry_run().
    The additional names are kept only as compatibility fallbacks.
    """
    candidate_names = (
        "run_home_fixed_vertical_dry_run",
        "build_home_fixed_vertical_dry_run",
        "build_home_fixed_dry_run",
        "build_home_fixed_vertical_testbed",
        "build_home_fixed_vertical_testbed_preview",
        "build_home_fixed_vertical_flow",
        "build_home_fixed_full_dry_run",
    )

    last_error: Exception | None = None

    for name in candidate_names:
        fn = getattr(home_fixed, name, None)
        if not callable(fn):
            continue

        for kwargs in (
            {"business_id": business_id, "job_id": job_id},
            {"job_id": job_id},
            {},
        ):
            try:
                out = fn(**kwargs)
                if isinstance(out, dict):
                    return out
            except TypeError as e:
                last_error = e
                continue

    raise ImportError(
        "No compatible Home Fixed vertical dry-run builder found in "
        "backend.modules.aion_gateway.home_fixed_vertical"
    ) from last_error


def _normalise_home_fixed_sections(dry_run: Dict[str, Any]) -> Dict[str, Any]:
    """
    Phase 8 section names are allowed to drift internally. Phase 9B exposes
    stable Boardroom names for the visibility payload.
    """
    machine_catalog = _pick(
        dry_run,
        "machine_catalog",
        "catalog",
        "parallel_catalog",
        "home_fixed_machine_catalog",
    )

    machine_cart = _pick(
        dry_run,
        "machine_cart",
        "machine_cart_request",
        "cart_request",
        "request",
        "repair_request",
        "customer_request",
    )

    quote_preview = _pick(
        dry_run,
        "quote_preview",
        "quote",
        "machine_quote_preview",
    )

    fulfilment_job_preview = _pick(
        dry_run,
        "fulfilment_job_preview",
        "fulfillment_job_preview",
        "job",
        "job_preview",
        "fulfilment_job",
    )

    settlement_readiness = _pick(
        dry_run,
        "settlement_readiness",
        "settlement",
        "settlement_readiness_preview",
    )

    proof_receipt = _pick(
        dry_run,
        "proof_receipt",
        "receipt",
        "proof",
        "glyphchain_proof_receipt",
        "proof_commit",
        "proof_commit_result",
        "commit_result",
        "proof_commitment",
        "proof_commitment_receipt",
        "proof_verification",
    )

    exception_recovery = _pick(
        dry_run,
        "exception_recovery",
        "exception",
        "recovery",
        "exception_state",
    )

    machine_trace_preview = _pick(
        dry_run,
        "machine_trace_preview",
        "machine_trace",
        "trace",
        "a2a_trace",
    )

    return {
        "machine_catalog": machine_catalog,
        "machine_cart": machine_cart,
        "quote_preview": quote_preview,
        "fulfilment_job_preview": fulfilment_job_preview,
        "settlement_readiness": settlement_readiness,
        "proof_receipt": proof_receipt,
        "exception_recovery": exception_recovery or {
            "ok": True,
            "status": "no_active_exception",
            "human_review_required": True,
            "autonomous_execution_allowed": False,
            "would_execute_workflow": False,
            "would_create_booking": False,
            "would_move_money": False,
            "would_move_pho": False,
            "would_create_payment": False,
            "would_create_escrow": False,
            "would_send_external_message": False,
            "blocked_reasons": [],
        },
        "machine_trace_preview": machine_trace_preview,
    }


def build_boardroom_parallel_twin_payload(
    *,
    business_id: str = "home_fixed",
    job_id: str = "home_fixed_job_001",
) -> Dict[str, Any]:
    dry_run = _build_home_fixed_vertical_dry_run(
        business_id=business_id,
        job_id=job_id,
    )

    sections = _normalise_home_fixed_sections(dry_run)

    payload: Dict[str, Any] = {
        "ok": True,
        "contract_version": BOARDROOM_PARALLEL_TWIN_PAYLOAD_VERSION,
        "payload_version": BOARDROOM_PARALLEL_TWIN_PAYLOAD_VERSION,
        "status": "preview_ready",
        "business_id": business_id,
        "business_name": "Home Fixed",
        "vertical_key": "home_repair",
        "job_id": job_id,
        "visibility_only": True,
        "human_review_required": True,
        "autonomous_execution_allowed": False,
        "would_execute_workflow": False,
        "would_create_booking": False,
        "would_move_money": False,
        "would_move_pho": False,
        "would_require_wallet": False,
        "would_create_payment": False,
        "would_create_escrow": False,
        "would_send_external_message": False,
        "public_a2a_route_exposed": False,
        "source": "home_fixed_vertical_testbed",
        "dry_run_status": dry_run.get("status") or "home_fixed_vertical_preview_ready",
        **sections,
    }

    payload["safety"] = {
        "visibility_only": True,
        "human_review_required": True,
        "autonomous_execution_allowed": False,
        "would_execute_workflow": False,
        "would_create_booking": False,
        "would_move_money": False,
        "would_move_pho": False,
        "would_require_wallet": False,
        "would_create_payment": False,
        "would_create_escrow": False,
        "would_send_external_message": False,
        "public_a2a_route_exposed": False,
    }

    payload["payload_hash"] = _stable_hash(
        {k: v for k, v in payload.items() if k != "payload_hash"}
    )

    return {
        "ok": True,
        "status": "preview_ready",
        "payload": payload,
        "payload_hash": payload["payload_hash"],
    }


def build_boardroom_parallel_twin_summary(
    *,
    business_id: str = "home_fixed",
    job_id: str = "home_fixed_job_001",
) -> Dict[str, Any]:
    out = build_boardroom_parallel_twin_payload(
        business_id=business_id,
        job_id=job_id,
    )
    payload = out["payload"]

    return {
        "ok": True,
        "status": "boardroom_parallel_twin_summary_ready",
        "contract_version": BOARDROOM_PARALLEL_TWIN_PAYLOAD_VERSION,
        "business_id": payload["business_id"],
        "business_name": payload["business_name"],
        "vertical_key": payload["vertical_key"],
        "job_id": payload["job_id"],
        "has_machine_catalog": bool(payload.get("machine_catalog")),
        "has_machine_cart": bool(payload.get("machine_cart")),
        "has_quote_preview": bool(payload.get("quote_preview")),
        "has_fulfilment_job_preview": bool(payload.get("fulfilment_job_preview")),
        "has_settlement_readiness": bool(payload.get("settlement_readiness")),
        "has_proof_receipt": bool(payload.get("proof_receipt")),
        "has_exception_recovery": bool(payload.get("exception_recovery")),
        "has_machine_trace_preview": bool(payload.get("machine_trace_preview")),
        "visibility_only": payload["visibility_only"],
        "human_review_required": payload["human_review_required"],
        "autonomous_execution_allowed": payload["autonomous_execution_allowed"],
        "public_a2a_route_exposed": payload["public_a2a_route_exposed"],
        "payload_hash": payload["payload_hash"],
    }
