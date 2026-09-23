from backend.modules.aion.goal_engine.orchestrator import (
    build_guarded_child_run_creation_request,
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



def test_guarded_child_run_creation_request_builds_review_only_packet():
    request = build_guarded_child_run_creation_request(
        handoff_preview=_valid_handoff(),
        workflow_id="workflow_marketing_child_v1",
        run_id="run_child_001",
    )

    assert request["schema_version"] == "aion.goal_engine.guarded_child_run_creation_request.v1"
    assert request["trace_type"] == "guarded_child_run_creation_request"
    assert request["approval_gate"] == "child_run_creation_review"
    assert request["status"] == "waiting_approval"
    assert request["workflow_id"] == "workflow_marketing_child_v1"
    assert request["run_id"] == "run_child_001"


def test_guarded_child_run_creation_request_preserves_parent_child_links():
    request = build_guarded_child_run_creation_request(
        handoff_preview=_valid_handoff(),
        workflow_id="workflow_marketing_child_v1",
        run_id="run_child_001",
    )

    assert request["parent_goal_id"] == "goal_parent_001"
    assert request["child_goal_id"] == "goal_child_001"
    assert request["child_agent_id"] == "agent_marketing"
    assert request["child_glyph_id"] == "MK-001"


def test_guarded_child_run_creation_request_is_never_autonomous():
    request = build_guarded_child_run_creation_request(
        handoff_preview=_valid_handoff(),
        workflow_id="workflow_marketing_child_v1",
        run_id="run_child_001",
    )

    assert request["dry_run"] is True
    assert request["visibility_only"] is True
    assert request["execution_allowed"] is False
    assert request["writes_allowed"] is False
    assert request["child_run_created"] is False
    assert request["requires_human_approval"] is True


def test_guarded_child_run_creation_request_blocks_invalid_handoff():
    bad_handoff = dict(_valid_handoff())
    bad_handoff["ready_for_execution_handoff"] = False
    bad_handoff["blocked_reasons"] = ["missing_child_goal"]

    request = build_guarded_child_run_creation_request(
        handoff_preview=bad_handoff,
        workflow_id="workflow_marketing_child_v1",
        run_id="run_child_001",
    )

    assert request["status"] == "blocked"
    assert request["child_run_created"] is False
    assert "invalid_guarded_handoff" in request["blocked_reasons"]


def test_guarded_child_run_creation_request_blocks_missing_workflow():
    request = build_guarded_child_run_creation_request(
        handoff_preview=_valid_handoff(),
        workflow_id="",
        run_id="run_child_001",
    )

    assert request["status"] == "blocked"
    assert "missing_workflow_id" in request["blocked_reasons"]


def test_guarded_child_run_creation_request_blocks_missing_run_id():
    request = build_guarded_child_run_creation_request(
        handoff_preview=_valid_handoff(),
        workflow_id="workflow_marketing_child_v1",
        run_id="",
    )

    assert request["status"] == "blocked"
    assert "missing_run_id" in request["blocked_reasons"]
