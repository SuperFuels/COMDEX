from backend.modules.workflow_capsules.execution.goal_engine_dry_run_bridge import (
    attach_goal_engine_manifest_to_dry_result,
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


def outcome_capsule(metric_target="10 enquiries", metric_actual=0):
    return {
        "canonical_key": "test.goal_engine.outcome_score_preview",
        "steps": [
            {
                "id": "goal_1",
                "title": "Grow local leads",
                "action_id": "goal_engine.goal",
                "config": {
                    "metric_target": metric_target,
                    "target_metric": "enquiries",
                    "target_value": 10,
                },
            },
            {
                "id": "outcome_1",
                "title": "Evaluate lead outcome",
                "action_id": "goal_engine.outcome_evaluation",
                "config": {
                    "metric_target": 10,
                    "metric_actual": metric_actual,
                    "metric_name": "enquiries",
                    "confidence": 0.7,
                    "source": "manual_confirmation",
                    "cost": 0,
                    "time_to_result": None,
                    "evidence_refs": ["manual:pending"],
                },
            },
        ],
    }


def test_outcome_step_trace_contains_score_preview():
    manifest = build_goal_engine_manifest_for_capsule(
        outcome_capsule(metric_actual=4),
        run_id="run_outcome_preview_1",
    )
    rows = build_goal_engine_step_trace_rows(manifest, run_id="run_outcome_preview_1")

    outcome_row = next(row for row in rows if row["node_kind"] == "outcome_evaluation")
    preview = outcome_row["outcome_score_preview"]

    assert preview["schema_version"] == "aion.goal_engine.outcome_score_preview.v1"
    assert preview["runtime"] == "aion_goal_engine"
    assert preview["node_id"] == "outcome_1"
    assert preview["metric_name"] == "enquiries"
    assert preview["metric_target"] == 10
    assert preview["metric_actual"] == 4
    assert preview["outcome_score"] == 0.4
    assert preview["confidence"] == 0.7
    assert preview["source"] == "manual_confirmation"
    assert preview["dry_run_only"] is True
    assert preview["grants_permission"] is False
    assert preview["external_write_performed"] is False
    assert preview["requires_evidence"] is True
    assert preview["completed_workflow_is_not_success_without_evidence"] is True


def test_outcome_score_preview_clamps_above_target():
    manifest = build_goal_engine_manifest_for_capsule(
        outcome_capsule(metric_actual=25),
        run_id="run_outcome_preview_2",
    )
    rows = build_goal_engine_step_trace_rows(manifest, run_id="run_outcome_preview_2")

    outcome_row = next(row for row in rows if row["node_kind"] == "outcome_evaluation")
    preview = outcome_row["outcome_score_preview"]

    assert preview["outcome_score"] == 1.0
    assert preview["metric_actual"] == 25
    assert preview["metric_target"] == 10


def test_outcome_score_preview_is_also_in_payload():
    manifest = build_goal_engine_manifest_for_capsule(
        outcome_capsule(metric_actual=5),
        run_id="run_outcome_preview_3",
    )
    rows = build_goal_engine_step_trace_rows(manifest, run_id="run_outcome_preview_3")

    outcome_row = next(row for row in rows if row["node_kind"] == "outcome_evaluation")
    preview = outcome_row["payload"]["outcome_score_preview"]

    assert preview["outcome_score"] == 0.5
    assert preview["evidence_refs"] == ["manual:pending"]


def test_manifest_attach_preserves_outcome_preview_in_dry_result_trace():
    result = attach_goal_engine_manifest_to_dry_result(
        DummyDryResult(),
        outcome_capsule(metric_actual=6),
        run_id="run_outcome_preview_4",
    )

    payload = result.to_dict()
    outcome_row = next(row for row in payload["trace"] if row.get("node_kind") == "outcome_evaluation")

    assert outcome_row["node_id"] == "outcome_1"
    assert outcome_row["outcome_score_preview"]["outcome_score"] == 0.6
    assert outcome_row["outcome_score_preview"]["requires_evidence"] is True
    assert outcome_row["outcome_score_preview"]["external_write_performed"] is False
