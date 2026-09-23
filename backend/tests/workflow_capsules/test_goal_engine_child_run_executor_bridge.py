from backend.modules.aion.goal_engine.orchestrator import (
    build_child_run_executor_bridge_packet,
)


def _approved_action():
    return {
        "schema_version": "aion.goal_engine.human_approved_child_run_creation_action.v1",
        "trace_type": "human_approved_child_run_creation_action",
        "status": "approved_for_runtime_executor",
        "child_run_creation_allowed": True,
        "requires_runtime_executor": True,
        "autonomous_execution": False,
        "external_writes_allowed": False,
        "business_mutation_allowed": False,
        "parent_goal_id": "goal_parent_001",
        "child_goal_id": "goal_child_001",
        "child_agent_id": "agent_marketing",
        "child_glyph_id": "MK-001",
        "target_workflow_id": "workflow_marketing_content_draft_v1",
        "target_child_run_id": "run_child_001",
        "reviewer_id": "human_ceo",
        "approval_decision": "approved",
        "runtime_seed": {
            "workflow_id": "workflow_marketing_content_draft_v1",
            "run_id": "run_child_001",
            "agent_id": "agent_marketing",
            "goal_id": "goal_child_001",
            "created_by": "human_ceo",
            "requires_runtime_executor": True,
            "external_writes_allowed": False,
            "business_mutation_allowed": False,
        },
    }


def test_child_run_executor_bridge_builds_creation_packet():
    packet = build_child_run_executor_bridge_packet(_approved_action())

    assert packet["schema_version"] == "aion.goal_engine.child_run_executor_bridge.v1"
    assert packet["trace_type"] == "child_run_executor_bridge_packet"
    assert packet["status"] == "ready_for_workflow_runtime"
    assert packet["workflow_run_creation_allowed"] is True
    assert packet["workflow_id"] == "workflow_marketing_content_draft_v1"
    assert packet["run_id"] == "run_child_001"


def test_child_run_executor_bridge_preserves_parent_child_agent_links():
    packet = build_child_run_executor_bridge_packet(_approved_action())

    assert packet["parent_goal_id"] == "goal_parent_001"
    assert packet["child_goal_id"] == "goal_child_001"
    assert packet["child_agent_id"] == "agent_marketing"
    assert packet["child_glyph_id"] == "MK-001"


def test_child_run_executor_bridge_remains_guarded():
    packet = build_child_run_executor_bridge_packet(_approved_action())

    assert packet["autonomous_execution"] is False
    assert packet["external_writes_allowed"] is False
    assert packet["business_mutation_allowed"] is False
    assert packet["requires_existing_workflow_runtime"] is True
    assert packet["creates_external_side_effects"] is False


def test_child_run_executor_bridge_blocks_unapproved_action():
    action = dict(_approved_action())
    action["approval_decision"] = "rejected"

    packet = build_child_run_executor_bridge_packet(action)

    assert packet["workflow_run_creation_allowed"] is False
    assert "approval_not_approved" in packet["blocked_reasons"]


def test_child_run_executor_bridge_blocks_missing_runtime_seed():
    action = dict(_approved_action())
    action.pop("runtime_seed")

    packet = build_child_run_executor_bridge_packet(action)

    assert packet["workflow_run_creation_allowed"] is False
    assert "missing_runtime_seed" in packet["blocked_reasons"]


def test_child_run_executor_bridge_blocks_missing_workflow_or_run_id():
    action = dict(_approved_action())
    action["runtime_seed"] = dict(action["runtime_seed"])
    action["runtime_seed"]["workflow_id"] = ""

    packet = build_child_run_executor_bridge_packet(action)

    assert packet["workflow_run_creation_allowed"] is False
    assert "missing_workflow_id" in packet["blocked_reasons"]
