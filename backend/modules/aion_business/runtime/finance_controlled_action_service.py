"""Exact-payload proposal and approval gate for controlled Finance actions."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from backend.modules.aion_business.contracts.department_pilot import DepartmentPilotWorkEnvelope
from backend.modules.aion_business.runtime.department_pilot_contracts import create_approval_record, propose_tool_call
from backend.modules.aion_business.runtime.department_pilot_profiles import get_department_pilot_profile
from backend.modules.aion_business.runtime.department_pilot_repository import DepartmentPilotRepository
from backend.modules.aion_business.runtime.department_pilot_runtime import DepartmentPilotRuntime


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


class FinanceControlledActionService:
    """Stages actions safely; no connector write is enabled by this service."""

    def __init__(self, repository: DepartmentPilotRepository | None = None) -> None:
        self.repository = repository or DepartmentPilotRepository()
        self.runtime = DepartmentPilotRuntime(self.repository)

    def propose(self, workspace_id: str, task_id: str, *, tool_call_id: str,
                tool_name: str, provider: str, payload: dict[str, Any], rationale: str,
                proposed_by: str = "finance_pilot", proposed_at: str | None = None) -> DepartmentPilotWorkEnvelope:
        occurred_at = proposed_at or _now()
        envelope = self.repository.load(workspace_id, "finance", task_id)
        self._assert_workspace(envelope, workspace_id)
        if envelope.task.status not in {"queued", "claimed", "running"}:
            raise ValueError(f"finance_proposal_task_not_stagable:{envelope.task.status}")
        if any(item.tool_call_id == tool_call_id for item in envelope.proposed_tool_calls):
            raise ValueError("finance_proposal_tool_call_id_already_exists")
        allowed = set((get_department_pilot_profile("finance") or {}).get("tool_permissions", {}).get("staged_external") or [])
        if tool_name not in allowed:
            raise PermissionError(f"finance_staged_tool_not_permitted:{tool_name}")
        if envelope.task.status == "queued":
            envelope = self.runtime.transition(workspace_id=workspace_id, department_id="finance", task_id=task_id, to_status="claimed", occurred_at=occurred_at, actor_id=proposed_by, event_id=f"{tool_call_id}-claimed", message="Finance Pilot claimed the task to prepare a controlled proposal.", progress_percent=10)
        if envelope.task.status == "claimed":
            envelope = self.runtime.transition(workspace_id=workspace_id, department_id="finance", task_id=task_id, to_status="running", occurred_at=occurred_at, actor_id=proposed_by, event_id=f"{tool_call_id}-started", message="Finance Pilot is preparing an exact-payload proposal.", progress_percent=25)
        proposal = propose_tool_call(
            tool_call_id=tool_call_id, task_id=task_id, department_id="finance",
            capability=envelope.task.capability, tool_name=tool_name, provider=provider,
            tool_mode="staged_external", payload=payload, rationale=rationale,
            external_side_effect=True, approval_required=True,
            proposed_at=occurred_at, proposed_by=proposed_by,
        )
        envelope = self.runtime.attach_proposed_tool_call(workspace_id=workspace_id, department_id="finance", task_id=task_id, proposal=proposal)
        return self.runtime.transition(workspace_id=workspace_id, department_id="finance", task_id=task_id, to_status="waiting_approval", occurred_at=occurred_at, actor_id=proposed_by, event_id=f"{tool_call_id}-approval-requested", message="Exact payload is waiting for founder approval. No external action has occurred.", progress_percent=50, data={"tool_call_id": tool_call_id, "payload_hash": proposal.payload_hash, "tool_name": tool_name})

    def decide(self, workspace_id: str, task_id: str, tool_call_id: str, *, approval_id: str,
               approved: bool, decided_by: str, decided_at: str | None = None,
               reason: str | None = None, decided_payload_hash: str | None = None) -> DepartmentPilotWorkEnvelope:
        occurred_at = decided_at or _now()
        envelope = self.repository.load(workspace_id, "finance", task_id)
        self._assert_workspace(envelope, workspace_id)
        if envelope.task.status != "waiting_approval":
            raise ValueError(f"finance_proposal_not_waiting_approval:{envelope.task.status}")
        proposal = next((item for item in envelope.proposed_tool_calls if item.tool_call_id == tool_call_id), None)
        if proposal is None:
            raise FileNotFoundError(f"Finance proposal not found: {tool_call_id}")
        if any(item.tool_call_id == tool_call_id for item in envelope.approvals):
            raise ValueError("finance_proposal_already_decided")
        if approved and decided_payload_hash != proposal.payload_hash:
            raise ValueError("approved_payload_hash_mismatch")
        approval = create_approval_record(
            approval_id=approval_id, task_id=task_id, tool_call_id=tool_call_id,
            department_id="finance", status="approved" if approved else "rejected",
            requested_payload_hash=proposal.payload_hash,
            decided_payload_hash=proposal.payload_hash if approved else None,
            requested_by=proposal.proposed_by, requested_at=proposal.proposed_at,
            decided_by=decided_by, decided_at=occurred_at, expires_at=None, reason=reason,
        )
        envelope = self.runtime.attach_approval(workspace_id=workspace_id, department_id="finance", task_id=task_id, approval=approval)
        return self.runtime.transition(
            workspace_id=workspace_id, department_id="finance", task_id=task_id,
            to_status="running" if approved else "blocked", occurred_at=occurred_at,
            actor_id=decided_by, event_id=f"{approval_id}-decision",
            message=("Exact payload approved; execution still requires an enabled live connector permission." if approved else "Finance proposal rejected; no external action occurred."),
            progress_percent=60 if approved else None,
            data={"approval_id": approval_id, "tool_call_id": tool_call_id, "payload_hash": proposal.payload_hash},
        )

    def execution_readiness(self, workspace_id: str, task_id: str, tool_call_id: str) -> dict[str, Any]:
        envelope = self.repository.load(workspace_id, "finance", task_id)
        self._assert_workspace(envelope, workspace_id)
        proposal = next((item for item in envelope.proposed_tool_calls if item.tool_call_id == tool_call_id), None)
        if proposal is None:
            raise FileNotFoundError(f"Finance proposal not found: {tool_call_id}")
        approval = next((item for item in reversed(envelope.approvals) if item.tool_call_id == tool_call_id and item.status == "approved"), None)
        if approval is None or approval.decided_payload_hash != proposal.payload_hash:
            raise PermissionError("exact_payload_approval_required")
        live = set((get_department_pilot_profile("finance") or {}).get("tool_permissions", {}).get("approved_live_external") or [])
        if proposal.tool_name not in live:
            return {"ready": False, "code": "live_connector_permission_not_enabled", "external_action_performed": False, "tool_call_id": tool_call_id, "payload_hash": proposal.payload_hash}
        return {"ready": True, "code": "exact_payload_approved", "external_action_performed": False, "tool_call_id": tool_call_id, "payload_hash": proposal.payload_hash}

    @staticmethod
    def _assert_workspace(envelope: DepartmentPilotWorkEnvelope, workspace_id: str) -> None:
        if envelope.task.workspace_id != workspace_id or envelope.task.business_id != workspace_id:
            raise PermissionError("finance_controlled_action_business_isolation_violation")
