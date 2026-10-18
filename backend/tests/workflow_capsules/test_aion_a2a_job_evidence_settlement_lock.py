from backend.modules.aion_gateway.a2a_job_evidence_settlement import (
    A2A_JOB_EVIDENCE_SETTLEMENT_VERSION,
    build_a2a_job_evidence_preview,
    build_a2a_settlement_readiness_preview,
    build_a2a_job_evidence_settlement_bundle,
)


def _job():
    return {
        "business_id": "home_fixed",
        "business_name": "Home Fixed",
        "vertical_key": "home_repair",
        "industry_key": "trades",
        "job_id": "home_fixed_roof_repair_preview",
        "required_evidence": ["before_photo", "after_photo", "completion_note"],
        "submitted_evidence": ["before_photo"],
        "currency": "EUR",
        "quote_amount": 280,
    }


def test_job_evidence_preview_shape():
    result = build_a2a_job_evidence_preview(_job())
    assert result["ok"] is True
    assert result["status"] == "job_evidence_preview_ready"
    assert result["contract_version"] == A2A_JOB_EVIDENCE_SETTLEMENT_VERSION
    assert result["endpoint_key"] == "job_evidence"
    assert result["method"] == "GET"
    assert result["business_id"] == "home_fixed"
    assert result["business_name"] == "Home Fixed"
    assert result["vertical_key"] == "home_repair"
    assert result["industry_key"] == "trades"
    assert result["job_id"] == "home_fixed_roof_repair_preview"
    assert result["evidence_hash"]


def test_job_evidence_tracks_required_submitted_and_missing_evidence():
    result = build_a2a_job_evidence_preview(_job())
    assert result["required_evidence"] == ["before_photo", "after_photo", "completion_note"]
    assert result["submitted_evidence"] == ["before_photo"]
    assert result["missing_evidence"] == ["after_photo", "completion_note"]
    assert result["evidence_status"] == "evidence_pending"
    assert result["evidence_backed_completion"] is False
    assert result["proof_commit_ready"] is False


def test_job_evidence_complete_when_all_required_evidence_present():
    job = _job()
    job["submitted_evidence"] = ["before_photo", "after_photo", "completion_note"]
    result = build_a2a_job_evidence_preview(job)
    assert result["missing_evidence"] == []
    assert result["evidence_status"] == "evidence_preview_complete"
    assert result["evidence_backed_completion"] is True
    assert result["proof_commit_ready"] is True


def test_job_evidence_is_not_live_completion():
    result = build_a2a_job_evidence_preview(_job())
    assert result["human_review_required"] is True
    assert result["evidence_review_status"] == "requires_human_review"
    assert result["final_completion_confirmed"] is False


def test_settlement_readiness_preview_shape():
    evidence = build_a2a_job_evidence_preview(_job())
    result = build_a2a_settlement_readiness_preview(_job(), evidence)
    assert result["ok"] is True
    assert result["status"] == "settlement_readiness_preview_ready"
    assert result["contract_version"] == A2A_JOB_EVIDENCE_SETTLEMENT_VERSION
    assert result["endpoint_key"] == "settlement_readiness"
    assert result["method"] == "GET"
    assert result["business_id"] == "home_fixed"
    assert result["job_id"] == "home_fixed_roof_repair_preview"
    assert result["currency"] == "EUR"
    assert result["quote_amount"] == 280
    assert result["settlement_readiness_hash"]


def test_settlement_readiness_is_not_payment_execution():
    result = build_a2a_settlement_readiness_preview(_job())
    assert result["settlement_status"] == "not_ready_human_review_required"
    assert result["settlement_ready"] is False
    assert result["payment_ready"] is False
    assert result["escrow_ready"] is False
    assert result["fiat_first"] is True
    assert result["glyphchain_is_payment_rail"] is False
    assert result["proof_required_before_settlement"] is True
    assert result["human_review_required"] is True
    assert result["would_move_money"] is False
    assert result["would_create_payment"] is False
    assert result["would_create_escrow"] is False
    assert result["would_release_funds"] is False
    assert result["next_step"] == "future_guarded_approval_path"


def test_bundle_contains_evidence_and_settlement():
    bundle = build_a2a_job_evidence_settlement_bundle(_job())
    assert bundle["ok"] is True
    assert bundle["status"] == "a2a_job_evidence_settlement_preview_ready"
    assert bundle["contract_version"] == A2A_JOB_EVIDENCE_SETTLEMENT_VERSION
    assert bundle["job_evidence_preview"]["endpoint_key"] == "job_evidence"
    assert bundle["settlement_readiness_preview"]["endpoint_key"] == "settlement_readiness"
    assert bundle["bundle_hash"]


def test_hashes_are_deterministic():
    a = build_a2a_job_evidence_settlement_bundle(_job())
    b = build_a2a_job_evidence_settlement_bundle(_job())
    assert a["bundle_hash"] == b["bundle_hash"]
    assert a["job_evidence_preview"]["evidence_hash"] == b["job_evidence_preview"]["evidence_hash"]
    assert a["settlement_readiness_preview"]["settlement_readiness_hash"] == b["settlement_readiness_preview"]["settlement_readiness_hash"]


def test_hashes_change_when_evidence_changes():
    a = build_a2a_job_evidence_settlement_bundle(_job())
    changed = _job()
    changed["submitted_evidence"] = ["before_photo", "after_photo"]
    b = build_a2a_job_evidence_settlement_bundle(changed)
    assert a["bundle_hash"] != b["bundle_hash"]
    assert a["job_evidence_preview"]["evidence_hash"] != b["job_evidence_preview"]["evidence_hash"]


def test_safety_flags_are_locked():
    bundle = build_a2a_job_evidence_settlement_bundle(_job())
    for safety in [
        bundle["safety"],
        bundle["job_evidence_preview"]["safety"],
        bundle["settlement_readiness_preview"]["safety"],
    ]:
        assert safety["guarded"] is True
        assert safety["preview_only"] is True
        assert safety["public_route_exposed"] is False
        assert safety["requires_auth"] is True
        assert safety["human_review_required"] is True
        assert safety["would_execute_workflow"] is False
        assert safety["would_create_booking"] is False
        assert safety["would_create_live_job"] is False
        assert safety["would_move_money"] is False
        assert safety["would_move_pho"] is False
        assert safety["would_require_wallet"] is False
        assert safety["would_create_payment"] is False
        assert safety["would_create_escrow"] is False
        assert safety["would_release_funds"] is False
        assert safety["would_send_external_message"] is False
        assert safety["live_status_polling_enabled"] is False


def test_blocked_reasons_explain_no_payment_or_escrow():
    bundle = build_a2a_job_evidence_settlement_bundle(_job())
    evidence_reasons = bundle["job_evidence_preview"]["blocked_reasons"]
    settlement_reasons = bundle["settlement_readiness_preview"]["blocked_reasons"]

    assert "preview_only" in evidence_reasons
    assert "human_review_required" in evidence_reasons
    assert "no_live_completion_confirmation" in evidence_reasons
    assert "no_payment_movement" in settlement_reasons
    assert "no_payment_creation" in settlement_reasons
    assert "no_escrow_creation" in settlement_reasons
    assert "no_fund_release" in settlement_reasons
