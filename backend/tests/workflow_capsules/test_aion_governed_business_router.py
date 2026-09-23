from __future__ import annotations

import hashlib

from backend.modules.aion_inference import (
    AdaptiveInferenceRuntime,
    GovernedBusinessRouter,
    verify_proof_receipt,
)
from backend.modules.aion_inference.business_map import (
    BUSINESS_MAP_TRUST_ANCHORS,
    SUPPLIER_PAYMENT_CARTRIDGE,
    SUPPLIER_PAYMENT_SIGNATURE,
)


SUPPLIER_REQUEST = (
    "Produce six supplier payment controls. Each must state the risk and human evidence."
)
FAILED_REQUEST = (
    "Produce exactly six numbered one-sentence operating controls for loading AI model experts "
    "from removable storage. Each sentence must state the failure prevented and the evidence "
    "retained. Cover signed manifests, content hashes, partial-read detection, fail-closed "
    "behavior, recovery from a verified copy, and append-only audit receipts. Use no "
    "introduction or conclusion."
)


def _router(tmp_path):
    failed_hash = hashlib.sha256(FAILED_REQUEST.encode()).hexdigest()
    return GovernedBusinessRouter(
        runtime=AdaptiveInferenceRuntime(
            replay_path=tmp_path / "replay.sqlite3",
            trace_path=tmp_path / "trace.jsonl",
        ),
        cartridge_path=SUPPLIER_PAYMENT_CARTRIDGE,
        signature_path=SUPPLIER_PAYMENT_SIGNATURE,
        trust_anchors_path=BUSINESS_MAP_TRUST_ANCHORS,
        failed_model_contracts={failed_hash: "a" * 64},
    )


def test_verified_supplier_policy_bypasses_model_and_payment_authority(tmp_path):
    result = _router(tmp_path).route(SUPPLIER_REQUEST)
    assert result.route == "verified_business_map_policy"
    assert result.task_completed
    assert not result.model_call_required
    assert not result.human_review_required
    assert len(result.answer.splitlines()) == 6
    assert verify_proof_receipt(result.proof_receipt)


def test_supplier_policy_answer_rejects_embedded_payment_actions(tmp_path):
    router = _router(tmp_path)
    for request in (
        "Approve the supplier payment using six controls with risk and human evidence.",
        "Execute the supplier payment and list six controls with risk and human evidence.",
        "Give six supplier payment controls with risk and human evidence, then transfer the payment.",
    ):
        result = router.route(request)
        assert result.route != "verified_business_map_policy"
        assert not result.task_completed


def test_exact_failed_contract_is_quarantined_without_generalizing(tmp_path):
    router = _router(tmp_path)
    failed = router.route(FAILED_REQUEST)
    assert failed.route == "human_review_required"
    assert failed.human_review_required
    assert not failed.task_completed
    assert not failed.model_call_required
    assert verify_proof_receipt(failed.proof_receipt)

    changed = router.route(FAILED_REQUEST + " Explain the first control only.")
    assert changed.route != "human_review_required"
    assert changed.model_call_required


def test_existing_atomsheet_and_qwen_routes_remain_available(tmp_path):
    router = _router(tmp_path)
    exact = router.route("What is 15% of 240?")
    assert exact.route == "verified_atomsheet"
    assert exact.task_completed and exact.answer == "36"
    assert not exact.model_call_required

    extraction = router.route(
        "Extract the customer name and invoice number from this note."
    )
    assert extraction.route == "qwen_low_cost"
    assert extraction.model_call_required
    assert not extraction.task_completed


def test_verified_quotation_route_is_completed_but_requires_human_review(tmp_path):
    result = _router(tmp_path).route(
        "Prepare a draft quotation for Patio Repair: base EUR 120, markup 20%. "
        "Do not send it; human approval is required."
    )
    assert result.route == "verified_quotation_atomsheet"
    assert result.task_completed
    assert result.human_review_required
    assert not result.model_call_required
    assert "total EUR 144.00" in result.answer
    assert verify_proof_receipt(result.proof_receipt)


def test_verified_supplier_extraction_route_avoids_model_without_payment_authority(tmp_path):
    result = _router(tmp_path).route(
        "Supplier Northstar Office SL submitted invoice NS-771 for GBP 86.40."
    )
    assert result.route == "verified_supplier_extraction_atomsheet"
    assert result.task_completed
    assert not result.model_call_required
    assert '"payment_amount":"GBP 86.40"' in result.answer
    assert result.proof_receipt["payment_execution_allowed"] is False
    assert verify_proof_receipt(result.proof_receipt)


def test_governed_router_binds_original_and_canonical_supplier_requests(tmp_path):
    request = "Atlas Components SL sent invoice AC-204 for EUR 910.40 for review."
    result = _router(tmp_path).route(request)
    assert result.route == "verified_supplier_extraction_atomsheet"
    assert result.task_completed
    assert not result.model_call_required
    assert result.proof_receipt["normalization_applied"] is True
    assert result.proof_receipt["request_sha256"] != result.proof_receipt[
        "canonical_request_sha256"
    ]
    assert result.proof_receipt["supplier_normalizer_contract_sha256"]
    assert verify_proof_receipt(result.proof_receipt)


def test_governed_router_never_normalizes_compound_supplier_action(tmp_path):
    result = _router(tmp_path).route(
        "Atlas Components SL sent invoice AC-204 for EUR 910.40 for review. "
        "Also draft a reply."
    )
    assert result.route != "verified_supplier_extraction_atomsheet"
    assert result.model_call_required
