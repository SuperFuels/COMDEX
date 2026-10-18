from backend.modules.workflow_capsules.execution.goal_engine_dry_run_bridge import (
    attach_goal_engine_manifest_to_dry_result,
)


class DummyDryResult:
    def to_dict(self):
        return {
            "schema_version": "aion.workflow_capsule_dry_run_result.v1",
            "dry_run": True,
        }


def goal_capsule():
    return {
        "canonical_key": "workflow_goal_engine_test",
        "workflow_id": "workflow_goal_engine_test",
        "steps": [
            {
                "step_id": "goal_1",
                "title": "Increase qualified leads",
                "action_id": "goal_engine.goal",
                "config": {
                    "goal_id": "goal_001",
                    "goal_name": "Increase qualified leads",
                    "target_metric": "qualified_leads",
                    "target_value": 50,
                },
            },
            {
                "step_id": "loop_1",
                "title": "Bounded improvement loop",
                "action_id": "goal_engine.loop",
                "config": {
                    "loop_id": "loop_001",
                    "goal_id": "goal_001",
                    "loop_mode": "until_goal_achieved",
                    "max_iterations": 3,
                    "max_runtime_minutes": 15,
                },
            },
        ],
    }


def test_attach_adds_goal_engine_boardroom_trace_attribute():
    result = attach_goal_engine_manifest_to_dry_result(
        DummyDryResult(),
        goal_capsule(),
        run_id="run_goal_engine_001",
    )

    assert hasattr(result, "goal_engine_manifest")
    assert hasattr(result, "goal_engine_boardroom_trace")

    trace = result.goal_engine_boardroom_trace
    assert trace["runtime"] == "aion_goal_engine"
    assert trace["available"] is True
    assert trace["run_id"] == "run_goal_engine_001"
    assert trace["workflow_id"] == "workflow_goal_engine_test"
    assert trace["dry_run_only"] is True
    assert trace["grants_permission"] is False
    assert trace["would_write_external"] is False
    assert trace["summary"] == "Goal Engine dry-run trace attached. Advisory only; grants no permission."


def test_attach_adds_goal_engine_boardroom_trace_to_to_dict_payload():
    result = attach_goal_engine_manifest_to_dry_result(
        DummyDryResult(),
        goal_capsule(),
        run_id="run_goal_engine_001",
    )

    payload = result.to_dict()

    assert payload["goal_engine_manifest"]["runtime"] == "aion_goal_engine"
    assert payload["goal_engine_boardroom_trace"]["runtime"] == "aion_goal_engine"
    assert payload["goal_engine_boardroom_trace"]["available"] is True
    assert payload["goal_engine_boardroom_trace"]["dry_run_only"] is True
    assert payload["goal_engine_boardroom_trace"]["grants_permission"] is False


def test_no_goal_engine_steps_does_not_attach_trace():
    capsule = {
        "canonical_key": "workflow_plain",
        "workflow_id": "workflow_plain",
        "steps": [
            {
                "step_id": "plain_1",
                "title": "Normal step",
                "action_id": "aion.simple_prompt",
            }
        ],
    }

    result = attach_goal_engine_manifest_to_dry_result(DummyDryResult(), capsule)

    assert not hasattr(result, "goal_engine_manifest")
    assert not hasattr(result, "goal_engine_boardroom_trace")
    assert "goal_engine_manifest" not in result.to_dict()
    assert "goal_engine_boardroom_trace" not in result.to_dict()
