"""Deterministic builders and legacy adapters for Department Pilot contracts."""

from __future__ import annotations

from typing import Any, Iterable, Optional

from backend.modules.aion_business.contracts.department_pilot import (
    BoardroomAssignmentAction,
    BoardroomAssignmentPackage,
    BoardroomHandbackSummary,
    BoardroomPackageApproval,
    ContextReference,
    ContractProvenance,
    DepartmentApprovalRecord,
    DepartmentArtifact,
    DepartmentConversationTurn,
    DepartmentExecutionReceipt,
    DepartmentIntelligencePatch,
    DepartmentPilotTask,
    DepartmentPilotWorkEnvelope,
    DepartmentTaskEvent,
    ProposedToolCall,
    RetrievedEvidence,
    canonical_contract_hash,
)


def _dump(value: Any) -> Any:
    return value.model_dump(mode="json") if hasattr(value, "model_dump") else value


def _hashed(
    model_type: type[Any],
    payload: dict[str, Any],
    hash_field: str,
    *excluded: str,
) -> dict[str, Any]:
    """Apply model defaults before hashing so saved/reloaded JSON remains valid."""

    seed = {**payload, hash_field: "sha256:pending"}
    normalized = model_type.model_construct(**seed).model_dump(mode="json")
    hash_payload = dict(normalized)
    hash_payload.pop(hash_field, None)
    for key in excluded:
        hash_payload.pop(key, None)
    normalized[hash_field] = canonical_contract_hash(hash_payload)
    return normalized


def create_provenance(
    *,
    created_by: str,
    created_at: str,
    source_system: str = "aion",
    source_record_id: str | None = None,
    source_hash: str | None = None,
    correlation_id: str | None = None,
) -> ContractProvenance:
    return ContractProvenance(
        created_by=created_by,
        created_at=created_at,
        source_system=source_system,
        source_record_id=source_record_id,
        source_hash=source_hash,
        correlation_id=correlation_id,
    )


def create_context_reference(**values: Any) -> ContextReference:
    return ContextReference(**values)


def create_assignment_package(
    *,
    package_id: str,
    workspace_id: str,
    business_id: str,
    boardroom_session_id: str,
    boardroom_decision_id: str,
    title: str,
    objective: str,
    department_id: str,
    actions: Iterable[BoardroomAssignmentAction | dict[str, Any]],
    provenance: ContractProvenance,
    context_refs: Iterable[ContextReference | dict[str, Any]] = (),
    constraints: Iterable[str] = (),
    status: str = "draft",
) -> BoardroomAssignmentPackage:
    payload = {
        "schema_version": "aion.department_pilot.boardroom_assignment_package.v1",
        "package_id": package_id,
        "workspace_id": workspace_id,
        "business_id": business_id,
        "boardroom_session_id": boardroom_session_id,
        "boardroom_decision_id": boardroom_decision_id,
        "title": title,
        "objective": objective,
        "department_id": department_id,
        "status": status,
        "actions": [_dump(item) for item in actions],
        "context_refs": [_dump(item) for item in context_refs],
        "constraints": list(constraints),
        "provenance": _dump(provenance),
        "approval": None,
    }
    payload["package_hash"] = canonical_contract_hash(
        {key: value for key, value in payload.items() if key != "approval"}
    )
    return BoardroomAssignmentPackage(**payload)


def approve_assignment_package(
    package: BoardroomAssignmentPackage,
    *,
    approval_id: str,
    approved_by: str,
    approved_at: str,
    notes: str | None = None,
) -> BoardroomAssignmentPackage:
    payload = package.model_dump(mode="json")
    payload["status"] = "approved"
    payload["approval"] = None
    payload.pop("package_hash", None)
    package_hash = canonical_contract_hash(
        {key: value for key, value in payload.items() if key != "approval"}
    )
    payload["package_hash"] = package_hash

    approval_payload = {
        "schema_version": "aion.department_pilot.package_approval.v1",
        "approval_id": approval_id,
        "package_id": package.package_id,
        "approved": True,
        "approved_by": approved_by,
        "approved_at": approved_at,
        "approved_package_hash": package_hash,
        "approval_scope": "boardroom_assignment_boundary",
        "notes": notes,
    }
    approval = BoardroomPackageApproval(
        **_hashed(BoardroomPackageApproval, approval_payload, "approval_hash")
    )
    payload["approval"] = approval.model_dump(mode="json")
    return BoardroomAssignmentPackage(**payload)


def create_task_from_package(
    package: BoardroomAssignmentPackage,
    *,
    action_id: str,
    task_id: str,
    pilot_id: str,
    assigned_at: str,
    provenance: ContractProvenance,
    dependency_task_ids: Iterable[str] = (),
) -> DepartmentPilotTask:
    if package.status not in {"approved", "routed"}:
        raise ValueError("department_task_requires_approved_boardroom_package")
    action = next((item for item in package.actions if item.action_id == action_id), None)
    if action is None:
        raise ValueError(f"assignment_action_not_found:{action_id}")

    payload = {
        "schema_version": "aion.department_pilot.task.v1",
        "task_id": task_id,
        "workspace_id": package.workspace_id,
        "business_id": package.business_id,
        "package_id": package.package_id,
        "package_hash": package.package_hash,
        "action_id": action.action_id,
        "department_id": package.department_id,
        "pilot_id": pilot_id,
        "title": action.title,
        "objective": action.objective,
        "capability": action.capability,
        "status": "queued",
        "priority": action.priority,
        "acceptance_criteria": list(action.acceptance_criteria),
        "dependency_task_ids": list(dependency_task_ids),
        "context_refs": [item.model_dump(mode="json") for item in package.context_refs],
        "approval_required": False,
        "assigned_at": assigned_at,
        "claimed_at": None,
        "started_at": None,
        "completed_at": None,
        "retry_count": 0,
        "max_retries": 3,
        "provenance": provenance.model_dump(mode="json"),
    }
    return DepartmentPilotTask(**_hashed(DepartmentPilotTask, payload, "task_hash"))


def adapt_legacy_department_queue_item(
    *,
    package: BoardroomAssignmentPackage,
    queue_item: dict[str, Any],
    assigned_at: str,
    created_by: str = "central_pilot_legacy_adapter",
) -> DepartmentPilotTask:
    """Adapt the existing v0 mission queue without creating a second queue authority."""

    if queue_item.get("business_id") != package.business_id:
        raise ValueError("legacy_queue_business_mismatch")
    if queue_item.get("department_id") != package.department_id:
        raise ValueError("legacy_queue_department_mismatch")
    action = next(
        (
            item
            for item in package.actions
            if item.action_id == queue_item.get("action_id")
            or item.capability == queue_item.get("capability")
        ),
        None,
    )
    if action is None:
        raise ValueError("legacy_queue_item_has_no_package_action")
    provenance = create_provenance(
        created_by=created_by,
        created_at=assigned_at,
        source_system="aion_mission_mode",
        source_record_id=queue_item.get("task_id"),
        source_hash=queue_item.get("queue_item_hash"),
        correlation_id=queue_item.get("mission_run_id"),
    )
    return create_task_from_package(
        package,
        action_id=action.action_id,
        task_id=str(queue_item.get("task_id") or action.action_id),
        pilot_id=f"{package.department_id}_pilot",
        assigned_at=assigned_at,
        provenance=provenance,
    )


_TASK_TRANSITIONS = {
    "queued": {"claimed", "cancelled"},
    "claimed": {"running", "blocked", "cancelled"},
    "running": {"waiting_approval", "blocked", "completed", "failed", "cancelled"},
    "waiting_approval": {"running", "blocked", "cancelled"},
    "blocked": {"queued", "retry_scheduled", "failed", "cancelled"},
    "retry_scheduled": {"queued", "failed", "cancelled"},
    "completed": set(),
    "failed": {"retry_scheduled", "cancelled"},
    "cancelled": set(),
}


def transition_department_task(
    task: DepartmentPilotTask,
    *,
    to_status: str,
    occurred_at: str,
) -> DepartmentPilotTask:
    if to_status not in _TASK_TRANSITIONS.get(task.status, set()):
        raise ValueError(f"invalid_department_task_transition:{task.status}->{to_status}")
    payload = task.model_dump(mode="json")
    payload["status"] = to_status
    if to_status == "claimed":
        payload["claimed_at"] = occurred_at
    if to_status == "running" and not payload.get("started_at"):
        payload["started_at"] = occurred_at
    if to_status == "retry_scheduled":
        payload["retry_count"] = int(payload.get("retry_count") or 0) + 1
    if to_status == "completed":
        payload["completed_at"] = occurred_at
    payload.pop("task_hash", None)
    return DepartmentPilotTask(**_hashed(DepartmentPilotTask, payload, "task_hash"))


def create_task_event(**values: Any) -> DepartmentTaskEvent:
    payload = {"schema_version": "aion.department_pilot.task_event.v1", **values}
    return DepartmentTaskEvent(**_hashed(DepartmentTaskEvent, payload, "event_hash"))


def create_conversation_turn(**values: Any) -> DepartmentConversationTurn:
    payload = {"schema_version": "aion.department_pilot.conversation_turn.v1", **values}
    payload["context_refs"] = [_dump(item) for item in payload.get("context_refs", [])]
    return DepartmentConversationTurn(
        **_hashed(DepartmentConversationTurn, payload, "turn_hash")
    )


def create_retrieved_evidence(**values: Any) -> RetrievedEvidence:
    payload = {"schema_version": "aion.department_pilot.retrieved_evidence.v1", **values}
    return RetrievedEvidence(
        **_hashed(RetrievedEvidence, payload, "retrieval_hash")
    )


def propose_tool_call(**values: Any) -> ProposedToolCall:
    payload = {"schema_version": "aion.department_pilot.proposed_tool_call.v1", **values}
    payload["payload_hash"] = canonical_contract_hash(payload.get("payload", {}))
    return ProposedToolCall(**_hashed(ProposedToolCall, payload, "proposal_hash"))


def create_approval_record(**values: Any) -> DepartmentApprovalRecord:
    payload = {"schema_version": "aion.department_pilot.approval_record.v1", **values}
    return DepartmentApprovalRecord(
        **_hashed(DepartmentApprovalRecord, payload, "approval_hash")
    )


def create_department_artifact(**values: Any) -> DepartmentArtifact:
    payload = {"schema_version": "aion.department_pilot.artifact.v1", **values}
    payload["provenance"] = _dump(payload["provenance"])
    return DepartmentArtifact(**payload)


def create_execution_receipt(**values: Any) -> DepartmentExecutionReceipt:
    payload = {"schema_version": "aion.department_pilot.execution_receipt.v1", **values}
    return DepartmentExecutionReceipt(
        **_hashed(DepartmentExecutionReceipt, payload, "receipt_hash")
    )


def adapt_legacy_capability_receipt(
    *,
    task: DepartmentPilotTask,
    legacy_receipt: dict[str, Any],
    receipt_id: str,
    completed_at: str,
) -> DepartmentExecutionReceipt:
    return create_execution_receipt(
        receipt_id=receipt_id,
        task_id=task.task_id,
        department_id=task.department_id,
        outcome="succeeded",
        started_at=None,
        completed_at=completed_at,
        requested_payload_hash=legacy_receipt.get("requested_payload_hash"),
        executed_payload_hash=legacy_receipt.get("executed_payload_hash"),
        before_state_hash=legacy_receipt.get("before_state_hash"),
        after_state_hash=legacy_receipt.get("after_state_hash"),
        artifact_ids=[],
        evidence_hashes=list(legacy_receipt.get("evidence_hashes") or []),
        approval_ids=[],
        error_code=None,
        error_message=None,
        rollback_available=bool(legacy_receipt.get("rollback_available")),
        rollback_instructions=legacy_receipt.get("rollback_instructions"),
        legacy_receipt_hash=legacy_receipt.get("receipt_hash"),
    )


def create_intelligence_patch(**values: Any) -> DepartmentIntelligencePatch:
    payload = {"schema_version": "aion.department_pilot.intelligence_patch.v1", **values}
    return DepartmentIntelligencePatch(
        **_hashed(DepartmentIntelligencePatch, payload, "patch_hash")
    )


def create_boardroom_handback(**values: Any) -> BoardroomHandbackSummary:
    payload = {"schema_version": "aion.department_pilot.boardroom_handback.v1", **values}
    return BoardroomHandbackSummary(
        **_hashed(BoardroomHandbackSummary, payload, "handback_hash")
    )


def create_work_envelope(
    *,
    package: BoardroomAssignmentPackage,
    task: DepartmentPilotTask,
    events: Iterable[DepartmentTaskEvent] = (),
    conversation: Iterable[DepartmentConversationTurn] = (),
    retrieved_evidence: Iterable[RetrievedEvidence] = (),
    proposed_tool_calls: Iterable[ProposedToolCall] = (),
    approvals: Iterable[DepartmentApprovalRecord] = (),
    artifacts: Iterable[DepartmentArtifact] = (),
    receipts: Iterable[DepartmentExecutionReceipt] = (),
    intelligence_patches: Iterable[DepartmentIntelligencePatch] = (),
    handback: Optional[BoardroomHandbackSummary] = None,
) -> DepartmentPilotWorkEnvelope:
    payload = {
        "schema_version": "aion.department_pilot.work_envelope.v1",
        "package": package.model_dump(mode="json"),
        "task": task.model_dump(mode="json"),
        "events": [_dump(item) for item in events],
        "conversation": [_dump(item) for item in conversation],
        "retrieved_evidence": [_dump(item) for item in retrieved_evidence],
        "proposed_tool_calls": [_dump(item) for item in proposed_tool_calls],
        "approvals": [_dump(item) for item in approvals],
        "artifacts": [_dump(item) for item in artifacts],
        "receipts": [_dump(item) for item in receipts],
        "intelligence_patches": [_dump(item) for item in intelligence_patches],
        "handback": _dump(handback) if handback else None,
    }
    return DepartmentPilotWorkEnvelope(
        **_hashed(DepartmentPilotWorkEnvelope, payload, "envelope_hash")
    )
