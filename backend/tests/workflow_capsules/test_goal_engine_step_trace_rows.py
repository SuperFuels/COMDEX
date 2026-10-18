from backend.modules.workflow_capsules.execution.goal_engine_dry_run_bridge import (
    attach_goal_engine_manifest_to_dry_result,
    attach_goal_engine_step_trace_rows_to_dry_result,
    build_goal_engine_manifest_for_capsule,
    build_goal_engine_step_trace_rows,
)


class DummyDryResult:
    def to_dict(self):
        return {
            "schema_version": "aion.workflow_capsule_dry_run_result.v1",
            "status": "dry_run_completed",
            "trace": [{"node_id": "existing", "status": "dry_run_simulated"}],
        }


def goal_capsule():
    return {
        "canonical_key": "test.goal_engine.step_trace",
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
                "config": {"variants": ["A", "B"]},
            },
            {
                "id": "loop_1",
                "title": "Bounded improvement loop",
                "action_id": "goal_engine.loop",
                "config": {"max_iterations": 3},
            },
        ],
    }


def test_build_goal_engine_step_trace_rows_from_manifest():
    manifest = build_goal_engine_manifest_for_capsule(goal_capsule(), run_id="run_step_trace_1")
    rows = build_goal_engine_step_trace_rows(manifest, run_id="run_step_trace_1")

    assert len(rows) == 3
    assert rows[0]["trace_schema_version"] == "aion.goal_engine.step_trace.v1"
    assert rows[0]["runtime"] == "aion_goal_engine"
    assert rows[0]["node_id"] == "goal_1"
    assert rows[0]["node_kind"] == "goal"
    assert rows[0]["status"] == "dry_run_simulated"
    assert rows[0]["dry_run_only"] is True
    assert rows[0]["grants_permission"] is False
    assert rows[0]["external_write_performed"] is False
    assert rows[0]["bounded_execution"] is True


def test_attach_goal_engine_step_trace_rows_to_dry_result_attribute():
    manifest = build_goal_engine_manifest_for_capsule(goal_capsule(), run_id="run_step_trace_2")
    result = attach_goal_engine_step_trace_rows_to_dry_result(
        DummyDryResult(),
        manifest,
        run_id="run_step_trace_2",
    )

    assert hasattr(result, "goal_engine_step_trace")
    assert len(result.goal_engine_step_trace) == 3
    assert result.goal_engine_step_trace[1]["node_kind"] == "experiment"
    assert result.goal_engine_step_trace[2]["node_kind"] == "loop"


def test_attach_goal_engine_step_trace_rows_to_to_dict_payload():
    manifest = build_goal_engine_manifest_for_capsule(goal_capsule(), run_id="run_step_trace_3")
    result = attach_goal_engine_step_trace_rows_to_dry_result(
        DummyDryResult(),
        manifest,
        run_id="run_step_trace_3",
    )

    payload = result.to_dict()

    assert "goal_engine_step_trace" in payload
    assert len(payload["goal_engine_step_trace"]) == 3
    assert len(payload["trace"]) == 4
    assert payload["trace"][-1]["node_id"] == "loop_1"


def test_manifest_attach_also_attaches_step_trace_rows():
    result = attach_goal_engine_manifest_to_dry_result(
        DummyDryResult(),
        goal_capsule(),
        run_id="run_step_trace_4",
    )

    payload = result.to_dict()

    assert "goal_engine_manifest" in payload
    assert "goal_engine_step_trace" in payload
    assert len(payload["goal_engine_step_trace"]) == 3
    assert payload["goal_engine_step_trace"][0]["would_grant_permission"] is False
