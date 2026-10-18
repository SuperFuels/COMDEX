"""
Workflow Connector Adapter - AION Workflow Glyph Capsules v1
────────────────────────────────────────────────────────────
Safe connector abstraction for workflow capsule execution.

This layer exists so workflow capsules can bind runtime connectors without
storing credentials inside capsules.

MVP safety:
- no live external writes
- Gmail read/draft/send are simulated unless a future real adapter is injected
- send only returns "ready" after approval/vault checks; it does not actually send
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional
import os
import time

from backend.modules.workflow_capsules.connectors.providers.gmail_connector import (
    GMAIL_VAULT_HANDLE,
    GmailWorkflowConnector,
)


SCHEMA_VERSION = "aion.workflow_connector_result.v1"

EXECUTION_MODE_DRY_RUN = "dry_run"
EXECUTION_MODE_CONNECTOR_READY = "connector_ready"
EXECUTION_MODE_LIVE_EXECUTE = "live_execute"
ALLOWED_EXECUTION_MODES = {
    EXECUTION_MODE_DRY_RUN,
    EXECUTION_MODE_CONNECTOR_READY,
    EXECUTION_MODE_LIVE_EXECUTE,
}
LIVE_GMAIL_ENV_GUARD = "AION_WORKFLOW_GMAIL_ALLOW_LIVE_SEND"


@dataclass
class WorkflowConnectorResult:
    ok: bool
    connector: str
    action: str
    schema_version: str = SCHEMA_VERSION

    status: str = "simulated"
    output_ref: Optional[str] = None
    payload: Dict[str, Any] = field(default_factory=dict)

    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    t: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class WorkflowConnectorAdapter:
    """
    Safe connector adapter facade.

    Real connector implementations should be added behind this interface later.
    The workflow runner should call this adapter, not raw Gmail APIs directly.
    """

    def __init__(
        self,
        *,
        gmail_connector: Optional[GmailWorkflowConnector] = None,
    ) -> None:
        self.gmail_connector = gmail_connector or GmailWorkflowConnector()

    def read(
        self,
        *,
        connector: str,
        step: Dict[str, Any],
        inputs: Dict[str, Any],
        available_vault_requirements: Optional[List[str]] = None,
    ) -> WorkflowConnectorResult:
        connector = str(connector or "").strip().lower()
        available_vault_requirements = available_vault_requirements or []

        if connector == "gmail":
            return self._gmail_read(
                step=step,
                inputs=inputs,
                available_vault_requirements=available_vault_requirements,
            )

        return WorkflowConnectorResult(
            ok=False,
            connector=connector or "unknown",
            action="read",
            status="unsupported_connector",
            output_ref=step.get("output_ref"),
            errors=[f"unsupported_connector:{connector or 'unknown'}"],
        )

    def draft(
        self,
        *,
        connector: str,
        step: Dict[str, Any],
        inputs: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> WorkflowConnectorResult:
        connector = str(connector or "").strip().lower()
        context = context or {}

        if connector == "gmail":
            return self._gmail_draft(step=step, inputs=inputs, context=context)

        return WorkflowConnectorResult(
            ok=False,
            connector=connector or "unknown",
            action="draft",
            status="unsupported_connector",
            output_ref=step.get("output_ref"),
            errors=[f"unsupported_connector:{connector or 'unknown'}"],
        )

    def create_draft(
        self,
        *,
        connector: str,
        step: Dict[str, Any],
        inputs: Dict[str, Any],
        approval: Dict[str, Any],
        available_vault_requirements: Optional[List[str]] = None,
        execution_mode: str = EXECUTION_MODE_CONNECTOR_READY,
    ) -> WorkflowConnectorResult:
        connector = str(connector or "").strip().lower()
        available_vault_requirements = available_vault_requirements or []
        execution_mode = str(execution_mode or EXECUTION_MODE_CONNECTOR_READY).strip()

        if connector != "gmail":
            return WorkflowConnectorResult(
                ok=False,
                connector=connector or "unknown",
                action="create_draft",
                status="unsupported_connector",
                output_ref=step.get("output_ref"),
                errors=[f"unsupported_connector:{connector or 'unknown'}"],
            )

        if approval.get("status") != "approved":
            return WorkflowConnectorResult(
                ok=False,
                connector="gmail",
                action="create_draft",
                status="blocked_missing_approval",
                output_ref=step.get("output_ref"),
                errors=["approval_not_approved"],
            )

        if GMAIL_VAULT_HANDLE not in set(available_vault_requirements or []):
            return WorkflowConnectorResult(
                ok=False,
                connector="gmail",
                action="create_draft",
                status="blocked_missing_vault",
                output_ref=step.get("output_ref"),
                errors=[f"missing_vault_requirement:{GMAIL_VAULT_HANDLE}"],
            )

        if execution_mode != EXECUTION_MODE_LIVE_EXECUTE:
            return WorkflowConnectorResult(
                ok=False,
                connector="gmail",
                action="create_draft",
                status="blocked_not_live_draft_mode",
                output_ref=step.get("output_ref"),
                errors=["gmail_draft_requires_live_execute_mode"],
                payload={
                    "must_not_send": True,
                    "sent": False,
                    "execution_mode": execution_mode,
                },
            )

        result = self.gmail_connector.create_draft(
            to=str(step.get("to") or inputs.get("to") or inputs.get("lead_email") or ""),
            subject=str(step.get("subject") or inputs.get("subject") or "Draft email"),
            body=str(step.get("body") or inputs.get("body") or ""),
            available_vault_requirements=available_vault_requirements,
            workspace_id=str(inputs.get("workspace_id") or ""),
            live=True,
        ).to_dict()

        ok = bool(result.get("ok"))
        payload = dict(result.get("payload") or {})
        payload.update(
            {
                "message": "Draft created in Gmail. No email was sent." if ok else "Gmail draft creation failed.",
                "sent": False,
                "must_not_send": True,
                "live_send_enabled": False,
            }
        )

        return WorkflowConnectorResult(
            ok=ok,
            connector="gmail",
            action="create_draft",
            status=str(result.get("status") or ("gmail_draft_created" if ok else "gmail_draft_failed")),
            output_ref=step.get("output_ref"),
            payload=payload,
            errors=list(result.get("errors") or []),
            warnings=list(result.get("warnings") or []),
        )

    def external_write_ready(
        self,
        *,
        connector: str,
        step: Dict[str, Any],
        approval: Dict[str, Any],
        available_vault_requirements: Optional[List[str]] = None,
        execution_mode: str = EXECUTION_MODE_CONNECTOR_READY,
    ) -> WorkflowConnectorResult:
        """
        Approval/vault-checked readiness result.

        IMPORTANT:
        This intentionally does not perform the write.
        It only says the write would now be permitted by adapter preconditions.
        """
        connector = str(connector or "").strip().lower()
        available_vault_requirements = available_vault_requirements or []
        execution_mode = str(execution_mode or EXECUTION_MODE_CONNECTOR_READY).strip()

        if execution_mode not in ALLOWED_EXECUTION_MODES:
            return WorkflowConnectorResult(
                ok=False,
                connector=connector or "unknown",
                action="external_write_ready",
                status="blocked_invalid_execution_mode",
                output_ref=step.get("output_ref"),
                errors=[f"invalid_execution_mode:{execution_mode}"],
            )

        if connector == "gmail":
            return self._gmail_send_ready(
                step=step,
                approval=approval,
                available_vault_requirements=available_vault_requirements,
                execution_mode=execution_mode,
            )

        return WorkflowConnectorResult(
            ok=False,
            connector=connector or "unknown",
            action="external_write_ready",
            status="unsupported_connector",
            output_ref=step.get("output_ref"),
            errors=[f"unsupported_connector:{connector or 'unknown'}"],
        )

    def _gmail_read(
        self,
        *,
        step: Dict[str, Any],
        inputs: Dict[str, Any],
        available_vault_requirements: List[str],
    ) -> WorkflowConnectorResult:
        required = list(step.get("requires") or [])
        missing = [r for r in required if r not in available_vault_requirements]

        if missing:
            return WorkflowConnectorResult(
                ok=False,
                connector="gmail",
                action="read",
                status="blocked_missing_vault",
                output_ref=step.get("output_ref"),
                errors=[f"missing_vault_requirement:{r}" for r in missing],
            )

        message_id = (
            inputs.get("gmail_message_id")
            or inputs.get("input.gmail_message_id")
            or "unknown-message"
        )

        return WorkflowConnectorResult(
            ok=True,
            connector="gmail",
            action="read",
            status="simulated_read",
            output_ref=step.get("output_ref"),
            payload={
                "gmail_message_id": message_id,
                "subject": "Simulated Gmail enquiry",
                "from": "customer@example.com",
                "body": "Simulated enquiry body for workflow capsule dry-run.",
                "note": "MVP simulated Gmail read; no Gmail API call performed.",
            },
        )

    def _gmail_draft(
        self,
        *,
        step: Dict[str, Any],
        inputs: Dict[str, Any],
        context: Dict[str, Any],
    ) -> WorkflowConnectorResult:
        return WorkflowConnectorResult(
            ok=True,
            connector="gmail",
            action="draft",
            status="simulated_draft_only",
            output_ref=step.get("output_ref"),
            payload={
                "subject": "Re: your enquiry",
                "body": "Draft reply preview would be generated here for human review.",
                "must_not_send": True,
                "note": "Draft-only adapter path; no email sent.",
            },
        )

    def _gmail_send_ready(
        self,
        *,
        step: Dict[str, Any],
        approval: Dict[str, Any],
        available_vault_requirements: List[str],
        execution_mode: str = EXECUTION_MODE_CONNECTOR_READY,
    ) -> WorkflowConnectorResult:
        required = list(step.get("requires") or [])
        missing = [r for r in required if r not in available_vault_requirements]

        if missing:
            return WorkflowConnectorResult(
                ok=False,
                connector="gmail",
                action="external_write_ready",
                status="blocked_missing_vault",
                output_ref=step.get("output_ref"),
                errors=[f"missing_vault_requirement:{r}" for r in missing],
            )

        if approval.get("status") != "approved":
            return WorkflowConnectorResult(
                ok=False,
                connector="gmail",
                action="external_write_ready",
                status="blocked_missing_approval",
                output_ref=step.get("output_ref"),
                errors=["approval_not_approved"],
            )

        if execution_mode == EXECUTION_MODE_DRY_RUN:
            return WorkflowConnectorResult(
                ok=False,
                connector="gmail",
                action="external_write_ready",
                status="blocked_dry_run_external_write",
                output_ref=step.get("output_ref"),
                errors=["dry_run_blocks_external_write"],
                payload={
                    "ready": False,
                    "external_write": "gmail.send",
                    "execution_mode": execution_mode,
                },
            )

        if execution_mode == EXECUTION_MODE_CONNECTOR_READY:
            return WorkflowConnectorResult(
                ok=True,
                connector="gmail",
                action="external_write_ready",
                status="simulated_external_write_ready",
                output_ref=step.get("output_ref"),
                payload={
                    "ready": True,
                    "external_write": "gmail.send",
                    "execution_mode": execution_mode,
                    "message": "Approval and vault checks passed. Real Gmail send is intentionally not wired in this MVP.",
                },
            )

        # Live execution has a second hard guard. Even with the env guard set,
        # real Gmail send remains intentionally unwired until a dedicated Gmail
        # service/client is integrated and tested.
        if execution_mode == EXECUTION_MODE_LIVE_EXECUTE:
            if os.getenv(LIVE_GMAIL_ENV_GUARD) != "1":
                return WorkflowConnectorResult(
                    ok=False,
                    connector="gmail",
                    action="external_write_ready",
                    status="blocked_live_env_guard",
                    output_ref=step.get("output_ref"),
                    errors=[f"missing_env_guard:{LIVE_GMAIL_ENV_GUARD}=1"],
                    payload={
                        "ready": False,
                        "external_write": "gmail.send",
                        "execution_mode": execution_mode,
                    },
                )

            return WorkflowConnectorResult(
                ok=False,
                connector="gmail",
                action="external_write_ready",
                status="blocked_live_connector_not_implemented",
                output_ref=step.get("output_ref"),
                errors=["gmail_live_send_not_implemented"],
                payload={
                    "ready": False,
                    "external_write": "gmail.send",
                    "execution_mode": execution_mode,
                    "message": "Live Gmail send guard passed, but real Gmail send is not implemented in this MVP.",
                },
            )

        return WorkflowConnectorResult(
            ok=False,
            connector="gmail",
            action="external_write_ready",
            status="blocked_invalid_execution_mode",
            output_ref=step.get("output_ref"),
            errors=[f"invalid_execution_mode:{execution_mode}"],
        )
