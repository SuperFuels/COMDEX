from __future__ import annotations

from backend.modules.workflow_capsules.architect import (
    MissingConnectorWarning,
    WorkflowArchitectReviewRunner,
    WorkflowBuilderSpec,
    WorkflowEdgeSpec,
    WorkflowStepSpec,
)


def _spec() -> WorkflowBuilderSpec:
    return WorkflowBuilderSpec(
        workflow_name="Architect Review Gmail Workflow",
        goal="Review generated Gmail customer reply workflow before runtime execution.",
        connectors_required=["gmail", "hubspot", "calendly"],
        missing_connectors=[
            MissingConnectorWarning(
                connector="calendly",
                reason="Calendly is not connected.",
                step_id="calendly_placeholder",
            )
        ],
        steps=[
            WorkflowStepSpec(
                step_id="read_gmail",
                node_type="gmail.read",
                label="Read Gmail",
                connector="gmail",
                config={"account": "newcustomer@example.com", "trigger": "new_email"},
                risk_tier="low",
            ),
            WorkflowStepSpec(
                step_id="extract_fields",
                node_type="extract_fields",
                label="Extract customer fields",
                config={"fields": ["name", "email", "phone"]},
                risk_tier="low",
            ),
            WorkflowStepSpec(
                step_id="hubspot_upsert",
                node_type="hubspot.upsert_contact",
                label="Create HubSpot contact",
                connector="hubspot",
                config={"email": "{{extract_fields.email}}"},
                risk_tier="medium",
            ),
            WorkflowStepSpec(
                step_id="compose_reply",
                node_type="compose_string",
                label="Compose reply",
                config={"template_ref": "welcome_email_template"},
                risk_tier="low",
            ),
            WorkflowStepSpec(
                step_id="approval",
                node_type="human_approval",
                label="Approve draft creation",
                config={"reason": "Approval required before customer-facing draft."},
                risk_tier="medium",
                requires_approval=True,
            ),
            WorkflowStepSpec(
                step_id="create_draft",
                node_type="gmail.create_draft",
                label="Create Gmail draft",
                connector="gmail",
                config={
                    "to": "{{extract_fields.email}}",
                    "body": "{{compose_reply.output}}",
                },
                risk_tier="medium",
                requires_approval=True,
            ),
            WorkflowStepSpec(
                step_id="calendly_placeholder",
                node_type="missing_connector_placeholder",
                label="Calendly placeholder",
                connector="calendly",
                config={
                    "connector": "calendly",
                    "reason": "Calendly is missing.",
                },
                risk_tier="blocked",
                requires_approval=True,
                missing_connector=True,
            ),
        ],
        edges=[
            WorkflowEdgeSpec("read_gmail", "extract_fields"),
            WorkflowEdgeSpec("extract_fields", "hubspot_upsert"),
            WorkflowEdgeSpec("hubspot_upsert", "compose_reply"),
            WorkflowEdgeSpec("compose_reply", "approval"),
            WorkflowEdgeSpec("approval", "create_draft"),
            WorkflowEdgeSpec("extract_fields", "calendly_placeholder"),
        ],
    )


def test_architect_review_runner_returns_canvas_capsule_and_dry_run_review() -> None:
    result = WorkflowArchitectReviewRunner().run_review(
        _spec(),
        connected_credentials=["gmail", "hubspot"],
        inputs={"gmail_message_id": "architect-review-test-message"},
    )

    out = result.to_dict()

    assert out["ok"] is True
    assert out["phase"] == "architect_review"

    assert out["validation"]["ok"] is True
    assert out["canvas"]["display_name"] == "Architect Review Gmail Workflow"
    assert out["capsule"]["canonical_key"].startswith("workflow:architect.")
    assert out["capsule"]["dry_run_first"] is True

    assert out["review"]["workflow_name"] == "Architect Review Gmail Workflow"
    assert out["review"]["dry_run_only"] is True
    assert out["review"]["live_send_enabled"] is False
    assert out["review"]["canvas_ready"] is True
    assert out["review"]["approval_required"] is True
    assert out["review"]["external_writes_blocked"] is True

    missing = out["review"]["missing_connectors"]
    assert missing[0]["connector"] == "calendly"

    combined = str(out).lower()
    assert "users.messages.send" not in combined
    assert "send_message" not in combined
    assert "gmail_live_send" not in combined
    assert out["review"]["live_send_enabled"] is False


def test_architect_review_runner_fails_closed_for_invalid_spec() -> None:
    spec = _spec()
    spec.steps[0].node_type = "unknown.node"

    result = WorkflowArchitectReviewRunner().run_review(
        spec,
        connected_credentials=["gmail", "hubspot"],
    )

    out = result.to_dict()

    assert out["ok"] is False
    assert out["validation"]["ok"] is False
    assert "unknown_node_type:unknown.node" in out["errors"]
    assert out["dry_run"] == {}
