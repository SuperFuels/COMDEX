import pytest

from backend.services.aion_mission_mode.autonomy_budget import (
    action_requires_approval_under_budget,
    create_usage_snapshot,
    default_autonomy_budget,
    evaluate_budget,
    trust_ladder_policy,
    update_usage_after_event,
    validate_trust_level,
)


def test_phase20n6_trust_levels_validate() -> None:
    assert validate_trust_level("trust_0") == "trust_0"
    assert validate_trust_level("trust_4") == "trust_4"


def test_phase20n6_unknown_trust_level_rejected() -> None:
    with pytest.raises(ValueError):
        validate_trust_level("trust_99")


def test_phase20n6_default_budget_has_zero_unapproved_side_effects() -> None:
    budget = default_autonomy_budget(
        mission_id="mission_001",
        mission_run_id="run_001",
        trust_level="trust_4",
    )

    assert budget["max_spend_without_payload_approval"] == 0
    assert budget["max_public_posts_without_approval"] == 0
    assert budget["max_production_deployments_without_approval"] == 0
    assert budget["max_live_customer_messages_without_approval"] == 0


def test_phase20n6_budget_hash_is_deterministic() -> None:
    first = default_autonomy_budget(mission_id="mission_001", mission_run_id="run_001")
    second = default_autonomy_budget(mission_id="mission_001", mission_run_id="run_001")
    assert first["budget_hash"] == second["budget_hash"]


def test_phase20n6_usage_hash_is_deterministic() -> None:
    first = create_usage_snapshot(mission_id="mission_001", mission_run_id="run_001", external_reads_used=1)
    second = create_usage_snapshot(mission_id="mission_001", mission_run_id="run_001", external_reads_used=1)
    assert first["usage_hash"] == second["usage_hash"]


def test_phase20n6_budget_allows_within_caps() -> None:
    budget = default_autonomy_budget(
        mission_id="mission_001",
        mission_run_id="run_001",
        trust_level="trust_2",
    )
    usage = create_usage_snapshot(
        mission_id="mission_001",
        mission_run_id="run_001",
        external_reads_used=10,
        browser_sessions_used=1,
        runtime_minutes_used=20,
        safe_steps_since_review=10,
        total_steps=20,
    )

    result = evaluate_budget(budget=budget, usage=usage)

    assert result["allowed"] is True
    assert result["mission_state"] == "running_autonomous_steps"
    assert result["violation_count"] == 0


def test_phase20n6_budget_exceeded_pauses_mission() -> None:
    budget = default_autonomy_budget(
        mission_id="mission_001",
        mission_run_id="run_001",
        trust_level="trust_1",
    )
    usage = create_usage_snapshot(
        mission_id="mission_001",
        mission_run_id="run_001",
        external_reads_used=11,
    )

    result = evaluate_budget(budget=budget, usage=usage)

    assert result["allowed"] is False
    assert result["mission_state"] == "waiting_human_review"
    assert result["violations"][0]["metric"] == "external_reads"


def test_phase20n6_unapproved_spend_always_violates_default_budget() -> None:
    budget = default_autonomy_budget(
        mission_id="mission_001",
        mission_run_id="run_001",
        trust_level="trust_4",
    )
    usage = create_usage_snapshot(
        mission_id="mission_001",
        mission_run_id="run_001",
        spend_without_payload_approval=0.01,
    )

    result = evaluate_budget(budget=budget, usage=usage)

    assert result["allowed"] is False
    assert result["violations"][0]["metric"] == "spend_without_payload_approval"


def test_phase20n6_unapproved_public_post_always_violates() -> None:
    budget = default_autonomy_budget(mission_id="mission_001", mission_run_id="run_001", trust_level="trust_4")
    usage = create_usage_snapshot(mission_id="mission_001", mission_run_id="run_001", public_posts_without_approval=1)

    result = evaluate_budget(budget=budget, usage=usage)

    assert result["allowed"] is False
    assert result["violations"][0]["metric"] == "public_posts_without_approval"


def test_phase20n6_unapproved_production_deploy_always_violates() -> None:
    budget = default_autonomy_budget(mission_id="mission_001", mission_run_id="run_001", trust_level="trust_4")
    usage = create_usage_snapshot(
        mission_id="mission_001",
        mission_run_id="run_001",
        production_deployments_without_approval=1,
    )

    result = evaluate_budget(budget=budget, usage=usage)

    assert result["allowed"] is False
    assert result["violations"][0]["metric"] == "production_deployments_without_approval"


def test_phase20n6_trust_ladder_unlocks_read_then_preview() -> None:
    trust_0 = trust_ladder_policy("trust_0")
    trust_2 = trust_ladder_policy("trust_2")

    assert trust_0["read_only_external_allowed"] is False
    assert trust_2["read_only_external_allowed"] is True
    assert trust_2["preview_deploys_allowed"] is True


def test_phase20n6_trust_ladder_never_removes_always_approval() -> None:
    for level in ["trust_0", "trust_1", "trust_2", "trust_3", "trust_4"]:
        policy = trust_ladder_policy(level)
        assert policy["always_approval_actions_remain_approval_required"] is True


def test_phase20n6_always_approval_actions_remain_required() -> None:
    result = action_requires_approval_under_budget(
        action_type="buy_domain",
        trust_level="trust_4",
    )

    assert result["approval_required"] is True
    assert result["reason"] == "always_approval_action"


def test_phase20n6_non_forced_action_not_forced_by_budget_layer() -> None:
    result = action_requires_approval_under_budget(
        action_type="draft_copy",
        trust_level="trust_0",
    )

    assert result["approval_required"] is False
    assert result["reason"] == "not_forced_by_budget_layer"


def test_phase20n6_update_usage_after_external_read() -> None:
    usage = create_usage_snapshot(mission_id="mission_001", mission_run_id="run_001")
    updated = update_usage_after_event(usage=usage, event_type="external_read", amount=3)

    assert updated["external_reads_used"] == 3
    assert updated["usage_hash"] != usage["usage_hash"]


def test_phase20n6_update_usage_after_runtime_minutes_is_rounded() -> None:
    usage = create_usage_snapshot(mission_id="mission_001", mission_run_id="run_001", runtime_minutes_used=1.111)
    updated = update_usage_after_event(usage=usage, event_type="runtime_minutes", amount=2.222)

    assert updated["runtime_minutes_used"] == 3.33


def test_phase20n6_unknown_usage_event_rejected() -> None:
    usage = create_usage_snapshot(mission_id="mission_001", mission_run_id="run_001")

    with pytest.raises(ValueError):
        update_usage_after_event(usage=usage, event_type="unknown_event")


def test_phase20n6_evaluation_hash_is_deterministic() -> None:
    budget = default_autonomy_budget(mission_id="mission_001", mission_run_id="run_001", trust_level="trust_2")
    usage = create_usage_snapshot(mission_id="mission_001", mission_run_id="run_001", external_reads_used=1)

    first = evaluate_budget(budget=budget, usage=usage)
    second = evaluate_budget(budget=budget, usage=usage)

    assert first["evaluation_hash"] == second["evaluation_hash"]
