"""Durable orchestration shell shared by all specialist Department Pilots."""

from __future__ import annotations

from typing import Any

from backend.modules.aion_business.contracts.department_pilot import (
    BoardroomAssignmentPackage,
    BoardroomHandbackSummary,
    ContractProvenance,
    DepartmentArtifact,
    DepartmentConversationTurn,
    DepartmentExecutionReceipt,
    DepartmentIntelligencePatch,
    DepartmentPilotWorkEnvelope,
    DepartmentApprovalRecord,
    ProposedToolCall,
    RetrievedEvidence,
)
from backend.modules.aion_business.runtime.department_pilot_contracts import (
    create_conversation_turn,
    create_task_event,
    create_task_from_package,
    create_work_envelope,
    transition_department_task,
)
from backend.modules.aion_business.runtime.department_pilot_repository import (
    DepartmentPilotRepository,
)


_EVENT_BY_STATUS = {
    "claimed": "claimed",
    "running": "started",
    "waiting_approval": "approval_requested",
    "blocked": "blocked",
    "retry_scheduled": "retry_scheduled",
    "completed": "completed",
    "failed": "failed",
    "cancelled": "cancelled",
    "queued": "progress",
}


class DepartmentPilotRuntime:
    def __init__(self, repository: DepartmentPilotRepository | None = None) -> None:
        self.repository = repository or DepartmentPilotRepository()

    def enqueue_approved_action(
        self,
        *,
        package: BoardroomAssignmentPackage,
        action_id: str,
        task_id: str,
        pilot_id: str,
        assigned_at: str,
        provenance: ContractProvenance,
        created_event_id: str,
    ) -> DepartmentPilotWorkEnvelope:
        task = create_task_from_package(
            package,
            action_id=action_id,
            task_id=task_id,
            pilot_id=pilot_id,
            assigned_at=assigned_at,
            provenance=provenance,
        )
        event = create_task_event(
            event_id=created_event_id,
            task_id=task.task_id,
            department_id=task.department_id,
            event_type="created",
            occurred_at=assigned_at,
            actor_id="central_pilot",
            from_status=None,
            to_status="queued",
            progress_percent=0,
            message="Approved Boardroom action routed to specialist Pilot.",
        )
        envelope = create_work_envelope(package=package, task=task, events=[event])
        self.repository.create(envelope)
        return envelope

    def transition(
        self,
        *,
        workspace_id: str,
        department_id: str,
        task_id: str,
        to_status: str,
        occurred_at: str,
        actor_id: str,
        event_id: str,
        message: str | None = None,
        progress_percent: int | None = None,
        data: dict[str, Any] | None = None,
    ) -> DepartmentPilotWorkEnvelope:
        current = self.repository.load(workspace_id, department_id, task_id)
        previous_status = current.task.status
        task = transition_department_task(
            current.task, to_status=to_status, occurred_at=occurred_at
        )
        previous_event_hash = current.events[-1].event_hash if current.events else None
        event = create_task_event(
            event_id=event_id,
            task_id=task.task_id,
            department_id=task.department_id,
            event_type=_EVENT_BY_STATUS[to_status],
            occurred_at=occurred_at,
            actor_id=actor_id,
            from_status=previous_status,
            to_status=to_status,
            progress_percent=progress_percent,
            message=message,
            data=data or {},
            previous_event_hash=previous_event_hash,
        )
        updated = create_work_envelope(
            package=current.package,
            task=task,
            events=[*current.events, event],
            conversation=current.conversation,
            retrieved_evidence=current.retrieved_evidence,
            proposed_tool_calls=current.proposed_tool_calls,
            approvals=current.approvals,
            artifacts=current.artifacts,
            receipts=current.receipts,
            intelligence_patches=current.intelligence_patches,
            handback=current.handback,
        )
        self.repository.save(updated, expected_previous_hash=current.envelope_hash)
        return updated

    def append_conversation_turn(
        self,
        *,
        workspace_id: str,
        department_id: str,
        task_id: str,
        turn_id: str,
        role: str,
        content: str,
        created_at: str,
        actor_id: str | None = None,
        tool_call_id: str | None = None,
    ) -> DepartmentPilotWorkEnvelope:
        current = self.repository.load(workspace_id, department_id, task_id)
        previous_turn_hash = current.conversation[-1].turn_hash if current.conversation else None
        turn = create_conversation_turn(
            turn_id=turn_id,
            task_id=task_id,
            department_id=department_id,
            role=role,
            content=content,
            created_at=created_at,
            actor_id=actor_id,
            context_refs=[],
            tool_call_id=tool_call_id,
            previous_turn_hash=previous_turn_hash,
        )
        updated = create_work_envelope(
            package=current.package,
            task=current.task,
            events=current.events,
            conversation=[*current.conversation, turn],
            retrieved_evidence=current.retrieved_evidence,
            proposed_tool_calls=current.proposed_tool_calls,
            approvals=current.approvals,
            artifacts=current.artifacts,
            receipts=current.receipts,
            intelligence_patches=current.intelligence_patches,
            handback=current.handback,
        )
        self.repository.save(updated, expected_previous_hash=current.envelope_hash)
        return updated

    def attach_retrieved_evidence(
        self,
        *,
        workspace_id: str,
        department_id: str,
        task_id: str,
        evidence: list[RetrievedEvidence],
    ) -> DepartmentPilotWorkEnvelope:
        current = self.repository.load(workspace_id, department_id, task_id)
        known_ids = {item.evidence_id for item in current.retrieved_evidence}
        if any(item.evidence_id in known_ids for item in evidence):
            raise ValueError("retrieved_evidence_id_already_attached")
        updated = create_work_envelope(
            package=current.package,
            task=current.task,
            events=current.events,
            conversation=current.conversation,
            retrieved_evidence=[*current.retrieved_evidence, *evidence],
            proposed_tool_calls=current.proposed_tool_calls,
            approvals=current.approvals,
            artifacts=current.artifacts,
            receipts=current.receipts,
            intelligence_patches=current.intelligence_patches,
            handback=current.handback,
        )
        self.repository.save(updated, expected_previous_hash=current.envelope_hash)
        return updated

    def attach_proposed_tool_call(
        self,
        *,
        workspace_id: str,
        department_id: str,
        task_id: str,
        proposal: ProposedToolCall,
    ) -> DepartmentPilotWorkEnvelope:
        current = self.repository.load(workspace_id, department_id, task_id)
        if current.task.status not in {"running", "waiting_approval"}:
            raise ValueError(f"tool_proposal_not_allowed_from_status:{current.task.status}")
        if any(item.tool_call_id == proposal.tool_call_id for item in current.proposed_tool_calls):
            raise ValueError("proposed_tool_call_id_already_attached")
        updated = create_work_envelope(
            package=current.package, task=current.task, events=current.events,
            conversation=current.conversation, retrieved_evidence=current.retrieved_evidence,
            proposed_tool_calls=[*current.proposed_tool_calls, proposal],
            approvals=current.approvals, artifacts=current.artifacts,
            receipts=current.receipts, intelligence_patches=current.intelligence_patches,
            handback=current.handback,
        )
        self.repository.save(updated, expected_previous_hash=current.envelope_hash)
        return updated

    def attach_approval(
        self,
        *,
        workspace_id: str,
        department_id: str,
        task_id: str,
        approval: DepartmentApprovalRecord,
    ) -> DepartmentPilotWorkEnvelope:
        current = self.repository.load(workspace_id, department_id, task_id)
        if current.task.status != "waiting_approval":
            raise ValueError(f"approval_not_allowed_from_status:{current.task.status}")
        if any(item.approval_id == approval.approval_id for item in current.approvals):
            raise ValueError("approval_id_already_attached")
        updated = create_work_envelope(
            package=current.package, task=current.task, events=current.events,
            conversation=current.conversation, retrieved_evidence=current.retrieved_evidence,
            proposed_tool_calls=current.proposed_tool_calls,
            approvals=[*current.approvals, approval], artifacts=current.artifacts,
            receipts=current.receipts, intelligence_patches=current.intelligence_patches,
            handback=current.handback,
        )
        self.repository.save(updated, expected_previous_hash=current.envelope_hash)
        return updated

    def complete(
        self,
        *,
        workspace_id: str,
        department_id: str,
        task_id: str,
        completed_at: str,
        actor_id: str,
        event_id: str,
        receipt: DepartmentExecutionReceipt,
        handback: BoardroomHandbackSummary,
        artifacts: list[DepartmentArtifact] | None = None,
        intelligence_patches: list[DepartmentIntelligencePatch] | None = None,
    ) -> DepartmentPilotWorkEnvelope:
        current = self.repository.load(workspace_id, department_id, task_id)
        task = transition_department_task(
            current.task, to_status="completed", occurred_at=completed_at
        )
        event = create_task_event(
            event_id=event_id,
            task_id=task.task_id,
            department_id=task.department_id,
            event_type="completed",
            occurred_at=completed_at,
            actor_id=actor_id,
            from_status=current.task.status,
            to_status="completed",
            progress_percent=100,
            message="Department task completed and prepared for Boardroom handback.",
            previous_event_hash=current.events[-1].event_hash if current.events else None,
        )
        updated = create_work_envelope(
            package=current.package,
            task=task,
            events=[*current.events, event],
            conversation=current.conversation,
            retrieved_evidence=current.retrieved_evidence,
            proposed_tool_calls=current.proposed_tool_calls,
            approvals=current.approvals,
            artifacts=[*current.artifacts, *(artifacts or [])],
            receipts=[*current.receipts, receipt],
            intelligence_patches=[
                *current.intelligence_patches,
                *(intelligence_patches or []),
            ],
            handback=handback,
        )
        self.repository.save(updated, expected_previous_hash=current.envelope_hash)
        return updated
