from backend.modules.aion.goal_engine.orchestrator import (
    build_multi_agent_execution_replay_history_record,
    append_multi_agent_execution_replay_history_record,
)


def _sample_source():
    return {
        "run_id": "run_parent_001",
        "workflow_id": "workflow_parent_goal",
        "parent_goal_id": "goal_parent_001",
        "orchestrator_parent_child_aggregation_runtime_summary": {
            "trace_type": "orchestrator_parent_child_aggregation_runtime_summary",
            "parent_goal_id": "goal_parent_001",
            "child_agents": [
                {"agent_id": "agent_marketing", "status": "completed"},
                {"agent_id": "agent_reviewer", "status": "waiting_approval"},
            ],
            "blocked_reasons": ["child_approval_required"],
        },
        "parent_goal_update_proposal": {
            "trace_type": "parent_goal_update_proposal",
            "approval_gate": "parent_goal_update_review",
        },
        "child_agent_conflict_preview": {
            "trace_type": "child_agent_conflict_preview",
            "conflict_detected": True,
            "recommended_resolution": "human_review_required",
        },
    }


def test_replay_history_record_builds_canonical_backend_record():
    record = build_multi_agent_execution_replay_history_record(_sample_source())

    assert record["schema_version"] == "aion.goal_engine.multi_agent_execution_replay_history.v1"
    assert record["trace_type"] == "multi_agent_execution_replay_history_record"
    assert record["run_id"] == "run_parent_001"
    assert record["workflow_id"] == "workflow_parent_goal"
    assert record["parent_goal_id"] == "goal_parent_001"
    assert record["dry_run"] is True
    assert record["visibility_only"] is True


def test_replay_history_record_preserves_canonical_payloads():
    record = build_multi_agent_execution_replay_history_record(_sample_source())

    assert "orchestrator_parent_child_aggregation_runtime_summary" in record["payload"]
    assert "parent_goal_update_proposal" in record["payload"]
    assert "child_agent_conflict_preview" in record["payload"]
    assert record["payload"]["child_agent_conflict_preview"]["conflict_detected"] is True


def test_replay_history_record_blocks_execution_and_writes():
    record = build_multi_agent_execution_replay_history_record(_sample_source())

    assert record["execution_allowed"] is False
    assert record["writes_allowed"] is False
    assert record["parent_mutation_allowed"] is False
    assert record["child_execution_allowed"] is False
    assert "visibility_only" in record["blocked_reasons"]


def test_replay_history_append_is_bounded_to_25_records():
    existing = [
        build_multi_agent_execution_replay_history_record(
            {
                **_sample_source(),
                "run_id": f"run_{idx:03d}",
            }
        )
        for idx in range(30)
    ]

    updated = append_multi_agent_execution_replay_history_record(
        existing,
        build_multi_agent_execution_replay_history_record(_sample_source()),
    )

    assert len(updated) == 25
    assert updated[0]["run_id"] == "run_parent_001"


def test_replay_history_append_ignores_non_dict_existing_items():
    updated = append_multi_agent_execution_replay_history_record(
        ["bad", None, {"run_id": "old"}],
        build_multi_agent_execution_replay_history_record(_sample_source()),
    )

    assert len(updated) == 2
    assert updated[0]["run_id"] == "run_parent_001"
    assert updated[1]["run_id"] == "old"


def test_replay_history_record_tolerates_empty_source():
    record = build_multi_agent_execution_replay_history_record({})

    assert record["schema_version"] == "aion.goal_engine.multi_agent_execution_replay_history.v1"
    assert record["run_id"] == ""
    assert record["workflow_id"] == ""
    assert record["payload"] == {}
    assert record["execution_allowed"] is False
