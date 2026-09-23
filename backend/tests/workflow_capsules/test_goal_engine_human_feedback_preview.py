from backend.modules.workflow_capsules.execution.goal_engine_dry_run_bridge import (
    attach_goal_engine_manifest_to_dry_result,
    build_goal_engine_human_feedback_preview,
    build_goal_engine_manifest_for_capsule,
    build_goal_engine_step_trace_rows,
)


class DummyDryResult:
    def to_dict(self):
        return {
            "schema_version": "aion.workflow_capsule_dry_run_result.v1",
            "status": "dry_run_completed",
            "trace": [],
        }


def feedback_capsule():
    return {
        "canonical_key": "test.goal_engine.human_feedback_preview",
        "steps": [
            {
                "id": "goal_1",
                "title": "Improve lead quality",
                "action_id": "goal_engine.goal",
                "config": {
                    "feedback_required": True,
                    "feedback_category": "lead_quality",
                    "feedback_rating": None,
                    "allow_learning": False,
                    "do_not_learn_from_this": True,
                    "feedback_comment": "Manual review pending",
                },
            },
            {
                "id": "outcome_1",
                "title": "Confirm outcome manually",
                "action_id": "goal_engine.outcome_evaluation",
                "config": {
                    "metric_name": "qualified_leads",
                    "metric_target": 5,
                    "metric_actual": None,
                    "feedback_required": True,
                    "feedback_category": "manual_outcome_confirmation",
                    "allow_learning": False,
                },
            },
        ],
    }


def test_build_human_feedback_preview_directly():
    preview = build_goal_engine_human_feedback_preview(
        {
            "node_id": "goal_1",
            "node_kind": "goal",
            "feedback_required": True,
            "feedback_category": "lead_quality",
            "feedback_rating": 4,
            "allow_learning": False,
            "do_not_learn_from_this": True,
            "feedback_comment": "Good but needs evidence",
        },
        run_id="run_feedback_1",
    )

    assert preview["schema_version"] == "aion.goal_engine.human_feedback_preview.v1"
    assert preview["node_id"] == "goal_1"
    assert preview["feedback_required"] is True
    assert preview["feedback_category"] == "lead_quality"
    assert preview["feedback_rating"] == 4
    assert preview["allow_learning"] is False
    assert preview["do_not_learn_from_this"] is True
    assert preview["negative_feedback_grants_permission"] is False
    assert preview["grants_permission"] is False
    assert preview["dry_run_only"] is True


def test_step_trace_rows_include_human_feedback_preview():
    manifest = build_goal_engine_manifest_for_capsule(
        feedback_capsule(),
        run_id="run_feedback_2",
    )
    rows = build_goal_engine_step_trace_rows(manifest, run_id="run_feedback_2")

    goal_row = next(row for row in rows if row["node_id"] == "goal_1")
    outcome_row = next(row for row in rows if row["node_id"] == "outcome_1")

    assert goal_row["human_feedback_preview"]["feedback_required"] is True
    assert goal_row["human_feedback_preview"]["feedback_category"] == "lead_quality"
    assert goal_row["human_feedback_preview"]["allow_learning"] is False
    assert goal_row["payload"]["human_feedback_preview"]["do_not_learn_from_this"] is True

    assert outcome_row["human_feedback_preview"]["feedback_category"] == "manual_outcome_confirmation"
    assert outcome_row["human_feedback_preview"]["attach_feedback_to_run_id"] == "run_feedback_2"


def test_manifest_attach_preserves_human_feedback_preview_in_dry_result_trace():
    result = attach_goal_engine_manifest_to_dry_result(
        DummyDryResult(),
        feedback_capsule(),
        run_id="run_feedback_3",
    )

    payload = result.to_dict()
    goal_row = next(row for row in payload["trace"] if row.get("node_id") == "goal_1")

    assert goal_row["human_feedback_preview"]["schema_version"] == "aion.goal_engine.human_feedback_preview.v1"
    assert goal_row["human_feedback_preview"]["feedback_required"] is True
    assert goal_row["human_feedback_preview"]["allow_learning"] is False
    assert goal_row["human_feedback_preview"]["negative_feedback_grants_permission"] is False


def test_human_feedback_preview_defaults_safe_when_missing():
    preview = build_goal_engine_human_feedback_preview(
        {"node_id": "goal_1", "node_kind": "goal"},
        run_id="run_feedback_4",
    )

    assert preview["feedback_required"] is False
    assert preview["feedback_rating"] is None
    assert preview["allow_learning"] is False
    assert preview["do_not_learn_from_this"] is False
    assert preview["negative_feedback_grants_permission"] is False
    assert preview["grants_permission"] is False
