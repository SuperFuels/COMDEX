import pytest

from backend.services.aion_mission_mode.approval_lattice import (
    apply_lattice_to_plan_steps,
    compare_control_modes,
    control_rank,
    resolve_effective_decision,
    strictness_sequence,
    supremum_control_mode,
    validate_control_mode,
)


def test_phase20n4_strictness_sequence_is_ordered() -> None:
    assert strictness_sequence() == [
        "autonomous",
        "human_approval_required",
        "human_task_required",
        "blocked",
    ]


def test_phase20n4_control_rank_order() -> None:
    assert control_rank("autonomous") < control_rank("human_approval_required")
    assert control_rank("human_approval_required") < control_rank("human_task_required")
    assert control_rank("human_task_required") < control_rank("blocked")


def test_phase20n4_unknown_control_mode_rejected() -> None:
    with pytest.raises(ValueError):
        validate_control_mode("god_mode")


def test_phase20n4_supremum_keeps_stricter_system_decision() -> None:
    assert supremum_control_mode("human_approval_required", "autonomous") == "human_approval_required"


def test_phase20n4_supremum_applies_stricter_user_decision() -> None:
    assert supremum_control_mode("autonomous", "blocked") == "blocked"


def test_phase20n4_safe_step_can_be_upgraded_to_approval() -> None:
    result = resolve_effective_decision(
        step_id="draft_copy",
        system_decision="autonomous",
        user_override="human_approval_required",
    )

    assert result["effective_decision"] == "human_approval_required"
    assert result["stricter_override"] is True
    assert result["policy_override_violation"] is False
    assert result["runtime_mount_allowed"] is True


def test_phase20n4_approval_step_cannot_be_downgraded_to_autonomous() -> None:
    result = resolve_effective_decision(
        step_id="buy_domain",
        system_decision="human_approval_required",
        user_override="autonomous",
    )

    assert result["effective_decision"] == "human_approval_required"
    assert result["policy_override_violation"] is True
    assert result["runtime_mount_allowed"] is False
    assert result["fail_closed"] is True
    assert result["reason"] == "policy_override_violation"


def test_phase20n4_blocked_system_step_cannot_be_unblocked() -> None:
    result = resolve_effective_decision(
        step_id="illegal_step",
        system_decision="blocked",
        user_override="autonomous",
    )

    assert result["effective_decision"] == "blocked"
    assert result["policy_override_violation"] is True
    assert result["runtime_mount_allowed"] is False


def test_phase20n4_no_user_override_preserves_system_decision() -> None:
    result = resolve_effective_decision(
        step_id="draft_copy",
        system_decision="autonomous",
        user_override=None,
    )

    assert result["effective_decision"] == "autonomous"
    assert result["user_override_present"] is False
    assert result["reason"] == "system_decision_preserved"


def test_phase20n4_equal_override_is_allowed() -> None:
    result = resolve_effective_decision(
        step_id="deploy",
        system_decision="human_approval_required",
        user_override="human_approval_required",
    )

    assert result["effective_decision"] == "human_approval_required"
    assert result["policy_override_violation"] is False
    assert result["reason"] == "equal_override"


def test_phase20n4_resolution_hash_is_deterministic() -> None:
    first = resolve_effective_decision(
        step_id="buy_domain",
        system_decision="human_approval_required",
        user_override="autonomous",
    )
    second = resolve_effective_decision(
        step_id="buy_domain",
        system_decision="human_approval_required",
        user_override="autonomous",
    )

    assert first["lattice_resolution_hash"] == second["lattice_resolution_hash"]


def test_phase20n4_compare_control_modes() -> None:
    result = compare_control_modes("autonomous", "blocked")

    assert result["relation"] == "less_strict"
    assert result["comparison_hash"].startswith("sha256:")


def test_phase20n4_plan_lattice_blocks_any_downgrade_violation() -> None:
    steps = [
        {
            "step_id": "draft_copy",
            "system_decision": "autonomous",
            "user_override": "human_approval_required",
        },
        {
            "step_id": "buy_domain",
            "system_decision": "human_approval_required",
            "user_override": "autonomous",
        },
    ]

    result = apply_lattice_to_plan_steps(
        mission_id="mission_001",
        mission_run_id="run_001",
        plan_id="plan_001",
        steps=steps,
    )

    assert result["resolution_count"] == 2
    assert result["policy_override_violation_count"] == 1
    assert result["runtime_mount_allowed"] is False
    assert result["fail_closed"] is True
    assert result["plan_lattice_hash"].startswith("sha256:")


def test_phase20n4_plan_lattice_allows_stricter_overrides() -> None:
    steps = [
        {
            "step_id": "draft_copy",
            "system_decision": "autonomous",
            "user_override": "human_approval_required",
        },
        {
            "step_id": "draft_posts",
            "system_decision": "autonomous",
            "user_override": "blocked",
        },
    ]

    result = apply_lattice_to_plan_steps(
        mission_id="mission_001",
        mission_run_id="run_001",
        plan_id="plan_001",
        steps=steps,
    )

    assert result["policy_override_violation_count"] == 0
    assert result["runtime_mount_allowed"] is True
    assert result["resolutions"][0]["effective_decision"] == "human_approval_required"
    assert result["resolutions"][1]["effective_decision"] == "blocked"


def test_phase20n4_plan_lattice_hash_is_deterministic() -> None:
    steps = [
        {
            "step_id": "draft_copy",
            "system_decision": "autonomous",
            "user_override": "human_approval_required",
        },
    ]

    first = apply_lattice_to_plan_steps(
        mission_id="mission_001",
        mission_run_id="run_001",
        plan_id="plan_001",
        steps=steps,
    )
    second = apply_lattice_to_plan_steps(
        mission_id="mission_001",
        mission_run_id="run_001",
        plan_id="plan_001",
        steps=steps,
    )

    assert first["plan_lattice_hash"] == second["plan_lattice_hash"]
