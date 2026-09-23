import pytest

from backend.services.aion_mission_mode.matrix_expiry_revocation import (
    assert_matrix_can_mount,
    create_matrix_freshness_record,
    create_stale_matrix_notice,
    evaluate_matrix_freshness,
    revoke_matrix_record,
    validate_matrix_type,
)


def test_phase20n7_valid_matrix_types() -> None:
    assert validate_matrix_type("mission_plan_matrix") == "mission_plan_matrix"
    assert validate_matrix_type("subplan_matrix") == "subplan_matrix"
    assert validate_matrix_type("profile_application") == "profile_application"
    assert validate_matrix_type("budget_contract") == "budget_contract"


def test_phase20n7_unknown_matrix_type_rejected() -> None:
    with pytest.raises(ValueError):
        validate_matrix_type("payload_approval")


def test_phase20n7_freshness_record_hash_is_deterministic() -> None:
    kwargs = dict(
        mission_id="mission_001",
        mission_run_id="run_001",
        matrix_id="matrix_001",
        matrix_type="mission_plan_matrix",
        matrix_hash="sha256:matrix",
        issued_at=100,
    )

    first = create_matrix_freshness_record(**kwargs)
    second = create_matrix_freshness_record(**kwargs)

    assert first["freshness_record_hash"] == second["freshness_record_hash"]


def test_phase20n7_default_ttl_sets_expiry() -> None:
    record = create_matrix_freshness_record(
        mission_id="mission_001",
        mission_run_id="run_001",
        matrix_id="matrix_001",
        matrix_type="subplan_matrix",
        matrix_hash="sha256:matrix",
        issued_at=100,
    )

    assert record["ttl_seconds"] == 1800
    assert record["expires_at"] == 1900


def test_phase20n7_fresh_matrix_can_continue() -> None:
    record = create_matrix_freshness_record(
        mission_id="mission_001",
        mission_run_id="run_001",
        matrix_id="matrix_001",
        matrix_type="mission_plan_matrix",
        matrix_hash="sha256:matrix",
        issued_at=100,
        ttl_seconds=100,
    )

    result = evaluate_matrix_freshness(
        record=record,
        evaluation_time=150,
        current_matrix_hash="sha256:matrix",
    )

    assert result["stale"] is False
    assert result["runtime_mount_allowed"] is True
    assert result["mission_state"] == "running_autonomous_steps"


def test_phase20n7_expired_matrix_requires_reapproval() -> None:
    record = create_matrix_freshness_record(
        mission_id="mission_001",
        mission_run_id="run_001",
        matrix_id="matrix_001",
        matrix_type="mission_plan_matrix",
        matrix_hash="sha256:matrix",
        issued_at=100,
        ttl_seconds=100,
    )

    result = evaluate_matrix_freshness(
        record=record,
        evaluation_time=201,
        current_matrix_hash="sha256:matrix",
    )

    assert result["expired"] is True
    assert result["stale"] is True
    assert result["runtime_mount_allowed"] is False
    assert result["mission_state"] == "waiting_human_review"
    assert "matrix_expired" in result["reasons"]


def test_phase20n7_matrix_hash_change_requires_reapproval() -> None:
    record = create_matrix_freshness_record(
        mission_id="mission_001",
        mission_run_id="run_001",
        matrix_id="matrix_001",
        matrix_type="mission_plan_matrix",
        matrix_hash="sha256:old",
        issued_at=100,
        ttl_seconds=100,
    )

    result = evaluate_matrix_freshness(
        record=record,
        evaluation_time=150,
        current_matrix_hash="sha256:new",
    )

    assert result["matrix_changed"] is True
    assert result["requires_matrix_reapproval"] is True
    assert "matrix_hash_changed" in result["reasons"]


def test_phase20n7_parent_hash_change_makes_subplan_stale() -> None:
    record = create_matrix_freshness_record(
        mission_id="mission_001",
        mission_run_id="run_001",
        matrix_id="subplan_001",
        matrix_type="subplan_matrix",
        matrix_hash="sha256:subplan",
        parent_matrix_hash="sha256:parent_old",
        issued_at=100,
        ttl_seconds=100,
    )

    result = evaluate_matrix_freshness(
        record=record,
        evaluation_time=150,
        current_matrix_hash="sha256:subplan",
        current_parent_matrix_hash="sha256:parent_new",
    )

    assert result["parent_changed"] is True
    assert result["stale"] is True
    assert "parent_matrix_hash_changed" in result["reasons"]


def test_phase20n7_profile_hash_change_makes_matrix_stale() -> None:
    record = create_matrix_freshness_record(
        mission_id="mission_001",
        mission_run_id="run_001",
        matrix_id="matrix_001",
        matrix_type="mission_plan_matrix",
        matrix_hash="sha256:matrix",
        profile_application_hash="sha256:profile_old",
        issued_at=100,
        ttl_seconds=100,
    )

    result = evaluate_matrix_freshness(
        record=record,
        evaluation_time=150,
        current_matrix_hash="sha256:matrix",
        current_profile_application_hash="sha256:profile_new",
    )

    assert result["profile_changed"] is True
    assert result["stale"] is True


def test_phase20n7_budget_hash_change_makes_matrix_stale() -> None:
    record = create_matrix_freshness_record(
        mission_id="mission_001",
        mission_run_id="run_001",
        matrix_id="matrix_001",
        matrix_type="mission_plan_matrix",
        matrix_hash="sha256:matrix",
        budget_hash="sha256:budget_old",
        issued_at=100,
        ttl_seconds=100,
    )

    result = evaluate_matrix_freshness(
        record=record,
        evaluation_time=150,
        current_matrix_hash="sha256:matrix",
        current_budget_hash="sha256:budget_new",
    )

    assert result["budget_changed"] is True
    assert result["stale"] is True


def test_phase20n7_revoked_matrix_requires_reapproval() -> None:
    record = create_matrix_freshness_record(
        mission_id="mission_001",
        mission_run_id="run_001",
        matrix_id="matrix_001",
        matrix_type="mission_plan_matrix",
        matrix_hash="sha256:matrix",
        issued_at=100,
    )
    revoked = revoke_matrix_record(
        record=record,
        revoked_by="operator",
        revocation_reason="operator_revoked_matrix",
        revoked_at=150,
    )

    result = evaluate_matrix_freshness(
        record=revoked,
        evaluation_time=160,
        current_matrix_hash="sha256:matrix",
    )

    assert result["revoked"] is True
    assert result["stale"] is True
    assert "operator_revoked_matrix" in result["reasons"]


def test_phase20n7_stale_notice_for_expired_matrix() -> None:
    record = create_matrix_freshness_record(
        mission_id="mission_001",
        mission_run_id="run_001",
        matrix_id="matrix_001",
        matrix_type="mission_plan_matrix",
        matrix_hash="sha256:matrix",
        issued_at=100,
        ttl_seconds=100,
    )
    evaluation = evaluate_matrix_freshness(
        record=record,
        evaluation_time=201,
        current_matrix_hash="sha256:matrix",
    )

    notice = create_stale_matrix_notice(evaluation=evaluation)

    assert notice["stale"] is True
    assert notice["requires_matrix_reapproval"] is True
    assert "stale" in notice["operator_message"].lower()
    assert notice["notice_hash"].startswith("sha256:")


def test_phase20n7_mount_assertion_blocks_stale_matrix() -> None:
    record = create_matrix_freshness_record(
        mission_id="mission_001",
        mission_run_id="run_001",
        matrix_id="matrix_001",
        matrix_type="mission_plan_matrix",
        matrix_hash="sha256:matrix",
        issued_at=100,
        ttl_seconds=100,
    )

    assertion = assert_matrix_can_mount(
        record=record,
        evaluation_time=201,
        current_matrix_hash="sha256:matrix",
    )

    assert assertion["runtime_mount_allowed"] is False
    assert assertion["requires_matrix_reapproval"] is True
    assert assertion["mission_state"] == "waiting_human_review"


def test_phase20n7_evaluation_hash_is_deterministic() -> None:
    record = create_matrix_freshness_record(
        mission_id="mission_001",
        mission_run_id="run_001",
        matrix_id="matrix_001",
        matrix_type="mission_plan_matrix",
        matrix_hash="sha256:matrix",
        issued_at=100,
        ttl_seconds=100,
    )

    first = evaluate_matrix_freshness(
        record=record,
        evaluation_time=150,
        current_matrix_hash="sha256:matrix",
    )
    second = evaluate_matrix_freshness(
        record=record,
        evaluation_time=150,
        current_matrix_hash="sha256:matrix",
    )

    assert first["freshness_evaluation_hash"] == second["freshness_evaluation_hash"]


def test_phase20n7_revocation_hash_changes() -> None:
    record = create_matrix_freshness_record(
        mission_id="mission_001",
        mission_run_id="run_001",
        matrix_id="matrix_001",
        matrix_type="mission_plan_matrix",
        matrix_hash="sha256:matrix",
        issued_at=100,
    )
    revoked = revoke_matrix_record(
        record=record,
        revoked_by="operator",
        revocation_reason="manual_review_required",
        revoked_at=120,
    )

    assert revoked["freshness_record_hash"] != record["freshness_record_hash"]
    assert revoked["revoked"] is True
