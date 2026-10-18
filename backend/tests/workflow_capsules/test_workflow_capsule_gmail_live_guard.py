from __future__ import annotations

import os

from backend.modules.workflow_capsules.execution.workflow_capsule_runner import WorkflowCapsuleRunner
from backend.modules.workflow_capsules.connectors.workflow_connector_adapter import (
    EXECUTION_MODE_LIVE_EXECUTE,
    LIVE_GMAIL_ENV_GUARD,
)


def _approved_workflow() -> tuple[WorkflowCapsuleRunner, str]:
    runner = WorkflowCapsuleRunner()

    dry = runner.run_dry(
        "WG-001",
        inputs={"gmail_message_id": "live-guard-demo-message"},
        available_vault_requirements=[],
        cau_state={
            "allow_learn": False,
            "adr_active": False,
            "deny_reason": "pytest_gmail_live_guard",
        },
        extra={"pytest": True, "stage": "gmail_live_guard"},
    )

    assert dry.ok is True
    assert dry.approval["status"] == "pending"

    approval_id = dry.approval["approval_id"]

    approved = runner.approve(
        approval_id,
        decided_by="pytest",
        reason="pytest live guard approval",
    )

    assert approved["ok"] is True
    assert approved["status"] == "approved"

    return runner, approval_id


def test_live_execute_is_blocked_without_env_guard(monkeypatch) -> None:
    monkeypatch.delenv(LIVE_GMAIL_ENV_GUARD, raising=False)

    runner, approval_id = _approved_workflow()

    result = runner.resume_after_approval(
        approval_id,
        available_vault_requirements=["vault.gmail.credentials"],
        cau_state={"allow_learn": False},
        execution_mode=EXECUTION_MODE_LIVE_EXECUTE,
    )

    assert result["ok"] is False
    assert result["execution_mode"] == "live_execute"
    assert result["status"] == "blocked_live_env_guard"
    assert result["error"] == "blocked_live_env_guard"
    assert result["connector_result"]["errors"] == [
        f"missing_env_guard:{LIVE_GMAIL_ENV_GUARD}=1"
    ]


def test_live_execute_is_still_blocked_when_env_guard_set_until_real_connector_exists(monkeypatch) -> None:
    monkeypatch.setenv(LIVE_GMAIL_ENV_GUARD, "1")

    runner, approval_id = _approved_workflow()

    result = runner.resume_after_approval(
        approval_id,
        available_vault_requirements=["vault.gmail.credentials"],
        cau_state={"allow_learn": False},
        execution_mode=EXECUTION_MODE_LIVE_EXECUTE,
    )

    assert result["ok"] is False
    assert result["execution_mode"] == "live_execute"
    assert result["status"] == "blocked_live_connector_not_implemented"
    assert result["error"] == "blocked_live_connector_not_implemented"
    assert "gmail_live_send_not_implemented" in result["connector_result"]["errors"]


def test_connector_ready_remains_safe_default_even_with_env_guard_set(monkeypatch) -> None:
    monkeypatch.setenv(LIVE_GMAIL_ENV_GUARD, "1")

    runner, approval_id = _approved_workflow()

    result = runner.resume_after_approval(
        approval_id,
        available_vault_requirements=["vault.gmail.credentials"],
        cau_state={"allow_learn": False},
    )

    assert result["ok"] is True
    assert result["execution_mode"] == "connector_ready"
    assert result["status"] == "simulated_external_write_ready"
    assert result["connector_result"]["payload"]["execution_mode"] == "connector_ready"
