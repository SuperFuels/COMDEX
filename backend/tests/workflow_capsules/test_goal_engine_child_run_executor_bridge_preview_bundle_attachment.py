from backend.modules.aion.goal_engine.preview_bundle import build_goal_engine_preview_bundle


def _executor_bridge_packet():
    return {
        "schema_version": "aion.goal_engine.child_run_executor_bridge.v1",
        "trace_type": "child_run_executor_bridge_packet",
        "status": "ready_for_workflow_runtime",
        "workflow_run_creation_allowed": True,
        "blocked_reasons": [],
        "workflow_id": "workflow_marketing_content_draft_v1",
        "run_id": "run_child_001",
        "target_workflow_id": "workflow_marketing_content_draft_v1",
        "target_child_run_id": "run_child_001",
        "parent_goal_id": "goal_parent_001",
        "child_goal_id": "goal_child_001",
        "child_agent_id": "agent_marketing",
        "child_glyph_id": "MK-001",
        "reviewer_id": "human_ceo",
        "runtime_seed": {
            "workflow_id": "workflow_marketing_content_draft_v1",
            "run_id": "run_child_001",
        },
        "requires_existing_workflow_runtime": True,
        "creates_external_side_effects": False,
        "autonomous_execution": False,
        "external_writes_allowed": False,
        "business_mutation_allowed": False,
    }


def _manifest():
    return {
        "workflow_id": "workflow_parent_child_executor_bundle",
        "runtime": "aion_goal_engine",
        "steps": [
            {
                "step_id": "child_run_executor_bridge_step",
                "step_type": "child_run_executor_bridge",
                "contract": _executor_bridge_packet(),
            }
        ],
    }


def test_preview_bundle_exposes_child_run_executor_bridge_runtime_summary():
    bundle = build_goal_engine_preview_bundle(
        run_id="run_parent_001",
        workflow_id="workflow_parent_child_executor_bundle",
        manifest=_manifest(),
    ).to_dict()

    summary = bundle["child_run_executor_bridge_runtime_summary"]

    assert summary["schema_version"] == "aion.goal_engine.child_run_executor_bridge_runtime_summary.v1"
    assert summary["trace_type"] == "child_run_executor_bridge_runtime_summary"
    assert summary["bridge_packet_count"] == 1
    assert summary["workflow_run_creation_allowed_count"] == 1
    assert summary["dry_run_only"] is True
    assert summary["would_execute"] is False
    assert summary["would_write_external"] is False
    assert summary["would_grant_permission"] is False

    packet = summary["child_run_executor_bridge_packets"][0]
    assert packet["trace_type"] == "child_run_executor_bridge_packet"
    assert packet["workflow_run_creation_allowed"] is True
    assert packet["target_workflow_id"] == "workflow_marketing_content_draft_v1"
    assert packet["target_child_run_id"] == "run_child_001"


def test_preview_bundle_machine_trace_exposes_child_run_executor_bridge_for_boardroom():
    bundle = build_goal_engine_preview_bundle(
        run_id="run_parent_001",
        workflow_id="workflow_parent_child_executor_bundle",
        manifest=_manifest(),
    ).to_dict()

    machine_trace = bundle["machine_trace"]

    assert "child_run_executor_bridge_runtime_summary" in machine_trace
    assert "child_run_executor_bridge_packets" in machine_trace
    assert machine_trace["child_run_executor_bridge_runtime_summary"]["bridge_packet_count"] == 1
    assert machine_trace["child_run_executor_bridge_packets"][0]["run_id"] == "run_child_001"


def test_preview_bundle_child_run_executor_bridge_aliases_stay_in_sync():
    bundle = build_goal_engine_preview_bundle(
        run_id="run_parent_001",
        workflow_id="workflow_parent_child_executor_bundle",
        manifest=_manifest(),
    ).to_dict()

    assert bundle["child_run_executor_bridge_packets"] == bundle["workflow_run_creation_bridge_packets"]
    assert (
        bundle["child_run_executor_bridge_runtime_summary"]
        == bundle["workflow_run_creation_bridge_runtime_summary"]
    )


def test_empty_manifest_keeps_safe_empty_child_run_executor_bridge_summary():
    bundle = build_goal_engine_preview_bundle(
        run_id="run_empty",
        workflow_id="workflow_empty",
        manifest={"valid": True, "steps": []},
    ).to_dict()

    summary = bundle["child_run_executor_bridge_runtime_summary"]

    assert summary["bridge_packet_count"] == 0
    assert summary["workflow_run_creation_allowed_count"] == 0
    assert summary["child_run_executor_bridge_packets"] == []
    assert summary["dry_run_only"] is True
    assert summary["would_execute"] is False
