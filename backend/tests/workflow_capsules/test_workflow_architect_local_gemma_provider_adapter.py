from __future__ import annotations

import json

from backend.modules.workflow_capsules.architect.build_pack import WorkflowBuildPackAssembler
from backend.modules.workflow_capsules.architect.local_gemma_provider_adapter import (
    LocalGemmaWorkflowBuilderProviderAdapter,
)
from backend.modules.workflow_capsules.architect.repair_loop import WorkflowArchitectRepairLoop


VALID_SPEC = {
    "schema_version": "aion.workflow_builder_spec.v1",
    "workflow_name": "Local Gemma Gmail Draft Workflow",
    "goal": "Handle new Gmail enquiries and prepare a safe draft reply.",
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
            "step_id": "extract_fields",
            "node_type": "extract_fields",
            "label": "Extract fields",
            "config": {"fields": ["name", "email", "phone"]},
            "risk_tier": "low",
            "requires_approval": False,
        },
        {
            "step_id": "compose_reply",
            "node_type": "compose_string",
            "label": "Compose reply",
            "config": {"template": "Hi {{extract_fields.name}}, thanks for your enquiry."},
            "risk_tier": "low",
            "requires_approval": False,
        },
        {
            "step_id": "approval",
            "node_type": "human_approval",
            "label": "Approve draft",
            "config": {"reason": "Approval required before customer-facing draft."},
            "risk_tier": "medium",
            "requires_approval": True,
        },
        {
            "step_id": "create_draft",
            "node_type": "gmail.create_draft",
            "label": "Create Gmail draft",
            "config": {"to": "{{extract_fields.email}}", "body": "{{compose_reply.output}}"},
            "risk_tier": "medium",
            "requires_approval": True,
        },
    ],
    "edges": [
        ["read_gmail", "extract_fields"],
        ["extract_fields", "compose_reply"],
        ["compose_reply", "approval"],
        ["approval", "create_draft"],
    ],
}


def _build_pack():
    return WorkflowBuildPackAssembler().assemble(
        workflow_goal="When a new Gmail email arrives, extract details and create a safe draft reply.",
        connected_credentials=["gmail"],
    )


def test_local_gemma_fails_closed_when_not_enabled() -> None:
    adapter = LocalGemmaWorkflowBuilderProviderAdapter(enabled=False)

    result = adapter.build_spec(_build_pack())
    out = result.to_dict()

    assert out["ok"] is False
    assert out["provider"] == "local_gemma"
    assert "provider_not_configured:local_gemma" in out["errors"]
    assert out["audit"]["network_call_attempted"] is False


def test_local_gemma_test_mode_does_not_make_network_call() -> None:
    adapter = LocalGemmaWorkflowBuilderProviderAdapter(
        enabled=False,
        raw_response_text=json.dumps(VALID_SPEC),
    )

    result = adapter.build_spec(_build_pack())
    out = result.to_dict()

    assert out["ok"] is True
    assert out["provider"] == "local_gemma"
    assert out["audit"]["build_pack_received"] is True
    assert out["audit"]["strict_json_only"] is True
    assert out["audit"]["network_call_attempted"] is False


def test_local_gemma_malformed_json_is_rejected() -> None:
    adapter = LocalGemmaWorkflowBuilderProviderAdapter(
        enabled=False,
        raw_response_text="{not valid json",
    )

    result = adapter.build_spec(_build_pack())
    out = result.to_dict()

    assert out["ok"] is False
    assert any("provider_json_parse_failed" in err for err in out["errors"])


def test_local_gemma_valid_json_returns_provider_response() -> None:
    adapter = LocalGemmaWorkflowBuilderProviderAdapter(
        enabled=False,
        raw_response_text=json.dumps(VALID_SPEC),
    )

    result = adapter.build_spec(_build_pack())
    out = result.to_dict()

    assert out["ok"] is True
    assert out["provider"] == "local_gemma"
    assert out["spec"]["workflow_name"] == "Local Gemma Gmail Draft Workflow"
    assert out["audit"]["local_provider"] is True


def test_local_gemma_live_send_output_is_rejected_by_normal_validator() -> None:
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

    adapter = LocalGemmaWorkflowBuilderProviderAdapter(
        enabled=False,
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
