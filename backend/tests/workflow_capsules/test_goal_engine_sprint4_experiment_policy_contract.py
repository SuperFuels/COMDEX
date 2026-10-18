from backend.modules.aion.goal_engine.experiment_policy import (
    EXPERIMENT_POLICY_SCHEMA_VERSION,
    ExperimentPolicyContract,
    build_experiment_policy_preview,
)


def test_experiment_policy_schema_version_is_locked():
    assert EXPERIMENT_POLICY_SCHEMA_VERSION == "aion.goal_engine.experiment_policy.v1"


def test_experiment_policy_requires_bounded_variants_and_metric():
    contract = ExperimentPolicyContract(
        experiment_id="exp_missing_bounds_001",
        goal_id="goal_leads_001",
        variants=[],
        metric="",
        max_iterations=0,
        max_runtime_minutes=0,
    )

    preview = build_experiment_policy_preview(contract)

    assert preview["schema_version"] == EXPERIMENT_POLICY_SCHEMA_VERSION
    assert preview["valid"] is False
    assert preview["bounded"] is False
    assert preview["experiment_id"] == "exp_missing_bounds_001"
    assert "variants_required" in preview["blocked_reasons"]
    assert "metric_required" in preview["blocked_reasons"]
    assert "max_iterations_required" in preview["blocked_reasons"]
    assert "max_runtime_minutes_required" in preview["blocked_reasons"]


def test_experiment_policy_blocks_unbounded_experiment_plan():
    contract = ExperimentPolicyContract(
        experiment_id="exp_unbounded_001",
        goal_id="goal_leads_001",
        variants=["variant_whatsapp", "variant_email"],
        metric="reply_count",
        max_iterations=0,
        max_runtime_minutes=0,
        exploration_factor=0.3,
        exploration_decay=0.98,
        min_exploration_floor=0.05,
        confidence_threshold=0.95,
    )

    preview = build_experiment_policy_preview(contract)

    assert preview["valid"] is False
    assert preview["bounded"] is False
    assert preview["variant_count"] == 2
    assert preview["metric"] == "reply_count"
    assert "unbounded_experiment_plan_blocked" in preview["blocked_reasons"]


def test_experiment_policy_accepts_bounded_experiment_plan():
    contract = ExperimentPolicyContract(
        experiment_id="exp_bounded_001",
        goal_id="goal_leads_001",
        variants=["variant_whatsapp", "variant_email"],
        metric="reply_count",
        max_iterations=10,
        max_runtime_minutes=120,
        exploration_factor=0.3,
        exploration_decay=0.98,
        min_exploration_floor=0.05,
        confidence_threshold=0.95,
    )

    preview = build_experiment_policy_preview(contract)

    assert preview["valid"] is True
    assert preview["bounded"] is True
    assert preview["variant_count"] == 2
    assert preview["max_iterations"] == 10
    assert preview["max_runtime_minutes"] == 120
    assert preview["premature_convergence_blocked"] is True
    assert preview["dry_run_only"] is True
    assert preview["would_execute"] is False
    assert preview["would_write_external"] is False
    assert preview["would_grant_permission"] is False


def test_experiment_policy_blocks_invalid_exploration_bounds():
    contract = ExperimentPolicyContract(
        experiment_id="exp_bad_policy_001",
        goal_id="goal_leads_001",
        variants=["variant_whatsapp", "variant_email"],
        metric="reply_count",
        max_iterations=10,
        max_runtime_minutes=120,
        exploration_factor=1.5,
        exploration_decay=1.2,
        min_exploration_floor=-0.1,
        confidence_threshold=1.5,
    )

    preview = build_experiment_policy_preview(contract)

    assert preview["valid"] is False
    assert "exploration_factor_out_of_range" in preview["blocked_reasons"]
    assert "exploration_decay_out_of_range" in preview["blocked_reasons"]
    assert "min_exploration_floor_out_of_range" in preview["blocked_reasons"]
    assert "confidence_threshold_out_of_range" in preview["blocked_reasons"]
