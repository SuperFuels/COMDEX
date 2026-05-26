from backend.modules.aion.goal_engine.orchestrator import (
    build_human_approved_child_run_creation_action,
)


def _valid_handoff():
    return {
        "schema_version": "aion.goal_engine.guarded_child_agent_execution_handoff.v1",
        "trace_type": "guarded_child_agent_execution_handoff_preview",
        "approval_gate": "child_agent_execution_review",
        "status": "waiting_approval",
        "ready_for_execution_handoff": True,
        "parent_goal_id": "goal_parent_001",
        "child_goal_id": "goal_child_001",
        "child_agent_id": "agent_marketing",
        "child_glyph_id": "MK-001",
        "requested_action": "create_child_workflow_run",
        "reviewer_id": "human_ceo",
        "blocked_reasons": [],
        "dry_run": True,
        "visibility_only": True,
        "execution_allowed": False,
        "writes_allowed": False,
        "requires_human_approval": True,
    }


def _valid_request():
    return {
        "schema_version": "aion.goal_engine.guarded_child_run_creation_request.v1",
        "trace_type": "guarded_child_run_creation_request",
        "status": "waiting_human_approval",
        "approval_gate": "child_run_creation_review",
        "child_run_creation_request_valid": True,
        "ready_for_execution_handoff": True,
        "parent_goal_id": "goal_parent_001",
        "child_goal_id": "goal_child_001",
        "child_agent_id": "agent_marketing",
        "child_glyph_id": "MK-001",
        "target_workflow_id": "workflow_marketing_content_draft_v1",
        "target_child_run_id": "run_child_001",
        "requested_by": "human_ceo",
        "requested_action": "create_child_workflow_run",
        "blocked_reasons": [],
        "child_run_created": False,
        "autonomous_execution": False,
        "external_writes_allowed": False,
        "business_mutation_allowed": False,
        "requires_human_approval": True,
    }



def test_human_approved_child_run_creation_action_builds_executable_seed():
    action = build_human_approved_child_run_creation_action(
        child_run_request=_valid_request(),
        approval_decision="approved",
        reviewer_id="human_ceo",
    )

    assert action["schema_version"] == "aion.goal_engine.human_approved_child_run_creation_action.v1"
    assert action["trace_type"] == "human_approved_child_run_creation_action"
    assert action["status"] == "approved_for_child_run_creation"
    assert action["child_run_creation_allowed"] is True
    assert action["child_run_created"] is False
    assert action["requires_runtime_executor"] is True


def test_human_approved_child_run_creation_action_preserves_seed_links():
    action = build_human_approved_child_run_creation_action(
        child_run_request=_valid_request(),
        approval_decision="approved",
        reviewer_id="human_ceo",
    )

    seed = action["child_run_seed"]
    assert seed["parent_goal_id"] == "goal_parent_001"
    assert seed["child_goal_id"] == "goal_child_001"
    assert seed["child_agent_id"] == "agent_marketing"
    assert seed["child_glyph_id"] == "MK-001"
    assert seed["workflow_id"] == "workflow_marketing_content_draft_v1"
    assert seed["run_id"] == "run_child_001"


def test_human_approved_child_run_creation_action_is_not_autonomous():
    action = build_human_approved_child_run_creation_action(
        child_run_request=_valid_request(),
        approval_decision="approved",
        reviewer_id="human_ceo",
    )

    assert action["autonomous_execution"] is False
    assert action["external_writes_allowed"] is False
    assert action["business_mutation_allowed"] is False
    assert action["human_approved"] is True


def test_human_approved_child_run_creation_action_blocks_rejected_decision():
    action = build_human_approved_child_run_creation_action(
        child_run_request=_valid_request(),
        approval_decision="rejected",
        reviewer_id="human_ceo",
    )

    assert action["status"] == "blocked"
    assert action["child_run_creation_allowed"] is False
    assert "approval_decision_not_approved" in action["blocked_reasons"]


def test_human_approved_child_run_creation_action_blocks_missing_reviewer():
    action = build_human_approved_child_run_creation_action(
        child_run_request=_valid_request(),
        approval_decision="approved",
        reviewer_id="",
    )

    assert action["status"] == "blocked"
    assert action["child_run_creation_allowed"] is False
    assert "missing_reviewer_id" in action["blocked_reasons"]


def test_human_approved_child_run_creation_action_blocks_invalid_request():
    bad_request = dict(_valid_request())
    bad_request["child_run_creation_request_valid"] = False
    bad_request["blocked_reasons"] = ["missing_target_workflow_id"]

    action = build_human_approved_child_run_creation_action(
        child_run_request=bad_request,
        approval_decision="approved",
        reviewer_id="human_ceo",
    )

    assert action["status"] == "blocked"
    assert action["child_run_creation_allowed"] is False
    assert "invalid_child_run_creation_request" in action["blocked_reasons"]
    assert "missing_target_workflow_id" in action["blocked_reasons"]
