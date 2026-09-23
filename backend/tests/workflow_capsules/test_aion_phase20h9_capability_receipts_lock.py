from backend.services.aion_mission_mode.capability_receipts import (
    bind_receipt_to_mission_trace,
    create_capability_receipt,
    create_receipt_container_record,
    summarize_capability_receipts,
    validate_capability_receipt,
)


def _receipt(**kwargs):
    base = dict(
        mission_id="mission_001",
        mission_run_id="run_001",
        business_id="home_fixed",
        step_id="deploy_site",
        tool_name="deploy_to_vercel",
        provider="vercel",
        action_type="deploy_to_production",
        requested_payload_hash="sha256:requested",
        executed_payload_hash="sha256:executed",
        before_state_hash="sha256:before",
        after_state_hash="sha256:after",
        evidence_hashes=["sha256:screenshot", "sha256:build"],
        provider_response_hash="sha256:response",
        rollback_available=True,
        rollback_instructions="Revert deployment to previous build.",
        rollback_deadline="2026-06-08T20:00:00Z",
        external_reference_id="vercel_deploy_123",
    )
    base.update(kwargs)
    return create_capability_receipt(**base)


def test_phase20h9_receipt_hash_is_deterministic() -> None:
    assert _receipt()["receipt_hash"] == _receipt()["receipt_hash"]


def test_phase20h9_evidence_hashes_are_sorted() -> None:
    receipt = _receipt(evidence_hashes=["sha256:z", "sha256:a"])
    assert receipt["evidence_hashes"] == ["sha256:a", "sha256:z"]


def test_phase20h9_valid_receipt_passes_validation() -> None:
    result = validate_capability_receipt(_receipt())
    assert result["valid"] is True
    assert result["validation_state"] == "receipt_valid"


def test_phase20h9_missing_required_field_fails_validation() -> None:
    receipt = _receipt()
    receipt["provider"] = ""
    result = validate_capability_receipt(receipt)
    assert result["valid"] is False
    assert "missing_provider" in result["reasons"]


def test_phase20h9_invalid_hash_field_fails_validation() -> None:
    receipt = _receipt(requested_payload_hash="not-a-hash")
    result = validate_capability_receipt(receipt)
    assert result["valid"] is False
    assert "invalid_requested_payload_hash" in result["reasons"]


def test_phase20h9_invalid_evidence_hash_fails_validation() -> None:
    receipt = _receipt(evidence_hashes=["bad"])
    result = validate_capability_receipt(receipt)
    assert result["valid"] is False
    assert "invalid_evidence_hash" in result["reasons"]


def test_phase20h9_tampered_receipt_hash_fails_validation() -> None:
    receipt = _receipt()
    receipt["after_state_hash"] = "sha256:changed"
    result = validate_capability_receipt(receipt)
    assert result["valid"] is False
    assert "receipt_hash_mismatch" in result["reasons"]


def test_phase20h9_rollback_available_requires_instructions() -> None:
    receipt = _receipt(rollback_available=True, rollback_instructions="")
    result = validate_capability_receipt(receipt)
    assert result["valid"] is False
    assert "rollback_available_without_instructions" in result["reasons"]


def test_phase20h9_container_record_binds_business_container_path() -> None:
    record = create_receipt_container_record(
        receipt=_receipt(),
        business_container_root="/businesses/home_fixed",
    )
    assert record["business_id"] == "home_fixed"
    assert record["contained_path"].startswith("/businesses/home_fixed/missions/")
    assert record["container_record_hash"].startswith("sha256:")


def test_phase20h9_container_record_hash_is_deterministic() -> None:
    first = create_receipt_container_record(
        receipt=_receipt(),
        business_container_root="/businesses/home_fixed",
    )
    second = create_receipt_container_record(
        receipt=_receipt(),
        business_container_root="/businesses/home_fixed",
    )
    assert first["container_record_hash"] == second["container_record_hash"]


def test_phase20h9_receipt_trace_binding_allowed() -> None:
    binding = bind_receipt_to_mission_trace(
        receipt=_receipt(),
        trace_hash="sha256:trace",
        proof_hash="sha256:proof",
        replay_hash="sha256:replay",
    )
    assert binding["allowed"] is True
    assert binding["binding_state"] == "receipt_trace_bound"


def test_phase20h9_receipt_trace_binding_blocks_invalid_trace_hash() -> None:
    binding = bind_receipt_to_mission_trace(
        receipt=_receipt(),
        trace_hash="bad",
        proof_hash="sha256:proof",
        replay_hash="sha256:replay",
    )
    assert binding["allowed"] is False
    assert "invalid_trace_hash" in binding["reasons"]


def test_phase20h9_receipt_summary_counts_receipts_and_rollbacks() -> None:
    r1 = _receipt(step_id="deploy_site", rollback_available=True)
    r2 = _receipt(step_id="publish_post", action_type="publish_post", rollback_available=False)
    summary = summarize_capability_receipts(
        mission_id="mission_001",
        mission_run_id="run_001",
        receipts=[r1, r2],
    )
    assert summary["receipt_count"] == 2
    assert summary["rollback_available_count"] == 1
    assert summary["summary_state"] == "capability_receipts_indexed"


def test_phase20h9_receipt_summary_hash_is_deterministic() -> None:
    receipt = _receipt()
    first = summarize_capability_receipts(
        mission_id="mission_001",
        mission_run_id="run_001",
        receipts=[receipt],
    )
    second = summarize_capability_receipts(
        mission_id="mission_001",
        mission_run_id="run_001",
        receipts=[receipt],
    )
    assert first["summary_hash"] == second["summary_hash"]
