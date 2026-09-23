from backend.modules.aion.goal_engine.contracts import (
    ExperimentNodeContract,
    GoalNodeContract,
    LoopNodeContract,
    OutcomeEvaluationContract,
)
from backend.modules.aion.goal_engine.preview_bundle import build_goal_engine_preview_bundle


def test_preview_bundle_exposes_goal_runtime_summary_section():
    bundle = build_goal_engine_preview_bundle(
        run_id="run_goal_summary_001",
        workflow_id="workflow_goal_summary",
        contracts=[
            GoalNodeContract(
                goal_id="goal_leads_001",
                goal_name="Generate qualified leads",
                target_metric="qualified_lead_count",
                target_value=10,
                max_iterations=5,
                approval_policy="dry_run_only",
            ),
            ExperimentNodeContract(
                experiment_id="exp_channel_001",
                goal_id="goal_leads_001",
                variants=["variant_whatsapp", "variant_email"],
                metric="reply_count",
            ),
            LoopNodeContract(
                loop_id="loop_followup_001",
                goal_id="goal_leads_001",
                loop_mode="fixed_count",
                max_iterations=3,
                max_external_writes=0,
            ),
            OutcomeEvaluationContract(
                outcome_id="outcome_001",
                goal_id="goal_leads_001",
                run_id="run_goal_summary_001",
                status="unknown",
                metric_actual=0,
                metric_target=10,
                evidence=[],
                reason="No evidence has been attached yet.",
            ),
        ],
    )

    payload = bundle.to_dict()

    assert "goal_runtime_summary" in payload
    summary = payload["goal_runtime_summary"]

    assert summary["runtime"] == "aion_goal_engine"
    assert summary["dry_run_only"] is True
    assert summary["would_execute"] is False
    assert summary["would_write_external"] is False
    assert summary["would_grant_permission"] is False

    assert summary["goal_count"] == 1
    assert summary["experiment_count"] == 1
    assert summary["loop_count"] == 1
    assert summary["outcome_evaluation_count"] == 1

    assert summary["active_goal_ids"] == ["goal_leads_001"]
    assert summary["experiment_ids"] == ["exp_channel_001"]
    assert summary["loop_ids"] == ["loop_followup_001"]
    assert summary["outcome_ids"] == ["outcome_001"]


def test_goal_runtime_summary_marks_missing_evidence_as_not_successful():
    bundle = build_goal_engine_preview_bundle(
        run_id="run_missing_evidence_001",
        workflow_id="workflow_missing_evidence",
        contracts=[
            GoalNodeContract(
                goal_id="goal_leads_001",
                goal_name="Generate qualified leads",
                target_metric="qualified_lead_count",
                target_value=10,
            ),
            OutcomeEvaluationContract(
                outcome_id="outcome_001",
                goal_id="goal_leads_001",
                run_id="run_missing_evidence_001",
                status="success",
                quality_score=1.0,
                metric_actual=10,
                metric_target=10,
                confidence=0.9,
                evidence=[],
                reason="Claimed success but no evidence attached.",
            ),
        ],
    )

    summary = bundle.to_dict()["goal_runtime_summary"]

    assert summary["has_outcome_evidence"] is False
    assert summary["evidence_required_for_success"] is True
    assert summary["successful_outcome_count"] == 0
    assert "outcome_success_requires_evidence" in summary["blocked_reasons"]


def test_goal_runtime_summary_tracks_bounded_loop_state():
    bundle = build_goal_engine_preview_bundle(
        run_id="run_loop_bounds_001",
        workflow_id="workflow_loop_bounds",
        contracts=[
            LoopNodeContract(
                loop_id="loop_followup_001",
                goal_id="goal_leads_001",
                loop_mode="fixed_count",
                max_iterations=3,
                max_runtime_minutes=60,
                max_external_writes=0,
                requires_human_approval=True,
            ),
        ],
    )

    summary = bundle.to_dict()["goal_runtime_summary"]

    assert summary["loop_count"] == 1
    assert summary["bounded_loop_count"] == 1
    assert summary["unbounded_loop_count"] == 0
    assert summary["max_total_iterations"] == 3
    assert summary["max_total_external_writes"] == 0
    assert summary["human_approval_required"] is True


def test_goal_runtime_summary_tracks_experiment_exploration_policy():
    bundle = build_goal_engine_preview_bundle(
        run_id="run_experiment_policy_001",
        workflow_id="workflow_experiment_policy",
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
            ),
        ],
    )

    summary = bundle.to_dict()["goal_runtime_summary"]

    assert summary["experiment_count"] == 1
    assert summary["variant_count"] == 2
    assert summary["min_exploration_floor"] == 0.05
    assert summary["max_exploration_factor"] == 0.2
    assert summary["max_confidence_threshold"] == 0.95
    assert summary["premature_convergence_blocked"] is True
