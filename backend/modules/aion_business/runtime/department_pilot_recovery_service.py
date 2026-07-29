"""Controlled retry, cancellation and diagnostics for Department Pilot tasks."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from backend.modules.aion_business.runtime.department_pilot_repository import DepartmentPilotRepository
from backend.modules.aion_business.runtime.department_pilot_runtime import DepartmentPilotRuntime


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


class DepartmentPilotRecoveryService:
    def __init__(self, repository: DepartmentPilotRepository | None = None) -> None:
        self.repository = repository or DepartmentPilotRepository()
        self.runtime = DepartmentPilotRuntime(self.repository)

    def retry(self, workspace_id: str, department_id: str, task_id: str, *, actor_id: str,
              occurred_at: str | None = None, reason: str | None = None):
        envelope = self._load_isolated(workspace_id, department_id, task_id)
        if envelope.task.status not in {"failed", "blocked"}:
            raise ValueError(f"department_task_not_retryable:{envelope.task.status}")
        if envelope.task.retry_count >= envelope.task.max_retries:
            raise ValueError("department_task_retry_limit_reached")
        at = occurred_at or _now()
        scheduled = self.runtime.transition(
            workspace_id=workspace_id, department_id=department_id, task_id=task_id,
            to_status="retry_scheduled", occurred_at=at, actor_id=actor_id,
            event_id=f"{task_id}-retry-{envelope.task.retry_count + 1}",
            message=reason or "Task retry scheduled after a controlled review.",
            data={"retry_number": envelope.task.retry_count + 1},
        )
        return self.runtime.transition(
            workspace_id=workspace_id, department_id=department_id, task_id=task_id,
            to_status="queued", occurred_at=at, actor_id=actor_id,
            event_id=f"{task_id}-recovered-{scheduled.task.retry_count}",
            message="Task recovered to the specialist queue; no external action was repeated.",
            progress_percent=0,
        )

    def cancel(self, workspace_id: str, department_id: str, task_id: str, *, actor_id: str,
               occurred_at: str | None = None, reason: str | None = None):
        envelope = self._load_isolated(workspace_id, department_id, task_id)
        if envelope.task.status in {"completed", "cancelled"}:
            raise ValueError(f"department_task_not_cancellable:{envelope.task.status}")
        return self.runtime.transition(
            workspace_id=workspace_id, department_id=department_id, task_id=task_id,
            to_status="cancelled", occurred_at=occurred_at or _now(), actor_id=actor_id,
            event_id=f"{task_id}-cancelled-{len(envelope.events) + 1}",
            message=reason or "Task cancelled by an authorised operator.",
            data={"external_action_replayed": False},
        )

    def diagnostics(self, workspace_id: str, department_id: str, task_id: str) -> dict[str, Any]:
        envelope = self._load_isolated(workspace_id, department_id, task_id)
        failures = [event for event in envelope.events if event.event_type == "failed"]
        last = envelope.events[-1] if envelope.events else None
        return {
            "schema_version": "aion.department_pilot.diagnostics.v1",
            "workspace_id": workspace_id,
            "department_id": department_id,
            "task_id": task_id,
            "status": envelope.task.status,
            "retry_count": envelope.task.retry_count,
            "max_retries": envelope.task.max_retries,
            "retry_available": envelope.task.status in {"failed", "blocked"}
            and envelope.task.retry_count < envelope.task.max_retries,
            "cancel_available": envelope.task.status not in {"completed", "cancelled"},
            "failure_count": len(failures),
            "latest_failure": failures[-1].model_dump(mode="json") if failures else None,
            "latest_event": last.model_dump(mode="json") if last else None,
            "proposal_count": len(envelope.proposed_tool_calls),
            "approval_count": len(envelope.approvals),
            "receipt_count": len(envelope.receipts),
            "envelope_hash": envelope.envelope_hash,
        }

    def _load_isolated(self, workspace_id: str, department_id: str, task_id: str):
        envelope = self.repository.load(workspace_id, department_id, task_id)
        if envelope.task.workspace_id != workspace_id or envelope.task.business_id != workspace_id:
            raise PermissionError("department_task_business_isolation_violation")
        if envelope.task.department_id != department_id:
            raise PermissionError("department_task_department_isolation_violation")
        return envelope
