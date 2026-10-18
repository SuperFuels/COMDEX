from backend.modules.aion.goal_engine.experiment_policy import ExperimentPolicyContract
from backend.modules.aion.goal_engine.preview_bundle import build_goal_engine_preview_bundle


def test_preview_bundle_exposes_experiment_runtime_summary():
    bundle = build_goal_engine_preview_bundle(
        run_id="run_experiment_summary_001",
        workflow_id="workflow_experiment_summary",
        contracts=[
            ExperimentPolicyContract(
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
            ),
        ],
    )

    payload = bundle.to_dict()

    assert "experiment_runtime_summary" in payload
    summary = payload["experiment_runtime_summary"]

    assert summary["trace_type"] == "experiment_runtime_summary"
    assert summary["experiment_count"] == 1
    assert summary["bounded_experiment_count"] == 1
    assert summary["unbounded_experiment_count"] == 0
    assert summary["variant_count"] == 2
    assert summary["metric_count"] == 1
    assert summary["premature_convergence_blocked"] is True
    assert summary["dry_run_only"] is True
    assert summary["would_execute"] is False
    assert summary["would_write_external"] is False
    assert summary["would_grant_permission"] is False


def test_preview_bundle_experiment_summary_blocks_unbounded_experiments():
    bundle = build_goal_engine_preview_bundle(
        run_id="run_experiment_summary_unbounded_001",
        workflow_id="workflow_experiment_summary_unbounded",
        contracts=[
            ExperimentPolicyContract(
                experiment_id="exp_unbounded_001",
                goal_id="goal_leads_001",
                variants=["variant_whatsapp", "variant_email"],
                metric="reply_count",
                max_iterations=0,
                max_runtime_minutes=0,
            ),
        ],
    )

    summary = bundle.to_dict()["experiment_runtime_summary"]

    assert summary["experiment_count"] == 1
    assert summary["bounded_experiment_count"] == 0
    assert summary["unbounded_experiment_count"] == 1
    assert "unbounded_experiment_plan_blocked" in summary["blocked_reasons"]


def test_preview_bundle_experiment_summary_preserves_policy_previews():
    bundle = build_goal_engine_preview_bundle(
        run_id="run_experiment_previews_001",
        workflow_id="workflow_experiment_previews",
        contracts=[
            ExperimentPolicyContract(
                experiment_id="exp_policy_001",
                goal_id="goal_leads_001",
                variants=["variant_a", "variant_b"],
                metric="reply_count",
                max_iterations=5,
                max_runtime_minutes=60,
                exploration_factor=0.25,
                exploration_decay=0.97,
                min_exploration_floor=0.04,
                confidence_threshold=0.9,
            ),
        ],
    )

    summary = bundle.to_dict()["experiment_runtime_summary"]

    assert "experiment_policy_previews" in summary
    assert len(summary["experiment_policy_previews"]) == 1

    preview = summary["experiment_policy_previews"][0]
    assert preview["experiment_id"] == "exp_policy_001"
    assert preview["exploration_factor"] == 0.25
    assert preview["exploration_decay"] == 0.97
    assert preview["min_exploration_floor"] == 0.04
    assert preview["confidence_threshold"] == 0.9
