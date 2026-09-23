from backend.modules.aion.goal_engine.boardroom_trace import build_goal_engine_boardroom_trace


def test_empty_manifest_returns_unavailable_trace():
    trace = build_goal_engine_boardroom_trace(None)

    assert trace["runtime"] == "aion_goal_engine"
    assert trace["available"] is False
    assert trace["safety"]["dry_run_only"] is True
    assert trace["safety"]["would_execute"] is False
    assert trace["safety"]["would_write_external"] is False
    assert trace["safety"]["would_grant_permission"] is False


def test_boardroom_trace_extracts_goal_summary():
    manifest = {
        "runtime": "aion_goal_engine",
        "run_id": "run_001",
        "workflow_id": "workflow_001",
        "valid": True,
        "dry_run_only": True,
        "would_execute": False,
        "would_write_external": False,
        "would_grant_permission": False,
        "safety_contract": {
            "external_writes_require_approval": True,
            "unbounded_loops_allowed": False,
            "resume_requires_environment_revalidation": True,
        },
        "steps": [
            {
                "contract_type": "GoalNodeContract",
                "dry_run_only": True,
                "would_execute": False,
                "would_write_external": False,
                "would_grant_permission": False,
                "payload": {
                    "goal_id": "goal_001",
                    "goal_name": "Generate leads",
                    "target_metric": "lead_count",
                    "target_value": 50,
                },
                "validation_errors": [],
            }
        ],
    }

    trace = build_goal_engine_boardroom_trace(manifest)

    assert trace["available"] is True
    assert trace["run_id"] == "run_001"
    assert trace["workflow_id"] == "workflow_001"
    assert trace["summary"] == "Goal Engine dry-run trace attached. Advisory only; grants no permission."
    assert trace["active_goals"] == [
        {
            "goal_id": "goal_001",
            "goal_name": "Generate leads",
            "target_metric": "lead_count",
            "target_value": 50,
        }
    ]
    assert trace["safety"]["dry_run_only"] is True
    assert trace["safety"]["would_execute"] is False
    assert trace["safety"]["would_write_external"] is False
    assert trace["safety"]["would_grant_permission"] is False
    assert trace["safety"]["unbounded_loops_allowed"] is False
    assert trace["safety"]["resume_requires_environment_revalidation"] is True
    assert trace["events"][0]["event_type"] == "goal_engine.dry_run_step_visible"


def test_boardroom_trace_collects_validation_errors_as_blocked_reasons():
    manifest = {
        "runtime": "aion_goal_engine",
        "valid": False,
        "steps": [
            {
                "contract_type": "LoopNodeContract",
                "validation_errors": [
                    "max_iterations must be at least 1",
                    "goal_id is required for goal-aware loop modes",
                ],
            }
        ],
    }

    trace = build_goal_engine_boardroom_trace(manifest)

    assert trace["available"] is True
    assert trace["valid"] is False
    assert "max_iterations must be at least 1" in trace["blocked_reasons"]
    assert "goal_id is required for goal-aware loop modes" in trace["blocked_reasons"]
