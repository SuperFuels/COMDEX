from __future__ import annotations

from backend.modules.aion_conversation.conversation_orchestrator import (
    ConversationOrchestrator,
)


def test_conversation_orchestrator_routes_gmail_workflow_to_dry_run_proposal() -> None:
    orch = ConversationOrchestrator()

    out = orch.handle_turn(
        session_id="pytest_workflow_orchestrator_route",
        user_text="Please draft a Gmail enquiry reply using the workflow.",
        include_debug=True,
        include_metadata=True,
    )

    assert out["ok"] is True
    assert out["mode"] == "workflow_proposal"
    assert "Workflow proposal ready" in out["response"]
    assert "Approval ID:" in out["response"]

    metadata = out["metadata"]
    orch_meta = metadata["orchestrator"]
    workflow = metadata["workflow_capsule"]

    assert orch_meta["local_mode_handler"] is True
    assert workflow["canonical_key"] == "workflow:gmail.enquiry_reply.v1"
    assert workflow["step_count"] == 5
    assert workflow["approval_required"] is True
    assert workflow["external_writes_blocked"] is True
    assert workflow["approval_id"]

    full = metadata["workflow_capsule_result"]
    assert full["ok"] is True
    assert full["approval"]["status"] == "pending"
    assert full["run"]["approval_required"] is True
    assert full["run"]["external_writes_blocked"] is True
    assert full["feedback"]["mutation_applied"] is False

    debug = out["debug"]
    assert debug["orchestrator_trace"]["used_local_handler"] is True
    assert debug["orchestrator_trace"]["local_handler_name"] == "workflow_capsule_route"
    assert debug["composer_out"]["metadata"]["workflow_capsule"]["canonical_key"] == "workflow:gmail.enquiry_reply.v1"


def test_conversation_orchestrator_routes_explicit_wg001_to_dry_run_proposal() -> None:
    orch = ConversationOrchestrator()

    out = orch.handle_turn(
        session_id="pytest_workflow_orchestrator_route_wg001",
        user_text="Run WG-001",
        include_debug=False,
        include_metadata=True,
    )

    assert out["ok"] is True
    assert out["mode"] == "workflow_proposal"

    workflow = out["metadata"]["workflow_capsule"]
    assert workflow["canonical_key"] == "workflow:gmail.enquiry_reply.v1"
    assert workflow["step_count"] == 5
    assert workflow["approval_id"]
