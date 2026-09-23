from __future__ import annotations

from backend.modules.workflow_capsules.architect.provider_adapter import (
    MockWorkflowBuilderProviderAdapter,
)
from backend.modules.workflow_capsules.architect.repair_loop import (
    WorkflowArchitectRepairLoop,
    clarification_questions_for_goal,
    is_vague_workflow_goal,
)


VALID_SPEC = {
    "schema_version": "aion.workflow_builder_spec.v1",
    "workflow_name": "Gmail Customer Reply Workflow",
    "goal": "Handle new customer enquiries from Gmail and prepare safe follow-up actions.",
    "requires_clarification": False,
    "connectors_required": ["gmail"],
    "missing_connectors": [],
    "steps": [
        {
            "step_id": "trigger_new_gmail",
            "node_type": "gmail.read",
            "label": "Watch Gmail inbox",
            "config": {
                "account": "newcustomer@kevin.com",
                "trigger": "new_email",
            },
            "risk_tier": "low",
            "requires_approval": False,
        },
        {
            "step_id": "extract_customer_details",
            "node_type": "extract_fields",
            "label": "Extract customer details",
            "config": {
                "fields": ["name", "email", "phone"],
            },
            "risk_tier": "low",
            "requires_approval": False,
        },
        {
            "step_id": "compose_welcome_email",
            "node_type": "compose_string",
            "label": "Draft welcome email text",
            "config": {
                "template": "Hi {{extract_customer_details.name}}, thanks for your enquiry.",
            },
            "risk_tier": "low",
            "requires_approval": False,
        },
        {
            "step_id": "approval_before_draft",
            "node_type": "human_approval",
            "label": "Approve before creating draft",
            "config": {
                "reason": "External customer reply requires approval.",
            },
            "risk_tier": "medium",
            "requires_approval": True,
        },
        {
            "step_id": "create_gmail_draft",
            "node_type": "gmail.create_draft",
            "label": "Create Gmail draft",
            "config": {
                "to": "{{extract_customer_details.email}}",
                "body": "{{compose_welcome_email.output}}",
            },
            "risk_tier": "medium",
            "requires_approval": True,
        },
    ],
    "edges": [
        ["trigger_new_gmail", "extract_customer_details"],
        ["extract_customer_details", "compose_welcome_email"],
        ["compose_welcome_email", "approval_before_draft"],
        ["approval_before_draft", "create_gmail_draft"],
    ],
}


INVALID_SPEC_UNKNOWN_NODE = {
    "schema_version": "aion.workflow_builder_spec.v1",
    "workflow_name": "Unsafe Workflow",
    "goal": "Use unknown tool.",
    "requires_clarification": False,
    "connectors_required": [],
    "missing_connectors": [],
    "steps": [
        {
            "step_id": "bad",
            "node_type": "external.random_tool",
            "label": "Unknown tool",
            "config": {},
            "risk_tier": "low",
            "requires_approval": False,
        }
    ],
    "edges": [],
}


def test_vague_goal_detection_requires_clarification() -> None:
    assert is_vague_workflow_goal("customer replies") is True
    assert is_vague_workflow_goal(
        "When a new Gmail email arrives, extract details, create a HubSpot lead, and draft a reply."
    ) is False


def test_clarification_questions_include_trigger_steps_connectors_and_approval() -> None:
    questions = clarification_questions_for_goal("customer replies")
    ids = {item["id"] for item in questions}

    assert {"trigger", "steps", "connectors", "approval"}.issubset(ids)


def test_repair_loop_returns_clarification_questions_for_vague_goal() -> None:
    result = WorkflowArchitectRepairLoop().build_with_repair(
        workflow_goal="customer replies",
        connected_credentials=["gmail"],
    )

    out = result.to_dict()

    assert out["ok"] is False
    assert "clarification_required:vague_workflow_goal" in out["errors"]
    assert out["clarification_questions"]
    assert out["review"] == {}


def test_valid_provider_spec_passes_without_repair() -> None:
    adapter = MockWorkflowBuilderProviderAdapter(response=VALID_SPEC)

    result = WorkflowArchitectRepairLoop(adapter=adapter).build_with_repair(
        workflow_goal="When a new Gmail email arrives, extract details and create a safe draft reply.",
        connected_credentials=["gmail"],
    )

    out = result.to_dict()

    assert out["ok"] is True
    assert out["repair_attempts"] == 0
    assert out["review"]["ok"] is True
    assert out["review"]["dry_run"]["ok"] is True


def test_invalid_provider_spec_fails_closed_without_repair_adapter() -> None:
    adapter = MockWorkflowBuilderProviderAdapter(response=INVALID_SPEC_UNKNOWN_NODE)

    result = WorkflowArchitectRepairLoop(adapter=adapter).build_with_repair(
        workflow_goal="When a new Gmail email arrives, use a suspicious external tool.",
        connected_credentials=["gmail"],
    )

    out = result.to_dict()

    assert out["ok"] is False
    assert "repair_not_attempted" in out["errors"]
    assert "unknown_node_type:external.random_tool" in out["errors"]


def test_invalid_provider_spec_can_be_repaired_then_validated() -> None:
    adapter = MockWorkflowBuilderProviderAdapter(response=INVALID_SPEC_UNKNOWN_NODE)
    repair_adapter = MockWorkflowBuilderProviderAdapter(response=VALID_SPEC)

    result = WorkflowArchitectRepairLoop(
        adapter=adapter,
        repair_adapter=repair_adapter,
        max_repair_attempts=1,
    ).build_with_repair(
        workflow_goal="When a new Gmail email arrives, extract details and create a safe draft reply.",
        connected_credentials=["gmail"],
    )

    out = result.to_dict()

    assert out["ok"] is True
    assert out["repair_attempts"] == 1
    assert out["review"]["ok"] is True


def test_repair_attempt_limit_fails_closed() -> None:
    adapter = MockWorkflowBuilderProviderAdapter(response=INVALID_SPEC_UNKNOWN_NODE)
    repair_adapter = MockWorkflowBuilderProviderAdapter(response=INVALID_SPEC_UNKNOWN_NODE)

    result = WorkflowArchitectRepairLoop(
        adapter=adapter,
        repair_adapter=repair_adapter,
        max_repair_attempts=1,
    ).build_with_repair(
        workflow_goal="When a new Gmail email arrives, extract details and create a safe draft reply.",
        connected_credentials=["gmail"],
    )

    out = result.to_dict()

    assert out["ok"] is False
    assert out["repair_attempts"] == 1
    assert "repair_attempt_limit_reached" in out["errors"]
    assert "unknown_node_type:external.random_tool" in out["errors"]


def test_repair_loop_never_allows_live_send_tokens() -> None:
    unsafe_live_send = {
        **VALID_SPEC,
        "steps": [
            {
                "step_id": "live_send",
                "node_type": "gmail.live_send",
                "label": "Live send",
                "config": {"method": "users.messages.send"},
                "risk_tier": "high",
                "requires_approval": True,
            }
        ],
        "edges": [],
    }

    adapter = MockWorkflowBuilderProviderAdapter(response=unsafe_live_send)

    result = WorkflowArchitectRepairLoop(adapter=adapter).build_with_repair(
        workflow_goal="When a new Gmail email arrives, send a reply.",
        connected_credentials=["gmail"],
    )

    out = result.to_dict()

    assert out["ok"] is False

    combined = str(out).lower()
    assert "unknown_node_type:gmail.live_send" in combined or "live_send" in combined
    assert out["review"]["ok"] is False
