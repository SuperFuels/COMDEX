from backend.modules.aion.goal_engine.orchestrator import (
    build_child_run_executor_bridge_packet,
    build_guarded_child_run_creation_request,
    build_human_approved_child_run_creation_action,
)
from backend.modules.aion.goal_engine.preview_bundle import build_goal_engine_preview_bundle


def _handoff():
    return {
        "trace_type": "guarded_child_agent_execution_handoff",
        "handoff_valid": True,
        "ready_for_execution_handoff": True,
        "parent_goal_id": "goal_parent_001",
        "child_goal_id": "goal_child_001",
        "child_agent_id": "agent_marketing",
        "child_glyph_id": "MK-001",
        "target_workflow_id": "workflow_marketing_content_draft_v1",
        "target_child_run_id": "run_child_001",
        "handoff_reason": "approved child marketing execution handoff",
        "blocked_reasons": [],
        "autonomous_execution": False,
        "external_writes_allowed": False,
        "business_mutation_allowed": False,
    }


def _request():
    handoff = _handoff()
    request = build_guarded_child_run_creation_request(
        handoff_preview=handoff,
        workflow_id=handoff["target_workflow_id"],
        run_id=handoff["target_child_run_id"],
    )

    # Canonical mirrors required by the approval/action and executor bridge chain.
    request.setdefault("target_workflow_id", handoff["target_workflow_id"])
    request.setdefault("target_child_run_id", handoff["target_child_run_id"])
    request.setdefault("child_agent_id", handoff["child_agent_id"])
    request.setdefault("child_glyph_id", handoff["child_glyph_id"])
    request.setdefault("parent_goal_id", handoff["parent_goal_id"])
    request.setdefault("child_goal_id", handoff["child_goal_id"])

    request.setdefault("requested_by", "human_ceo")
    request["reviewer_id"] = "human_ceo"
    request["requested_action"] = "create_child_run"
    request["handoff_schema_version"] = "aion.goal_engine.guarded_child_agent_execution_handoff.v1"
    request["child_run_creation_request_valid"] = True
    return request


def _approved_action(request):
    return build_human_approved_child_run_creation_action(
        child_run_request=request,
        approval_decision="approved",
        reviewer_id="human_ceo",
    )


def test_child_run_creation_end_to_end_builds_preview_visible_packet_chain():
    request = _request()

    action = _approved_action(request)

    packet = build_child_run_executor_bridge_packet(action)

    bundle = build_goal_engine_preview_bundle(
        run_id="run_parent_001",
        workflow_id="workflow_parent_001",
        goal_engine_manifest={
            "workflow_id": "workflow_parent_001",
            "runtime": "aion_goal_engine",
            "steps": [],
            "child_run_executor_bridge_packets": [packet],
        },
    ).to_dict()

    summary = bundle["child_run_executor_bridge_runtime_summary"]

    assert request["trace_type"] == "guarded_child_run_creation_request"
    assert request["status"] == "waiting_approval"
    assert request["child_run_created"] is False
    assert request.get("autonomous_execution", False) is False

    assert action["trace_type"] == "human_approved_child_run_creation_action"
    assert action["child_run_creation_allowed"] is True
    assert action["requires_runtime_executor"] is True
    assert action.get("autonomous_execution", False) is False

    assert packet["trace_type"] == "child_run_executor_bridge_packet"
    assert packet["status"] == "ready_for_workflow_runtime"
    assert packet["workflow_run_creation_allowed"] is True
    assert packet["workflow_id"] == "workflow_marketing_content_draft_v1"
    assert packet["run_id"] == "run_child_001"

    assert summary["trace_type"] == "child_run_executor_bridge_runtime_summary"
    assert summary["bridge_packet_count"] == 1
    assert summary["workflow_run_creation_allowed_count"] == 1
    assert summary["child_run_executor_bridge_packets"][0]["run_id"] == "run_child_001"

    assert bundle["workflow_run_creation_bridge_runtime_summary"] == summary
    assert bundle["workflow_run_creation_bridge_packets"] == bundle["child_run_executor_bridge_packets"]

    machine_trace = bundle["machine_trace"]
    assert machine_trace["child_run_executor_bridge_runtime_summary"] == summary
    assert machine_trace["workflow_run_creation_bridge_runtime_summary"] == summary


def test_child_run_creation_end_to_end_blocks_without_human_approval():
    request = _request()

    action = build_human_approved_child_run_creation_action(
        child_run_request=request,
        approval_decision="rejected",
        reviewer_id="human_ceo",
    )

    packet = build_child_run_executor_bridge_packet(action)

    assert action["child_run_creation_allowed"] is False
    assert packet["workflow_run_creation_allowed"] is False
    assert packet["status"] == "blocked"
    assert "child_run_creation_not_allowed" in packet["blocked_reasons"]


def test_child_run_creation_end_to_end_blocks_missing_reviewer():
    request = _request()

    action = build_human_approved_child_run_creation_action(
        child_run_request=request,
        approval_decision="approved",
        reviewer_id="",
    )

    packet = build_child_run_executor_bridge_packet(action)

    assert action["child_run_creation_allowed"] is False
    assert "missing_reviewer_id" in action["blocked_reasons"]
    assert packet["workflow_run_creation_allowed"] is False


def test_child_run_creation_end_to_end_never_executes_or_mutates_directly():
    request = _request()
    action = _approved_action(request)
    packet = build_child_run_executor_bridge_packet(action)

    for item in (request, action, packet):
        assert item.get("autonomous_execution", False) is False
        assert item.get("external_writes_allowed", False) is False
        assert item.get("business_mutation_allowed", False) is False

    assert action["requires_runtime_executor"] is True
    assert packet["requires_existing_workflow_runtime"] is True
    assert packet["creates_external_side_effects"] is False


def test_child_run_creation_end_to_end_preview_bundle_is_dry_run_visible_only():
    request = _request()
    action = _approved_action(request)
    packet = build_child_run_executor_bridge_packet(action)

    bundle = build_goal_engine_preview_bundle(
        run_id="run_parent_001",
        workflow_id="workflow_parent_001",
        goal_engine_manifest={
            "steps": [],
            "child_run_executor_bridge_packets": [packet],
        },
    ).to_dict()

    assert bundle["dry_run_only"] is True
    assert bundle["would_execute"] is False
    assert bundle["would_write_external"] is False
    assert bundle["would_grant_permission"] is False
    assert bundle["safety_contract"]["external_writes_require_approval"] is True
