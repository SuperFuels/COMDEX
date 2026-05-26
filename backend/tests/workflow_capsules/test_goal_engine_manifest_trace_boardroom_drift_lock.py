from backend.modules.aion.goal_engine.boardroom_trace import build_goal_engine_boardroom_trace
from backend.modules.workflow_capsules.execution.goal_engine_dry_run_bridge import (
    build_goal_engine_manifest_for_capsule,
    build_goal_engine_step_trace_rows,
)


def drift_lock_capsule():
    return {
        "canonical_key": "test.goal_engine.manifest_trace_boardroom_drift_lock",
        "steps": [
            {
                "id": "goal_1",
                "title": "Grow local leads",
                "action_id": "goal_engine.goal",
                "config": {
                    "metric_target": "10 enquiries",
                    "goal_budget": 25,
                    "estimated_cost": 5,
                    "risk_score": 0.2,
                    "feedback_required": True,
                },
            },
            {
                "id": "experiment_1",
                "title": "A/B test offer",
                "action_id": "goal_engine.experiment",
                "config": {
                    "variants": ["A", "B"],
                    "metric": "reply_rate",
                    "winner_policy": "manual",
                    "risk_score": 0.3,
                },
            },
            {
                "id": "loop_1",
                "title": "Bounded improvement loop",
                "action_id": "goal_engine.loop",
                "config": {
                    "max_iterations": 3,
                    "max_checkpoint_size": 2048,
                    "risk_score": 0.25,
                },
            },
            {
                "id": "outcome_1",
                "title": "Evaluate outcome",
                "action_id": "goal_engine.outcome_evaluation",
                "config": {
                    "metric_name": "enquiries",
                    "metric_target": 10,
                    "metric_actual": 0,
                    "evidence_refs": ["manual:pending"],
                },
            },
        ],
    }


def build_all():
    manifest = build_goal_engine_manifest_for_capsule(
        drift_lock_capsule(),
        run_id="run_drift_lock_1",
    )
    rows = build_goal_engine_step_trace_rows(
        manifest,
        run_id="run_drift_lock_1",
    )
    manifest["goal_engine_step_trace"] = rows
    manifest["steps"] = rows
    boardroom = build_goal_engine_boardroom_trace(manifest)
    return manifest, rows, boardroom


def test_manifest_step_trace_and_boardroom_share_runtime_safety_flags():
    manifest, rows, boardroom = build_all()

    assert manifest["runtime"] == "aion_goal_engine"
    assert boardroom["runtime"] == "aion_goal_engine"

    assert manifest["dry_run_only"] is True
    assert boardroom["dry_run_only"] is True

    assert manifest["would_grant_permission"] is False
    assert boardroom["would_grant_permission"] is False

    assert manifest["would_write_external"] is False
    assert boardroom["would_write_external"] is False

    for row in rows:
        assert row["runtime"] == "aion_goal_engine"
        assert row["dry_run_only"] is True
        assert row["grants_permission"] is False
        assert row["would_grant_permission"] is False
        assert row["external_write_performed"] is False


def test_step_trace_node_ids_are_visible_in_boardroom_manifest_steps():
    _manifest, rows, boardroom = build_all()

    row_ids = {row["node_id"] for row in rows}
    boardroom_ids = {
        row["node_id"]
        for row in boardroom.get("goal_engine_steps", [])
        if isinstance(row, dict)
    }

    assert row_ids
    assert row_ids.issubset(boardroom_ids)


def test_step_trace_preview_bundle_names_remain_visible_in_rows():
    _manifest, rows, _boardroom = build_all()

    goal = next(row for row in rows if row["node_id"] == "goal_1")
    experiment = next(row for row in rows if row["node_id"] == "experiment_1")
    loop = next(row for row in rows if row["node_id"] == "loop_1")
    outcome = next(row for row in rows if row["node_id"] == "outcome_1")

    assert "goal_engine_preview_bundle" in goal
    assert "simulation_what_if_preview" in goal["goal_engine_preview_bundle"]["previews"]
    assert "resource_cost_governance_preview" in goal["goal_engine_preview_bundle"]["previews"]
    assert "human_feedback_preview" in goal["goal_engine_preview_bundle"]["previews"]

    assert "experiment_variant_preview" in experiment["goal_engine_preview_bundle"]["previews"]
    assert "loop_iteration_preview" in loop["goal_engine_preview_bundle"]["previews"]
    assert "checkpoint_resume_preview" in loop["goal_engine_preview_bundle"]["previews"]
    assert "outcome_score_preview" in outcome["goal_engine_preview_bundle"]["previews"]


def test_boardroom_visibility_fields_cover_core_preview_summaries():
    _manifest, _rows, boardroom = build_all()

    fields = boardroom.get("boardroom_visibility_fields") or []

    assert "budget_status" in fields
    assert "resource_cost_governance" in fields
    assert "learning_summary" in fields
    assert "human_feedback_summary" in fields
    assert "red_team_safety_summary" in fields


def test_boardroom_events_cover_core_goal_engine_visibility():
    _manifest, _rows, boardroom = build_all()

    event_text = str(boardroom.get("events", []))

    assert "goal_engine.resource_cost_governance_visible" in event_text
    assert "goal_engine.human_feedback_visible" in event_text
    assert "goal_engine.red_team_safety_visible" in event_text


def test_no_view_claims_external_write_or_permission_grant():
    manifest, rows, boardroom = build_all()

    assert manifest.get("would_write_external") is False
    assert manifest.get("would_grant_permission") is False

    assert boardroom.get("would_write_external") is False
    assert boardroom.get("would_grant_permission") is False
    assert boardroom.get("grants_permission") is False

    for summary_key in (
        "red_team_safety_summary",
        "human_feedback_summary",
        "learning_summary",
        "resource_cost_governance",
    ):
        summary = boardroom.get(summary_key)
        if isinstance(summary, dict):
            assert summary.get("grants_permission", False) is False
            assert summary.get("would_grant_permission", False) is False
            assert summary.get("external_write_performed", False) is False

    for row in rows:
        assert row.get("grants_permission") is False
        assert row.get("would_grant_permission") is False
        assert row.get("external_write_performed") is False
