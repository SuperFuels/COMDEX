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


def loop_capsule(max_iterations=3):
    return {
        "canonical_key": "test.goal_engine.loop_iteration_preview",
        "steps": [
            {
                "id": "goal_1",
                "title": "Grow local leads",
                "action_id": "goal_engine.goal",
                "config": {"metric_target": "10 enquiries"},
            },
            {
                "id": "loop_1",
                "title": "Bounded improvement loop",
                "action_id": "goal_engine.loop",
                "config": {"max_iterations": max_iterations},
            },
        ],
    }


def test_loop_step_trace_contains_iteration_preview():
    manifest = build_goal_engine_manifest_for_capsule(
        loop_capsule(max_iterations=3),
        run_id="run_loop_preview_1",
    )
    rows = build_goal_engine_step_trace_rows(manifest, run_id="run_loop_preview_1")

    loop_row = next(row for row in rows if row["node_kind"] == "loop")
    preview = loop_row["loop_iteration_preview"]

    assert preview["schema_version"] == "aion.goal_engine.loop_iteration_preview.v1"
    assert preview["node_id"] == "loop_1"
    assert preview["max_iterations"] == 3
    assert preview["current_iteration"] == 0
    assert preview["would_run_iterations"] == 3
    assert preview["kill_switch_available"] is True
    assert preview["bounded_execution"] is True
    assert preview["unbounded_execution_blocked"] is True
    assert preview["external_write_performed"] is False


def test_loop_iteration_preview_is_also_in_payload():
    manifest = build_goal_engine_manifest_for_capsule(
        loop_capsule(max_iterations=4),
        run_id="run_loop_preview_2",
    )
    rows = build_goal_engine_step_trace_rows(manifest, run_id="run_loop_preview_2")

    loop_row = next(row for row in rows if row["node_kind"] == "loop")
    assert loop_row["payload"]["loop_iteration_preview"]["max_iterations"] == 4
    assert loop_row["payload"]["loop_iteration_preview"]["would_run_iterations"] == 4


def test_manifest_attach_preserves_loop_iteration_preview_in_dry_result_trace():
    result = attach_goal_engine_manifest_to_dry_result(
        DummyDryResult(),
        loop_capsule(max_iterations=5),
        run_id="run_loop_preview_3",
    )

    payload = result.to_dict()
    loop_row = next(row for row in payload["trace"] if row.get("node_kind") == "loop")

    assert loop_row["node_id"] == "loop_1"
    assert loop_row["loop_iteration_preview"]["max_iterations"] == 5
    assert loop_row["loop_iteration_preview"]["current_iteration"] == 0
    assert loop_row["loop_iteration_preview"]["kill_switch_available"] is True
    assert loop_row["loop_iteration_preview"]["unbounded_execution_blocked"] is True


def test_loop_iteration_preview_clamps_unbounded_or_invalid_iterations():
    manifest = build_goal_engine_manifest_for_capsule(
        loop_capsule(max_iterations=999999),
        run_id="run_loop_preview_4",
    )
    rows = build_goal_engine_step_trace_rows(manifest, run_id="run_loop_preview_4")
    loop_row = next(row for row in rows if row["node_kind"] == "loop")
    preview = loop_row["loop_iteration_preview"]

    assert preview["max_iterations"] <= 100
    assert preview["would_run_iterations"] <= 100
    assert preview["unbounded_execution_blocked"] is True
    assert preview["bounded_execution"] is True
