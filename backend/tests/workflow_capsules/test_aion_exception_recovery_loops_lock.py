from __future__ import annotations

from backend.modules.aion_gateway.exceptions import (
    EXCEPTION_CONTRACT_VERSION,
    SUPPORTED_EXCEPTION_TYPES,
    SUPPORTED_RECOVERY_ACTIONS,
    build_exception_recovery_preview,
    build_exception_state_for_machine_trace,
    example_home_fixed_exception_preview,
)


def _preview(exception_type: str = "provider_late"):
    return build_exception_recovery_preview(
        exception_type=exception_type,
        business_id="home_fixed",
        job_id="hf_job_001",
        summary="Home Fixed operational exception preview.",
        evidence_refs=["ev_001"],
        metadata={"vertical_key": "home_repair"},
    )


def test_exception_contract_version_locked():
    assert EXCEPTION_CONTRACT_VERSION == "aion.exception_recovery.v0.1"


def test_supported_exception_types_cover_phase_7e_scope():
    for item in [
        "provider_late",
        "provider_cancelled",
        "missing_evidence",
        "quote_changed",
        "budget_exceeded",
        "approval_delayed",
        "unsafe_request_blocked",
        "customer_dispute",
        "proof_verification_failed",
        "settlement_readiness_blocked",
    ]:
        assert item in SUPPORTED_EXCEPTION_TYPES


def test_supported_recovery_actions_cover_phase_7e_scope():
    for item in [
        "reschedule",
        "backup_provider",
        "pause",
        "cancel",
        "escalate",
        "request_missing_evidence",
        "revise_quote",
        "recommend_refund",
    ]:
        assert item in SUPPORTED_RECOVERY_ACTIONS


def test_provider_late_preview_returns_reschedule_and_escalate():
    out = _preview("provider_late")

    assert out["ok"] is True
    assert out["status"] == "preview_ready"
    assert out["exception"]["exception_type"] == "provider_late"

    action_types = [a["action_type"] for a in out["recovery_actions"]]
    assert "reschedule" in action_types
    assert "escalate" in action_types


def test_missing_evidence_preview_returns_request_missing_evidence():
    out = _preview("missing_evidence")

    action_types = [a["action_type"] for a in out["recovery_actions"]]
    assert "request_missing_evidence" in action_types
    assert "pause" in action_types


def test_quote_changed_preview_returns_revise_quote():
    out = _preview("quote_changed")

    action_types = [a["action_type"] for a in out["recovery_actions"]]
    assert "revise_quote" in action_types


def test_customer_dispute_preview_can_recommend_refund():
    out = _preview("customer_dispute")

    action_types = [a["action_type"] for a in out["recovery_actions"]]
    assert "recommend_refund" in action_types


def test_proof_verification_failed_preview_blocks_autonomous_execution():
    out = _preview("proof_verification_failed")

    assert out["human_review_required"] is True
    assert out["autonomous_execution_allowed"] is False
    assert out["would_execute_workflow"] is False
    assert out["would_move_money"] is False


def test_settlement_readiness_blocked_preview_can_recommend_refund():
    out = _preview("settlement_readiness_blocked")

    action_types = [a["action_type"] for a in out["recovery_actions"]]
    assert "recommend_refund" in action_types
    assert "pause" in action_types


def test_invalid_exception_type_blocks_preview():
    out = build_exception_recovery_preview(
        exception_type="not_real",
        business_id="home_fixed",
        job_id="hf_job_001",
    )

    assert out["ok"] is False
    assert out["status"] == "blocked"
    assert "unsupported_exception_type" in out["blocked_reasons"]


def test_missing_business_and_job_blocks_preview():
    out = build_exception_recovery_preview(
        exception_type="provider_late",
        business_id="",
        job_id="",
    )

    assert out["ok"] is False
    assert "missing_business_id" in out["blocked_reasons"]
    assert "missing_job_id" in out["blocked_reasons"]


def test_recovery_actions_require_human_review_by_default():
    out = _preview("provider_cancelled")

    for action in out["recovery_actions"]:
        assert action["requires_human_review"] is True
        assert action["autonomous_execution_allowed"] is False
        assert "human_review_required" in action["blocked_reasons"]
        assert "autonomous_recovery_execution_disabled" in action["blocked_reasons"]


def test_no_recovery_action_has_side_effects():
    out = _preview("budget_exceeded")

    assert out["would_create_booking"] is False
    assert out["would_move_money"] is False
    assert out["would_create_payment"] is False
    assert out["would_create_escrow"] is False
    assert out["would_send_external_message"] is False

    for action in out["recovery_actions"]:
        assert action["would_execute_workflow"] is False
        assert action["would_create_booking"] is False
        assert action["would_move_money"] is False
        assert action["would_create_payment"] is False
        assert action["would_create_escrow"] is False
        assert action["would_send_external_message"] is False


def test_exception_hash_changes_when_summary_changes():
    first = build_exception_recovery_preview(
        exception_type="provider_late",
        business_id="home_fixed",
        job_id="hf_job_001",
        summary="late by 10 minutes",
    )
    second = build_exception_recovery_preview(
        exception_type="provider_late",
        business_id="home_fixed",
        job_id="hf_job_001",
        summary="late by 60 minutes",
    )

    assert first["exception"]["exception_hash"] != second["exception"]["exception_hash"]


def test_exception_state_for_machine_trace_is_compact_and_hashed():
    out = _preview("approval_delayed")
    state = build_exception_state_for_machine_trace(out)

    assert state["contract_version"] == EXCEPTION_CONTRACT_VERSION
    assert state["status"] == "preview_ready"
    assert state["exception_type"] == "approval_delayed"
    assert state["business_id"] == "home_fixed"
    assert state["job_id"] == "hf_job_001"
    assert state["autonomous_execution_allowed"] is False
    assert isinstance(state["machine_trace_exception_hash"], str)
    assert len(state["machine_trace_exception_hash"]) == 64


def test_home_fixed_example_preview_uses_home_repair_vertical():
    out = example_home_fixed_exception_preview()

    assert out["ok"] is True
    assert out["exception"]["business_id"] == "home_fixed"
    assert out["exception"]["metadata"]["vertical_key"] == "home_repair"
