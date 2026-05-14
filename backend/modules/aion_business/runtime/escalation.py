from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

from backend.modules.aion_business.contracts.agents import AgentSpec
from backend.modules.aion_business.contracts.roles import RoleSpec
from backend.modules.aion_business.contracts.tasks import TaskRecord
from backend.modules.aion_business.runtime.audit_log import AuditLog
from backend.modules.aion_business.runtime.task_record_repository import TaskRecordRepository


@dataclass(slots=True)
class EscalationResult:
    ok: bool
    task_id: str
    from_status: str
    to_status: str
    escalation_reason: str
    escalation_target: Optional[str] = None
    error_code: Optional[str] = None


class EscalationHandler:
    """
    Minimal escalation handler for Aion Business v1.

    Responsibilities:
    - mark task escalated
    - attach escalation reason/output
    - emit audit event
    - keep escalation target symbolic for now
    """

    def __init__(
        self,
        *,
        task_repository: Optional[TaskRecordRepository] = None,
        audit_log: Optional[AuditLog] = None,
    ):
        self.task_repository = task_repository or TaskRecordRepository()
        self.audit_log = audit_log or AuditLog()

    def escalate_task(
        self,
        *,
        workspace_id: str,
        task: TaskRecord,
        role: RoleSpec,
        agent: Optional[AgentSpec],
        reason: str,
        escalation_target: Optional[str] = None,
        details: Optional[Dict[str, str]] = None,
    ) -> EscalationResult:
        if task.workspace_id != workspace_id:
            return EscalationResult(
                ok=False,
                task_id=task.id,
                from_status=task.status,
                to_status=task.status,
                escalation_reason=reason,
                escalation_target=escalation_target,
                error_code="workspace_task_mismatch",
            )

        previous_status = task.status
        task.status = "escalated"
        task.outputs["escalation"] = {
            "reason": reason,
            "target": escalation_target,
            "details": details or {},
        }
        self.task_repository.save(task)

        self.audit_log.log_event(
            workspace_id=workspace_id,
            event_type="task_escalated",
            summary=f"Task escalated: {reason}",
            role_id=role.id,
            agent_id=agent.id if agent else None,
            task_id=task.id,
            payload={
                "from_status": previous_status,
                "to_status": task.status,
                "reason": reason,
                "target": escalation_target,
                "details": details or {},
            },
            tags=["task", "escalation"],
        )

        return EscalationResult(
            ok=True,
            task_id=task.id,
            from_status=previous_status,
            to_status=task.status,
            escalation_reason=reason,
            escalation_target=escalation_target,
            error_code=None,
        )