from backend.modules.aion.goal_engine.boardroom_trace import build_goal_engine_boardroom_trace
from backend.modules.workflow_capsules.execution.goal_engine_dry_run_bridge import (
    build_goal_engine_manifest_for_capsule,
    build_goal_engine_step_trace_rows,
)


def visibility_capsule():
    return {
        "canonical_key": "test.goal_engine.boardroom_visibility_preview_fields",
        "steps": [
            {
                "id": "goal_1",
                "title": "Grow local leads",
                "action_id": "goal_engine.goal",
                "config": {"metric_target": "10 enquiries"},
            },
            {
                "id": "experiment_1",
                "title": "A/B test offer",
                "action_id": "goal_engine.experiment",
                "config": {
                    "variants": ["A", "B"],
                    "metric": "reply_rate",
                    "winner_policy": "manual",
                },
            },
            {
                "id": "loop_1",
                "title": "Bounded improvement loop",
                "action_id": "goal_engine.loop",
                "config": {
                    "max_iterations": 3,
                    "max_checkpoint_size": 2048,
                },
            },
            {
                "id": "outcome_1",
                "title": "Evaluate enquiry outcome",
                "action_id": "goal_engine.outcome_evaluation",
                "config": {
                    "metric_name": "enquiries",
                    "metric_target": 10,
                    "metric_actual": 0,
                    "evidence_refs": ["manual:pending"],
                    "confidence": 0.25,
                },
            },
            {
                "id": "delta_1",
                "title": "Bounded state delta",
                "action_id": "goal_engine.state_delta_accumulator",
                "config": {
                    "max_delta_bytes": 1024,
                    "loop_context_snapshot": {"iteration": 0, "status": "preview"},
                },
            },
        ],
    }


def build_trace():
    manifest = build_goal_engine_manifest_for_capsule(
        visibility_capsule(),
        run_id="run_boardroom_visibility_1",
    )
    manifest["goal_engine_step_trace"] = build_goal_engine_step_trace_rows(
        manifest,
        run_id="run_boardroom_visibility_1",
    )
    return build_goal_engine_boardroom_trace(manifest)


def test_boardroom_trace_exposes_preview_fields_summary():
    trace = build_trace()

    assert trace["runtime"] == "aion_goal_engine"
    assert trace["dry_run_only"] is True
    assert trace["grants_permission"] is False

    previews = trace["preview_fields"]

    assert previews["loop_iteration_count"] == 3
    assert previews["experiment_variants"] == ["A", "B"]
    assert previews["outcome_score"]["metric_name"] == "enquiries"
    assert previews["checkpoint_resume_state"]["max_checkpoint_size"] == 2048
    assert previews["state_delta_summary"]["max_delta_bytes"] == 1024
    assert previews["evidence_refs"] == ["manual:pending"]


def test_boardroom_trace_exposes_per_node_preview_rows():
    trace = build_trace()

    rows = trace["preview_rows"]
    kinds = {row["node_kind"] for row in rows}

    assert "experiment" in kinds
    assert "loop" in kinds
    assert "outcome_evaluation" in kinds
    assert "state_delta_accumulator" in kinds

    loop_row = next(row for row in rows if row["node_kind"] == "loop")
    assert loop_row["loop_iteration_preview"]["max_iterations"] == 3
    assert loop_row["checkpoint_resume_preview"]["max_checkpoint_size"] == 2048

    outcome_row = next(row for row in rows if row["node_kind"] == "outcome_evaluation")
    assert outcome_row["outcome_score_preview"]["metric_name"] == "enquiries"
    assert outcome_row["outcome_score_preview"]["evidence_refs"] == ["manual:pending"]


def test_boardroom_visibility_never_grants_permission_or_external_write():
    trace = build_trace()

    assert trace["grants_permission"] is False
    assert trace["would_grant_permission"] is False
    assert trace["would_write_external"] is False
    assert trace["preview_fields"]["external_write_performed"] is False
    assert trace["preview_fields"]["blocked_reasons"]
