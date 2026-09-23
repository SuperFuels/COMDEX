from __future__ import annotations

import json

from backend.modules.workflow_capsules.architect.build_pack import WorkflowBuildPackAssembler
from backend.modules.workflow_capsules.architect.openai_provider_adapter import (
    OpenAIWorkflowBuilderProviderAdapter,
)
from backend.modules.workflow_capsules.architect.repair_loop import WorkflowArchitectRepairLoop


VALID_SPEC = {
    "schema_version": "aion.workflow_builder_spec.v1",
    "workflow_name": "OpenAI Generated Gmail Draft Workflow",
    "goal": "Handle Gmail enquiries safely by creating a draft only.",
    "requires_clarification": False,
    "connectors_required": ["gmail"],
    "missing_connectors": [],
    "steps": [
        {
            "step_id": "read_gmail",
            "node_type": "gmail.read",
            "label": "Read Gmail",
            "config": {"account": "newcustomer@example.com", "trigger": "new_email"},
            "risk_tier": "low",
            "requires_approval": False,
        },
        {
            "step_id": "approval",
            "node_type": "human_approval",
            "label": "Approve draft",
            "config": {"reason": "Approval before external customer-facing action."},
            "risk_tier": "medium",
            "requires_approval": True,
        },
        {
            "step_id": "create_draft",
            "node_type": "gmail.create_draft",
            "label": "Create draft",
            "config": {"to": "{{read_gmail.sender}}", "body": "Thanks for your enquiry."},
            "risk_tier": "medium",
            "requires_approval": True,
        },
    ],
    "edges": [
        ["read_gmail", "approval"],
        ["approval", "create_draft"],
    ],
}


def _build_pack():
    return WorkflowBuildPackAssembler().assemble(
        workflow_goal="When a new Gmail email arrives, create a safe draft reply after approval.",
        user_steps=[],
        business_context={"business_name": "Tessaris AI"},
        connected_credentials=["gmail"],
        missing_credentials=[],
        must_not_do=["do not send live emails"],
    )


def test_openai_provider_fails_closed_without_api_key(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("AION_WORKFLOW_ARCHITECT_OPENAI_NETWORK", raising=False)

    adapter = OpenAIWorkflowBuilderProviderAdapter(api_key="")
    result = adapter.build_spec(_build_pack())
    out = result.to_dict()

    assert out["ok"] is False
    assert out["provider"] == "openai"
    assert "provider_not_configured:openai" in out["errors"]
    assert out["audit"]["network_call_attempted"] is False


def test_openai_provider_makes_no_network_call_in_test_mode(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.delenv("AION_WORKFLOW_ARCHITECT_OPENAI_NETWORK", raising=False)

    adapter = OpenAIWorkflowBuilderProviderAdapter()
    result = adapter.build_spec(_build_pack())
    out = result.to_dict()

    assert out["ok"] is False
    assert "provider_network_disabled:openai" in out["errors"]
    assert out["audit"]["network_call_attempted"] is False
    assert out["audit"]["build_pack_received"] is True
    assert out["audit"]["strict_json_only"] is True


def test_openai_provider_rejects_malformed_json() -> None:
    adapter = OpenAIWorkflowBuilderProviderAdapter(
        api_key="test-key",
        raw_response_text="{not valid json",
    )

    result = adapter.build_spec(_build_pack())
    out = result.to_dict()

    assert out["ok"] is False
    assert any(error.startswith("provider_json_parse_failed") for error in out["errors"])
    assert out["audit"]["network_call_attempted"] is False


def test_openai_provider_valid_json_returns_provider_response() -> None:
    adapter = OpenAIWorkflowBuilderProviderAdapter(
        api_key="test-key",
        raw_response_text=json.dumps(VALID_SPEC),
    )

    result = adapter.build_spec(_build_pack())
    out = result.to_dict()

    assert out["ok"] is True
    assert out["provider"] == "openai"
    assert out["spec"]["workflow_name"] == "OpenAI Generated Gmail Draft Workflow"
    assert out["audit"]["build_pack_received"] is True
    assert out["audit"]["strict_json_only"] is True


def test_openai_live_send_output_is_rejected_by_normal_validator() -> None:
    unsafe_spec = {
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

    adapter = OpenAIWorkflowBuilderProviderAdapter(
        api_key="test-key",
        raw_response_text=json.dumps(unsafe_spec),
    )

    result = WorkflowArchitectRepairLoop(adapter=adapter).build_with_repair(
        workflow_goal="When a new Gmail email arrives, send a reply.",
        connected_credentials=["gmail"],
    )

    out = result.to_dict()
    combined = str(out).lower()

    assert out["ok"] is False
    assert "live_send" in combined
    assert "users.messages.send" in combined or "unknown_node_type:gmail.live_send" in combined
    assert out["review"]["ok"] is False
