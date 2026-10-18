from backend.modules.aion_gateway.a2a_proof_receipt import (
    A2A_PROOF_RECEIPT_VERSION,
    build_a2a_proof_bundle_preview,
    build_a2a_proof_bundle_summary,
    build_a2a_proof_commitment_preview,
    build_a2a_proof_receipt_preview,
)


def test_proof_commitment_preview_contract():
    preview = build_a2a_proof_commitment_preview()

    assert preview["ok"] is True
    assert preview["status"] == "proof_commitment_preview_only"
    assert preview["contract_version"] == A2A_PROOF_RECEIPT_VERSION
    assert preview["endpoint_key"] == "proof_commitment"
    assert preview["method"] == "GET"
    assert preview["business_id"] == "home_fixed"
    assert preview["vertical_key"] == "home_repair"
    assert preview["industry_key"] == "trades"
    assert preview["proof_commitment_created"] is False
    assert preview["proof_commitment_status"] == "preview_not_committed"
    assert preview["proof_commitment_hash"]


def test_proof_receipt_preview_contract():
    preview = build_a2a_proof_receipt_preview(
        proof_commitment_hash="commitment_hash_123"
    )

    assert preview["ok"] is True
    assert preview["status"] == "proof_receipt_preview_only"
    assert preview["contract_version"] == A2A_PROOF_RECEIPT_VERSION
    assert preview["endpoint_key"] == "proof_receipt"
    assert preview["method"] == "GET"
    assert preview["business_id"] == "home_fixed"
    assert preview["vertical_key"] == "home_repair"
    assert preview["proof_commitment_hash"] == "commitment_hash_123"
    assert preview["proof_receipt_created"] is False
    assert preview["proof_receipt_status"] == "preview_not_issued"
    assert preview["proof_verified"] is False
    assert preview["proof_receipt_hash"]


def test_proof_bundle_contains_commitment_and_receipt():
    bundle = build_a2a_proof_bundle_preview()

    assert bundle["ok"] is True
    assert bundle["status"] == "proof_bundle_preview_only"
    assert bundle["business_id"] == "home_fixed"
    assert bundle["vertical_key"] == "home_repair"
    assert bundle["proof_commitment"]["endpoint_key"] == "proof_commitment"
    assert bundle["proof_receipt"]["endpoint_key"] == "proof_receipt"
    assert bundle["proof_receipt"]["proof_commitment_hash"] == bundle["proof_commitment"]["proof_commitment_hash"]
    assert bundle["bundle_hash"]


def test_proof_bundle_summary():
    bundle = build_a2a_proof_bundle_preview()
    summary = build_a2a_proof_bundle_summary(bundle)

    assert summary["ok"] is True
    assert summary["has_proof_commitment"] is True
    assert summary["has_proof_receipt"] is True
    assert summary["proof_commitment_created"] is False
    assert summary["proof_receipt_created"] is False
    assert summary["proof_verified"] is False
    assert summary["glyphchain_is_payment_rail"] is False
    assert summary["human_review_required"] is True
    assert summary["public_route_exposed"] is False
    assert summary["summary_hash"]


def test_hashes_are_deterministic_for_same_input():
    first = build_a2a_proof_bundle_preview(job_id="job_123")
    second = build_a2a_proof_bundle_preview(job_id="job_123")

    assert first["proof_commitment"]["proof_commitment_hash"] == second["proof_commitment"]["proof_commitment_hash"]
    assert first["proof_receipt"]["proof_receipt_hash"] == second["proof_receipt"]["proof_receipt_hash"]
    assert first["bundle_hash"] == second["bundle_hash"]


def test_hashes_change_when_job_changes():
    first = build_a2a_proof_bundle_preview(job_id="job_123")
    second = build_a2a_proof_bundle_preview(job_id="job_456")

    assert first["proof_commitment"]["proof_commitment_hash"] != second["proof_commitment"]["proof_commitment_hash"]
    assert first["proof_receipt"]["proof_receipt_hash"] != second["proof_receipt"]["proof_receipt_hash"]
    assert first["bundle_hash"] != second["bundle_hash"]


def test_glyphchain_is_proof_only_not_payment():
    bundle = build_a2a_proof_bundle_preview()

    assert bundle["glyphchain_is_payment_rail"] is False
    assert bundle["proof_only_not_payment"] is True
    assert bundle["proof_commitment"]["glyphchain_is_payment_rail"] is False
    assert bundle["proof_receipt"]["glyphchain_is_payment_rail"] is False
    assert bundle["proof_commitment"]["proof_only_not_payment"] is True
    assert bundle["proof_receipt"]["proof_only_not_payment"] is True


def test_safety_blocks_live_side_effects():
    bundle = build_a2a_proof_bundle_preview()

    for scope in [bundle, bundle["proof_commitment"], bundle["proof_receipt"]]:
        safety = scope["safety"]
        assert safety["guarded"] is True
        assert safety["preview_only"] is True
        assert safety["public_route_exposed"] is False
        assert safety["human_review_required"] is True
        assert safety["autonomous_execution_allowed"] is False
        assert safety["would_execute_workflow"] is False
        assert safety["would_create_booking"] is False
        assert safety["would_create_live_job"] is False
        assert safety["would_confirm_final_completion"] is False
        assert safety["would_move_money"] is False
        assert safety["would_move_pho"] is False
        assert safety["would_require_wallet"] is False
        assert safety["would_create_payment"] is False
        assert safety["would_create_escrow"] is False
        assert safety["would_release_funds"] is False
        assert safety["would_send_external_message"] is False
        assert safety["live_status_polling_enabled"] is False


def test_blocked_reasons_explain_preview_boundary():
    commitment = build_a2a_proof_commitment_preview()
    receipt = build_a2a_proof_receipt_preview()

    for term in [
        "preview_only",
        "public_route_not_exposed",
        "human_review_required",
        "no_payment_side_effect",
        "no_escrow_side_effect",
        "no_fund_release_side_effect",
    ]:
        assert term in commitment["blocked_reasons"]
        assert term in receipt["blocked_reasons"]
