from __future__ import annotations

from backend.modules.workflow_capsules.connectors.workflow_connector_adapter import (
    WorkflowConnectorAdapter,
)
from backend.modules.workflow_capsules.execution.workflow_capsule_runner import (
    WorkflowCapsuleRunner,
)


def test_gmail_connector_adapter_blocks_read_without_vault() -> None:
    adapter = WorkflowConnectorAdapter()

    result = adapter.read(
        connector="gmail",
        step={
            "step_id": "read_email",
            "output_ref": "email.raw",
            "requires": ["vault.gmail.credentials"],
        },
        inputs={"gmail_message_id": "demo-message-001"},
        available_vault_requirements=[],
    )

    assert result.ok is False
    assert result.status == "blocked_missing_vault"
    assert "missing_vault_requirement:vault.gmail.credentials" in result.errors


def test_gmail_connector_adapter_simulates_read_with_vault() -> None:
    adapter = WorkflowConnectorAdapter()

    result = adapter.read(
        connector="gmail",
        step={
            "step_id": "read_email",
            "output_ref": "email.raw",
            "requires": ["vault.gmail.credentials"],
        },
        inputs={"gmail_message_id": "demo-message-001"},
        available_vault_requirements=["vault.gmail.credentials"],
    )

    assert result.ok is True
    assert result.connector == "gmail"
    assert result.action == "read"
    assert result.status == "simulated_read"
    assert result.output_ref == "email.raw"
    assert result.payload["gmail_message_id"] == "demo-message-001"
    assert "no Gmail API call performed" in result.payload["note"]


def test_gmail_external_write_ready_requires_approval_and_vault() -> None:
    adapter = WorkflowConnectorAdapter()

    blocked_no_approval = adapter.external_write_ready(
        connector="gmail",
        step={
            "step_id": "send_email_after_approval",
            "output_ref": "gmail.send_result",
            "requires": ["vault.gmail.credentials"],
        },
        approval={"status": "pending"},
        available_vault_requirements=["vault.gmail.credentials"],
    )

    assert blocked_no_approval.ok is False
    assert blocked_no_approval.status == "blocked_missing_approval"

    blocked_no_vault = adapter.external_write_ready(
        connector="gmail",
        step={
            "step_id": "send_email_after_approval",
            "output_ref": "gmail.send_result",
            "requires": ["vault.gmail.credentials"],
        },
        approval={"status": "approved"},
        available_vault_requirements=[],
    )

    assert blocked_no_vault.ok is False
    assert blocked_no_vault.status == "blocked_missing_vault"
    assert "missing_vault_requirement:vault.gmail.credentials" in blocked_no_vault.errors

    ready = adapter.external_write_ready(
        connector="gmail",
        step={
            "step_id": "send_email_after_approval",
            "output_ref": "gmail.send_result",
            "requires": ["vault.gmail.credentials"],
        },
        approval={"status": "approved"},
        available_vault_requirements=["vault.gmail.credentials"],
    )

    assert ready.ok is True
    assert ready.connector == "gmail"
    assert ready.action == "external_write_ready"
    assert ready.status == "simulated_external_write_ready"
    assert ready.output_ref == "gmail.send_result"
    assert ready.payload["ready"] is True
    assert ready.payload["external_write"] == "gmail.send"
    assert "Real Gmail send is intentionally not wired" in ready.payload["message"]


def test_runner_resume_after_approval_uses_connector_adapter() -> None:
    runner = WorkflowCapsuleRunner()

    dry = runner.run_dry(
        "WG-001",
        inputs={"gmail_message_id": "demo-message-001"},
        available_vault_requirements=[],
        cau_state={
            "allow_learn": False,
            "adr_active": False,
            "deny_reason": "pytest_connector_binding_no_learning",
        },
        extra={"pytest": True, "stage": "connector_binding"},
    )

    assert dry.ok is True
    assert dry.approval["ok"] is True
    assert dry.approval["status"] == "pending"

    approval_id = dry.approval["approval_id"]

    approved = runner.approve(
        approval_id,
        decided_by="pytest",
        reason="pytest connector binding approval",
    )

    assert approved["ok"] is True
    assert approved["status"] == "approved"

    blocked = runner.resume_after_approval(
        approval_id,
        available_vault_requirements=[],
        cau_state={"allow_learn": False},
    )

    assert blocked["ok"] is False
    assert blocked["error"] == "missing_vault_requirements"
    assert "vault.gmail.credentials" in blocked["missing_vault_requirements"]

    ready = runner.resume_after_approval(
        approval_id,
        available_vault_requirements=["vault.gmail.credentials"],
        cau_state={"allow_learn": False},
    )

    assert ready["ok"] is True
    assert ready["schema_version"] == "aion.workflow_capsule_resume_result.v1"
    assert ready["phase"] == "resume_after_approval"
    assert ready["canonical_key"] == "workflow:gmail.enquiry_reply.v1"
    assert ready["executed_external_step"] == "send_email_after_approval"
    assert ready["status"] == "simulated_external_write_ready"

    connector_result = ready["connector_result"]
    assert connector_result["ok"] is True
    assert connector_result["connector"] == "gmail"
    assert connector_result["action"] == "external_write_ready"
    assert connector_result["status"] == "simulated_external_write_ready"
    assert connector_result["payload"]["ready"] is True
    assert "Real Gmail send is intentionally not wired" in connector_result["payload"]["message"]
