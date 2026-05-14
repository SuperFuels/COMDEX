from __future__ import annotations

from backend.modules.workflow_capsules.connectors.workflow_connector_adapter import (
    WorkflowConnectorAdapter,
)
from backend.modules.workflow_capsules.execution.workflow_capsule_runner import (
    WorkflowCapsuleRunner,
)


SEND_STEP = {
    "step_id": "send_email_after_approval",
    "output_ref": "gmail.send_result",
    "requires": ["vault.gmail.credentials"],
}


def test_connector_ready_mode_is_simulated_and_safe() -> None:
    adapter = WorkflowConnectorAdapter()

    result = adapter.external_write_ready(
        connector="gmail",
        step=SEND_STEP,
        approval={"status": "approved"},
        available_vault_requirements=["vault.gmail.credentials"],
        execution_mode="connector_ready",
    )

    assert result.ok is True
    assert result.status == "simulated_external_write_ready"
    assert result.payload["execution_mode"] == "connector_ready"
    assert "Real Gmail send is intentionally not wired" in result.payload["message"]


def test_live_execute_requires_env_guard(monkeypatch) -> None:
    monkeypatch.delenv("AION_WORKFLOW_GMAIL_ALLOW_LIVE_SEND", raising=False)

    adapter = WorkflowConnectorAdapter()

    result = adapter.external_write_ready(
        connector="gmail",
        step=SEND_STEP,
        approval={"status": "approved"},
        available_vault_requirements=["vault.gmail.credentials"],
        execution_mode="live_execute",
    )

    assert result.ok is False
    assert result.status == "blocked_live_env_guard"
    assert "missing_env_guard:AION_WORKFLOW_GMAIL_ALLOW_LIVE_SEND=1" in result.errors


def test_live_execute_still_blocks_until_real_gmail_is_implemented(monkeypatch) -> None:
    monkeypatch.setenv("AION_WORKFLOW_GMAIL_ALLOW_LIVE_SEND", "1")

    adapter = WorkflowConnectorAdapter()

    result = adapter.external_write_ready(
        connector="gmail",
        step=SEND_STEP,
        approval={"status": "approved"},
        available_vault_requirements=["vault.gmail.credentials"],
        execution_mode="live_execute",
    )

    assert result.ok is False
    assert result.status == "blocked_live_connector_not_implemented"
    assert "gmail_live_send_not_implemented" in result.errors


def test_runner_live_execute_does_not_send_and_returns_guarded_block(monkeypatch) -> None:
    monkeypatch.setenv("AION_WORKFLOW_GMAIL_ALLOW_LIVE_SEND", "1")

    runner = WorkflowCapsuleRunner()

    dry = runner.run_dry(
        "WG-001",
        inputs={"gmail_message_id": "demo-message-001"},
        available_vault_requirements=[],
        cau_state={
            "allow_learn": False,
            "adr_active": False,
            "deny_reason": "pytest_live_guard_no_learning",
        },
        extra={"pytest": True, "stage": "live_guard"},
    )

    assert dry.ok is True
    approval_id = dry.approval["approval_id"]

    approved = runner.approve(
        approval_id,
        decided_by="pytest",
        reason="pytest live guard check",
    )
    assert approved["ok"] is True

    result = runner.resume_after_approval(
        approval_id,
        available_vault_requirements=["vault.gmail.credentials"],
        cau_state={"allow_learn": False},
        execution_mode="live_execute",
    )

    assert result["ok"] is False
    assert result["execution_mode"] == "live_execute"
    assert result["error"] == "blocked_live_connector_not_implemented"
    assert result["connector_result"]["status"] == "blocked_live_connector_not_implemented"
