from backend.modules.workflow_capsules.architect.builder_spec import (
    WorkflowBuilderSpec,
    WorkflowEdgeSpec,
    WorkflowStepSpec,
)
from backend.modules.workflow_capsules.architect.spec_validator import (
    WorkflowBuilderSpecValidator,
)


def _spec(*steps: WorkflowStepSpec) -> WorkflowBuilderSpec:
    return WorkflowBuilderSpec(
        workflow_name="gmail_validator_lock",
        goal="Validate Gmail connector safety rules",
        steps=list(steps),
        edges=[
            WorkflowEdgeSpec(source=steps[index].step_id, target=steps[index + 1].step_id)
            for index in range(len(steps) - 1)
        ],
    )


def _approval(step_id: str = "approval") -> WorkflowStepSpec:
    return WorkflowStepSpec(
        step_id=step_id,
        node_type="human_approval",
        label="Human approval",
        config={"reason": "Review before external write."},
        requires_approval=True,
    )


def test_gmail_create_draft_requires_approval_checkpoint() -> None:
    spec = _spec(
        WorkflowStepSpec(
            step_id="create_draft",
            node_type="gmail.create_draft",
            label="Create Gmail draft",
            connector="gmail",
            config={
                "to": "{{lead_email}}",
                "body": "Hello",
                "permission": {"action": "gmail.create_draft"},
            },
        ),
    )

    result = WorkflowBuilderSpecValidator().validate(spec, connected_credentials=["gmail"])

    assert result.ok is False
    assert "gmail_create_draft_without_approval:create_draft" in result.errors
    assert "external_write_without_approval_checkpoint" in result.errors


def test_gmail_create_draft_valid_with_approval() -> None:
    spec = _spec(
        _approval(),
        WorkflowStepSpec(
            step_id="create_draft",
            node_type="gmail.create_draft",
            label="Create Gmail draft",
            connector="gmail",
            config={
                "to": "{{lead_email}}",
                "body": "Hello",
                "permission": {
                    "action": "gmail.create_draft",
                    "requires_approval": True,
                },
            },
            requires_approval=True,
        ),
    )

    result = WorkflowBuilderSpecValidator().validate(spec, connected_credentials=["gmail"])

    assert result.ok is True
    assert result.errors == []


def test_gmail_live_send_family_is_blocked_even_if_provider_invents_action() -> None:
    for action in ["gmail.send_email", "gmail.reply_email", "gmail.send_draft"]:
        spec = _spec(
            _approval(),
            WorkflowStepSpec(
                step_id=f"bad_{action.split('.')[-1]}",
                node_type="gmail.create_draft",
                label="Bad Gmail action",
                connector="gmail",
                config={
                    "to": "{{lead_email}}",
                    "body": "Hello",
                    "permission": {"action": action},
                },
                requires_approval=True,
            ),
        )

        result = WorkflowBuilderSpecValidator().validate(spec, connected_credentials=["gmail"])

        assert result.ok is False
        assert any(error.startswith("forbidden_token:") for error in result.errors)
        assert f"blocked_gmail_action:bad_{action.split('.')[-1]}:{action}" in result.errors


def test_gmail_api_call_is_blocked() -> None:
    spec = _spec(
        _approval(),
        WorkflowStepSpec(
            step_id="gmail_api_call",
            node_type="gmail.create_draft",
            label="Gmail API call",
            connector="gmail",
            config={
                "to": "{{lead_email}}",
                "body": "Hello",
                "permission": {"action": "gmail.api_call"},
            },
            requires_approval=True,
        ),
    )

    result = WorkflowBuilderSpecValidator().validate(spec, connected_credentials=["gmail"])

    assert result.ok is False
    assert "blocked_gmail_action:gmail_api_call:gmail.api_call" in result.errors


def test_unknown_connector_action_is_rejected() -> None:
    spec = _spec(
        _approval(),
        WorkflowStepSpec(
            step_id="invented",
            node_type="gmail.create_draft",
            label="Invented Gmail action",
            connector="gmail",
            config={
                "to": "{{lead_email}}",
                "body": "Hello",
                "permission": {"action": "gmail.magic_thing"},
            },
            requires_approval=True,
        ),
    )

    result = WorkflowBuilderSpecValidator().validate(spec, connected_credentials=["gmail"])

    assert result.ok is False
    assert "unknown_connector_action:invented:gmail.magic_thing" in result.errors
