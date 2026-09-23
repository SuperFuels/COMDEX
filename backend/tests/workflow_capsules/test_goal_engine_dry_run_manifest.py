import pytest

from backend.modules.aion.goal_engine.contracts import (
    ExperimentNodeContract,
    GoalNodeContract,
    LoopNodeContract,
    OutcomeEvaluationContract,
    ReflectionLearningContract,
)
from backend.modules.aion.goal_engine.dry_run import build_goal_engine_dry_run_manifest


def test_dry_run_manifest_is_safe_by_default():
    manifest = build_goal_engine_dry_run_manifest(
        run_id="run_001",
        workflow_id="workflow_001",
        contracts=[
            GoalNodeContract(
                goal_id="goal_001",
                goal_name="Generate leads",
                target_metric="lead_count",
                target_value=50,
            ),
        ],
    )

    assert manifest["manifest_type"] == "aion_goal_engine_dry_run"
    assert manifest["dry_run_only"] is True
    assert manifest["would_execute"] is False
    assert manifest["would_write_external"] is False
    assert manifest["would_mutate_learning_memory"] is False
    assert manifest["would_grant_permission"] is False
    assert manifest["requires_approval_before_live_write"] is True
    assert manifest["valid"] is True


def test_dry_run_manifest_serializes_goal_experiment_loop_outcome_reflection():
    manifest = build_goal_engine_dry_run_manifest(
        run_id="run_002",
        workflow_id="workflow_002",
        contracts=[
            GoalNodeContract(
                goal_id="goal_001",
                goal_name="Generate leads",
                target_metric="lead_count",
                target_value=50,
            ),
            ExperimentNodeContract(
                experiment_id="exp_001",
                goal_id="goal_001",
                variants=["variant_a", "variant_b"],
                metric="lead_count",
                exploration_factor=0.15,
                exploration_decay=0.98,
                min_exploration_floor=0.05,
            ),
            LoopNodeContract(
                loop_id="loop_001",
                loop_mode="until_goal_achieved",
                max_iterations=10,
                max_runtime_minutes=60,
            ),
            OutcomeEvaluationContract(
                outcome_id="outcome_001",
                goal_id="goal_001",
                run_id="run_001",
                status="success",
                quality_score=0.82,
                metric_actual=14,
                metric_target=50,
                cost=12.50,
                time_to_result_seconds=7200,
                confidence=0.95,
                reason="Manual confirmation",
                evidence=["manual_review"],
            ),
            ReflectionLearningContract(
                reflection_id="reflect_001",
                source_run_id="run_002",
                source_workflow_id="workflow_002",
                allow_learn=True,
                adr_active=False,
            ),
        ],
    )

    assert manifest["step_count"] == 5
    assert [step["step_type"] for step in manifest["steps"]] == [
        "goal",
        "experiment",
        "loop",
        "outcome_evaluation",
        "reflect_learn",
    ]

    for step in manifest["steps"]:
        assert step["dry_run_only"] is True
        assert step["would_execute"] is False
        assert step["would_write_external"] is False
        assert step["would_grant_permission"] is False


def test_dry_run_manifest_collects_validation_errors():
    manifest = build_goal_engine_dry_run_manifest(
        run_id="run_bad",
        workflow_id="workflow_bad",
        contracts=[
            LoopNodeContract(
                loop_id="loop_bad",
                loop_mode="until_goal_achieved",
                max_iterations=0,
                max_runtime_minutes=0,
            ),
        ],
    )

    assert manifest["valid"] is False
    assert "max_iterations must be at least 1" in manifest["validation_errors"]
    assert "max_runtime_minutes must be at least 1" in manifest["validation_errors"]
    assert "goal_id is required for goal-aware loop modes" in manifest["validation_errors"]


def test_dry_run_manifest_requires_run_and_workflow_id():
    with pytest.raises(ValueError):
        build_goal_engine_dry_run_manifest(
            run_id="",
            workflow_id="workflow_001",
            contracts=[],
        )

    with pytest.raises(ValueError):
        build_goal_engine_dry_run_manifest(
            run_id="run_001",
            workflow_id="",
            contracts=[],
        )


def test_dry_run_manifest_rejects_non_contract_objects():
    with pytest.raises(TypeError):
        build_goal_engine_dry_run_manifest(
            run_id="run_001",
            workflow_id="workflow_001",
            contracts=[{"not": "a contract"}],
        )
