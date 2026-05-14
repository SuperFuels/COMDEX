from __future__ import annotations

import json

from backend.modules.workflow_capsules.architect import (
    MockWorkflowBuilderProviderAdapter,
    PlaceholderWorkflowBuilderProviderAdapter,
    ProviderJSONParser,
    WorkflowArchitectProviderOrchestrator,
    WorkflowBuildPackAssembler,
)


def test_provider_json_parser_accepts_strict_json() -> None:
    data = ProviderJSONParser.parse('{"schema_version":"aion.workflow_builder_spec.v1"}')

    assert data["schema_version"] == "aion.workflow_builder_spec.v1"


def test_provider_json_parser_accepts_fenced_json() -> None:
    data = ProviderJSONParser.parse(
        """```json
{"schema_version":"aion.workflow_builder_spec.v1","workflow_name":"Demo"}
```"""
    )

    assert data["workflow_name"] == "Demo"


def test_mock_provider_receives_build_pack_and_returns_spec() -> None:
    pack = WorkflowBuildPackAssembler().assemble(
        workflow_goal="Create a Gmail reply workflow.",
        connected_credentials=["gmail"],
        missing_credentials=["hubspot"],
    )

    response = MockWorkflowBuilderProviderAdapter().build_spec(pack)
    out = response.to_dict()

    assert out["ok"] is True
    assert out["provider"] == "mock"
    assert out["model"] == "mock-workflow-builder-v1"
    assert out["spec"]["schema_version"] == "aion.workflow_builder_spec.v1"
    assert out["audit"]["build_pack_received"] is True
    assert out["audit"]["node_registry_present"] is True
    assert out["audit"]["step_count"] >= 1


def test_mock_provider_invalid_json_fails_closed() -> None:
    pack = WorkflowBuildPackAssembler().assemble(
        workflow_goal="Create a Gmail reply workflow.",
        connected_credentials=["gmail"],
    )

    response = MockWorkflowBuilderProviderAdapter(
        response="this is not json"
    ).build_spec(pack)

    out = response.to_dict()

    assert out["ok"] is False
    assert out["spec"] is None
    assert any("provider_json_parse_failed" in error for error in out["errors"])


def test_placeholder_provider_fails_closed() -> None:
    pack = WorkflowBuildPackAssembler().assemble(
        workflow_goal="Create a Gmail reply workflow.",
        connected_credentials=["gmail"],
    )

    response = PlaceholderWorkflowBuilderProviderAdapter(
        provider="openai",
        model="placeholder",
    ).build_spec(pack)

    out = response.to_dict()

    assert out["ok"] is False
    assert out["provider"] == "openai"
    assert "provider_not_implemented:openai" in out["errors"]
    assert out["audit"]["fail_closed"] is True


def test_provider_orchestrator_mock_builds_valid_review_payload() -> None:
    result = WorkflowArchitectProviderOrchestrator().build_and_review(
        workflow_goal="Create a Gmail customer reply workflow.",
        business_context={
            "business_name": "Demo Business",
            "industry": "local services",
        },
        connected_credentials=["gmail"],
        inputs={"gmail_message_id": "provider-adapter-test"},
    )

    out = result.to_dict()

    assert out["ok"] is True
    assert out["provider"]["provider"] == "mock"
    assert out["provider"]["spec"]["schema_version"] == "aion.workflow_builder_spec.v1"
    assert out["review"]["phase"] == "architect_review"
    assert out["review"]["review"]["dry_run_only"] is True
    assert out["review"]["review"]["live_send_enabled"] is False
    assert out["build_pack"]["permission_runtime_rules"]["live_send_disabled"] is True

    combined = str(out).lower()
    assert "users.messages.send" not in combined
    assert "send_message" not in combined
    assert "gmail_live_send" not in combined


def test_provider_orchestrator_placeholder_provider_does_not_reach_review_runner() -> None:
    adapter = PlaceholderWorkflowBuilderProviderAdapter(
        provider="claude",
        model="placeholder",
    )

    result = WorkflowArchitectProviderOrchestrator(adapter=adapter).build_and_review(
        workflow_goal="Create a Gmail customer reply workflow.",
        connected_credentials=["gmail"],
    )

    out = result.to_dict()

    assert out["ok"] is False
    assert out["review"] == {}
    assert "provider_not_implemented:claude" in out["errors"]


def test_provider_output_with_unknown_node_fails_during_review_validation() -> None:
    unsafe_response = {
        "schema_version": "aion.workflow_builder_spec.v1",
        "workflow_name": "Unsafe Unknown Tool Workflow",
        "goal": "Use an unknown tool.",
        "requires_clarification": False,
        "connectors_required": [],
        "missing_connectors": [],
        "steps": [
            {
                "step_id": "unknown",
                "node_type": "external.random_tool",
                "label": "Unknown tool",
                "config": {},
                "risk_tier": "low",
                "requires_approval": False,
            }
        ],
        "edges": [],
    }

    adapter = MockWorkflowBuilderProviderAdapter(response=unsafe_response)

    result = WorkflowArchitectProviderOrchestrator(adapter=adapter).build_and_review(
        workflow_goal="Create unsafe unknown workflow.",
        connected_credentials=[],
    )

    out = result.to_dict()

    assert out["ok"] is False
    assert out["provider"]["ok"] is True
    assert "unknown_node_type:external.random_tool" in out["errors"]
