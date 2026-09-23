from backend.modules.aion.goal_engine.contracts import (
    ExperimentNodeContract,
    GoalNodeContract,
    LoopNodeContract,
    OutcomeEvaluationContract,
)
from backend.modules.aion.goal_engine.preview_bundle import build_goal_engine_preview_bundle


def test_goal_preview_contains_goal_runtime_semantics():
    bundle = build_goal_engine_preview_bundle(
        run_id="run_goal_sprint2_001",
        workflow_id="workflow_goal_sprint2",
        contracts=[
            GoalNodeContract(
                goal_id="goal_leads_001",
                goal_name="Generate qualified leads",
                target_metric="qualified_lead_count",
                target_value=10,
                max_iterations=5,
                approval_policy="dry_run_only",
            )
        ],
    )

    payload = bundle.to_dict()
    manifest = payload["manifest"]
    step = manifest["steps"][0]

    assert step["step_type"] == "goal"
    assert step["dry_run_only"] is True
    assert step["would_execute"] is False
    assert step["would_grant_permission"] is False

    contract = step["contract"]
    assert contract["goal_id"] == "goal_leads_001"
    assert contract["target_metric"] == "qualified_lead_count"
    assert contract["target_value"] == 10
    assert contract["max_iterations"] == 5


def test_experiment_preview_contains_variant_runtime_semantics():
    bundle = build_goal_engine_preview_bundle(
        run_id="run_exp_sprint2_001",
        workflow_id="workflow_exp_sprint2",
        contracts=[
            ExperimentNodeContract(
                experiment_id="exp_channel_001",
                goal_id="goal_leads_001",
                variants=["variant_whatsapp", "variant_email"],
                metric="reply_count",
                exploration_factor=0.2,
                exploration_decay=0.98,
                min_exploration_floor=0.05,
                confidence_threshold=0.95,
            )
        ],
    )

    payload = bundle.to_dict()
    step = payload["manifest"]["steps"][0]
    contract = step["contract"]

    assert step["step_type"] == "experiment"
    assert contract["variants"] == ["variant_whatsapp", "variant_email"]
    assert contract["metric"] == "reply_count"
    assert contract["exploration_factor"] == 0.2
    assert contract["min_exploration_floor"] == 0.05
    assert contract["confidence_threshold"] == 0.95


def test_loop_preview_contains_bound_runtime_semantics():
    bundle = build_goal_engine_preview_bundle(
        run_id="run_loop_sprint2_001",
        workflow_id="workflow_loop_sprint2",
        contracts=[
            LoopNodeContract(
                loop_id="loop_followup_001",
                goal_id="goal_leads_001",
                loop_mode="fixed_count",
                max_iterations=3,
                max_runtime_minutes=60,
                max_external_writes=0,
                requires_human_approval=True,
                state_delta_strategy="isolate_increments",
            )
        ],
    )

    payload = bundle.to_dict()
    step = payload["manifest"]["steps"][0]
    contract = step["contract"]

    assert step["step_type"] == "loop"
    assert contract["max_iterations"] == 3
    assert contract["max_runtime_minutes"] == 60
    assert contract["max_external_writes"] == 0
    assert contract["requires_human_approval"] is True
    assert contract["state_delta_strategy"] == "isolate_increments"


def test_outcome_preview_does_not_treat_completion_as_success_without_evidence():
    bundle = build_goal_engine_preview_bundle(
        run_id="run_outcome_sprint2_001",
        workflow_id="workflow_outcome_sprint2",
        contracts=[
            OutcomeEvaluationContract(
                outcome_id="outcome_001",
                goal_id="goal_leads_001",
                run_id="run_outcome_sprint2_001",
                status="unknown",
                quality_score=0.0,
                metric_actual=0,
                metric_target=10,
                confidence=0.0,
                evidence=[],
                reason="No evidence has been attached yet.",
            )
        ],
    )

    payload = bundle.to_dict()
    step = payload["manifest"]["steps"][0]
    contract = step["contract"]

    assert step["step_type"] == "outcome_evaluation"
    assert contract["status"] == "unknown"
    assert contract["quality_score"] == 0.0
    assert contract["metric_actual"] == 0
    assert contract["metric_target"] == 10
    assert contract["confidence"] == 0.0
    assert contract["evidence"] == []
    assert "No evidence" in contract["reason"]


def test_machine_trace_remains_a2a_deferred_during_sprint2():
    bundle = build_goal_engine_preview_bundle(
        run_id="run_machine_sprint2_001",
        workflow_id="workflow_machine_sprint2",
        contracts=[
            GoalNodeContract(
                goal_id="goal_machine_001",
                goal_name="Machine trace preview",
                target_metric="outcome_score",
                target_value=1,
            )
        ],
    )

    machine_trace = bundle.to_dict()["machine_trace"]

    assert machine_trace["agent_ready"] is False
    assert machine_trace["a2a_deferred"] is True
    assert machine_trace["commercial_interface_ready"] is False
    assert machine_trace["dry_run_only"] is True
