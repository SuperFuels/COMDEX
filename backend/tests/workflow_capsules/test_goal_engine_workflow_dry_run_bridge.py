from backend.modules.workflow_capsules.execution.goal_engine_dry_run_bridge import (
    attach_goal_engine_manifest_to_dry_result,
    build_goal_engine_manifest_for_capsule,
    is_goal_engine_step,
)


class DummyDryResult:
    run_id = "run_goal_engine_001"

    def to_dict(self):
        return {
            "run_id": self.run_id,
            "dry_run": True,
        }


def test_detects_goal_engine_step_by_action_id():
    assert is_goal_engine_step({"action_id": "goal_engine.goal"}) is True
    assert is_goal_engine_step({"config": {"module_id": "goal_engine.loop"}}) is True
    assert is_goal_engine_step({"action_id": "gmail.create_draft"}) is False


def test_builds_goal_engine_manifest_from_capsule_steps():
    capsule = {
        "workflow_id": "workflow_goal_engine_001",
        "steps": [
            {
                "id": "goal_step",
                "title": "Generate 20 qualified leads",
                "action_id": "goal_engine.goal",
                "config": {
                    "goal_id": "goal_001",
                    "goal_name": "Generate leads",
                    "target_metric": "lead_count",
                    "target_value": 20,
                },
            },
            {
                "id": "loop_step",
                "title": "Bounded improvement loop",
                "action_id": "goal_engine.loop",
                "config": {
                    "loop_id": "loop_001",
                    "goal_id": "goal_001",
                    "loop_mode": "fixed_iterations",
                    "max_iterations": 3,
                    "max_runtime_minutes": 10,
                },
            },
        ],
    }

    manifest = build_goal_engine_manifest_for_capsule(
        capsule,
        run_id="run_goal_engine_001",
    )

    assert manifest["runtime"] == "aion_goal_engine"
    assert manifest["workflow_id"] == "workflow_goal_engine_001"
    assert manifest["run_id"] == "run_goal_engine_001"
    assert manifest["valid"] is True
    assert len(manifest["steps"]) == 2

    for step in manifest["steps"]:
        assert step["dry_run_only"] is True
        assert step["would_execute"] is False
        assert step["would_write_external"] is False
        assert step["would_grant_permission"] is False


def test_attach_goal_engine_manifest_to_dry_result_dict_output():
    capsule = {
        "workflow_id": "workflow_goal_engine_001",
        "steps": [
            {
                "id": "goal_step",
                "title": "Goal",
                "action_id": "goal_engine.goal",
                "config": {
                    "goal_id": "goal_001",
                    "goal_name": "Generate leads",
                    "target_metric": "lead_count",
                    "target_value": 20,
                },
            }
        ],
    }

    result = attach_goal_engine_manifest_to_dry_result(
        DummyDryResult(),
        capsule,
        run_id="run_goal_engine_001",
    )

    assert hasattr(result, "goal_engine_manifest")
    payload = result.to_dict()
    assert payload["goal_engine_manifest"]["runtime"] == "aion_goal_engine"
    assert payload["goal_engine"]["safety_contract"]["goals_grant_permission"] is False


def test_non_goal_engine_capsule_is_unchanged():
    capsule = {
        "workflow_id": "workflow_regular",
        "steps": [{"id": "draft", "action_id": "gmail.create_draft"}],
    }

    result = attach_goal_engine_manifest_to_dry_result(DummyDryResult(), capsule)

    assert not hasattr(result, "goal_engine_manifest")
    assert "goal_engine_manifest" not in result.to_dict()
